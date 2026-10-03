"""
LADM Cadastral Repository
Handles database persistence and retrieval for ISO 19152 records (Buildings, Units, Parties, RRRs, Disputes).
Supports both Supabase REST API client and direct PostgreSQL connections.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from .supabase_client import get_supabase_client, get_db_connection
from backend.ladm.schema import (
    LA_SpatialUnit, LA_LegalSpaceBuildingUnit, LA_Party, LA_Source,
    LA_RRR, RRRType, LegalSpaceType, UnitStatus, BoundingBox3D
)

logger = logging.getLogger("cadastral_repository")


class CadastralRepository:
    def __init__(self):
        pass

    def clear_all_buildings(self) -> bool:
        """
        Purges existing cadastral records from PostgreSQL / Supabase when registering a new survey area.
        """
        conn = get_db_connection()
        client = get_supabase_client()
        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM cadastral_disputes;
                        DELETE FROM cadastral_rrrs;
                        DELETE FROM cadastral_sources;
                        DELETE FROM cadastral_parties;
                        DELETE FROM cadastral_units;
                        DELETE FROM cadastral_buildings;
                    """)
                    conn.commit()
                conn.close()
                logger.info("Purged previous cadastral records from database.")
                return True
            elif client is not None:
                for tbl in ["cadastral_disputes", "cadastral_rrrs", "cadastral_sources", "cadastral_parties", "cadastral_units", "cadastral_buildings"]:
                    try:
                        client.table(tbl).delete().neq("id" if tbl == "cadastral_disputes" else "building_id" if tbl == "cadastral_buildings" else "unit_id", "___NONE___").execute()
                    except Exception:
                        pass
                return True
        except Exception as e:
            logger.error(f"Error purging cadastral records from database: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return False

    def save_building(self, building: LA_SpatialUnit) -> bool:
        """
        Persists an LA_SpatialUnit building and all nested legal units, parties, RRRs, and sources.
        """
        client = get_supabase_client()
        conn = get_db_connection()

        if client is None and conn is None:
            # Fallback mode: handled in memory
            return False

        try:
            # 1. Direct PostgreSQL execution
            if conn is not None:
                with conn.cursor() as cur:
                    # Upsert building
                    cur.execute("""
                        INSERT INTO cadastral_buildings (
                            building_id, building_name, pincode, total_floors, basement_floors,
                            height_m, ground_elevation_m, centroid_lat, centroid_lng,
                            footprint_polygon, point_count, raw_las_filename, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (building_id) DO UPDATE SET
                            building_name = EXCLUDED.building_name,
                            total_floors = EXCLUDED.total_floors,
                            height_m = EXCLUDED.height_m,
                            footprint_polygon = EXCLUDED.footprint_polygon,
                            point_count = EXCLUDED.point_count,
                            updated_at = NOW();
                    """, (
                        str(building.building_id), str(building.building_name), str(building.pincode),
                        int(building.total_floors), int(building.basement_floors), float(building.height_m),
                        float(building.ground_elevation_m), float(building.centroid_lat), float(building.centroid_lng),
                        json.dumps(building.footprint_polygon), int(building.point_count),
                        str(building.raw_las_filename)
                    ))

                    # Clean up existing units for this building to avoid stale orphaned children
                    cur.execute("DELETE FROM cadastral_units WHERE building_id = %s;", (str(building.building_id),))

                    # Also delete any conflicting units with matching ULPINs to strictly prevent UniqueViolation
                    incoming_ulpins = [str(unit.ulpin) for unit in building.legal_units if unit.ulpin]
                    if incoming_ulpins:
                        cur.execute("DELETE FROM cadastral_units WHERE ulpin = ANY(%s);", (incoming_ulpins,))

                    # Batch upsert units
                    from psycopg2.extras import execute_values
                    unit_tuples = [
                        (
                            str(unit.unit_id), str(unit.building_id), str(unit.unit_name),
                            str(unit.space_type.value if hasattr(unit.space_type, 'value') else unit.space_type),
                            str(unit.ulpin), int(unit.floor_level), float(unit.bbox.carpet_area_sqm), float(unit.bbox.volume_m3),
                            str(unit.status.value if hasattr(unit.status, 'value') else unit.status),
                            float(unit.bbox.min_x), float(unit.bbox.max_x), float(unit.bbox.min_y), float(unit.bbox.max_y),
                            float(unit.bbox.min_z), float(unit.bbox.max_z),
                            json.dumps(unit.mesh_geometry) if unit.mesh_geometry else '{}'
                        )
                        for unit in building.legal_units
                    ]
                    if unit_tuples:
                        execute_values(cur, """
                            INSERT INTO cadastral_units (
                                unit_id, building_id, unit_name, space_type, ulpin, floor_level,
                                carpet_area_sqm, volume_m3, status, min_x, max_x, min_y, max_y,
                                min_z, max_z, mesh_geometry, updated_at
                            ) VALUES %s
                            ON CONFLICT (unit_id) DO UPDATE SET
                                ulpin = EXCLUDED.ulpin,
                                unit_name = EXCLUDED.unit_name,
                                status = EXCLUDED.status,
                                mesh_geometry = EXCLUDED.mesh_geometry,
                                updated_at = NOW();
                        """, unit_tuples, template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())")

                    # Batch insert parties
                    party_tuples = [
                        (party.party_id, unit.unit_id, party.name, party.party_type, party.id_hash, party.contact_email, party.role)
                        for unit in building.legal_units for party in unit.parties
                    ]
                    if party_tuples:
                        execute_values(cur, """
                            INSERT INTO cadastral_parties (
                                party_id, unit_id, name, party_type, id_hash, contact_email, role
                            ) VALUES %s ON CONFLICT (party_id) DO NOTHING;
                        """, party_tuples)

                    # Batch insert RRRs
                    rrr_tuples = [
                        (
                            rrr.rrr_id, unit.unit_id,
                            rrr.rrr_type.value if hasattr(rrr.rrr_type, 'value') else str(rrr.rrr_type),
                            rrr.description, rrr.share_ratio, rrr.beneficiary_party,
                            rrr.amount_inr, rrr.is_active, rrr.valid_from, rrr.valid_to
                        )
                        for unit in building.legal_units for rrr in unit.rrrs
                    ]
                    if rrr_tuples:
                        execute_values(cur, """
                            INSERT INTO cadastral_rrrs (
                                rrr_id, unit_id, rrr_type, description, share_ratio,
                                beneficiary_party, amount_inr, is_active, valid_from, valid_to
                            ) VALUES %s ON CONFLICT (rrr_id) DO NOTHING;
                        """, rrr_tuples)

                    # Batch insert Sources
                    src_tuples = [
                        (
                            src.source_id, unit.unit_id, src.document_type, src.document_number,
                            src.issuing_authority, src.registration_date, src.digital_signature,
                            src.ipfs_hash, src.verification_status
                        )
                        for unit in building.legal_units for src in unit.sources
                    ]
                    if src_tuples:
                        execute_values(cur, """
                            INSERT INTO cadastral_sources (
                                source_id, unit_id, document_type, document_number,
                                issuing_authority, registration_date, digital_signature,
                                ipfs_hash, verification_status
                            ) VALUES %s ON CONFLICT (source_id) DO NOTHING;
                        """, src_tuples)

                    conn.commit()
                conn.close()
                logger.info(f"Persisted building {building.building_id} to PostgreSQL database.")
                return True

            # 2. Supabase REST API execution
            elif client is not None:
                b_data = {
                    "building_id": building.building_id,
                    "building_name": building.building_name,
                    "pincode": building.pincode,
                    "total_floors": building.total_floors,
                    "basement_floors": building.basement_floors,
                    "height_m": building.height_m,
                    "ground_elevation_m": building.ground_elevation_m,
                    "centroid_lat": building.centroid_lat,
                    "centroid_lng": building.centroid_lng,
                    "footprint_polygon": building.footprint_polygon,
                    "point_count": building.point_count,
                    "raw_las_filename": building.raw_las_filename
                }
                client.table("cadastral_buildings").upsert(b_data).execute()

                units_data = []
                for unit in building.legal_units:
                    units_data.append({
                        "unit_id": unit.unit_id,
                        "building_id": unit.building_id,
                        "unit_name": unit.unit_name,
                        "space_type": unit.space_type.value if hasattr(unit.space_type, 'value') else str(unit.space_type),
                        "ulpin": unit.ulpin,
                        "floor_level": unit.floor_level,
                        "carpet_area_sqm": unit.bbox.carpet_area_sqm,
                        "volume_m3": unit.bbox.volume_m3,
                        "status": unit.status.value if hasattr(unit.status, 'value') else str(unit.status),
                        "min_x": unit.bbox.min_x,
                        "max_x": unit.bbox.max_x,
                        "min_y": unit.bbox.min_y,
                        "max_y": unit.bbox.max_y,
                        "min_z": unit.bbox.min_z,
                        "max_z": unit.bbox.max_z,
                        "mesh_geometry": unit.mesh_geometry or {}
                    })
                if units_data:
                    client.table("cadastral_units").upsert(units_data).execute()

                logger.info(f"Persisted building {building.building_id} via Supabase REST API.")
                return True

        except Exception as e:
            logger.error(f"Error persisting building to Supabase/PostgreSQL: {e}", exc_info=True)
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            return False

        return False

    def save_dispute_report(self, conflicts: List[Dict[str, Any]], building_id: str) -> bool:
        """Saves detected 3D topological disputes into cadastral_disputes table."""
        conn = get_db_connection()
        client = get_supabase_client()

        if not conflicts:
            return True

        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute("SELECT building_id FROM cadastral_buildings;")
                    existing_building_ids = {row[0] for row in cur.fetchall()}
                    cur.execute("SELECT unit_id FROM cadastral_units;")
                    existing_unit_ids = {row[0] for row in cur.fetchall()}
                    for c in conflicts:
                        cand_bld = building_id or c.get("building_id")
                        if cand_bld not in existing_building_ids:
                            cand_bld = list(existing_building_ids)[0] if existing_building_ids else None
                        if not cand_bld:
                            continue
                        u_a = c.get("unit_a") if c.get("unit_a") in existing_unit_ids else None
                        u_b = c.get("unit_b") if c.get("unit_b") in existing_unit_ids else None
                        cur.execute("""
                            INSERT INTO cadastral_disputes (
                                building_id, conflict_type, severity, unit_a_id, unit_a_name,
                                unit_a_ulpin, unit_b_id, unit_b_name, unit_b_ulpin,
                                overlap_volume_m3, message, detected_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
                        """, (
                            cand_bld,
                            c.get("type", "COLLISION"),
                            c.get("severity", "CRITICAL"),
                            u_a, c.get("unit_a_name"), c.get("unit_a_ulpin"),
                            u_b, c.get("unit_b_name"), c.get("unit_b_ulpin"),
                            float(c.get("overlap_volume_m3", 0.0)),
                            c.get("message", "")
                        ))
                    conn.commit()
                conn.close()
                return True
            elif client is not None:
                rows = []
                for c in conflicts:
                    rows.append({
                        "building_id": building_id or c.get("building_id", "GLOBAL"),
                        "conflict_type": c.get("type", "COLLISION"),
                        "severity": c.get("severity", "CRITICAL"),
                        "unit_a_id": c.get("unit_a"),
                        "unit_a_name": c.get("unit_a_name"),
                        "unit_a_ulpin": c.get("unit_a_ulpin"),
                        "unit_b_id": c.get("unit_b"),
                        "unit_b_name": c.get("unit_b_name"),
                        "unit_b_ulpin": c.get("unit_b_ulpin"),
                        "overlap_volume_m3": c.get("overlap_volume_m3", 0.0),
                        "message": c.get("message", "")
                    })
                client.table("cadastral_disputes").insert(rows).execute()
                return True
        except Exception as e:
            logger.error(f"Error saving disputes to database: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return False

    def log_pipeline_run(self, data: Dict[str, Any]) -> bool:
        """Logs pipeline telemetry to pipeline_execution_logs table."""
        conn = get_db_connection()
        client = get_supabase_client()

        task_id = data.get("task_id", "")
        summary = data.get("summary", {})

        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO pipeline_execution_logs (
                            task_id, area_name, pincode, points_processed, buildings_detected,
                            units_minted, disputes_flagged, processing_time_s, status, raw_summary
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (task_id) DO NOTHING;
                    """, (
                        task_id, data.get("area_name", ""), data.get("pincode", ""),
                        summary.get("total_points_processed", 0),
                        summary.get("buildings_detected", 0),
                        summary.get("legal_space_units_minted", 0),
                        summary.get("disputes_flagged", 0),
                        data.get("total_processing_time_s", 0.0),
                        data.get("status", "SUCCESS"),
                        json.dumps(summary)
                    ))
                    conn.commit()
                conn.close()
                return True
            elif client is not None:
                client.table("pipeline_execution_logs").upsert({
                    "task_id": task_id,
                    "area_name": data.get("area_name", ""),
                    "pincode": data.get("pincode", ""),
                    "points_processed": summary.get("total_points_processed", 0),
                    "buildings_detected": summary.get("buildings_detected", 0),
                    "units_minted": summary.get("legal_space_units_minted", 0),
                    "disputes_flagged": summary.get("disputes_flagged", 0),
                    "processing_time_s": data.get("total_processing_time_s", 0.0),
                    "status": data.get("status", "SUCCESS"),
                    "raw_summary": summary
                }).execute()
                return True
        except Exception as e:
            logger.error(f"Error logging pipeline run to database: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return False

    def load_all_buildings(self) -> List[Dict[str, Any]]:
        """
        Fetches all buildings and their units from Supabase / PostgreSQL.
        Returns list of building dictionaries.
        """
        conn = get_db_connection()
        client = get_supabase_client()

        buildings_out = []

        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT building_id, building_name, pincode, total_floors, basement_floors,
                               height_m, ground_elevation_m, centroid_lat, centroid_lng,
                               footprint_polygon, point_count, raw_las_filename
                        FROM cadastral_buildings;
                    """)
                    b_rows = cur.fetchall()

                    for b_row in b_rows:
                        b_id = b_row[0]
                        # Fetch units for this building
                        cur.execute("""
                            SELECT unit_id, building_id, unit_name, space_type, ulpin, floor_level,
                                   carpet_area_sqm, volume_m3, status, min_x, max_x, min_y, max_y,
                                   min_z, max_z, mesh_geometry
                            FROM cadastral_units WHERE building_id = %s;
                        """, (b_id,))
                        u_rows = cur.fetchall()
                        u_ids = [u[0] for u in u_rows]

                        # Batch fetch parties, rrrs, sources for these units
                        parties_by_unit = {}
                        rrrs_by_unit = {}
                        sources_by_unit = {}

                        if u_ids:
                            cur.execute("""
                                SELECT party_id, unit_id, name, party_type, id_hash, contact_email, role
                                FROM cadastral_parties WHERE unit_id = ANY(%s);
                            """, (u_ids,))
                            for pr in cur.fetchall():
                                parties_by_unit.setdefault(pr[1], []).append({
                                    "party_id": pr[0],
                                    "name": pr[2],
                                    "party_type": pr[3],
                                    "id_hash": pr[4],
                                    "contact_email": pr[5],
                                    "role": pr[6]
                                })

                            cur.execute("""
                                SELECT rrr_id, unit_id, rrr_type, description, share_ratio,
                                       beneficiary_party, amount_inr, is_active, valid_from, valid_to
                                FROM cadastral_rrrs WHERE unit_id = ANY(%s);
                            """, (u_ids,))
                            for rr in cur.fetchall():
                                rrrs_by_unit.setdefault(rr[1], []).append({
                                    "rrr_id": rr[0],
                                    "rrr_type": rr[2],
                                    "description": rr[3],
                                    "share_ratio": rr[4],
                                    "beneficiary_party": rr[5],
                                    "amount_inr": rr[6],
                                    "is_active": rr[7],
                                    "valid_from": rr[8],
                                    "valid_to": rr[9]
                                })

                            cur.execute("""
                                SELECT source_id, unit_id, document_type, document_number,
                                       issuing_authority, registration_date, digital_signature,
                                       ipfs_hash, verification_status
                                FROM cadastral_sources WHERE unit_id = ANY(%s);
                            """, (u_ids,))
                            for sr in cur.fetchall():
                                sources_by_unit.setdefault(sr[1], []).append({
                                    "source_id": sr[0],
                                    "document_type": sr[2],
                                    "document_number": sr[3],
                                    "issuing_authority": sr[4],
                                    "registration_date": sr[5],
                                    "digital_signature": sr[6],
                                    "ipfs_hash": sr[7],
                                    "verification_status": sr[8]
                                })

                        units_list = []
                        for u in u_rows:
                            uid = u[0]
                            units_list.append({
                                "unit_id": uid,
                                "building_id": u[1],
                                "unit_name": u[2],
                                "space_type": u[3],
                                "ulpin": u[4],
                                "floor_level": u[5],
                                "carpet_area_sqm": u[6],
                                "volume_m3": u[7],
                                "status": u[8],
                                "bbox": {
                                    "min_x": u[9], "max_x": u[10],
                                    "min_y": u[11], "max_y": u[12],
                                    "min_z": u[13], "max_z": u[14]
                                },
                                "parties": parties_by_unit.get(uid, []),
                                "rrrs": rrrs_by_unit.get(uid, []),
                                "sources": sources_by_unit.get(uid, []),
                                "mesh_geometry": u[15] if isinstance(u[15], dict) else json.loads(u[15] or '{}')
                            })

                        fp = b_row[9]
                        if isinstance(fp, str):
                            fp = json.loads(fp)

                        buildings_out.append({
                            "building_id": b_row[0],
                            "building_name": b_row[1],
                            "pincode": b_row[2],
                            "total_floors": b_row[3],
                            "basement_floors": b_row[4],
                            "height_m": b_row[5],
                            "ground_elevation_m": b_row[6],
                            "centroid_lat": b_row[7],
                            "centroid_lng": b_row[8],
                            "footprint_polygon": fp,
                            "legal_unit_count": len(units_list),
                            "legal_units": units_list,
                            "point_count": b_row[10],
                            "raw_las_filename": b_row[11]
                        })
                conn.close()

            elif client is not None:
                b_res = client.table("cadastral_buildings").select("*").execute()
                for b in (b_res.data or []):
                    u_res = client.table("cadastral_units").select("*").eq("building_id", b["building_id"]).execute()
                    units = []
                    u_ids = [u["unit_id"] for u in (u_res.data or [])]
                    parties_by_unit = {}
                    rrrs_by_unit = {}
                    sources_by_unit = {}
                    if u_ids:
                        try:
                            p_res = client.table("cadastral_parties").select("*").in_("unit_id", u_ids).execute()
                            for p in (p_res.data or []):
                                parties_by_unit.setdefault(p["unit_id"], []).append(p)
                        except Exception:
                            pass
                        try:
                            r_res = client.table("cadastral_rrrs").select("*").in_("unit_id", u_ids).execute()
                            for r in (r_res.data or []):
                                rrrs_by_unit.setdefault(r["unit_id"], []).append(r)
                        except Exception:
                            pass
                        try:
                            s_res = client.table("cadastral_sources").select("*").in_("unit_id", u_ids).execute()
                            for s in (s_res.data or []):
                                sources_by_unit.setdefault(s["unit_id"], []).append(s)
                        except Exception:
                            pass

                    for u in (u_res.data or []):
                        uid = u["unit_id"]
                        units.append({
                            "unit_id": uid,
                            "building_id": u["building_id"],
                            "unit_name": u["unit_name"],
                            "space_type": u["space_type"],
                            "ulpin": u["ulpin"],
                            "floor_level": u["floor_level"],
                            "carpet_area_sqm": u["carpet_area_sqm"],
                            "volume_m3": u["volume_m3"],
                            "status": u["status"],
                            "bbox": {
                                "min_x": u["min_x"], "max_x": u["max_x"],
                                "min_y": u["min_y"], "max_y": u["max_y"],
                                "min_z": u["min_z"], "max_z": u["max_z"]
                            },
                            "parties": parties_by_unit.get(uid, []),
                            "rrrs": rrrs_by_unit.get(uid, []),
                            "sources": sources_by_unit.get(uid, []),
                            "mesh_geometry": u.get("mesh_geometry") or {}
                        })
                    b_copy = dict(b)
                    b_copy["legal_units"] = units
                    b_copy["legal_unit_count"] = len(units)
                    buildings_out.append(b_copy)

        except Exception as e:
            logger.error(f"Error fetching buildings from database: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        return buildings_out


cadastral_repo = CadastralRepository()
