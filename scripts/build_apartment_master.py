"""
수도권 아파트 마스터 DB 초기 구축 스크립트.

사용법:
    arch -arm64 .venv/bin/python3.12 scripts/build_apartment_master.py
    arch -arm64 .venv/bin/python3.12 scripts/build_apartment_master.py --rebuild

특징:
    - 수도권(서울 11·인천 28·경기 41) 단지만 수집
    - 중단 후 재실행 시 DB 기준으로 자동 이어받기 (재시작해도 안전)
    - --rebuild: 기존 DB를 초기화하고 전체 재수집 (신규 필드 채우기용)
    - data/apartment_master_progress.json 에 실시간 진행상황 기록
"""
import os
import sys
import json
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import yaml
from modules.real_estate.apartment_master.client import ApartmentMasterClient
from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
from modules.real_estate.apartment_master.service import ApartmentMasterService

# ── 로깅 설정 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── 수도권 지역 코드 prefix ────────────────────────────────────────────────────
METRO_PREFIXES = ("11", "28", "41")  # 서울, 인천, 경기

# ── 경로 ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "src", "modules", "real_estate", "config.yaml")
DB_PATH = os.path.join(BASE_DIR, "data", "apartment_master.db")
PROGRESS_PATH = os.path.join(BASE_DIR, "data", "apartment_master_progress.json")


def load_metro_districts() -> list:
    """config.yaml에서 수도권(서울·인천·경기) 지구만 로드."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    all_districts = cfg.get("districts", [])
    metro = [d for d in all_districts if str(d.get("code", "")).startswith(METRO_PREFIXES)]
    return metro


def print_progress_summary():
    """현재 진행상황 파일 요약 출력."""
    if not os.path.exists(PROGRESS_PATH):
        print("  (진행상황 파일 없음 — 첫 실행)")
        return
    with open(PROGRESS_PATH, encoding="utf-8") as f:
        p = json.load(f)
    c = p.get("complexes", {})
    d = p.get("districts", {})
    print(f"  상태: {p.get('status')}")
    print(f"  최종 업데이트: {p.get('last_updated_at', '-')}")
    print(f"  지구 진행: {d.get('current_index')}/{d.get('total')} ({d.get('current_name')})")
    print(f"  단지: 저장 {c.get('saved')}건 / 스킵 {c.get('skipped_existing')}건 / 오류 {c.get('errors')}건")


def main():
    parser = argparse.ArgumentParser(description="수도권 아파트 마스터 DB 구축")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="기존 DB를 초기화하고 전체 재수집 (신규 필드 채우기용)",
    )
    args = parser.parse_args()

    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

    # 수도권 지구 로드
    metro_districts = load_metro_districts()
    logger.info(f"수도권 대상 지구: {len(metro_districts)}개")

    # 저장소 초기화
    repo = ApartmentMasterRepository(db_path=DB_PATH)

    # --rebuild: 기존 DB 삭제 후 전체 재수집
    if args.rebuild:
        existing_count = repo.count()
        logger.info(f"[--rebuild] 기존 DB {existing_count}건 삭제 후 전체 재수집")
        repo.truncate()
        logger.info("[--rebuild] DB 초기화 완료 — 전체 수집 시작")
    else:
        # 기존 진행상황 확인
        existing_count = repo.count()
        if existing_count > 0:
            logger.info(f"기존 DB에 {existing_count}건 저장됨 → 이어받기 모드")
            print("\n[이전 진행상황]")
            print_progress_summary()
            print()
        else:
            logger.info("첫 실행 — 전체 수집 시작")

    # 서비스 초기화
    client = ApartmentMasterClient()
    service = ApartmentMasterService(
        client=client,
        repository=repo,
        rate_limit_sec=float(
            _get_config_value(CONFIG_PATH, "apartment_master_rate_limit_sec", 0.3)
        ),
    )

    # 실행
    logger.info("=" * 60)
    logger.info("수도권 아파트 마스터 DB 구축 시작")
    logger.info(f"DB 경로: {DB_PATH}")
    logger.info(f"진행상황: {PROGRESS_PATH}")
    logger.info("중단(Ctrl+C) 후 재실행 시 자동 이어받기")
    logger.info("=" * 60)

    try:
        stats = service.build_initial(
            districts=metro_districts,
            progress_path=PROGRESS_PATH,
        )
    except KeyboardInterrupt:
        logger.info("\n[중단됨] Ctrl+C 감지. 현재까지 저장된 데이터는 유지됩니다.")
        logger.info("같은 명령으로 재실행하면 이어서 계속됩니다.")
        print("\n[현재 진행상황]")
        print_progress_summary()
        return

    # 완료
    logger.info("=" * 60)
    logger.info(f"완료! 총 {stats['saved']}건 신규 저장 / {stats['skipped']}건 스킵 / {stats['errors']}건 오류")
    logger.info(f"전체 DB 건수: {repo.count()}건")
    print("\n[최종 진행상황]")
    print_progress_summary()


def _get_config_value(config_path: str, key: str, default):
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return cfg.get(key, default)
    except Exception:
        return default


if __name__ == "__main__":
    main()
