"""
migrate_to_real_estate_db.py
────────────────────────────
ChromaDB → SQLite 마이그레이션 스크립트.

수행 작업:
  1. apartment_master.db → real_estate.db/apartments  (ApartmentRepository)
  2. ChromaDB real_estate_reports → real_estate.db/transactions  (TransactionRepository)
  3. resolve_complex_codes()로 FK 자동 해소

실행 방법 (프로젝트 루트에서):
  arch -arm64 .venv/bin/python3.12 scripts/migrate_to_real_estate_db.py
  arch -arm64 .venv/bin/python3.12 scripts/migrate_to_real_estate_db.py --dry-run
"""
import sys
import os
import argparse

# src/ 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.real_estate.config import RealEstateConfig
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.transaction_repository import TransactionRepository
from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
from modules.real_estate.models import RealEstateTransaction
from core.logger import get_logger

logger = get_logger(__name__)


def _parse_args():
    parser = argparse.ArgumentParser(description="ChromaDB → SQLite 마이그레이션")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="DB 변경 없이 카운트만 출력"
    )
    parser.add_argument(
        "--skip-masters", action="store_true",
        help="아파트 마스터 복사 단계 건너뜀"
    )
    parser.add_argument(
        "--skip-transactions", action="store_true",
        help="ChromaDB 거래 마이그레이션 단계 건너뜀"
    )
    return parser.parse_args()


def _fetch_all_chroma_transactions(chroma_repo) -> list:
    """ChromaDB real_estate_reports 컬렉션에서 거래 레코드만 추출.

    거래 레코드 판별: metadata에 'deal_date' 필드가 있는 항목.
    (리포트 레코드는 'complex_name' 필드를 가지며 deal_date가 없음)
    """
    PAGE_SIZE = 1000
    offset, all_items = 0, []

    while True:
        page = chroma_repo.collection.get(
            include=["metadatas"],
            limit=PAGE_SIZE,
            offset=offset,
        )
        if not page or not page["ids"]:
            break
        for meta in page["metadatas"]:
            if meta.get("deal_date"):
                all_items.append(meta)
        if len(page["ids"]) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_items


def _meta_to_tx(meta: dict) -> RealEstateTransaction:
    return RealEstateTransaction(
        apt_name=str(meta.get("apt_name", "")),
        district_code=str(meta.get("district_code", "")),
        deal_date=str(meta.get("deal_date", "")),
        price=int(meta.get("price", 0)),
        floor=int(meta.get("floor", 0)),
        exclusive_area=float(meta.get("exclusive_area", 0.0)),
        build_year=int(meta.get("build_year", 0)),
        road_name=str(meta.get("road_name", "")),
        complex_code=meta.get("complex_code") or None,
    )


def step1_migrate_masters(
    master_repo: ApartmentMasterRepository,
    apt_repo: ApartmentRepository,
    dry_run: bool,
) -> None:
    """apartment_master.db → real_estate.db/apartments"""
    print("\n[Step 1] 아파트 마스터 복사: apartment_master.db → real_estate.db/apartments")

    all_masters = master_repo.search(limit=999_999)
    print(f"  소스: {len(all_masters)}개 단지")

    if dry_run:
        print("  [dry-run] 쓰기 생략")
        return

    saved = 0
    for m in all_masters:
        apt_repo.save(m)
        saved += 1
        if saved % 500 == 0:
            print(f"  ... {saved}/{len(all_masters)} 저장 완료")

    print(f"  ✅ 완료: {saved}개 upsert → real_estate.db/apartments ({apt_repo.count()}개 총계)")


def step2_migrate_transactions(
    chroma_repo,
    tx_repo: TransactionRepository,
    dry_run: bool,
) -> None:
    """ChromaDB real_estate_reports → real_estate.db/transactions"""
    print("\n[Step 2] 거래 마이그레이션: ChromaDB → real_estate.db/transactions")

    metas = _fetch_all_chroma_transactions(chroma_repo)
    print(f"  ChromaDB 거래 레코드: {len(metas)}건")

    if not metas:
        print("  ⚠️ 이전할 데이터 없음. 건너뜀.")
        return

    # 변환
    txs = []
    skipped = 0
    for meta in metas:
        if not meta.get("apt_name") or not meta.get("deal_date") or not meta.get("district_code"):
            skipped += 1
            continue
        txs.append(_meta_to_tx(meta))

    print(f"  변환 가능: {len(txs)}건 / 누락 필드로 건너뜀: {skipped}건")

    if dry_run:
        print("  [dry-run] 쓰기 생략")
        return

    saved = tx_repo.save_batch(txs)
    print(f"  ✅ 완료: {saved}건 신규 저장 (중복 제외)")


def step3_resolve_fk(
    tx_repo: TransactionRepository,
    apt_repo: ApartmentRepository,
    dry_run: bool,
) -> None:
    """complex_code NULL 거래 → apartments 테이블 fuzzy 매칭으로 FK 해소"""
    print("\n[Step 3] FK 해소: transactions.complex_code NULL → apartments 매칭")

    if dry_run:
        with tx_repo._conn() as conn:
            null_count = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL"
            ).fetchone()[0]
        print(f"  [dry-run] FK NULL 건수: {null_count}건")
        return

    resolved = tx_repo.resolve_complex_codes(apt_repo)
    print(f"  ✅ 완료: {resolved}건 FK 해소")

    with tx_repo._conn() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL"
        ).fetchone()[0]
    print(f"  남은 NULL: {remaining}건 (이름 매칭 불가 거래)")


def main():
    args = _parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("=" * 60)
        print("  [DRY-RUN MODE] — DB에 아무 변경도 하지 않습니다")
        print("=" * 60)

    cfg = RealEstateConfig()
    master_db   = cfg.get("apartment_master_db_path", "data/apartment_master.db")
    re_db       = cfg.get("real_estate_db_path",       "data/real_estate.db")

    print(f"\n소스 (마스터): {master_db}")
    print(f"대상 (SQLite): {re_db}")

    # 레포지토리 초기화
    master_repo = ApartmentMasterRepository(db_path=master_db)
    apt_repo    = ApartmentRepository(db_path=re_db)
    tx_repo     = TransactionRepository(db_path=re_db)

    # ChromaDB 레포지토리 (거래 이전용)
    if not args.skip_transactions:
        try:
            from modules.real_estate.repository import ChromaRealEstateRepository
            chroma_repo = ChromaRealEstateRepository()
        except Exception as e:
            print(f"\n⚠️ ChromaDB 연결 실패: {e}")
            print("   --skip-transactions 옵션으로 거래 마이그레이션을 건너뛸 수 있습니다.")
            sys.exit(1)

    # Step 1: 마스터 복사
    if not args.skip_masters:
        step1_migrate_masters(master_repo, apt_repo, dry_run)
    else:
        print("\n[Step 1] 마스터 복사 건너뜀 (--skip-masters)")

    # Step 2: 거래 이전
    if not args.skip_transactions:
        step2_migrate_transactions(chroma_repo, tx_repo, dry_run)
    else:
        print("\n[Step 2] 거래 마이그레이션 건너뜀 (--skip-transactions)")

    # Step 3: FK 해소
    step3_resolve_fk(tx_repo, apt_repo, dry_run)

    print("\n마이그레이션 완료.")
    if not dry_run:
        print(f"  apartments: {apt_repo.count()}개")
        with tx_repo._conn() as conn:
            tx_total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        print(f"  transactions: {tx_total}건")


if __name__ == "__main__":
    main()
