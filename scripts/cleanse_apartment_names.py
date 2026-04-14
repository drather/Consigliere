"""
cleanse_apartment_names.py
──────────────────────────
아파트 이름 데이터 클렌징 스크립트.

문제:
  - apartments.apt_name: "래미안 대치 팰리스" (공백 포함)
  - transactions.apt_name: "래미안대치팰리스" (공백 없음)
  → fuzzy match 실패 → complex_code=NULL 유지

수행 작업:
  1. real_estate.db / apartments.apt_name  — 공백 정규화
  2. real_estate.db / transactions.apt_name — 공백 + 괄호 표기 정규화
  3. apartment_master.db / apartment_master.cache_key + apt_name 재구성
  4. resolve_complex_codes() 재실행 → complex_code NULL 해소

정규화 규칙:
  - 앞뒤 공백 제거 (strip)
  - 내부 공백 전부 제거
  - 거래 데이터 한정: 괄호 및 괄호 내용 제거 ("(고층)", "(872)" 등 noise)

실행:
  arch -arm64 .venv/bin/python3.12 scripts/cleanse_apartment_names.py
  arch -arm64 .venv/bin/python3.12 scripts/cleanse_apartment_names.py --dry-run
"""
import sys
import os
import re
import argparse
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from modules.real_estate.config import RealEstateConfig
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.transaction_repository import TransactionRepository


# ── 정규화 함수 ────────────────────────────────────────────────────────────────

def normalize_apt_name(name: str) -> str:
    """아파트 마스터 이름 정규화 (공백 + 괄호 기호 제거, 내용 보존).

    - 공백 제거: "래미안 대치 팰리스" → "래미안대치팰리스"
    - 괄호 기호만 제거: "경희궁자이1단지(임대아파트)" → "경희궁자이1단지임대아파트"
      transactions 정규화와 동일 기준을 맞춰 상호 매핑 가능하게 함
    """
    n = name.strip()
    n = re.sub(r"[()]", "", n)
    n = n.replace(" ", "")
    return n


def normalize_tx_name(name: str) -> str:
    """실거래가 이름 정규화 (공백 제거 + 괄호 기호만 제거, 내용 보존).

    - 괄호 내용은 보존: "경희궁자이(3단지)" → "경희궁자이3단지"
      이유: "(3단지)"와 "(4단지)"는 다른 단지를 가리키므로 제거하면 매핑 오류 발생
    - 공백 제거: "래미안 대치 팰리스" → "래미안대치팰리스"
    """
    n = name.strip()
    n = re.sub(r"[()]", "", n)   # 괄호 기호만 제거, 내용 보존
    n = n.replace(" ", "")
    return n


# ── 클렌징 로직 ────────────────────────────────────────────────────────────────

def cleanse_real_estate_db(db_path: str, dry_run: bool) -> dict:
    """real_estate.db 내 apartments, transactions 테이블 이름 클렌징."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    stats = {
        "apt_changed": 0,
        "tx_changed": 0,
    }

    # ── 1. apartments.apt_name 클렌징 ──────────────────────────────────────────
    apts = conn.execute("SELECT complex_code, apt_name FROM apartments").fetchall()
    apt_updates = []
    for row in apts:
        cleaned = normalize_apt_name(row["apt_name"])
        if cleaned != row["apt_name"]:
            apt_updates.append((cleaned, row["complex_code"]))

    print(f"[apartments] 변경 대상: {len(apt_updates)}건")
    for old_row, (new_name, cc) in zip(
        [r for r in apts if normalize_apt_name(r["apt_name"]) != r["apt_name"]],
        apt_updates[:10],
    ):
        print(f'  [{cc}] "{old_row["apt_name"]}" → "{new_name}"')
    if len(apt_updates) > 10:
        print(f"  ... 외 {len(apt_updates) - 10}건")

    if not dry_run:
        for new_name, cc in apt_updates:
            conn.execute(
                "UPDATE apartments SET apt_name = ? WHERE complex_code = ?",
                (new_name, cc),
            )
        stats["apt_changed"] = len(apt_updates)

    # ── 2. transactions.apt_name 클렌징 ───────────────────────────────────────
    txs = conn.execute("SELECT id, apt_name FROM transactions").fetchall()
    tx_updates = []
    for row in txs:
        cleaned = normalize_tx_name(row["apt_name"])
        if cleaned != row["apt_name"]:
            tx_updates.append((cleaned, row["id"]))

    print(f"\n[transactions] 변경 대상: {len(tx_updates)}건")
    for old_row, (new_name, rid) in zip(
        [r for r in txs if normalize_tx_name(r["apt_name"]) != r["apt_name"]],
        tx_updates[:10],
    ):
        print(f'  [id={rid}] "{old_row["apt_name"]}" → "{new_name}"')
    if len(tx_updates) > 10:
        print(f"  ... 외 {len(tx_updates) - 10}건")

    if not dry_run:
        for new_name, rid in tx_updates:
            conn.execute(
                "UPDATE transactions SET apt_name = ? WHERE id = ?",
                (new_name, rid),
            )
        stats["tx_changed"] = len(tx_updates)

    if not dry_run:
        conn.commit()
    conn.close()
    return stats


def cleanse_apartment_master_db(db_path: str, dry_run: bool) -> dict:
    """apartment_master.db 이름 클렌징.

    cache_key = "{district_code}__{apt_name}" 구조이므로
    cache_key 컬럼도 함께 재구성해야 한다.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT cache_key FROM apartment_master").fetchall()
    updates = []
    for row in rows:
        old_key = row["cache_key"]
        parts = old_key.split("__", 1)
        if len(parts) != 2:
            continue
        district_code, old_name = parts
        new_name = normalize_apt_name(old_name)
        if new_name != old_name:
            new_key = f"{district_code}__{new_name}"
            updates.append((new_key, new_name, old_key))

    print(f"\n[apartment_master.db] 변경 대상: {len(updates)}건")
    for new_key, new_name, old_key in updates[:10]:
        print(f'  "{old_key}" → "{new_key}"')
    if len(updates) > 10:
        print(f"  ... 외 {len(updates) - 10}건")

    if not dry_run:
        updated = 0
        skipped = 0
        for new_key, new_name, old_key in updates:
            # new_key가 이미 존재하면 중복 → 구버전(old_key) 삭제
            exists = conn.execute(
                "SELECT 1 FROM apartment_master WHERE cache_key = ?", (new_key,)
            ).fetchone()
            if exists:
                conn.execute(
                    "DELETE FROM apartment_master WHERE cache_key = ?", (old_key,)
                )
                skipped += 1
            else:
                conn.execute(
                    "UPDATE apartment_master SET cache_key = ? WHERE cache_key = ?",
                    (new_key, old_key),
                )
                updated += 1
        conn.commit()
        print(f"  → 갱신 {updated}건, 중복 삭제 {skipped}건")

    conn.close()
    return {"master_changed": len(updates)}


def run_resolve(db_path: str) -> int:
    """클렌징 후 complex_code NULL 재해소."""
    apt_repo = ApartmentRepository(db_path=db_path)
    tx_repo = TransactionRepository(db_path=db_path)

    before = _count_null(db_path)
    resolved = tx_repo.resolve_complex_codes(apt_repo)
    after = _count_null(db_path)
    print(f"\n[resolve_complex_codes]")
    print(f"  before NULL: {before}건")
    print(f"  resolved:    {resolved}건")
    print(f"  after NULL:  {after}건")
    return resolved


def _count_null(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    n = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE complex_code IS NULL"
    ).fetchone()[0]
    conn.close()
    return n


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="아파트 이름 데이터 클렌징")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 변경 대상만 출력")
    args = parser.parse_args()

    cfg = RealEstateConfig()
    re_db = cfg.get("real_estate_db_path", "data/real_estate.db")
    master_db = cfg.get("apartment_master_db_path", "data/apartment_master.db")

    print("=" * 60)
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}아파트 이름 클렌징 시작")
    print(f"  real_estate.db:    {re_db}")
    print(f"  apartment_master:  {master_db}")
    print("=" * 60)

    # 1. real_estate.db 클렌징
    re_stats = cleanse_real_estate_db(re_db, args.dry_run)

    # 2. apartment_master.db 클렌징
    master_stats = cleanse_apartment_master_db(master_db, args.dry_run)

    # 3. resolve_complex_codes (실제 실행 시)
    if not args.dry_run:
        run_resolve(re_db)

    # 결과 요약
    print("\n" + "=" * 60)
    print("클렌징 결과 요약")
    print(f"  apartments    변경: {re_stats['apt_changed']}건")
    print(f"  transactions  변경: {re_stats['tx_changed']}건")
    print(f"  master_db     변경: {master_stats['master_changed']}건")
    if args.dry_run:
        print("\n  ※ --dry-run 모드 — DB 변경 없음. 실제 적용하려면 --dry-run 제거")
    print("=" * 60)


if __name__ == "__main__":
    main()
