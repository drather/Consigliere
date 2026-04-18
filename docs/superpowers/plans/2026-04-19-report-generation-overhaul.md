# 부동산 인사이트 리포트 생성 전면 점검 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ChromaDB→SQLite 전환, apt_master enrich 수정, 거시경제 반영, LLM 2회→1회 통합으로 리포트 품질과 토큰 효율을 동시에 개선한다.

**Architecture:** Python이 모든 데이터(실거래가·세대수·거시경제·호재)를 준비하고 LLM 1회 호출로 자연어 서술만 담당한다. `ScoringEngine`과 `CandidateFilter`는 변경 없이 유지한다.

**Tech Stack:** Python 3.12, SQLite (real_estate.db / macro.db), Gemini Flash 2.5 (via `BaseLLMClient`), pytest

---

## 변경 파일 목록

| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/calculator.py` | `calculate_budget()` — `mortgage_rate` 파라미터 추가 |
| `src/modules/real_estate/service.py` | `generate_report()` SQLite 전환, `_lookup_apt_details()`, `_format_macro_summary()`, `_extract_horea_data()` 추가 |
| `src/modules/real_estate/insight_orchestrator.py` | `generate_strategy()` 시그니처 변경, `_analyze_horea()` 제거 |
| `src/modules/real_estate/prompts/report_synthesizer.md` | `macro_summary`, `horea_text` 섹션 추가 |
| `tests/modules/real_estate/test_calculator_macro_rate.py` | 신규 |
| `tests/modules/real_estate/test_report_helpers.py` | 신규 |
| `tests/modules/real_estate/test_enrich_apt_details.py` | 신규 |
| `tests/modules/real_estate/test_orchestrator_single_llm.py` | 신규 |

---

## Task 1: `FinancialCalculator.calculate_budget()` — mortgage_rate 파라미터

**Files:**
- Modify: `src/modules/real_estate/calculator.py`
- Test: `tests/modules/real_estate/test_calculator_macro_rate.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_calculator_macro_rate.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.calculator import FinancialCalculator

PERSONA = {
    "user": {
        "assets": {"total": 300_000_000},
        "income": {"total": 160_000_000},
        "plans": {"is_first_time_buyer": True},
    }
}
POLICY = {"ltv": {"first_time_buyer": "80%"}, "dsr": {"limit": "40%"}}


def test_calculate_budget_accepts_mortgage_rate():
    """mortgage_rate 파라미터를 받으면 DSR 계산에 반영된다."""
    calc = FinancialCalculator()
    plan_high = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.06)
    plan_low  = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.03)
    # 금리가 낮으면 DSR 한도 대출이 더 크다 → DSR 기준 최대가
    assert plan_low.max_price_dsr > plan_high.max_price_dsr


def test_calculate_budget_default_rate_unchanged():
    """mortgage_rate 생략 시 기존 기본값(config) 동작과 동일하다."""
    calc = FinancialCalculator()
    plan_default = calc.calculate_budget(PERSONA, POLICY)
    plan_explicit = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=calc.default_interest_rate)
    assert plan_default.final_max_price == plan_explicit.final_max_price


def test_calculate_budget_reasoning_includes_rate():
    """reasoning 문자열에 사용된 금리가 포함된다."""
    calc = FinancialCalculator()
    plan = calc.calculate_budget(PERSONA, POLICY, mortgage_rate=0.042)
    assert "4.2%" in plan.reasoning or "0.042" in plan.reasoning or "주담대" in plan.reasoning
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_calculator_macro_rate.py -v
```
Expected: FAIL — `TypeError: calculate_budget() got an unexpected keyword argument 'mortgage_rate'`

- [ ] **Step 3: calculator.py 수정**

`calculate_budget()` 시그니처에 `mortgage_rate: float = None` 추가, DSR 계산에 반영:

```python
def calculate_budget(
    self,
    persona: Dict[str, Any],
    policy: Dict[str, Any],
    mortgage_rate: float = None,      # ← 추가: MacroRepository 최신 주담대금리
) -> BudgetPlan:
    try:
        data = persona.get("user", persona)
        capital = data.get("assets", {}).get("total", 0)
        income = data.get("income", {}).get("total", 0)
        is_first_time = data.get("plans", {}).get("is_first_time_buyer", False)

        ltv_dict = policy.get("ltv", {})
        if is_first_time:
            ltv_str = ltv_dict.get("first_time_buyer", "80%")
        else:
            ltv_str = ltv_dict.get("non_regulated_area", "70%")

        ltv_rate = self._parse_numeric(ltv_str) or 0.7
        if not (0.3 <= ltv_rate <= 0.9):
            logger.warning(f"⚠️ [Calculator] Abnormal LTV rate {ltv_rate:.2f}, falling back to 0.7")
            ltv_rate = 0.7

        dsr_str = policy.get("dsr", {}).get("limit", "40%")
        dsr_rate = self._parse_numeric(dsr_str) or 0.4
        if not (0.3 <= dsr_rate <= 0.6):
            logger.warning(f"⚠️ [Calculator] Abnormal DSR rate {dsr_rate:.4f}, falling back to 0.4")
            dsr_rate = 0.4

        first_time_loan_cap = 600_000_000

        max_p_ltv = int(capital / (1 - ltv_rate + self.tax_rate_multiplier))
        loan_ltv = int(max_p_ltv * ltv_rate)

        if is_first_time and loan_ltv > first_time_loan_cap:
            loan_ltv = first_time_loan_cap
            max_p_ltv = int((capital + loan_ltv) / (1 + self.tax_rate_multiplier))

        # mortgage_rate 파라미터 우선, 없으면 config 기본값 사용
        interest_rate = mortgage_rate if mortgage_rate is not None else self.default_interest_rate
        years = self.default_loan_term
        annual_payment = income * dsr_rate
        monthly_payment = annual_payment / 12
        monthly_rate = interest_rate / 12
        n_payments = years * 12

        max_loan_dsr = int((monthly_payment * (1 - (1 + monthly_rate)**(-n_payments))) / monthly_rate)
        max_p_dsr = int((capital + max_loan_dsr) / (1 + self.tax_rate_multiplier))

        final_max_price = min(max_p_ltv, max_p_dsr)
        estimated_loan = min(loan_ltv, max_loan_dsr)
        estimated_taxes = int(final_max_price * self.tax_rate_multiplier)

        _억 = 100_000_000
        rate_pct = round(interest_rate * 100, 2)
        reasoning = (
            f"총 자산 {capital/_억:.1f}억원, 연소득 {income/_억:.1f}억원 기준 (주담대금리 {rate_pct}%).\n"
            f"- LTV ({ltv_rate*100:.0f}%) 한도: {max_p_ltv/_억:.2f}억원 (대출 {loan_ltv/_억:.2f}억원)\n"
            f"- DSR ({dsr_rate*100:.0f}%) 한도: {max_p_dsr/_억:.2f}억원 (대출 {max_loan_dsr/_억:.2f}억원)\n"
            f"☞ 최종 보수적 매수 한도: {final_max_price/_억:.2f}억원 (예상 부대비용: {estimated_taxes/_억:.2f}억원)"
        )

        logger.info(f"🧮 [FinancialCalculator] Max Price: {final_max_price:,} KRW (rate={rate_pct}%)")

        return BudgetPlan(
            available_cash=capital - estimated_taxes,
            max_price_ltv=max_p_ltv,
            max_price_dsr=max_p_dsr,
            final_max_price=final_max_price,
            estimated_loan=estimated_loan,
            estimated_taxes=estimated_taxes,
            reasoning=reasoning,
        )

    except Exception as e:
        logger.error(f"❌ [FinancialCalculator] Failed to calculate budget: {e}")
        raise
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_calculator_macro_rate.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: 회귀 테스트**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e -q
```
Expected: 기존 테스트 모두 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/calculator.py tests/modules/real_estate/test_calculator_macro_rate.py
git commit -m "feat(calculator): mortgage_rate 파라미터 추가 — MacroRepository 금리 주입 지원"
```

---

## Task 2: service.py — `_format_macro_summary()` + `_extract_horea_data()` 헬퍼

**Files:**
- Modify: `src/modules/real_estate/service.py`
- Test: `tests/modules/real_estate/test_report_helpers.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_report_helpers.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.service import RealEstateAgent


def _make_agent():
    agent = object.__new__(RealEstateAgent)
    return agent


MACRO_DATA = {
    "base_rate": {"name": "기준금리", "value": 3.0, "unit": "%", "date": "2026-04"},
    "loan_rate": {"name": "주담대금리", "value": 4.2, "unit": "%", "date": "2026-04"},
    "m2_growth": {"name": "M2", "value": 4200000, "unit": "십억원", "date": "2026-04"},
}


def test_format_macro_summary_contains_base_rate():
    agent = _make_agent()
    summary = agent._format_macro_summary(MACRO_DATA)
    assert "3.0" in summary
    assert "기준금리" in summary


def test_format_macro_summary_contains_loan_rate():
    agent = _make_agent()
    summary = agent._format_macro_summary(MACRO_DATA)
    assert "4.2" in summary
    assert "주담대" in summary


def test_format_macro_summary_empty_returns_empty():
    agent = _make_agent()
    assert agent._format_macro_summary({}) == ""
    assert agent._format_macro_summary(None) == ""


def test_extract_horea_data_finds_gtx():
    agent = _make_agent()
    news = "GTX-A 수서역 착공 소식이 전해졌다. 송파구 잠실 일대 수혜 예상."
    result = agent._extract_horea_data(news, ["송파구"])
    assert "송파구" in result
    assert result["송파구"]["gtx"] is True
    assert len(result["송파구"]["items"]) > 0


def test_extract_horea_data_finds_reconstruction():
    agent = _make_agent()
    news = "서초구 반포주공 재건축 사업 인허가 완료. 2030년 완공 예정."
    result = agent._extract_horea_data(news, ["서초구"])
    assert "서초구" in result
    assert len(result["서초구"]["items"]) > 0


def test_extract_horea_data_no_match_returns_empty():
    agent = _make_agent()
    news = "코스피가 하락했다."
    result = agent._extract_horea_data(news, ["송파구"])
    assert result == {}


def test_extract_horea_data_formats_for_prompt():
    agent = _make_agent()
    news = "GTX-A 수서역 착공 확정. 송파구 수혜 기대."
    result = agent._extract_horea_data(news, ["송파구"])
    text = agent._horea_data_to_text(result)
    assert "송파구" in text
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_helpers.py -v
```
Expected: FAIL — `AttributeError: _format_macro_summary`

- [ ] **Step 3: service.py에 두 헬퍼 메서드 추가**

`RealEstateAgent` 클래스에 아래 메서드를 추가한다 (`_load_persona` 이후 위치):

```python
def _format_macro_summary(self, macro_data: Optional[Dict[str, Any]]) -> str:
    """MacroService.fetch_latest_macro_data() 결과 → 프롬프트용 텍스트."""
    if not macro_data:
        return ""
    lines = []
    entry = macro_data.get("base_rate")
    if entry and entry.get("value") is not None:
        lines.append(f"- 기준금리: {entry['value']}% ({entry.get('date', '')})")
    entry = macro_data.get("loan_rate")
    if entry and entry.get("value") is not None:
        lines.append(f"- 주담대금리(주택담보대출): {entry['value']}% ({entry.get('date', '')})")
    entry = macro_data.get("m2_growth")
    if entry and entry.get("value") is not None:
        lines.append(f"- M2 통화량: {entry['value']:,}{entry.get('unit', '')} ({entry.get('date', '')})")
    return "\n".join(lines)

def _extract_horea_data(self, news_text: str, interest_areas: List[str]) -> Dict[str, Any]:
    """뉴스 텍스트에서 지역별 호재 정보를 Python 키워드 매칭으로 추출한다.
    반환 형식은 ScoringEngine.score_all()의 horea_data 포맷과 호환된다.
    """
    GTX_KW = ["GTX", "광역급행철도"]
    HOREA_KW = ["재건축", "재개발", "정비사업", "지구지정", "개발사업", "신도시", "택지지구",
                "학군", "학교신설", "착공", "개통", "노선"]
    result: Dict[str, Any] = {}
    sentences = [s.strip() for s in news_text.replace("\n", ".").split(".") if s.strip()]
    for area in interest_areas:
        items, has_gtx = [], False
        for sent in sentences:
            if area not in sent:
                continue
            if any(kw in sent for kw in GTX_KW):
                has_gtx = True
                items.append(sent)
            elif any(kw in sent for kw in HOREA_KW):
                items.append(sent)
        if items:
            result[area] = {"gtx": has_gtx, "items": items[:5]}
    return result

def _horea_data_to_text(self, horea_data: Dict[str, Any]) -> str:
    """horea_data dict → 프롬프트용 텍스트."""
    if not horea_data:
        return "호재 정보 없음"
    lines = []
    for area, info in horea_data.items():
        gtx_tag = " [GTX 수혜]" if info.get("gtx") else ""
        for item in info.get("items", []):
            lines.append(f"- {area}{gtx_tag}: {item}")
    return "\n".join(lines) if lines else "호재 정보 없음"
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_helpers.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/service.py tests/modules/real_estate/test_report_helpers.py
git commit -m "feat(service): _format_macro_summary / _extract_horea_data 헬퍼 추가"
```

---

## Task 3: service.py — `_lookup_apt_details()` + `_enrich_transactions()` 수정

**Files:**
- Modify: `src/modules/real_estate/service.py`
- Test: `tests/modules/real_estate/test_enrich_apt_details.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_enrich_apt_details.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import ApartmentMaster, AptMasterEntry
from modules.real_estate.service import RealEstateAgent
from datetime import timezone, datetime


def _make_agent(apt_repo, apt_master_repo):
    agent = object.__new__(RealEstateAgent)
    agent.apt_repo = apt_repo
    agent.apt_master_repo = apt_master_repo
    return agent


def _make_apt_master(complex_code="K001", apt_name="테스트아파트", district_code="11680",
                     household_count=600, constructor="현대건설", approved_date="20100101"):
    return ApartmentMaster(
        complex_code=complex_code, apt_name=apt_name, district_code=district_code,
        household_count=household_count, building_count=5, parking_count=0,
        constructor=constructor, approved_date=approved_date,
    )


def test_lookup_apt_details_via_complex_code():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")
    
    apt_repo.save(_make_apt_master())
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="테스트아파트", district_code="11680", complex_code="K001",
        created_at=datetime.now(timezone.utc).isoformat()
    ))
    
    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("테스트아파트", "11680")
    
    assert result is not None
    assert result.household_count == 600
    assert result.constructor == "현대건설"


def test_lookup_apt_details_fallback_search():
    """complex_code 없어도 apt_repo 부분 검색으로 찾는다."""
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")
    
    apt_repo.save(_make_apt_master(apt_name="래미안아파트"))
    # apt_master_repo에 complex_code 없이 등록
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="래미안아파트", district_code="11680", complex_code=None,
        created_at=datetime.now(timezone.utc).isoformat()
    ))
    
    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("래미안아파트", "11680")
    
    assert result is not None
    assert result.household_count == 600


def test_lookup_apt_details_returns_none_when_missing():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")
    agent = _make_agent(apt_repo, apt_master_repo)
    
    result = agent._lookup_apt_details("없는아파트", "11680")
    assert result is None


def test_enrich_transactions_sets_household_count():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")
    
    apt_repo.save(_make_apt_master())
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="테스트아파트", district_code="11680", complex_code="K001",
        created_at=datetime.now(timezone.utc).isoformat()
    ))
    
    agent = _make_agent(apt_repo, apt_master_repo)
    txs = [{"apt_name": "테스트아파트", "district_code": "11680", "price": 500_000_000}]
    enriched = agent._enrich_transactions(txs, {})
    
    assert enriched[0]["household_count"] == 600
    assert enriched[0]["constructor"] == "현대건설"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_enrich_apt_details.py -v
```
Expected: FAIL — `AttributeError: _lookup_apt_details`

- [ ] **Step 3: service.py — `_lookup_apt_details()` 추가 및 `_enrich_transactions()` 수정**

`RealEstateAgent` 클래스에 아래 메서드를 추가한다:

```python
def _lookup_apt_details(self, apt_name: str, district_code: str) -> Optional[Any]:
    """apt_master_repo + apt_repo 2단계 조회로 ApartmentMaster 반환.
    1) apt_master_repo에서 complex_code 조회
    2) complex_code → apt_repo.get() 정확 조회
    3) 없으면 apt_repo.search() 부분 매칭 fallback
    """
    entry = self.apt_master_repo.get_by_name_district(apt_name, district_code)
    if entry and entry.complex_code:
        detail = self.apt_repo.get(entry.complex_code)
        if detail:
            return detail
    results = self.apt_repo.search(apt_name=apt_name, district_code=district_code, limit=1)
    return results[0] if results else None
```

그리고 `_enrich_transactions()` 내부의 아파트 마스터 조회 블록을 교체한다:

```python
# 기존 (제거):
try:
    master = self.apt_master_service.get_or_fetch(apt_name, district_code)
    if master:
        tx["household_count"] = master.household_count
        tx["building_count"] = master.building_count
        tx["constructor"] = master.constructor
        tx["approved_date"] = master.approved_date
except Exception as e:
    logger.warning(f"[Enrich] 마스터 조회 실패 {apt_name}: {e}")

# 교체 (신규):
try:
    detail = self._lookup_apt_details(apt_name, district_code)
    if detail:
        tx["household_count"] = detail.household_count
        tx["building_count"] = detail.building_count
        tx["constructor"] = detail.constructor
        tx["approved_date"] = detail.approved_date
except Exception as e:
    logger.warning(f"[Enrich] apt_details 조회 실패 {apt_name}: {e}")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_enrich_apt_details.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: 전체 회귀 테스트**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e -q
```
Expected: 기존 테스트 모두 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/service.py tests/modules/real_estate/test_enrich_apt_details.py
git commit -m "fix(service): apt_master enrich를 apt_master_repo+apt_repo SQLite 직접 조회로 교체"
```

---

## Task 4: service.py — `generate_report()` ChromaDB → tx_repo + 가격 ±10% 필터

**Files:**
- Modify: `src/modules/real_estate/service.py`

- [ ] **Step 1: `generate_report()` 전체 교체**

`service.py`의 `generate_report()` 메서드를 아래로 교체한다:

```python
def generate_report(self, district_code: Optional[str] = None, target_date: Optional[date] = None) -> Dict[str, Any]:
    """Job 4: SQLite tx_repo 기반 인사이트 리포트 생성.

    district_code=None → persona.interest_areas 기반 구 동시 수집
    district_code 지정 → 해당 구만 수집
    """
    from dataclasses import asdict
    if target_date is None:
        target_date = date.today()
    logger.info(f"[Job4] Generating report for {target_date}, district_code={district_code}")

    # 1. 뉴스/거시경제 로드
    news_text = self._load_stored_news(target_date)
    macro_data = self._load_stored_macro(target_date) or {}

    # 2. 거시경제 금리 추출 → 예산 계산
    from core.policy_fetcher import fetch_latest_financial_policies
    policy_context = fetch_latest_financial_policies()
    persona_data = self._load_persona()

    mortgage_rate = None
    loan_entry = macro_data.get("loan_rate", {})
    if loan_entry and loan_entry.get("value") is not None:
        mortgage_rate = float(loan_entry["value"]) / 100.0  # % → 소수
        logger.info(f"[Job4] 주담대금리 {loan_entry['value']}% 적용")

    budget_plan = self.calculator.calculate_budget(persona_data, policy_context, mortgage_rate=mortgage_rate)
    budget_ceiling = budget_plan.final_max_price

    # 3. 관심 지역 코드 목록
    target_codes = self._resolve_interest_districts(persona_data, district_code)
    logger.info(f"[Job4] districts: {target_codes}")

    # 4. SQLite tx_repo에서 실거래가 조회
    recent_days = self.config.get("report", {}).get("recent_days", 7)
    cutoff = (date.today() - timedelta(days=recent_days)).isoformat()
    all_txs: List[Dict[str, Any]] = []
    for code in target_codes:
        try:
            rows = self.tx_repo.get_by_district(code, limit=200, date_from=cutoff)
            all_txs.extend(asdict(tx) for tx in rows)
        except Exception as e:
            logger.error(f"[Job4] tx_repo 조회 실패 {code}: {e}")

    # 5. 중복 제거
    seen_keys: set = set()
    deduped_txs = []
    for tx in all_txs:
        key = f"{tx.get('apt_name')}_{tx.get('exclusive_area')}_{tx.get('deal_date')}_{tx.get('floor')}"
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_txs.append(tx)

    # 6. 가격 ±10% 밴드 필터 (예산과 관련성 높은 매물만)
    lo, hi = budget_ceiling * 0.9, budget_ceiling * 1.1
    candidates = [tx for tx in deduped_txs if lo <= tx.get("price", 0) <= hi]
    logger.info(f"[Job4] 예산 {budget_ceiling/1e8:.1f}억 ±10% → {len(candidates)}건 (전체 {len(deduped_txs)}건)")

    # 7. area_intel enrich
    area_intel = self._load_area_intel()
    workplace_station = persona_data.get("commute", {}).get("workplace_station", "")
    candidates = self._enrich_transactions(candidates, area_intel, workplace_station)

    # 8. Python 데이터 준비
    interest_areas = persona_data.get("user", {}).get("interest_areas", [])
    horea_data = self._extract_horea_data(news_text, interest_areas) if news_text.strip() else {}
    macro_summary = self._format_macro_summary(macro_data)
    horea_text = self._horea_data_to_text(horea_data)

    # 9. 오케스트레이터에 위임
    preference_rules = PreferenceRulesManager().get()
    report_json = self.insight_orchestrator.generate_strategy(
        target_date=target_date,
        candidates=candidates,
        budget_plan=budget_plan,
        persona_data=persona_data,
        preference_rules=preference_rules,
        scoring_config=self.config.get("scoring", {}),
        report_config=self.config.get("report", {}),
        horea_data=horea_data,
        macro_summary=macro_summary,
        horea_text=horea_text,
    )

    self._save_report(report_json, target_date, len(candidates))
    return {"success": True, "tx_count": len(candidates), "date": target_date.isoformat()}
```

- [ ] **Step 2: 통합 확인 (Docker 환경)**

```bash
docker compose restart api
# FastAPI 로그에서 [Job4] 시작 확인
```

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/service.py
git commit -m "fix(service): generate_report ChromaDB→tx_repo SQLite 전환, 가격 ±10% 필터 적용"
```

---

## Task 5: `InsightOrchestrator` — LLM 1회 통합

**Files:**
- Modify: `src/modules/real_estate/insight_orchestrator.py`
- Test: `tests/modules/real_estate/test_orchestrator_single_llm.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_orchestrator_single_llm.py
import pytest
import sys, os
from datetime import date
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.insight_orchestrator import InsightOrchestrator
from modules.real_estate.calculator import BudgetPlan


def _make_orchestrator():
    llm = MagicMock()
    llm.generate_json.return_value = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "테스트"}}]}
    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "synthesis"}, "test prompt")
    return InsightOrchestrator(llm=llm, prompt_loader=prompt_loader), llm


def _make_budget_plan():
    return BudgetPlan(
        available_cash=274_000_000, max_price_ltv=874_000_000, max_price_dsr=950_000_000,
        final_max_price=874_000_000, estimated_loan=600_000_000, estimated_taxes=26_000_000,
        reasoning="테스트 예산 근거",
    )


def test_generate_strategy_calls_llm_exactly_once():
    """LLM은 정확히 1번만 호출된다 (horea_analyst 제거 확인)."""
    orch, llm = _make_orchestrator()
    candidates = [{"apt_name": "테스트아파트", "price": 800_000_000, "district_code": "11680",
                   "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10}]
    
    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=candidates,
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="- 기준금리: 3.0%\n- 주담대금리: 4.2%",
        horea_text="호재 정보 없음",
    )
    
    assert llm.generate_json.call_count == 1


def test_generate_strategy_prompt_includes_macro_summary():
    """LLM 호출 시 프롬프트에 macro_summary가 전달된다."""
    orch, llm = _make_orchestrator()
    candidates = [{"apt_name": "테스트아파트", "price": 800_000_000, "district_code": "11680",
                   "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10}]
    
    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=candidates,
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="기준금리 3.0%",
        horea_text="호재 없음",
    )
    
    call_args = orch.prompt_loader.load.call_args
    variables = call_args.kwargs.get("variables", {})
    assert "macro_summary" in variables
    assert "기준금리 3.0%" in variables["macro_summary"]


def test_generate_strategy_empty_candidates_returns_empty_report():
    orch, llm = _make_orchestrator()
    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=[],
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
    )
    assert "blocks" in result
    llm.generate_json.assert_not_called()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_orchestrator_single_llm.py -v
```
Expected: FAIL — `TypeError: generate_strategy() got unexpected keyword arguments`

- [ ] **Step 3: `insight_orchestrator.py` 전면 수정**

파일을 아래 내용으로 교체한다:

```python
"""
InsightOrchestrator — 부동산 인사이트 리포트 파이프라인 오케스트레이터

흐름:
  1. Python: preference_rules 필터
  2. Python: ScoringEngine → 상위 N개 선정
  3. LLM #1 (단일): macro_summary + horea_text + scored 결과 → 리포트 서술

horea_data 추출과 macro_summary 포맷팅은 service.py에서 Python으로 수행한다.
"""
import json
from datetime import date
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from .candidate_filter import CandidateFilter
from .scoring import ScoringEngine
from .presenter import RealEstatePresenter

logger = get_logger(__name__)

_억 = 100_000_000


class InsightOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        presenter: Optional[RealEstatePresenter] = None,
    ):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.presenter = presenter or RealEstatePresenter()

    def generate_strategy(
        self,
        target_date: date,
        candidates: List[Dict[str, Any]],
        budget_plan: Any,
        persona_data: Dict[str, Any],
        preference_rules: List[Dict[str, Any]],
        scoring_config: Dict[str, Any],
        report_config: Dict[str, Any],
        horea_data: Dict[str, Any] = None,   # Python 추출 결과
        macro_summary: str = "",              # Python 포맷팅 결과
        horea_text: str = "",                 # horea_data 텍스트 표현
    ) -> Dict[str, Any]:
        horea_data = horea_data or {}
        top_n = report_config.get("top_n", 5)

        # Step 1: preference_rules 필터
        filtered = CandidateFilter(preference_rules).apply(candidates)
        logger.info(f"[Orchestrator] preference_rules 필터 후: {len(filtered)}건")

        if not filtered:
            logger.warning("[Orchestrator] 필터 후 후보 없음 — 빈 리포트 반환")
            return self._empty_report()

        # Step 2: 점수 계산 (Python 수식)
        priority_weights = persona_data.get("priority_weights", {})
        engine = ScoringEngine(weights=priority_weights, config=scoring_config)
        scored = engine.score_all(filtered, horea_data=horea_data)
        top_candidates = scored[:top_n]
        logger.info(f"[Orchestrator] 상위 {len(top_candidates)}개 선정 (전체 {len(scored)}개 중)")

        # Step 3: LLM 단일 호출 — 서술만 담당
        report_json = self._synthesize_report(
            target_date=target_date,
            top_candidates=top_candidates,
            budget_plan=budget_plan,
            persona_data=persona_data,
            top_n=top_n,
            macro_summary=macro_summary,
            horea_text=horea_text,
        )
        return report_json

    def _synthesize_report(
        self,
        target_date: date,
        top_candidates: List[Dict],
        budget_plan: Any,
        persona_data: Dict,
        top_n: int,
        macro_summary: str = "",
        horea_text: str = "",
    ) -> Dict[str, Any]:
        """scored 상위 목록 → Slack Block Kit JSON 리포트 (LLM 1회)."""
        pw = persona_data.get("priority_weights", {})
        total_w = sum(pw.values()) or 1
        label_map = {
            "commute": "출퇴근편의성",
            "liquidity": "환금성",
            "price_potential": "가격상승가능성",
            "living_convenience": "생활편의",
            "school": "학군",
        }
        ranked = sorted(pw.items(), key=lambda x: x[1], reverse=True)
        priority_desc = ", ".join(
            f"{label_map.get(k, k)} {round(v/total_w*100)}%"
            for k, v in ranked
        )

        try:
            metadata, prompt = self.prompt_loader.load(
                "report_synthesizer",
                variables={
                    "target_date": target_date.strftime("%Y-%m-%d"),
                    "budget_reasoning": getattr(budget_plan, "reasoning", ""),
                    "priority_weights_desc": priority_desc,
                    "top_n": top_n,
                    "macro_summary": macro_summary or "거시경제 데이터 없음",
                    "horea_text": horea_text or "호재 정보 없음",
                    "ranked_candidates": json.dumps(
                        top_candidates, ensure_ascii=False, default=str
                    ),
                },
            )
            result = self.llm.generate_json(prompt, metadata=metadata)
            if "blocks" in result:
                return result
            logger.warning("[Orchestrator] Synthesizer 응답에 blocks 없음")
        except Exception as e:
            logger.error(f"[Orchestrator] 리포트 생성 실패: {e}")

        return self._empty_report()

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "blocks": [{
                "type": "section",
                "text": {"type": "mrkdwn", "text": "⚠️ 조건에 맞는 추천 단지가 없습니다."},
            }]
        }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_orchestrator_single_llm.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: 전체 회귀 테스트**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e -q
```
Expected: 기존 테스트 모두 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/insight_orchestrator.py tests/modules/real_estate/test_orchestrator_single_llm.py
git commit -m "refactor(orchestrator): LLM 2회→1회 통합, horea_analyst 제거, macro_summary/horea_text 주입"
```

---

## Task 6: `report_synthesizer.md` 프롬프트 개선

**Files:**
- Modify: `src/modules/real_estate/prompts/report_synthesizer.md`

- [ ] **Step 1: 프롬프트 파일 교체**

```markdown
---
task_type: synthesis
cache_boundary: "## 추천 아파트 목록"
ttl: 3600
---
# 부동산 추천 리포트 작성관

## 역할
Python이 계산한 점수와 데이터를 바탕으로 **읽기 쉬운 아침 브리핑 리포트**를 작성합니다.
점수 결정은 이미 완료되었습니다. 당신의 역할은 데이터를 자연스럽고 유익한 문장으로 서술하는 것입니다.

## 고정 정보 (캐시 가능)

### 기준일
{{target_date}}

### 거시경제 현황
{{macro_summary}}

### 예산 계획
{{budget_reasoning}}

### 사용자 선호 기준 및 가중치
{{priority_weights_desc}}

### 뉴스 호재 정보
{{horea_text}}

---

## 추천 아파트 목록
(Python 점수 기준 상위 {{top_n}}개, 내림차순)

{{ranked_candidates}}

---

## 작업 지침

### 1. 리포트 서두 (2~3문장)
기준일, 분석 대상 지역, 거시경제 핵심 수치(기준금리·주담대금리)를 언급하십시오.

### 2. 예산 요약 (3줄 이내)
`budget_reasoning`을 간결하게 정리하십시오. 주담대금리가 반영되었다면 언급하십시오.

### 3. 추천 단지별 서술
각 단지에 대해 아래 형식으로 작성하십시오:

```
🥇 1위: [단지명] — 종합 {{total_score}}점
실거래가: X억 Y천만원 ({{deal_date}}, {{exclusive_area}}㎡, {{floor}}층)
단지 정보: [constructor] 시공, [approved_date 앞 4자리]년 준공, [household_count]세대 / [building_count]개동
(constructor 또는 approved_date 값이 없으면 해당 항목 생략)

⚡ 출퇴근편의성 ({{commute_score}}점): [commute_minutes]분 소요. [nearest_stations 서술]
💰 환금성 ({{liquidity_score}}점): [household_count]세대. [역세권 여부]
📈 가격상승가능성 ({{price_potential_score}}점): [horea_text의 해당 지역 항목 인용. 없으면 "관련 호재 정보 없음"]
🛍️ 생활편의 ({{living_convenience_score}}점): [역 접근성 서술]
🎒 학군 ({{school_score}}점): [school_zone_notes 인용]
```

- 순위는 🥇🥈🥉 이후 4위부터 숫자로 표기하십시오.
- 각 기준의 점수가 낮은 경우 단점도 함께 서술하십시오.
- `horea_text`에 해당 지역의 호재가 있으면 가격상승가능성 섹션에 반드시 인용하십시오.
- 세대수가 0이거나 없으면 "세대수 미확인"으로 서술하십시오.

### 4. 종합 제언 (3~5문장)
거시경제 현황(금리 수준)을 매수 시점 판단에 연결하여 서술하십시오.
전체 추천 단지의 공통 특징과 매수 시점에 대한 의견을 제시하십시오.

---

## 출력 형식
`{"blocks": [...]}` 형태의 Slack Block Kit JSON으로 응답하십시오.
`section`, `divider`, `header` 타입만 사용하고, 모든 내용은 `mrkdwn` 형식으로 작성하십시오.
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/prompts/report_synthesizer.md
git commit -m "feat(prompt): report_synthesizer에 macro_summary/horea_text 섹션 추가"
```

---

## Task 7: progress.md 업데이트 및 최종 검증

- [ ] **Step 1: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ --ignore=tests/e2e -v
```
Expected: 전체 PASS (새 테스트 14개 + 기존 테스트 모두)

- [ ] **Step 2: progress.md Phase 2 체크리스트 완료 표시**

`docs/features/report-generation-overhaul/progress.md` Phase 2 항목 전체 체크 후 커밋:

```bash
git add docs/features/report-generation-overhaul/progress.md
git commit -m "docs(progress): Phase 2 구현 완료 체크"
```

- [ ] **Step 3: config.yaml 업데이트 (Zero Hardcoding)**

`src/modules/real_estate/config.yaml` 의 `report` 섹션을 수정한다:

```yaml
report:
  recent_days: 7
  top_n: 5               # 10 → 5 변경
  budget_band_ratio: 0.1  # 가격 ±10% 필터 비율 추가
```

그리고 `service.py generate_report()` 내 가격 필터를 config에서 읽도록 수정:

```python
band = self.config.get("report", {}).get("budget_band_ratio", 0.1)
lo, hi = budget_ceiling * (1 - band), budget_ceiling * (1 + band)
```

```bash
git add src/modules/real_estate/config.yaml src/modules/real_estate/service.py
git commit -m "fix(config): top_n 10→5, budget_band_ratio 추가 (Zero Hardcoding)"
```

- [ ] **Step 4: SOLID Review (Phase 2.5)**

- SRP: `_lookup_apt_details()`, `_format_macro_summary()`, `_extract_horea_data()` 각각 단일 책임 ✓
- Zero Hardcoding: top_n, recent_days, budget_band_ratio 모두 config.yaml ✓ (Step 3에서 완료)
- DIP: `_lookup_apt_details()`가 `apt_repo`, `apt_master_repo` 인터페이스에 의존 ✓
- 에러 처리: 각 헬퍼의 try/except 확인 ✓

- [ ] **Step 4: issues.md 작성**

```bash
# docs/features/report-generation-overhaul/issues.md 작성 후 커밋
git add docs/features/report-generation-overhaul/issues.md
git commit -m "docs(issues): 결정사항 및 트레이드오프 기록"
```
