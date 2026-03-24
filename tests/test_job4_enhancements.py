"""
Tests for Job4 Report Enhancement (Phase 1-5)
브랜치: feature/job4-report-enhancement
"""
import os
import sys
import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import types as _types
from modules.real_estate.agents.specialized import CodeBasedValidator
from modules.real_estate import service as _service_mod


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_report(text: str) -> dict:
    return {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]}

def _run(text: str, budget_억: float = 9.0, policy_facts: list = None):
    budget = {"final_max_price": int(budget_억 * 1e8)}
    return CodeBasedValidator().run({
        "budget_plan": budget,
        "generated_report": _make_report(text),
        "policy_facts": policy_facts or [],
    })

def _make_agent_self():
    """RealEstateAgent 메서드들을 바인딩한 더미 self (ChromaDB 없이 동작)."""
    agent = SimpleNamespace()
    agent.repository = MagicMock()
    agent.repository.search_policy.return_value = []
    # service.py의 인스턴스 메서드를 더미 self에 바인딩
    for method_name in ("_compute_district_average", "_deep_merge", "_enrich_transactions",
                        "_load_stored_news", "update_persona", "get_persona", "_load_persona"):
        fn = getattr(_service_mod.RealEstateAgent, method_name, None)
        if fn:
            setattr(agent, method_name, _types.MethodType(fn, agent))
    return agent


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 + 4: CodeBasedValidator — 예산 준수
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgetCompliance:
    def test_hard_over_budget_fail(self):
        """10억 언급 (9억 한도 +11%) → FAIL, score < 75"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분\n10억 단지")
        assert r["status"] == "FAIL"
        assert r["score"] < 75
        assert "10억" in r["feedback"]

    def test_soft_over_budget_score_reduced(self):
        """9.5억 언급 (9억 한도 +5.5%) → 예산점 20점(40점 아님)"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분\n9.5억")
        # 예산 20 + 스코어카드 25 + commute 20 + policy면제 15 = 80 → WARN
        assert r["status"] in ("WARN", "FAIL")
        assert "9.5억" in r["feedback"]

    def test_within_budget_full_score(self):
        """예산 이하 → 예산 40점 만점"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분\n8억 단지")
        assert r["score"] == 100
        assert r["status"] == "PASS"

    def test_small_prices_not_flagged(self):
        """3억 미만 가격(보증금 등)은 예산 체크 대상 제외"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분\n보증금 1억")
        assert r["score"] >= 90

    def test_no_price_in_report_full_budget_score(self):
        """가격 언급 없으면 예산 40점 만점"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분")
        assert r["score"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Validator — 스코어카드 완성도 (25pt)
# ─────────────────────────────────────────────────────────────────────────────

class TestScorecardCompleteness:
    def test_three_ranks_full_score(self):
        """3개 순위 모두 → 25점 만점, score=100"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분")
        assert r["score"] == 100
        assert r["status"] == "PASS"

    def test_two_ranks_penalty(self):
        """2개 순위 → 스코어카드 15점 (25점 아님), 이슈 리스트에 포함"""
        r = _run("1순위: A\n2순위: B\n출퇴근편의성 — 20분")
        # 예산 40 + 스코어카드 15 + commute 20 + policy면제 15 = 90 → PASS지만 최대점 미달
        assert r["score"] < 100

    def test_two_ranks_feedback_contains_third(self):
        """2개 순위 → 피드백에 3순위 누락 메시지 (score < 90인 경우에만 노출)"""
        # score=90이면 feedback 비워짐 (PASS). score<90을 만들려면 다른 항목도 누락해야 함.
        r = _run("1순위: A\n2순위: B")  # commute 없음 → score = 40+15+0+15 = 70 → FAIL
        assert r["score"] < 75
        assert "3순위" in r["feedback"]

    def test_zero_ranks_fail(self):
        """순위 없음 → 스코어카드 0점, 점수 낮음"""
        r = _run("출퇴근편의성 — 20분")
        assert r["score"] < 90
        assert "단지" in r["feedback"] or "3순위" in r["feedback"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Validator — commute_minutes 인용 (20pt)
# ─────────────────────────────────────────────────────────────────────────────

class TestCommuteCitation:
    def test_commute_cited_gives_20pt(self):
        """출퇴근편의성 + 분 수치 → 20점"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 (30점): HIGH — 25분")
        assert r["score"] == 100

    def test_commute_missing_reduces_score(self):
        """출퇴근 미인용 → 20점 감점"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n역세권 좋음")
        # 예산 40 + 스코어카드 25 + commute 0 + policy면제 15 = 80 → WARN
        assert r["score"] == 80
        assert r["status"] == "WARN"

    def test_commute_keyword_without_minutes_not_counted(self):
        """'출퇴근편의성'만 있고 분 수치 없으면 미인용 처리"""
        r = _run("🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성: 우수")
        assert r["score"] < 100  # commute 20pt 없음


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Validator — policy_facts 인용 (15pt)
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyFactsCitation:
    BASE = "🥇 1순위\n🥈 2순위\n🥉 3순위\n출퇴근편의성 — 20분\n"

    def test_policy_term_found_gives_15pt(self):
        """policy_facts 내 키워드가 리포트에 존재 → 15점"""
        facts = [{"content": "GTX-A 수서역 2026년 개통 확정"}]
        r = _run(self.BASE + "수서역 GTX-A 수혜 단지 추천", 9.0, policy_facts=facts)
        assert r["score"] == 100
        assert r["status"] == "PASS"

    def test_policy_term_not_found_reduces_score(self):
        """policy_facts 있지만 리포트에 미인용 → 15점 감점"""
        facts = [{"content": "GTX-A 수서역 2026년 개통"}]
        r = _run(self.BASE, 9.0, policy_facts=facts)
        # 예산 40 + 스코어카드 25 + commute 20 + policy 0 = 85 → WARN
        assert r["score"] == 85
        assert "policy_facts" in r["feedback"]

    def test_empty_policy_facts_exempted(self):
        """policy_facts가 비어있으면 15점 자동 면제"""
        r = _run(self.BASE, 9.0, policy_facts=[])
        assert r["score"] == 100

    def test_3char_korean_term_matched(self):
        """한국어 3글자 이상 키워드 매칭 ('수서역' 등)"""
        facts = [{"content": "수서역 환승 개선"}]
        r = _run(self.BASE + "수서역 인근 단지", 9.0, policy_facts=facts)
        assert r["score"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Budget filter 로직 (service.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestBudgetFilter:
    def test_over_budget_txs_removed(self):
        txs = [
            {"apt_name": "A", "price": 800_000_000},
            {"apt_name": "B", "price": 1_000_000_000},
            {"apt_name": "C", "price": 900_000_000},
        ]
        ceiling = 900_000_000
        filtered = [tx for tx in txs if tx.get("price", 0) <= ceiling]
        assert len(filtered) == 2
        assert "B" not in [tx["apt_name"] for tx in filtered]

    def test_filtered_count_correct(self):
        txs = [{"price": i * 100_000_000} for i in range(1, 11)]  # 1억~10억
        ceiling = 500_000_000  # 5억
        filtered = [tx for tx in txs if tx["price"] <= ceiling]
        assert len(filtered) == 5
        assert len(txs) - len(filtered) == 5  # filtered_tx_count


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: _compute_district_average
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeDistrictAverage:
    @pytest.fixture
    def dist_intel(self):
        return {
            "name": "강남구",
            "default_commute_minutes": 20,
            "dongs": {
                "대치동": {
                    "commute_minutes_to_samsung": 18,
                    "nearest_stations": [{"name": "대치역", "line": "3호선", "walk_minutes": 5}],
                    "school_zone_notes": "대치 학원가",
                    "notable_complexes": ["은마아파트"],
                },
                "역삼동": {
                    "commute_minutes_to_samsung": 12,
                    "nearest_stations": [{"name": "역삼역", "line": "2호선", "walk_minutes": 5}],
                    "school_zone_notes": "역삼 학군",
                    "notable_complexes": ["역삼래미안"],
                },
                "삼성동": {
                    "commute_minutes_to_samsung": 10,
                    "nearest_stations": [{"name": "삼성역", "line": "2호선", "walk_minutes": 5}],
                    "school_zone_notes": "",
                    "notable_complexes": [],
                },
            }
        }

    def test_commute_average(self, dist_intel):
        """(18 + 12 + 10) / 3 = 13"""
        agent = _make_agent_self()
        result = agent._compute_district_average(dist_intel)
        assert result["commute_minutes_to_samsung"] == 13

    def test_stations_deduplicated(self, dist_intel):
        """동별 역 중복 없이 집계"""
        agent = _make_agent_self()
        result = agent._compute_district_average(dist_intel)
        names = [s["name"] for s in result["nearest_stations"]]
        assert len(names) == len(set(names))

    def test_all_stations_collected(self, dist_intel):
        """3개 동 각 1개 역 → 3개 집계"""
        agent = _make_agent_self()
        result = agent._compute_district_average(dist_intel)
        names = [s["name"] for s in result["nearest_stations"]]
        assert "대치역" in names
        assert "역삼역" in names
        assert "삼성역" in names

    def test_empty_dongs_returns_empty(self):
        agent = _make_agent_self()
        result = agent._compute_district_average({"name": "X", "dongs": {}})
        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: _enrich_transactions — fallback 동작
# ─────────────────────────────────────────────────────────────────────────────

class TestEnrichTransactions:
    @pytest.fixture
    def area_intel(self):
        return {
            "districts": {
                "11680": {
                    "name": "강남구",
                    "default_commute_minutes": 20,
                    "dongs": {
                        "대치동": {
                            "commute_minutes_to_samsung": 18,
                            "nearest_stations": [{"name": "대치역", "line": "3호선", "walk_minutes": 5}],
                            "school_zone_notes": "대치 학원가",
                            "elementary_schools": ["대치초"],
                            "notable_complexes": ["은마아파트"],
                        },
                        "역삼동": {
                            "commute_minutes_to_samsung": 12,
                            "nearest_stations": [{"name": "역삼역", "line": "2호선", "walk_minutes": 5}],
                            "school_zone_notes": "역삼 학군",
                            "elementary_schools": ["역삼초"],
                            "notable_complexes": ["역삼래미안"],
                        },
                    }
                }
            },
            "apartment_overrides": {
                "은마아파트": {
                    "reconstruction_status": "안전진단 통과",
                    "reconstruction_potential": "HIGH",
                    "gtx_benefit": False,
                }
            }
        }

    def test_notable_complex_matched_to_dong(self, area_intel):
        """notable_complexes 매칭 → 해당 dong 데이터 사용"""
        agent = _make_agent_self()
        txs = [{"apt_name": "은마아파트", "district_code": "11680", "price": 700_000_000}]
        result = agent._enrich_transactions(txs, area_intel)
        assert result[0]["commute_minutes_to_samsung"] == 18
        assert result[0]["school_zone_notes"] == "대치 학원가"

    def test_apartment_override_applied(self, area_intel):
        """apartment_overrides 매칭 → reconstruction_status 부착"""
        agent = _make_agent_self()
        txs = [{"apt_name": "은마아파트", "district_code": "11680", "price": 700_000_000}]
        result = agent._enrich_transactions(txs, area_intel)
        assert result[0]["reconstruction_status"] == "안전진단 통과"
        assert result[0]["reconstruction_potential"] == "HIGH"

    def test_unknown_complex_uses_district_average(self, area_intel):
        """notable_complexes 미매칭 → 구 평균 fallback (첫 번째 dong 아님)"""
        agent = _make_agent_self()
        txs = [{"apt_name": "신규단지XX", "district_code": "11680", "price": 600_000_000}]
        result = agent._enrich_transactions(txs, area_intel)
        # 평균 = (18 + 12) / 2 = 15, 첫 번째 dong 값(18)이 아님
        assert result[0]["commute_minutes_to_samsung"] == 15

    def test_unknown_district_no_enrichment(self, area_intel):
        """area_intel에 없는 district_code → enrichment 없이 원본 반환"""
        agent = _make_agent_self()
        txs = [{"apt_name": "어떤단지", "district_code": "99999", "price": 500_000_000}]
        result = agent._enrich_transactions(txs, area_intel)
        assert "commute_minutes_to_samsung" not in result[0]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: _load_stored_news
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadStoredNews:
    def test_loads_existing_news_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        news_dir = tmp_path / "real_estate" / "news"
        news_dir.mkdir(parents=True)
        (news_dir / "2026-03-24_News.md").write_text("# 뉴스\n- GTX-A 개통", encoding="utf-8")

        agent = _make_agent_self()
        result = agent._load_stored_news(date(2026, 3, 24))
        assert "GTX-A" in result

    def test_returns_empty_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        agent = _make_agent_self()
        result = agent._load_stored_news(date(2026, 3, 24))
        assert result == ""

    def test_truncates_at_3000_chars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        news_dir = tmp_path / "real_estate" / "news"
        news_dir.mkdir(parents=True)
        (news_dir / "2026-03-24_News.md").write_text("X" * 5000, encoding="utf-8")

        agent = _make_agent_self()
        result = agent._load_stored_news(date(2026, 3, 24))
        assert len(result) == 3000


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: _deep_merge + update_persona
# ─────────────────────────────────────────────────────────────────────────────

class TestDeepMerge:
    def test_partial_nested_update(self):
        """지정한 필드만 변경, 나머지 보존"""
        agent = _make_agent_self()
        base = {"user": {"assets": {"self": 200_000_000, "partner": 100_000_000, "total": 300_000_000}}}
        updates = {"user": {"assets": {"total": 500_000_000}}}
        result = agent._deep_merge(base, updates)
        assert result["user"]["assets"]["total"] == 500_000_000
        assert result["user"]["assets"]["self"] == 200_000_000
        assert result["user"]["assets"]["partner"] == 100_000_000

    def test_list_replaced_not_merged(self):
        """list 값은 merge가 아닌 replace"""
        agent = _make_agent_self()
        base = {"user": {"interest_areas": ["강남구", "서초구"]}}
        updates = {"user": {"interest_areas": ["강남구", "서초구", "송파구"]}}
        result = agent._deep_merge(base, updates)
        assert result["user"]["interest_areas"] == ["강남구", "서초구", "송파구"]

    def test_sibling_keys_preserved(self):
        """업데이트하지 않은 형제 키 보존"""
        agent = _make_agent_self()
        base = {"commute": {"max_door_to_door_minutes": 50, "preferred_lines": [2, 9]}}
        updates = {"commute": {"max_door_to_door_minutes": 40}}
        result = agent._deep_merge(base, updates)
        assert result["commute"]["max_door_to_door_minutes"] == 40
        assert result["commute"]["preferred_lines"] == [2, 9]

    def test_new_key_added(self):
        """기존에 없던 키 추가"""
        agent = _make_agent_self()
        base = {"user": {"name": "kks"}}
        updates = {"investment_style": "투자우선형"}
        result = agent._deep_merge(base, updates)
        assert result["investment_style"] == "투자우선형"
        assert result["user"]["name"] == "kks"


class TestUpdatePersona:
    def test_backup_file_created(self, tmp_path, monkeypatch):
        """update_persona 호출 시 이력 백업 파일 생성"""
        import yaml

        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        monkeypatch.setattr(_service_mod, "__file__", str(tmp_path / "service.py"))

        persona_data = {
            "user": {"name": "kks", "assets": {"total": 300_000_000}, "interest_areas": ["강남구"]},
            "commute": {"max_door_to_door_minutes": 50},
        }
        persona_path = tmp_path / "persona.yaml"
        persona_path.write_text(yaml.dump(persona_data, allow_unicode=True))

        agent = _make_agent_self()
        agent.update_persona({"commute": {"max_door_to_door_minutes": 40}})

        history_dir = tmp_path / "real_estate" / "persona_history"
        backups = list(history_dir.glob("*_persona.yaml"))
        assert len(backups) == 1

    def test_persona_updated_and_original_preserved(self, tmp_path, monkeypatch):
        """deep merge: 변경된 값 + 기존 값 보존"""
        import yaml

        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        monkeypatch.setattr(_service_mod, "__file__", str(tmp_path / "service.py"))

        persona_data = {
            "user": {"name": "kks", "interest_areas": ["강남구"]},
            "commute": {"max_door_to_door_minutes": 50, "preferred_lines": [2, 9]},
        }
        persona_path = tmp_path / "persona.yaml"
        persona_path.write_text(yaml.dump(persona_data, allow_unicode=True))

        agent = _make_agent_self()
        result = agent.update_persona({"commute": {"max_door_to_door_minutes": 40}})

        assert result["commute"]["max_door_to_door_minutes"] == 40
        assert result["commute"]["preferred_lines"] == [2, 9]
        assert result["user"]["interest_areas"] == ["강남구"]

    def test_persona_yaml_written_to_disk(self, tmp_path, monkeypatch):
        """update_persona 후 persona.yaml 파일에 변경사항 반영"""
        import yaml

        monkeypatch.setenv("LOCAL_STORAGE_PATH", str(tmp_path))
        monkeypatch.setattr(_service_mod, "__file__", str(tmp_path / "service.py"))

        persona_data = {
            "user": {"name": "kks", "interest_areas": ["강남구"]},
            "commute": {"max_door_to_door_minutes": 50},
        }
        persona_path = tmp_path / "persona.yaml"
        persona_path.write_text(yaml.dump(persona_data, allow_unicode=True))

        agent = _make_agent_self()
        agent.update_persona({"commute": {"max_door_to_door_minutes": 40}})

        saved = yaml.safe_load(persona_path.read_text())
        assert saved["commute"]["max_door_to_door_minutes"] == 40
        assert saved["user"]["interest_areas"] == ["강남구"]  # 보존
