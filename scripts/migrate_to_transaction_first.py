"""
마이그레이션: Transaction-First 아키텍처 전환

실행: arch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py
옵션: --dry-run   실제 변경 없이 결과 미리보기

단계:
  Step 1: apt_master 테이블 생성 + transactions에서 초기 적재
  Step 2: apt_master.complex_code 채우기 (기존 transactions.complex_code)
  Step 3: transactions.apt_master_id 컬럼 추가 + 채우기

참고: apartments 테이블은 유지 (apt_details 리네임은 별도 cleanup 작업)
"""
import argparse
import sqlite3
import sys
import os

# 프로젝트 루트 기준 src/ 경로 등록
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "src"))

from modules.real_estate.config import RealEstateConfig


def _get_db_path() -> str:
    cfg = RealEstateConfig()
    return cfg.get("real_estate_db_path", "data/real_estate.db")


def migrate(db_path: str, dry_run: bool = False) -> dict:
    """apt_master 테이블 생성 및 transactions 기반 초기 적재.

    Returns:
        dict: 각 단계 결과 요약
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    results = {}

    try:
        # ── Step 1: apt_master 테이블 생성 ─────────────────────────────────
        print("[Step 1] apt_master 테이블 생성...")
        create_sql = """
        CREATE TABLE IF NOT EXISTS apt_master (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            apt_name      TEXT NOT NULL,
            district_code TEXT NOT NULL,
            sido          TEXT NOT NULL DEFAULT '',
            sigungu       TEXT NOT NULL DEFAULT '',
            complex_code  TEXT,
            tx_count      INTEGER DEFAULT 0,
            first_traded  TEXT,
            last_traded   TEXT,
            created_at    TEXT NOT NULL,
            UNIQUE(apt_name, district_code)
        );
        CREATE INDEX IF NOT EXISTS idx_am_district ON apt_master(district_code);
        CREATE INDEX IF NOT EXISTS idx_am_sido     ON apt_master(sido);
        CREATE INDEX IF NOT EXISTS idx_am_sigungu  ON apt_master(sigungu);
        CREATE INDEX IF NOT EXISTS idx_am_name     ON apt_master(apt_name);
        """
        if not dry_run:
            conn.executescript(create_sql)
        print("  → apt_master 테이블 준비 완료")

        # ── Step 2: transactions → apt_master 초기 적재 ────────────────────
        print("[Step 2] transactions 기반 apt_master 초기 적재...")

        # 전체 트랜잭션 단지 수 확인
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        unique_pairs = conn.execute(
            "SELECT COUNT(DISTINCT apt_name || '||' || district_code) FROM transactions"
        ).fetchone()[0]
        print(f"  → 전체 거래: {tx_count:,}건, 유니크 단지: {unique_pairs:,}개")

        # apartments 테이블 존재 여부 확인 (LEFT JOIN 가능 여부)
        has_apartments = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='apartments'"
        ).fetchone() is not None

        if has_apartments:
            insert_sql = """
            INSERT OR IGNORE INTO apt_master
                (apt_name, district_code, sido, sigungu, tx_count, first_traded, last_traded, created_at)
            SELECT
                t.apt_name,
                t.district_code,
                COALESCE(a.sido, '')    AS sido,
                COALESCE(a.sigungu, '') AS sigungu,
                COUNT(*)               AS tx_count,
                MIN(t.deal_date)       AS first_traded,
                MAX(t.deal_date)       AS last_traded,
                datetime('now')        AS created_at
            FROM transactions t
            LEFT JOIN apartments a ON t.complex_code = a.complex_code
            GROUP BY t.apt_name, t.district_code
            """
            print("  → apartments LEFT JOIN으로 sido/sigungu 보강 적재")
        else:
            insert_sql = """
            INSERT OR IGNORE INTO apt_master
                (apt_name, district_code, sido, sigungu, tx_count, first_traded, last_traded, created_at)
            SELECT
                apt_name, district_code, '', '',
                COUNT(*), MIN(deal_date), MAX(deal_date), datetime('now')
            FROM transactions
            GROUP BY apt_name, district_code
            """
            print("  → apartments 테이블 없음: sido/sigungu 빈 값으로 적재")

        if dry_run:
            inserted = unique_pairs
        else:
            before = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
            conn.execute(insert_sql)
            conn.commit()
            after = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
            inserted = after - before

        results["step2_inserted"] = inserted
        print(f"  → apt_master {inserted:,}건 신규 삽입")

        # ── Step 3: apt_master.complex_code 채우기 ─────────────────────────
        print("[Step 3] apt_master.complex_code 채우기...")
        fill_sql = """
        UPDATE apt_master SET complex_code = (
            SELECT complex_code FROM transactions
            WHERE apt_name      = apt_master.apt_name
              AND district_code = apt_master.district_code
              AND complex_code IS NOT NULL
            LIMIT 1
        )
        WHERE complex_code IS NULL
        """
        if dry_run:
            # dry-run: apt_master 미존재 — transactions에서 직접 추정
            total_pairs = unique_pairs
            fillable = conn.execute("""
                SELECT COUNT(DISTINCT apt_name || '||' || district_code)
                FROM transactions
                WHERE complex_code IS NOT NULL
            """).fetchone()[0]
            filled = fillable
            null_after = total_pairs - filled
        else:
            null_before = conn.execute(
                "SELECT COUNT(*) FROM apt_master WHERE complex_code IS NULL"
            ).fetchone()[0]
            conn.execute(fill_sql)
            conn.commit()
            null_after = conn.execute(
                "SELECT COUNT(*) FROM apt_master WHERE complex_code IS NULL"
            ).fetchone()[0]
            filled = null_before - null_after

        results["step3_complex_code_filled"] = filled
        results["step3_still_null"] = null_after
        print(f"  → complex_code 채움: {filled:,}개, 여전히 NULL: {null_after:,}개")

        # ── Step 4: transactions.apt_master_id 컬럼 추가 + 채우기 ─────────
        print("[Step 4] transactions.apt_master_id 컬럼 추가 및 채우기...")

        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()
        }
        if "apt_master_id" not in existing_cols:
            if not dry_run:
                conn.execute(
                    "ALTER TABLE transactions ADD COLUMN apt_master_id INTEGER "
                    "REFERENCES apt_master(id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tx_apt_master "
                    "ON transactions(apt_master_id)"
                )
                conn.commit()
            print("  → apt_master_id 컬럼 신규 추가")
        else:
            print("  → apt_master_id 컬럼 이미 존재")

        # apt_master_id 채우기
        fill_id_sql = """
        UPDATE transactions SET apt_master_id = (
            SELECT id FROM apt_master
            WHERE apt_name      = transactions.apt_name
              AND district_code = transactions.district_code
            LIMIT 1
        )
        WHERE apt_master_id IS NULL
        """
        if dry_run:
            # dry-run: 컬럼 미존재 — 전체 트랜잭션 수를 채울 대상으로 추정
            tx_filled = tx_count
            null_tx_after = 0
        else:
            null_tx_before = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE apt_master_id IS NULL"
            ).fetchone()[0]
            conn.execute(fill_id_sql)
            conn.commit()
            null_tx_after = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE apt_master_id IS NULL"
            ).fetchone()[0]
            tx_filled = null_tx_before - null_tx_after

        results["step4_tx_filled"] = tx_filled
        results["step4_tx_still_null"] = null_tx_after
        print(f"  → transactions.apt_master_id 채움: {tx_filled:,}건, NULL 잔여: {null_tx_after:,}건")

        # ── 최종 요약 ──────────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("마이그레이션 완료" if not dry_run else "Dry-run 시뮬레이션 완료")
        print("=" * 60)
        if dry_run:
            apt_master_total = results["step2_inserted"]
        else:
            apt_master_total = conn.execute("SELECT COUNT(*) FROM apt_master").fetchone()[0]
        tx_total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        print(f"  apt_master 총 단지:    {apt_master_total:>8,}개")
        print(f"  transactions 총 거래:  {tx_total:>8,}건")
        mapping_rate = (
            f"{(apt_master_total - results['step3_still_null']) / apt_master_total * 100:.1f}%"
            if apt_master_total > 0 else "N/A"
        )
        print(f"  complex_code 매핑률:   {mapping_rate}")
        print(f"  apt_master_id NULL:    {results['step4_tx_still_null']:>8,}건")

        results["apt_master_total"] = apt_master_total
        results["tx_total"] = tx_total

    finally:
        conn.close()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Transaction-First 아키텍처 마이그레이션"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 변경 없이 결과를 미리 확인"
    )
    parser.add_argument(
        "--db-path", type=str, default=None,
        help="DB 파일 경로 (기본: config.yaml의 real_estate_db_path)"
    )
    args = parser.parse_args()

    db_path = args.db_path or _get_db_path()
    print(f"DB: {db_path}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'EXECUTE'}")
    print()

    if not os.path.exists(db_path):
        print(f"[ERROR] DB 파일을 찾을 수 없습니다: {db_path}")
        sys.exit(1)

    migrate(db_path=db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
