"""
수도권 아파트 Building Master DB 구축 스크립트.

사용법:
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --collect
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --map
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --rebuild

옵션:
    --collect  : 건축물대장 API 수집만 수행 (이어받기 지원)
    --map      : building_master → apt_master 매핑만 수행
    --rebuild  : DB 초기화 후 전체 재수집 + 매핑
"""
import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from modules.real_estate.config import RealEstateConfig
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.building_master.building_master_service import BuildingMasterService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Building Master DB 구축")
    parser.add_argument("--collect", action="store_true", help="건축물대장 수집")
    parser.add_argument("--map", action="store_true", help="apt_master 매핑")
    parser.add_argument("--rebuild", action="store_true", help="전체 재수집 + 매핑")
    args = parser.parse_args()

    if not any([args.collect, args.map, args.rebuild]):
        parser.print_help()
        sys.exit(1)

    config = RealEstateConfig()
    db_path = config.get("real_estate_db_path", "data/real_estate.db")

    client = BuildingRegisterClient()
    bm_repo = BuildingMasterRepository(db_path=db_path)
    apt_repo = AptMasterRepository(db_path=db_path)
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    if args.rebuild:
        logger.info("=== REBUILD: building_master 초기화 ===")
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS building_master")
        bm_repo._init_db()
        _run_collect(svc)
        _run_map(svc)
        return

    if args.collect:
        _run_collect(svc)

    if args.map:
        _run_map(svc)


def _run_collect(svc: BuildingMasterService) -> None:
    logger.info("=== COLLECT 시작 ===")
    result = svc.collect()
    logger.info(
        f"완료 — collected={result['collected']} "
        f"skipped={result['skipped']} "
        f"failed={len(result['failed'])}"
    )
    if result["failed"]:
        logger.warning(f"실패 코드: {result['failed']}")


def _run_map(svc: BuildingMasterService) -> None:
    logger.info("=== MAP 시작 ===")
    result = svc.map_to_apt_master()
    logger.info(
        f"완료 — mapped={result['mapped']} "
        f"below_threshold={result['below_threshold']} "
        f"no_candidates={result['no_candidates']} "
        f"total={result['total']}"
    )


if __name__ == "__main__":
    main()
