import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.config import RealEstateConfig

logger = logging.getLogger(__name__)

_config = RealEstateConfig()
METRO_SIGUNGU_CODES: List[str] = _config.get("building_master_sigungu_codes", [])


def _normalize_name(name: str) -> str:
    n = re.sub(r"[()（）\s·\-_]", "", name).lower()
    n = n.replace("아파트", "").replace("apt", "")
    return n


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _best_match(
    apt_name: str, candidates: List[BuildingMaster]
) -> Tuple[Optional[BuildingMaster], float]:
    best: Optional[BuildingMaster] = None
    best_score = 0.0
    for bm in candidates:
        score = _name_similarity(apt_name, bm.building_name)
        if score > best_score:
            best_score = score
            best = bm
    return best, best_score


class BuildingMasterService:
    def __init__(
        self,
        client: BuildingRegisterClient,
        bm_repo: BuildingMasterRepository,
        apt_master_repo: AptMasterRepository,
    ):
        self._client = client
        self._bm_repo = bm_repo
        self._apt_master_repo = apt_master_repo

    def collect(self, sigungu_codes: Optional[List[str]] = None) -> dict:
        """수도권 시군구별 아파트 수집. 이미 수집된 시군구는 스킵 (이어받기 지원)."""
        codes = sigungu_codes or METRO_SIGUNGU_CODES
        result = {"collected": 0, "failed": [], "skipped": 0}
        for code in codes:
            if self._bm_repo.count_by_sigungu(code) > 0:
                result["skipped"] += 1
                logger.info(f"[Collect] {code}: skip (already collected)")
                continue
            try:
                raw_items = self._client.fetch_apartments_by_sigungu(code)
            except Exception as e:
                logger.error(f"[Collect] {code} fetch failed: {e}")
                result["failed"].append(code)
                continue
            for raw in raw_items:
                try:
                    parsed = self._client.parse_item(raw)
                    if not parsed.get("mgm_pk") or not parsed.get("building_name"):
                        continue
                    bm = BuildingMaster(
                        mgm_pk=parsed["mgm_pk"],
                        building_name=parsed["building_name"],
                        sigungu_code=parsed.get("sigungu_code") or code,
                        bjdong_code=parsed.get("bjdong_code", ""),
                        parcel_pnu=parsed.get("parcel_pnu", ""),
                        road_address=parsed.get("road_address"),
                        jibun_address=parsed.get("jibun_address"),
                        completion_year=parsed.get("completion_year"),
                        total_units=parsed.get("total_units"),
                        total_buildings=parsed.get("total_buildings"),
                        floor_area_ratio=parsed.get("floor_area_ratio"),
                        building_coverage_ratio=parsed.get("building_coverage_ratio"),
                        collected_at=datetime.now(timezone.utc).isoformat(),
                    )
                    self._bm_repo.upsert(bm)
                    result["collected"] += 1
                except Exception as e:
                    logger.warning(f"[Collect] {code} item skip: {e}")
            logger.info(f"[Collect] {code}: {len(raw_items)} items")
        return result

    def reset_building_master(self, db_path: str) -> None:
        """building_master 테이블 DROP 후 재생성 (rebuild 플로우 전용)."""
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS building_master")
        self._bm_repo._init_db()

    def map_to_apt_master(self) -> dict:
        """apt_master 항목을 building_master와 매핑. 유사도 >= 0.8이면 pnu 업데이트."""
        entries = self._apt_master_repo.get_all_for_mapping()
        result = {"mapped": 0, "no_candidates": 0, "below_threshold": 0, "total": len(entries)}
        for entry in entries:
            candidates = self._bm_repo.get_by_sigungu(entry.district_code)
            if not candidates:
                result["no_candidates"] += 1
                continue
            best_bm, best_score = _best_match(entry.apt_name, candidates)
            if best_bm and best_score >= 0.8:
                self._apt_master_repo.update_building_mapping(
                    entry.id, best_bm.mgm_pk, best_score
                )
                result["mapped"] += 1
            else:
                result["below_threshold"] += 1
        return result
