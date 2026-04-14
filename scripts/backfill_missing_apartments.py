"""
backfill_missing_apartments.py
───────────────────────────────
transactions 테이블에 complex_code=NULL인 거래의 아파트를
API에서 찾아 마스터 DB에 보충하는 스크립트.

배경:
  - transactions.complex_code=NULL 거래 중 상당수는 마스터 DB에 없는 단지.
  - 마스터는 완전해야 한다 — 거래 데이터를 지우는 게 아니라 마스터를 채운다.

수행 작업:
  1. real_estate.db의 complex_code=NULL 거래에서 (apt_name, district_code) 추출
  2. 각 district의 API 목록에서 정규화 이름 매칭으로 kaptCode 탐색
  3. 매칭 시 getAphusBassInfoV4로 상세정보 수집
  4. apartment_master.db + real_estate.db/apartments 양쪽에 저장
  5. resolve_complex_codes() 재실행

실행:
  arch -arm64 .venv/bin/python3.12 scripts/backfill_missing_apartments.py
  arch -arm64 .venv/bin/python3.12 scripts/backfill_missing_apartments.py --dry-run
  arch -arm64 .venv/bin/python3.12 scripts/backfill_missing_apartments.py --limit 50
"""
import sys
import os
import re
import time
import argparse
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from modules.real_estate.config import RealEstateConfig
from modules.real_estate.apartment_master.client import ApartmentMasterClient
from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
from modules.real_estate.apartment_master.service import ApartmentMasterService
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.transaction_repository import TransactionRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── 이름 정규화 (cleanse_apartment_names.py 와 동일 기준) ──────────────────────

def _norm(name: str) -> str:
    """공백·괄호 기호 제거, 내용 보존, 소문자화."""
    n = name.strip()
    n = re.sub(r"[()]", "", n)
    n = n.replace(" ", "").lower()
    return n


def _fuzzy_match(tx_nm: str, kapt_nm: str) -> bool:
    """정규화 이름 기반 양방향 포함 매칭."""
    a, b = _norm(tx_nm), _norm(kapt_nm)
    if a in b or b in a:
        return True
    # suffix 매칭: 짧은 이름의 끝 4자 이상이 긴 이름에 포함
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    if len(shorter) < 4:
        return False
    for n in range(4, len(shorter) + 1):
        if shorter[-n:] in longer:
            return True
    return False


# ── 핵심 로직 ──────────────────────────────────────────────────────────────────

def get_null_targets(re_db_path: str) -> list[tuple[str, str]]:
    """complex_code=NULL 거래에서 고유 (apt_name, district_code) 목록 반환."""
    conn = sqlite3.connect(re_db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT DISTINCT apt_name, district_code FROM transactions "
        "WHERE complex_code IS NULL ORDER BY district_code, apt_name"
    ).fetchall()
    conn.close()
    return [(r["apt_name"], r["district_code"]) for r in rows]


def find_kapt_code(apt_name: str, district_code: str, client: ApartmentMasterClient) -> Optional[tuple]:
    """API 목록에서 apt_name에 매칭되는 (kaptCode, kaptName, list_item) 반환."""
    candidates = client.fetch_complex_list(district_code)
    # 1순위: 완전일치
    for c in candidates:
        if _norm(c.get("kaptName", "")) == _norm(apt_name):
            return c["kaptCode"], c.get("kaptName", ""), c
    # 2순위: 포함 관계 fuzzy
    for c in candidates:
        if _fuzzy_match(apt_name, c.get("kaptName", "")):
            return c["kaptCode"], c.get("kaptName", ""), c
    return None


def backfill(
    re_db_path: str,
    master_db_path: str,
    dry_run: bool = False,
    limit: Optional[int] = None,
    rate_limit_sec: float = 0.3,
) -> dict:
    """NULL 거래 아파트 backfill 실행."""
    client = ApartmentMasterClient()
    apt_repo = ApartmentRepository(db_path=re_db_path)
    master_repo = ApartmentMasterRepository(db_path=master_db_path)
    service = ApartmentMasterService(client=client, repository=master_repo, rate_limit_sec=rate_limit_sec)

    targets = get_null_targets(re_db_path)
    if limit:
        targets = targets[:limit]

    logger.info(f"backfill 대상: {len(targets)}건 (고유 단지명)")

    stats = {"found": 0, "not_found": 0, "error": 0, "skipped_existing": 0}

    # district별 API 캐시 (district당 1회만 조회)
    district_cache: dict = {}

    for idx, (apt_name, district_code) in enumerate(targets, 1):
        # 이미 마스터에 있는지 확인 (real_estate.db 기준)
        existing = apt_repo.search(apt_name=apt_name, district_code=district_code, limit=1)
        if existing:
            stats["skipped_existing"] += 1
            continue

        # API 목록에서 탐색
        result = find_kapt_code(apt_name, district_code, client)

        if result is None:
            logger.debug(f"[{idx}] 미탐지: [{district_code}] {apt_name}")
            stats["not_found"] += 1
            continue

        kapt_code, kapt_name, list_item = result
        logger.info(f"[{idx}] 매칭: [{district_code}] \"{apt_name}\" → \"{kapt_name}\" ({kapt_code})")

        if dry_run:
            stats["found"] += 1
            continue

        # 상세정보 조회
        try:
            info = client.fetch_complex_info(kapt_code)
            time.sleep(rate_limit_sec)

            if not info:
                logger.warning(f"  상세정보 없음: {kapt_code}")
                stats["error"] += 1
                continue

            # ApartmentMaster 객체 생성
            master = ApartmentMasterService._parse_info(
                apt_name=apt_name,
                district_code=district_code,
                kapt_code=kapt_code,
                info=info,
                list_item=list_item,
            )

            # real_estate.db/apartments 저장
            apt_repo.save(master)
            # apartment_master.db 저장
            master_repo.save(master)

            stats["found"] += 1
            logger.info(f"  저장 완료: {master.apt_name} / 세대 {master.household_count}")

        except Exception as e:
            logger.error(f"  저장 실패 [{district_code}] {apt_name}: {e}")
            stats["error"] += 1

    return stats


def run_resolve(re_db_path: str) -> int:
    """backfill 후 complex_code NULL 재해소."""
    apt_repo = ApartmentRepository(db_path=re_db_path)
    tx_repo = TransactionRepository(db_path=re_db_path)

    conn = sqlite3.connect(re_db_path)
    before = conn.execute("SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL").fetchone()[0]
    conn.close()

    resolved = tx_repo.resolve_complex_codes(apt_repo)

    conn = sqlite3.connect(re_db_path)
    after = conn.execute("SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL").fetchone()[0]
    conn.close()

    logger.info(f"[resolve] before={before}, resolved={resolved}, after={after}")
    return resolved


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="마스터에 없는 아파트 backfill")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 탐지 결과만 출력")
    parser.add_argument("--limit", type=int, default=None, help="처리할 최대 고유 단지 수 (테스트용)")
    parser.add_argument("--rate", type=float, default=0.3, help="API 호출 간격 (초, 기본 0.3)")
    args = parser.parse_args()

    cfg = RealEstateConfig()
    re_db = cfg.get("real_estate_db_path", "data/real_estate.db")
    master_db = cfg.get("apartment_master_db_path", "data/apartment_master.db")

    print("=" * 60)
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}마스터 backfill 시작")
    print(f"  real_estate.db:   {re_db}")
    print(f"  apartment_master: {master_db}")
    if args.limit:
        print(f"  limit: {args.limit}건")
    print("=" * 60)

    conn = sqlite3.connect(re_db)
    null_before = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL"
    ).fetchone()[0]
    conn.close()
    print(f"현재 complex_code NULL: {null_before}건\n")

    stats = backfill(
        re_db_path=re_db,
        master_db_path=master_db,
        dry_run=args.dry_run,
        limit=args.limit,
        rate_limit_sec=args.rate,
    )

    print("\n" + "=" * 60)
    print("backfill 결과")
    print(f"  API 매칭·저장:  {stats['found']}건")
    print(f"  이미 존재(스킵): {stats['skipped_existing']}건")
    print(f"  미탐지:         {stats['not_found']}건")
    print(f"  오류:           {stats['error']}건")

    if not args.dry_run and stats["found"] > 0:
        print("\n[resolve_complex_codes 실행 중...]")
        resolved = run_resolve(re_db)

        conn = sqlite3.connect(re_db)
        null_after = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL"
        ).fetchone()[0]
        conn.close()

        print(f"  해소: {resolved}건")
        print(f"  NULL: {null_before}건 → {null_after}건")

    if args.dry_run:
        print("\n  ※ --dry-run 모드 — DB 변경 없음")
    print("=" * 60)


if __name__ == "__main__":
    main()
