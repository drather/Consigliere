"""
BOK ECOS 지표 초기 시딩 스크립트.
실행: arch -arm64 .venv/bin/python3.12 scripts/seed_macro_indicators.py
중복 실행 시 이미 존재하는 지표는 건너뜀.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from datetime import datetime, timezone
from modules.macro.models import MacroIndicatorDef
from modules.macro.repository import MacroRepository

NOW = datetime.now(timezone.utc).isoformat()

# item_code 검증 상태:
# ✅ sample key로 확인 완료
# 📋 BOK 문서 기반 (실키 환경에서 재확인 권장)
INDICATORS = [
    MacroIndicatorDef(id=None, code="722Y001",  item_code="0101000",       # ✅
                      name="한국은행 기준금리",         unit="%",    frequency="M",
                      collect_every_days=30, domain="common",        category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="121Y002",  item_code="BEABAA2",       # ✅
                      name="예금은행 주택담보대출 금리", unit="%",    frequency="M",
                      collect_every_days=30, domain="real_estate",   category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="121Y013",  item_code="BECBBA",        # 📋 COFIX 신규취급액
                      name="COFIX 신규취급액 기준금리", unit="%",    frequency="M",
                      collect_every_days=30, domain="real_estate",   category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="101Y001",  item_code="BBGS00",        # 📋 M2 계절조정
                      name="M2 통화량(기말, 계절조정)", unit="십억원", frequency="M",
                      collect_every_days=30, domain="common",        category="유동성",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="600Y001",  item_code="?",             # 📋 전체 항목 조회
                      name="가계신용 총량",              unit="십억원", frequency="Q",
                      collect_every_days=90, domain="common",        category="유동성",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="901Y062",  item_code="P63A",          # ✅ 총지수
                      name="주택매매가격지수(전국)",     unit="지수",  frequency="M",
                      collect_every_days=30, domain="real_estate",   category="주택시장",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="901Y063",  item_code="P64A",          # ✅ 총지수
                      name="전세가격지수(전국)",          unit="지수",  frequency="M",
                      collect_every_days=30, domain="real_estate",   category="주택시장",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="902Y009",  item_code="0",             # 📋 총지수
                      name="소비자물가지수(CPI)",         unit="지수",  frequency="M",
                      collect_every_days=30, domain="common",        category="물가",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="200Y001",  item_code="10101",         # 📋 실질GDP 전기비
                      name="실질GDP 성장률",              unit="%",    frequency="Q",
                      collect_every_days=90, domain="common",        category="경기",
                      is_active=True, last_collected_at=None, created_at=NOW),
]


def main():
    db_path = os.getenv("MACRO_DB_PATH", "data/macro.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    repo = MacroRepository(db_path=db_path)

    for ind in INDICATORS:
        try:
            new_id = repo.insert_indicator(ind)
            print(f"✅ [{new_id}] {ind.name} ({ind.code}/{ind.item_code})")
        except Exception as e:
            print(f"⚠️  Skip: {ind.name} — {e}")

    total = len(repo.get_active_indicators())
    print(f"\n📊 총 활성 지표: {total}개")


if __name__ == "__main__":
    main()
