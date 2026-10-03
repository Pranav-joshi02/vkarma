"""
Geospatial Building Discovery & Actual Name Extraction Engine
Queries Overture Maps for building footprints and OpenStreetMap / Overpass API
for real building names within any user-selected bounding box.

Naming priority:
  1. Overture names.primary
  2. OSM name
  3. OSM name:en
  4. OSM official_name
  5. OSM addr:housename
  6. Synthetic area-based name: "<AREA_NAME> Building XX"

Data flow:
  User selects area → Get BBOX → Determine locality/area name →
  Query Overture Buildings → Query OSM named buildings →
  Spatially match OSM ↔ Overture → Assign real or synthetic names →
  Display on map
"""

import math
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("building_discovery")

# ---------------------------------------------------------------------------
# Overture Maps API helpers
# ---------------------------------------------------------------------------

OVERTURE_API_URL = "https://overturemaps.xyz/buildings"


def _fetch_overture_buildings(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float
) -> List[Dict[str, Any]]:
    """
    Fetches building footprints from the Overture Maps API.
    Returns a list of dicts with id, name (if available), centroid, polygon coords.
    """
    try:
        params = {
            "bbox": f"{min_lng},{min_lat},{max_lng},{max_lat}",
            "format": "geojson",
        }
        headers = {"User-Agent": "VKarma-Cadastral3D/1.0"}
        resp = requests.get(OVERTURE_API_URL, params=params, headers=headers, timeout=10)

        if resp.status_code != 200 or len(resp.content) < 100:
            logger.warning(f"Overture API returned status {resp.status_code}")
            return []

        data = resp.json()
        features = data.get("features", [])
        buildings = []

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            # Extract Overture primary name
            overture_name = None
            names = props.get("names", {})
            if isinstance(names, dict):
                overture_name = names.get("primary", None)
            elif isinstance(names, str):
                overture_name = names

            # Parse polygon coordinates
            coords_raw = geom.get("coordinates", [])
            poly_coords = []
            if geom.get("type") == "Polygon" and len(coords_raw) > 0:
                # GeoJSON Polygon: first ring is exterior
                for pt in coords_raw[0]:
                    if len(pt) >= 2:
                        poly_coords.append((pt[1], pt[0]))  # (lat, lng)
            elif geom.get("type") == "MultiPolygon" and len(coords_raw) > 0:
                for pt in coords_raw[0][0]:
                    if len(pt) >= 2:
                        poly_coords.append((pt[1], pt[0]))

            if len(poly_coords) < 3:
                continue

            # Centroid
            c_lat = sum(p[0] for p in poly_coords) / len(poly_coords)
            c_lng = sum(p[1] for p in poly_coords) / len(poly_coords)

            overture_id = props.get("id", feat.get("id", f"overture_{len(buildings)}"))

            # Height and levels from Overture
            height = props.get("height", None)
            levels = props.get("num_floors", props.get("building:levels", None))

            buildings.append({
                "_source_api": "overture",
                "_overture_id": str(overture_id),
                "_overture_name": overture_name,
                "_poly_coords": poly_coords,
                "_centroid": (round(c_lat, 6), round(c_lng, 6)),
                "_height": height,
                "_levels": levels,
                "_props": props,
            })

        logger.info(f"Overture returned {len(buildings)} building footprints.")
        return buildings

    except Exception as e:
        logger.warning(f"Failed to fetch Overture buildings: {e}")
        return []


# ---------------------------------------------------------------------------
# OSM / Overpass API helpers
# ---------------------------------------------------------------------------

OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"


def _fetch_osm_buildings_overpass(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float
) -> List[Dict[str, Any]]:
    """
    Fetches building footprints and names from OSM via the Overpass API.
    Returns a list of dicts with id, tags, centroid, polygon coords.
    """
    query = f"""
    [out:json][timeout:10];
    (
      way["building"]({min_lat},{min_lng},{max_lat},{max_lng});
      relation["building"]({min_lat},{min_lng},{max_lat},{max_lng});
    );
    out body;
    >;
    out skel qt;
    """

    try:
        resp = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            headers={"User-Agent": "VKarma-Cadastral3D/1.0"},
            timeout=12,
        )

        if resp.status_code != 200:
            logger.warning(f"Overpass API returned status {resp.status_code}")
            return []

        data = resp.json()
        elements = data.get("elements", [])

        # Build node lookup
        nodes: Dict[int, Tuple[float, float]] = {}
        for el in elements:
            if el.get("type") == "node":
                nodes[el["id"]] = (el["lat"], el["lon"])

        buildings = []
        for el in elements:
            if el.get("type") not in ("way", "relation"):
                continue
            tags = el.get("tags", {})
            if "building" not in tags and "building:part" not in tags:
                continue

            # Resolve polygon coordinates
            poly_coords = []
            if el.get("type") == "way":
                for nd_id in el.get("nodes", []):
                    if nd_id in nodes:
                        poly_coords.append(nodes[nd_id])
            elif el.get("type") == "relation":
                for member in el.get("members", []):
                    if member.get("type") == "node" and member.get("ref") in nodes:
                        poly_coords.append(nodes[member["ref"]])

            if len(poly_coords) < 3:
                continue

            c_lat = sum(p[0] for p in poly_coords) / len(poly_coords)
            c_lng = sum(p[1] for p in poly_coords) / len(poly_coords)

            buildings.append({
                "_source_api": "osm",
                "_osm_id": str(el["id"]),
                "_tags": tags,
                "_poly_coords": poly_coords,
                "_centroid": (round(c_lat, 6), round(c_lng, 6)),
            })

        logger.info(f"Overpass returned {len(buildings)} OSM building footprints.")
        return buildings

    except Exception as e:
        logger.warning(f"Failed to fetch OSM buildings via Overpass: {e}")
        return []


def _fetch_osm_buildings_api06(
    min_lat: float, min_lng: float, max_lat: float, max_lng: float
) -> List[Dict[str, Any]]:
    """
    Fallback: Fetches buildings from the OSM 0.6 Map API (XML).
    Used when Overpass is unreachable.
    """
    import xml.etree.ElementTree as ET

    osm_url = f"https://api.openstreetmap.org/api/0.6/map?bbox={min_lng},{min_lat},{max_lng},{max_lat}"
    headers = {"User-Agent": "VKarma-Cadastral3D/1.0"}

    try:
        resp = requests.get(osm_url, headers=headers, timeout=8)
        if resp.status_code != 200 or len(resp.content) < 500:
            return []

        root = ET.fromstring(resp.content)
        nodes: Dict[str, Tuple[float, float]] = {}
        for node in root.findall(".//node"):
            n_id = node.attrib["id"]
            nodes[n_id] = (float(node.attrib["lat"]), float(node.attrib["lon"]))

        buildings = []
        for way in root.findall(".//way"):
            tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
            if "building" not in tags and "building:part" not in tags:
                continue

            nd_refs = [nd.attrib["ref"] for nd in way.findall("nd")]
            poly_coords = [nodes[ref] for ref in nd_refs if ref in nodes]
            if len(poly_coords) < 3:
                continue

            c_lat = sum(p[0] for p in poly_coords) / len(poly_coords)
            c_lng = sum(p[1] for p in poly_coords) / len(poly_coords)

            buildings.append({
                "_source_api": "osm",
                "_osm_id": way.attrib["id"],
                "_tags": tags,
                "_poly_coords": poly_coords,
                "_centroid": (round(c_lat, 6), round(c_lng, 6)),
            })

        logger.info(f"OSM API 0.6 returned {len(buildings)} building footprints.")
        return buildings

    except Exception as e:
        logger.warning(f"Failed to fetch OSM buildings via API 0.6: {e}")
        return []


# ---------------------------------------------------------------------------
# Locality / area name detection
# ---------------------------------------------------------------------------

def _detect_area_name(
    center_lat: float, center_lng: float, provided_area_name: Optional[str] = None
) -> str:
    """
    Determines the best available locality name for synthetic naming.
    Priority:
      1. User-provided area name (if specific enough)
      2. OSM Nominatim reverse geocoding (suburb/neighbourhood)
      3. City name
      4. Fallback: "Selected Area"
    """
    # 1. Use provided name if it looks like a real locality
    if provided_area_name:
        cleaned = provided_area_name.strip()
        # Skip overly generic names
        generic_patterns = [
            "survey area", "custom survey area", "selected area",
            "custom area", "urban zone",
        ]
        if cleaned and cleaned.lower() not in generic_patterns:
            # Extract just the locality part if it's a compound name like "Hinjawadi, Pune"
            parts = [p.strip() for p in cleaned.split(",")]
            # Use the first (most specific) part
            locality = parts[0]
            # Remove parenthetical coordinates
            if "(" in locality:
                locality = locality[:locality.index("(")].strip()
            if locality:
                return locality

    # 2. Try Nominatim reverse geocoding
    try:
        url = (
            f"https://nominatim.openstreetmap.org/reverse"
            f"?format=json&lat={center_lat}&lon={center_lng}&zoom=16"
        )
        headers = {"User-Agent": "VKarma-Cadastral3D/1.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.ok:
            data = resp.json()
            addr = data.get("address", {})

            # Try suburb/neighbourhood first (most specific locality)
            locality = (
                addr.get("suburb")
                or addr.get("neighbourhood")
                or addr.get("city_district")
                or addr.get("village")
                or addr.get("town")
            )
            if locality:
                return locality.strip()

            # 3. Fall back to city
            city = addr.get("city") or addr.get("county") or addr.get("state")
            if city:
                return city.strip()

    except Exception as e:
        logger.warning(f"Nominatim reverse geocoding failed: {e}")

    # 4. Absolute fallback
    return "Selected Area"


# ---------------------------------------------------------------------------
# Spatial matching: Overture ↔ OSM
# ---------------------------------------------------------------------------

def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Returns approximate distance in meters between two lat/lng points."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_osm_name(tags: Dict[str, str]) -> Optional[str]:
    """
    Extracts the best real name from OSM tags following priority:
      OSM name → name:en → official_name → addr:housename
    """
    return (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("official_name")
        or tags.get("addr:housename")
    )


def _infer_building_meta(tags: Dict[str, str], b_type: str) -> Tuple[str, int, float]:
    """Infers building usage type, estimated storeys, and height from OSM tags."""
    floors = 7
    if "building:levels" in tags:
        try:
            floors = max(2, int(tags["building:levels"]))
        except ValueError:
            pass

    height = round(floors * 3.2, 1)
    if "height" in tags:
        try:
            height = float(tags["height"].replace("m", "").strip())
            floors = max(2, int(round(height / 3.2)))
        except ValueError:
            pass

    if any(k in tags for k in ["office", "commercial"]) or b_type in ["office", "commercial"]:
        usage = "Commercial"
    elif any(k in tags for k in ["residential", "apartments"]) or b_type in ["apartments", "residential"]:
        usage = "Residential"
    elif "hotel" in tags or b_type == "hotel":
        usage = "Hospitality"
    elif any(k in tags for k in ["retail", "shop", "mall"]) or b_type in ["retail", "supermarket"]:
        usage = "Retail"
    elif "amenity" in tags or b_type in ["civic", "public", "school", "hospital"]:
        usage = "Institutional"
    else:
        usage = "Commercial"

    return usage, floors, height


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def discover_buildings_in_bbox(
    min_lat: float,
    min_lng: float,
    max_lat: float,
    max_lng: float,
    max_buildings: int = 40,
    area_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Discovers all buildings present in the geographic bounding box:

    1. Queries Overture Maps for building footprints.
    2. Queries OSM / Overpass for real building names.
    3. Spatially matches OSM data onto Overture footprints.
    4. Assigns real names where available, synthetic area-based names otherwise.

    Returns a list of building dicts ready for frontend display.
    """
    center_lat = (min_lat + max_lat) / 2.0
    center_lng = (min_lng + max_lng) / 2.0

    # Step 1: Determine locality/area name for synthetic naming
    locality = _detect_area_name(center_lat, center_lng, area_name)
    logger.info(f"Area name resolved to: '{locality}'")

    # Step 2: Fetch Overture building footprints
    overture_buildings = _fetch_overture_buildings(min_lat, min_lng, max_lat, max_lng)

    # Step 3: Fetch OSM buildings (Overpass preferred, API 0.6 fallback)
    osm_buildings = _fetch_osm_buildings_overpass(min_lat, min_lng, max_lat, max_lng)
    if not osm_buildings:
        osm_buildings = _fetch_osm_buildings_api06(min_lat, min_lng, max_lat, max_lng)

    # Step 4: Build unified building list
    # If Overture has data, use Overture footprints as the base and match OSM names onto them.
    # If Overture is unavailable, use OSM buildings directly.
    if overture_buildings:
        unified = _merge_overture_with_osm(overture_buildings, osm_buildings)
    elif osm_buildings:
        unified = _build_from_osm_only(osm_buildings)
    else:
        # Both APIs failed — return empty list, handled cleanly by the frontend
        logger.warning("Both Overture and OSM returned no buildings.")
        return []

    # Step 5: Assign final names (real or synthetic) and build output
    result = _assign_names_and_build_output(unified, locality)

    # Sort: real-named buildings first, then synthetic
    result.sort(key=lambda b: (b["name_source"] == "synthetic", b["name"]))

    return result[:max_buildings]


def _merge_overture_with_osm(
    overture_buildings: List[Dict[str, Any]],
    osm_buildings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merges Overture footprints with OSM data.
    For each Overture building, finds the nearest OSM building within 30m
    and transfers name/tag information.
    """
    MATCH_THRESHOLD_M = 30.0
    unified = []

    # Index OSM buildings for spatial matching
    osm_matched = set()

    for ob in overture_buildings:
        o_lat, o_lng = ob["_centroid"]

        best_osm = None
        best_dist = float("inf")

        for i, sb in enumerate(osm_buildings):
            if i in osm_matched:
                continue
            s_lat, s_lng = sb["_centroid"]
            dist = _haversine_distance_m(o_lat, o_lng, s_lat, s_lng)
            if dist < best_dist:
                best_dist = dist
                best_osm = (i, sb)

        osm_tags = {}
        osm_name = None
        osm_id = None
        if best_osm and best_dist < MATCH_THRESHOLD_M:
            idx, matched_sb = best_osm
            osm_matched.add(idx)
            osm_tags = matched_sb.get("_tags", {})
            osm_name = _extract_osm_name(osm_tags)
            osm_id = matched_sb.get("_osm_id")

        unified.append({
            "_poly_coords": ob["_poly_coords"],
            "_centroid": ob["_centroid"],
            "_overture_name": ob.get("_overture_name"),
            "_osm_name": osm_name,
            "_osm_tags": osm_tags,
            "_overture_id": ob.get("_overture_id"),
            "_osm_id": osm_id,
            "_height": ob.get("_height"),
            "_levels": ob.get("_levels"),
            "_props": ob.get("_props", {}),
        })

    # Add any unmatched OSM buildings that weren't in Overture
    for i, sb in enumerate(osm_buildings):
        if i not in osm_matched:
            tags = sb.get("_tags", {})
            unified.append({
                "_poly_coords": sb["_poly_coords"],
                "_centroid": sb["_centroid"],
                "_overture_name": None,
                "_osm_name": _extract_osm_name(tags),
                "_osm_tags": tags,
                "_overture_id": None,
                "_osm_id": sb.get("_osm_id"),
                "_height": None,
                "_levels": None,
                "_props": {},
            })

    return unified


def _build_from_osm_only(
    osm_buildings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Builds unified list from OSM data only (when Overture is unavailable)."""
    unified = []
    for sb in osm_buildings:
        tags = sb.get("_tags", {})
        unified.append({
            "_poly_coords": sb["_poly_coords"],
            "_centroid": sb["_centroid"],
            "_overture_name": None,
            "_osm_name": _extract_osm_name(tags),
            "_osm_tags": tags,
            "_overture_id": None,
            "_osm_id": sb.get("_osm_id"),
            "_height": None,
            "_levels": None,
            "_props": {},
        })
    return unified


def _assign_names_and_build_output(
    unified: List[Dict[str, Any]],
    locality: str,
) -> List[Dict[str, Any]]:
    """
    Assigns final names to each building and constructs the output dicts.

    Name priority:
      1. Overture names.primary
      2. OSM name
      3. OSM name:en
      4. OSM official_name
      5. OSM addr:housename
      6. Synthetic: "<AREA_NAME> Building XX"

    Synthetic numbering is sequential among unnamed buildings only,
    zero-padded, and restarts for each area selection.
    """
    result = []
    synthetic_counter = 0

    for entry in unified:
        # Determine best available real name
        real_name = None
        name_source = "synthetic"

        # Priority 1: Overture primary name
        if entry.get("_overture_name"):
            real_name = entry["_overture_name"]
            name_source = "overture"

        # Priority 2-5: OSM names (already extracted in order by _extract_osm_name)
        if not real_name and entry.get("_osm_name"):
            real_name = entry["_osm_name"]
            name_source = "osm"

        # Determine final name
        if real_name:
            final_name = real_name
        else:
            synthetic_counter += 1
            final_name = f"{locality} Building {synthetic_counter:02d}"
            name_source = "synthetic"

        # Build metadata from tags
        osm_tags = entry.get("_osm_tags", {})
        b_type_raw = osm_tags.get("building", "yes").lower() if osm_tags else "yes"
        usage_type, floors, height = _infer_building_meta(osm_tags, b_type_raw)

        # Override with Overture height/levels if available
        if entry.get("_height"):
            try:
                height = float(entry["_height"])
                floors = max(2, int(round(height / 3.2)))
            except (ValueError, TypeError):
                pass
        if entry.get("_levels"):
            try:
                floors = max(2, int(entry["_levels"]))
                height = round(floors * 3.2, 1)
            except (ValueError, TypeError):
                pass

        # Compute local metric footprint
        poly_coords = entry["_poly_coords"]
        c_lat, c_lng = entry["_centroid"]

        footprint_local = []
        for p in poly_coords:
            d_lat_m = (p[0] - c_lat) * 111320.0
            d_lng_m = (p[1] - c_lng) * (111320.0 * math.cos(math.radians(c_lat)))
            footprint_local.append([round(d_lng_m, 2), round(d_lat_m, 2)])

        xs = [pt[0] for pt in footprint_local]
        ys = [pt[1] for pt in footprint_local]
        w = max(14.0, max(xs) - min(xs)) if xs else 24.0
        l_dim = max(14.0, max(ys) - min(ys)) if ys else 22.0

        coords_geo = [[round(p[0], 6), round(p[1], 6)] for p in poly_coords]

        # Build ID
        bid = entry.get("_overture_id") or entry.get("_osm_id")
        if entry.get("_overture_id"):
            bid = f"overture_{entry['_overture_id']}"
        elif entry.get("_osm_id"):
            bid = f"osm_{entry['_osm_id']}"
        else:
            bid = f"bld_{id(entry)}"

        pincode = osm_tags.get("addr:postcode", "")

        result.append({
            "id": bid,
            "name": final_name,
            "name_source": name_source,
            "centroid": [c_lat, c_lng],
            "centroid_lat": c_lat,
            "centroid_lng": c_lng,
            "footprint_coordinates": coords_geo,
            "footprint_polygon": coords_geo,
            "footprint_local": footprint_local,
            "width_m": round(w, 1),
            "length_m": round(l_dim, 1),
            "floors": floors,
            "height_m": height,
            "type": usage_type,
            "building_type": usage_type,
            "pincode": pincode,
            "has_real_osm_name": name_source != "synthetic",
            "source": "overture+osm" if entry.get("_overture_id") else "osm",
        })

    return result
