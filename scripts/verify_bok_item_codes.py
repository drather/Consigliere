"""
BOK ECOS item_code 사전 검증 스크립트.
실행: arch -arm64 .venv/bin/python3.12 scripts/verify_bok_item_codes.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from modules.macro.bok_client import BOKClient

STAT_CODES_TO_VERIFY = [
    ("121Y013", "COFIX 신규취급액"),
    ("600Y001", "가계신용"),
    ("901Y062", "주택매매가격지수"),
    ("901Y063", "전세가격지수"),
    ("902Y009", "소비자물가지수(CPI)"),
    ("200Y001", "GDP 성장률"),
]

def main():
    client = BOKClient()
    for code, name in STAT_CODES_TO_VERIFY:
        print(f"\n{'='*60}")
        print(f"[{code}] {name}")
        rows = client.get_statistic_series(code, item_code="?", months=1)
        if not rows:
            print("  ⚠️  데이터 없음 (sample key 한도 또는 코드 오류)")
            continue
        for r in rows[:5]:
            print(f"  item_code: {r.get('ITEM_CODE1', r.get('STAT_CODE', '?'))} "
                  f"| TIME: {r.get('TIME')} | VALUE: {r.get('DATA_VALUE')} "
                  f"| 항목명: {r.get('ITEM_NAME1', '')}")

if __name__ == "__main__":
    main()
