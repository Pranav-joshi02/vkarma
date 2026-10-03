"""
LADM 3D Cadastral Database & Query Engine
Manages buildings, physical space units, legal space units, parties, and ULPIN indices.
"""

from typing import Dict, List, Optional, Any
from .schema import (
    LA_SpatialUnit, LA_LegalSpaceBuildingUnit, LA_Party, LA_Source,
    LA_RRR, RRRType, LegalSpaceType, UnitStatus, BoundingBox3D
)
from .topological_validator import validate_cadastral_topology


class CadastralDatabase:
    def __init__(self):
        self.buildings: Dict[str, LA_SpatialUnit] = {}
        self.legal_units_by_id: Dict[str, LA_LegalSpaceBuildingUnit] = {}
        self.legal_units_by_ulpin: Dict[str, LA_LegalSpaceBuildingUnit] = {}

    def register_building(self, building: LA_SpatialUnit, persist: bool = True):
        self.buildings[building.building_id] = building
        for unit in building.legal_units:
            self.legal_units_by_id[unit.unit_id] = unit
            self.legal_units_by_ulpin[unit.ulpin] = unit

        if persist:
            try:
                from backend.database.repository import cadastral_repo
                cadastral_repo.save_building(building)
            except Exception:
                pass

    def register_buildings_from_dicts(self, building_dicts: List[Dict[str, Any]], clear_first: bool = False, persist: bool = True):
        if clear_first:
            self.clear()
            if persist:
                try:
                    from backend.database.repository import cadastral_repo
                    cadastral_repo.clear_all_buildings()
                except Exception:
                    pass
        for b_dict in building_dicts:
            b = LA_SpatialUnit.from_dict(b_dict)
            self.register_building(b, persist=persist)

    def load_from_database(self) -> int:
        """
        Loads all persisted buildings and legal units from Supabase / PostgreSQL into memory.
        Returns the number of buildings loaded.
        """
        try:
            from backend.database.repository import cadastral_repo
            db_buildings = cadastral_repo.load_all_buildings()
            if db_buildings:
                self.register_buildings_from_dicts(db_buildings, clear_first=False, persist=False)
                return len(db_buildings)
        except Exception:
            pass
        return 0

    def clear(self):
        self.buildings.clear()
        self.legal_units_by_id.clear()
        self.legal_units_by_ulpin.clear()

    def get_building(self, building_id: str) -> Optional[LA_SpatialUnit]:
        if building_id not in self.buildings:
            self.load_from_database()
        return self.buildings.get(building_id)

    def get_unit_by_ulpin(self, ulpin: str) -> Optional[LA_LegalSpaceBuildingUnit]:
        clean = ulpin.strip().upper()
        if clean not in self.legal_units_by_ulpin:
            self.load_from_database()
        return self.legal_units_by_ulpin.get(clean)

    def get_unit_by_id(self, unit_id: str) -> Optional[LA_LegalSpaceBuildingUnit]:
        if unit_id not in self.legal_units_by_id:
            self.load_from_database()
        return self.legal_units_by_id.get(unit_id)

    def list_all_buildings(self) -> List[Dict[str, Any]]:
        if len(self.buildings) == 0:
            self.load_from_database()
        return [b.to_dict() for b in self.buildings.values()]

    def search_units(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower().strip()
        results = []
        for unit in self.legal_units_by_id.values():
            if (query_lower in unit.ulpin.lower() or
                query_lower in unit.unit_name.lower() or
                any(query_lower in p.name.lower() for p in unit.parties) or
                query_lower in unit.status.value.lower()):
                results.append(unit.to_dict())
        return results

    def run_conflict_scan(self, building_id: Optional[str] = None) -> Dict[str, Any]:
        if building_id:
            b = self.buildings.get(building_id)
            if not b:
                return {"error": f"Building '{building_id}' not found"}
            units = b.legal_units
        else:
            units = list(self.legal_units_by_id.values())
        return validate_cadastral_topology(units)


# Global singleton instance
cadastre_db = CadastralDatabase()
