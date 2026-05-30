# 개별 아파트 심층 분석 기능 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 단지 코드를 입력받아 DB 축적 데이터(실거래가, 전세가율, 공급리스크, 입지점수, 거시경제, 출퇴근)를 통합하고, 로컬 LLM CLI로 자연어 인사이트를 생성·저장·슬랙·대시보드 표시하는 엔드-투-엔드 기능을 구축한다.

**Architecture:** FastAPI `POST /jobs/apt/analyze` → `AptAnalysisOrchestrator.analyze(complex_code)` → 7개 레포지토리 + LLM CLI 서브프로세스 → `AptAnalysisRepository.save()` + Slack 전송. `GET /dashboard/apt/analysis/{complex_code}/latest` 등 조회 엔드포인트 2개 추가. 대시보드 Tab1 `_render_apt_detail_panel` 하단에 버튼 2개 추가.

**Tech Stack:** Python 3.12, FastAPI, SQLite, subprocess (claude CLI / gemini CLI), Streamlit, pytest + MagicMock

---

## File Map

| 파일 | 변경 | 역할 |
|------|------|------|
| `src/core/llm.py` | 수정 | `ClaudeCodeClient`, `GeminiCliClient` 추가, `LLMFactory` 확장 |
| `src/modules/real_estate/jeonse/repository.py` | 수정 | `get_by_complex()` 추가 (area 필터 없이 전체 조회) |
| `src/modules/real_estate/apt_master_repository.py` | 수정 | `get_by_complex_code()` 추가 |
| `src/modules/real_estate/commute/commute_repository.py` | 수정 | `get_all_by_origin()` 추가 |
| `src/modules/real_estate/apt_analysis/__init__.py` | 신규 | 패키지 |
| `src/modules/real_estate/apt_analysis/models.py` | 신규 | `AptAnalysisReport` dataclass |
| `src/modules/real_estate/apt_analysis/repository.py` | 신규 | `AptAnalysisRepository` (SQLite) |
| `src/modules/real_estate/apt_analysis/orchestrator.py` | 신규 | `AptAnalysisOrchestrator` |
| `src/modules/real_estate/apt_analysis/formatter.py` | 신규 | Slack/markdown 포맷터 |
| `src/api/routers/real_estate.py` | 수정 | 3개 엔드포인트 추가 |
| `src/dashboard/views/real_estate.py` | 수정 | Tab1 버튼 2개 추가 |
| `docker-compose.yml` | 수정 | claude/gemini 볼륨 마운트 추가 |
| `tests/core/test_llm_cli_clients.py` | 신규 | CLI 클라이언트 유닛 테스트 |
| `tests/modules/real_estate/apt_analysis/__init__.py` | 신규 | |
| `tests/modules/real_estate/apt_analysis/test_apt_analysis_repository.py` | 신규 | |
| `tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py` | 신규 | |
| `tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py` | 신규 | |
| `tests/api/test_apt_analysis_api.py` | 신규 | |
| `docs/features/apt-analysis/spec.md` | 신규 | SOP 스펙 |
| `docs/features/apt-analysis/progress.md` | 신규 | SOP 진행 추적 |

---

## Task 1: SOP 문서 생성

**Files:**
- Create: `docs/features/apt-analysis/spec.md`
- Create: `docs/features/apt-analysis/progress.md`

- [ ] **Step 1: spec.md 작성**

`docs/features/apt-analysis/spec.md` 생성:

```markdown
# 개별 아파트 심층 분석 기능

**작성일:** 2026-05-30
**브랜치:** feature/apt-analysis

## 목표

단지 코드를 입력받아 DB에 축적된 모든 데이터를 통합하고,
로컬 LLM CLI(Claude Code / Gemini CLI)로 자연어 종합 인사이트를 생성한다.
결과는 DB에 저장되어 이후에도 조회 가능하며, Slack 알림과 대시보드 Tab1에서 확인 가능하다.

## 변경 파일

- `src/core/llm.py` — ClaudeCodeClient, GeminiCliClient 추가
- `src/modules/real_estate/apt_analysis/` — 신규 패키지
- `src/api/routers/real_estate.py` — 3개 엔드포인트
- `src/dashboard/views/real_estate.py` — Tab1 버튼 추가
- `docker-compose.yml` — CLI 볼륨 마운트
```

- [ ] **Step 2: progress.md 작성**

`docs/features/apt-analysis/progress.md` 생성:

```markdown
# Progress

- [ ] Task 1: SOP 문서 생성
- [ ] Task 2: LLM CLI 클라이언트 (TDD Red)
- [ ] Task 3: LLM CLI 클라이언트 (TDD Green)
- [ ] Task 4: Repository 확장 (JeonseRepo, AptMasterRepo, CommuteRepo)
- [ ] Task 5: AptAnalysisReport 모델 + AptAnalysisRepository
- [ ] Task 6: AptAnalysisOrchestrator
- [ ] Task 7: Formatter
- [ ] Task 8: API 엔드포인트
- [ ] Task 9: 대시보드 Tab1 버튼
- [ ] Task 10: Docker Compose + Context 업데이트
```

- [ ] **Step 3: 커밋**

```bash
git add docs/features/apt-analysis/spec.md \
        docs/features/apt-analysis/progress.md
git commit -m "docs(sop): apt-analysis spec + progress 생성"
```

---

## Task 2: LLM CLI 클라이언트 테스트 (TDD Red)

**Files:**
- Create: `tests/core/test_llm_cli_clients.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/core/test_llm_cli_clients.py` 생성:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from unittest.mock import patch, MagicMock
import subprocess


class TestClaudeCodeClient:
    def test_generate_returns_stdout(self):
        from core.llm import ClaudeCodeClient
        client = ClaudeCodeClient()
        mock_result = MagicMock()
        mock_result.stdout = "분석 결과입니다."
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = client.generate("테스트 프롬프트")
        assert result == "분석 결과입니다."
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "claude"
        assert "--print" in call_args[0][0]

    def test_generate_subprocess_error_returns_error_string(self):
        from core.llm import ClaudeCodeClient
        client = ClaudeCodeClient()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 120)):
            result = client.generate("테스트")
        assert "분석 시간 초과" in result

    def test_generate_json_parses_valid_json(self):
        from core.llm import ClaudeCodeClient
        client = ClaudeCodeClient()
        mock_result = MagicMock()
        mock_result.stdout = '{"insight": "강남권 추천", "score": 85}'
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json("테스트")
        assert result["insight"] == "강남권 추천"
        assert result["score"] == 85

    def test_generate_json_fallback_on_non_json(self):
        from core.llm import ClaudeCodeClient
        client = ClaudeCodeClient()
        mock_result = MagicMock()
        mock_result.stdout = "이 단지는 좋습니다."
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json("테스트")
        assert "insight" in result
        assert result["insight"] == "이 단지는 좋습니다."

    def test_get_last_usage_returns_zero_token_usage(self):
        from core.llm import ClaudeCodeClient, TokenUsage
        client = ClaudeCodeClient()
        usage = client.get_last_usage()
        assert isinstance(usage, TokenUsage)
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0


class TestGeminiCliClient:
    def test_generate_returns_stdout(self):
        from core.llm import GeminiCliClient
        client = GeminiCliClient()
        mock_result = MagicMock()
        mock_result.stdout = "Gemini 분석 결과"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = client.generate("테스트 프롬프트")
        assert result == "Gemini 분석 결과"
        call_args = mock_run.call_args
        assert call_args[0][0][0] == "gemini"

    def test_generate_timeout_returns_error_string(self):
        from core.llm import GeminiCliClient
        client = GeminiCliClient()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gemini", 120)):
            result = client.generate("테스트")
        assert "분석 시간 초과" in result

    def test_generate_json_parses_json(self):
        from core.llm import GeminiCliClient
        client = GeminiCliClient()
        mock_result = MagicMock()
        mock_result.stdout = '{"insight": "분당권 유망"}'
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json("테스트")
        assert result["insight"] == "분당권 유망"


class TestLLMFactoryCliProviders:
    def test_factory_returns_claude_code_client(self):
        from core.llm import LLMFactory, ClaudeCodeClient
        with patch.dict(os.environ, {"LLM_PROVIDER": "claude-code"}):
            client = LLMFactory.create()
        assert isinstance(client, ClaudeCodeClient)

    def test_factory_returns_gemini_cli_client(self):
        from core.llm import LLMFactory, GeminiCliClient
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini-cli"}):
            client = LLMFactory.create()
        assert isinstance(client, GeminiCliClient)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/core/test_llm_cli_clients.py -v 2>&1 | tail -20
```

예상: `ImportError: cannot import name 'ClaudeCodeClient'`

---

## Task 3: LLM CLI 클라이언트 구현 (TDD Green)

**Files:**
- Modify: `src/core/llm.py`

- [ ] **Step 1: ClaudeCodeClient + GeminiCliClient 클래스 추가**

`src/core/llm.py` 에서 `ClaudeClient` 클래스 정의 끝 직후, `LLMFactory` 클래스 시작 전에 추가:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Claude Code CLI Client (subprocess, 로컬 설치 필요)
# ─────────────────────────────────────────────────────────────────────────────

class ClaudeCodeClient(BaseLLMClient):
    """로컬에 설치된 `claude` CLI를 subprocess로 호출한다."""

    def generate(self, prompt: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["claude", "--print", prompt],
                capture_output=True, text=True, timeout=120
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning("[ClaudeCodeClient] subprocess timeout (120s)")
            return "분석 시간 초과"
        except Exception as e:
            logger.error("[ClaudeCodeClient] subprocess 오류: %s", e)
            return f"분석 실패: {e}"

    def generate_json(self, prompt: str, max_tokens: int = 8192, metadata=None) -> Dict[str, Any]:
        raw = self.generate(prompt)
        if not raw or raw.startswith("분석"):
            return {"insight": raw or "분석 실패"}
        parsed = _parse_json_robust(raw, logger, "ClaudeCode")
        if "error" in parsed and len(parsed) == 1:
            return {"insight": raw}
        return parsed


# ─────────────────────────────────────────────────────────────────────────────
# Gemini CLI Client (subprocess, 로컬 설치 필요)
# ─────────────────────────────────────────────────────────────────────────────

class GeminiCliClient(BaseLLMClient):
    """로컬에 설치된 `gemini` CLI를 subprocess로 호출한다."""

    def generate(self, prompt: str) -> str:
        import subprocess
        try:
            result = subprocess.run(
                ["gemini", prompt],
                capture_output=True, text=True, timeout=120
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.warning("[GeminiCliClient] subprocess timeout (120s)")
            return "분석 시간 초과"
        except Exception as e:
            logger.error("[GeminiCliClient] subprocess 오류: %s", e)
            return f"분석 실패: {e}"

    def generate_json(self, prompt: str, max_tokens: int = 8192, metadata=None) -> Dict[str, Any]:
        raw = self.generate(prompt)
        if not raw or raw.startswith("분석"):
            return {"insight": raw or "분석 실패"}
        parsed = _parse_json_robust(raw, logger, "GeminiCli")
        if "error" in parsed and len(parsed) == 1:
            return {"insight": raw}
        return parsed
```

- [ ] **Step 2: LLMFactory.create() 확장**

`src/core/llm.py` 의 `LLMFactory.create()` 메서드에서:

```python
    @staticmethod
    def create(task_type: Optional[TaskType] = None) -> BaseLLMClient:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider == "claude":
            if task_type is None:
                logger.info("Initializing Claude LLM Client.")
                return ClaudeClient()
            env_key, default_model = LLMFactory._CLAUDE_MODEL_ENV_MAP[task_type]
            model = os.getenv(env_key, default_model)
            logger.info(f"Initializing Claude LLM Client. task_type={task_type}, model={model}")
            return ClaudeClient(model_override=model)

        # Default: Gemini
        logger.info("Initializing Gemini LLM Client.")
        return GeminiClient()
```

를 아래로 교체:

```python
    @staticmethod
    def create(task_type: Optional[TaskType] = None) -> BaseLLMClient:
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider == "claude-code":
            logger.info("Initializing ClaudeCodeClient (local CLI subprocess).")
            return ClaudeCodeClient()
        if provider == "gemini-cli":
            logger.info("Initializing GeminiCliClient (local CLI subprocess).")
            return GeminiCliClient()
        if provider == "claude":
            if task_type is None:
                logger.info("Initializing Claude LLM Client.")
                return ClaudeClient()
            env_key, default_model = LLMFactory._CLAUDE_MODEL_ENV_MAP[task_type]
            model = os.getenv(env_key, default_model)
            logger.info(f"Initializing Claude LLM Client. task_type={task_type}, model={model}")
            return ClaudeClient(model_override=model)
        # Default: Gemini
        logger.info("Initializing Gemini LLM Client.")
        return GeminiClient()
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/core/test_llm_cli_clients.py -v 2>&1 | tail -20
```

예상: `11 passed`

- [ ] **Step 4: 커밋**

```bash
git add src/core/llm.py tests/core/test_llm_cli_clients.py
git commit -m "feat(llm): ClaudeCodeClient + GeminiCliClient (local CLI subprocess) 추가"
```

---

## Task 4: Repository 확장 (TDD)

**Files:**
- Modify: `src/modules/real_estate/jeonse/repository.py`
- Modify: `src/modules/real_estate/apt_master_repository.py`
- Modify: `src/modules/real_estate/commute/commute_repository.py`

이 태스크는 3개의 기존 레포지토리에 메서드를 1개씩 추가한다. 각각 Red → Green → 커밋으로 진행한다.

### 4A: JeonseRepository.get_by_complex()

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/jeonse/test_jeonse_repository.py` (파일이 있으면 추가, 없으면 신규):

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.models import JeonseTransaction


@pytest.fixture
def jeonse_repo(tmp_path):
    return JeonseRepository(db_path=str(tmp_path / "test.db"))


def test_get_by_complex_returns_all_for_complex_code(jeonse_repo):
    tx1 = JeonseTransaction(
        complex_code="CC001", apt_name="래미안", district_code="41135",
        deal_date="2026-01-15", exclusive_area=84.0, deposit=500_000_000,
        monthly_rent=0, contract_type="jeonse", floor=5
    )
    tx2 = JeonseTransaction(
        complex_code="CC001", apt_name="래미안", district_code="41135",
        deal_date="2026-02-10", exclusive_area=59.0, deposit=350_000_000,
        monthly_rent=0, contract_type="jeonse", floor=3
    )
    tx_other = JeonseTransaction(
        complex_code="CC999", apt_name="힐스테이트", district_code="41135",
        deal_date="2026-02-01", exclusive_area=84.0, deposit=600_000_000,
        monthly_rent=0, contract_type="jeonse", floor=7
    )
    jeonse_repo.save(tx1)
    jeonse_repo.save(tx2)
    jeonse_repo.save(tx_other)

    results = jeonse_repo.get_by_complex("CC001")
    assert len(results) == 2
    assert all(r.complex_code == "CC001" for r in results)


def test_get_by_complex_returns_empty_when_no_data(jeonse_repo):
    assert jeonse_repo.get_by_complex("NONEXISTENT") == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/jeonse/ -k "get_by_complex" -v 2>&1 | tail -10
```

예상: `AttributeError: 'JeonseRepository' object has no attribute 'get_by_complex'`

- [ ] **Step 3: get_by_complex 구현**

`src/modules/real_estate/jeonse/repository.py` 의 `get_recent()` 메서드 직후에 추가:

```python
    def get_by_complex(self, complex_code: str, months: int = 12) -> List[JeonseTransaction]:
        """complex_code 기준으로 최근 N개월 전세 거래 전체 반환 (area 필터 없음)."""
        from datetime import date
        today = date.today()
        year = today.year - (months // 12)
        month = today.month - (months % 12)
        if month <= 0:
            month += 12
            year -= 1
        cutoff = today.replace(year=year, month=month).isoformat()
        rows = self._conn.execute(
            "SELECT * FROM jeonse_transactions "
            "WHERE complex_code = ? AND deal_date >= ? ORDER BY deal_date DESC",
            (complex_code, cutoff)
        ).fetchall()
        return [JeonseTransaction(
            id=r["id"], complex_code=r["complex_code"], apt_name=r["apt_name"],
            district_code=r["district_code"], deal_date=r["deal_date"],
            exclusive_area=r["exclusive_area"], deposit=r["deposit"],
            monthly_rent=r["monthly_rent"], contract_type=r["contract_type"],
            floor=r["floor"]
        ) for r in rows]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/jeonse/ -k "get_by_complex" -v 2>&1 | tail -10
```

예상: `2 passed`

### 4B: AptMasterRepository.get_by_complex_code()

- [ ] **Step 5: 실패하는 테스트 추가**

`tests/modules/real_estate/test_apt_master_repository.py` 파일 끝에 추가:

```python
def test_get_by_complex_code_returns_entry(tmp_path):
    from modules.real_estate.apt_master_repository import AptMasterRepository
    from modules.real_estate.models import AptMasterEntry
    repo = AptMasterRepository(db_path=":memory:")
    entry = AptMasterEntry(
        apt_name="래미안블레스티지",
        district_code="11680",
        sido="서울특별시",
        sigungu="강남구",
        complex_code="CC123",
        tx_count=10,
    )
    repo.upsert(entry)
    found = repo.get_by_complex_code("CC123")
    assert found is not None
    assert found.apt_name == "래미안블레스티지"
    assert found.complex_code == "CC123"


def test_get_by_complex_code_returns_none_when_not_found(tmp_path):
    from modules.real_estate.apt_master_repository import AptMasterRepository
    repo = AptMasterRepository(db_path=":memory:")
    assert repo.get_by_complex_code("NONEXISTENT") is None
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_apt_master_repository.py -k "get_by_complex_code" -v 2>&1 | tail -10
```

예상: `AttributeError: 'AptMasterRepository' object has no attribute 'get_by_complex_code'`

- [ ] **Step 7: get_by_complex_code 구현**

`src/modules/real_estate/apt_master_repository.py` 의 `get_by_name_district()` 메서드 직후에 추가:

```python
    def get_by_complex_code(self, complex_code: str) -> Optional[AptMasterEntry]:
        """complex_code로 단지 조회 (apartments JOIN 포함)."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT am.*, a.household_count, a.road_address, a.approved_date "
                    "FROM apt_master am "
                    "LEFT JOIN apartments a ON am.complex_code = a.complex_code "
                    "WHERE am.complex_code = ?",
                    (complex_code,)
                ).fetchone()
        except Exception:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM apt_master WHERE complex_code = ?",
                    (complex_code,)
                ).fetchone()
        return _row_to_entry(row) if row else None
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_apt_master_repository.py -k "get_by_complex_code" -v 2>&1 | tail -10
```

예상: `2 passed`

### 4C: CommuteRepository.get_all_by_origin()

- [ ] **Step 9: 실패하는 테스트 추가**

`tests/modules/real_estate/commute/test_commute_repository.py` (파일이 있으면 추가, 없으면 신규):

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from modules.real_estate.commute.commute_repository import CommuteRepository
from modules.real_estate.commute.models import CommuteResult


@pytest.fixture
def commute_repo(tmp_path):
    return CommuteRepository(db_path=str(tmp_path / "commute.db"))


def test_get_all_by_origin_returns_all_modes(commute_repo):
    for mode in ("transit", "car"):
        commute_repo.upsert(CommuteResult(
            origin_key="41135__래미안",
            destination="삼성역",
            mode=mode,
            duration_minutes=35,
            distance_meters=15000,
        ))
    results = commute_repo.get_all_by_origin("41135__래미안")
    assert len(results) == 2
    modes = {r.mode for r in results}
    assert "transit" in modes
    assert "car" in modes


def test_get_all_by_origin_returns_empty_when_no_data(commute_repo):
    results = commute_repo.get_all_by_origin("NONEXISTENT__단지")
    assert results == []
```

- [ ] **Step 10: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/ -k "get_all_by_origin" -v 2>&1 | tail -10
```

예상: `AttributeError: 'CommuteRepository' object has no attribute 'get_all_by_origin'`

- [ ] **Step 11: get_all_by_origin 구현**

`src/modules/real_estate/commute/commute_repository.py` 의 `upsert()` 메서드 직후에 추가:

```python
    def get_all_by_origin(self, origin_key: str) -> list:
        """origin_key에 해당하는 모든 캐시 항목 반환 (destination/mode 무관)."""
        rows = self._conn.execute(
            "SELECT * FROM commute_cache WHERE origin_key = ?",
            (origin_key,)
        ).fetchall()
        results = []
        for row in rows:
            try:
                legs = json.loads(row["route_json"])
            except (json.JSONDecodeError, TypeError):
                legs = []
            results.append(CommuteResult(
                origin_key=row["origin_key"],
                destination=row["destination"],
                mode=row["mode"],
                duration_minutes=row["duration_minutes"],
                distance_meters=row["distance_meters"],
                cached=True,
                legs=legs,
                route_summary=row["route_summary"] or "",
            ))
        return results
```

- [ ] **Step 12: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/ -k "get_all_by_origin" -v 2>&1 | tail -10
```

예상: `2 passed`

- [ ] **Step 13: 커밋**

```bash
git add src/modules/real_estate/jeonse/repository.py \
        src/modules/real_estate/apt_master_repository.py \
        src/modules/real_estate/commute/commute_repository.py \
        tests/modules/real_estate/jeonse/ \
        tests/modules/real_estate/test_apt_master_repository.py \
        tests/modules/real_estate/commute/ \
        docs/features/apt-analysis/progress.md
git commit -m "feat(repo): get_by_complex, get_by_complex_code, get_all_by_origin 추가"
```

---

## Task 5: AptAnalysisReport 모델 + AptAnalysisRepository (TDD)

**Files:**
- Create: `src/modules/real_estate/apt_analysis/__init__.py`
- Create: `src/modules/real_estate/apt_analysis/models.py`
- Create: `src/modules/real_estate/apt_analysis/repository.py`
- Create: `tests/modules/real_estate/apt_analysis/__init__.py`
- Create: `tests/modules/real_estate/apt_analysis/test_apt_analysis_repository.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/apt_analysis/test_apt_analysis_repository.py` 생성:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from modules.real_estate.apt_analysis.models import AptAnalysisReport
from modules.real_estate.apt_analysis.repository import AptAnalysisRepository


@pytest.fixture
def repo(tmp_path):
    return AptAnalysisRepository(db_path=str(tmp_path / "re.db"))


def _make_report(complex_code: str = "CC001") -> AptAnalysisReport:
    return AptAnalysisReport(
        complex_code=complex_code,
        apt_name="래미안블레스티지",
        generated_at="2026-05-30T12:00:00",
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km 공급 3,500세대 — 위험",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32, "car": 25},
        macro_snapshot={"base_rate": {"value": 3.0}, "updated_at": "2026-05-30"},
        llm_insight="이 단지는 입지가 우수합니다.",
        slack_text="*래미안블레스티지* 분석 완료",
        markdown_text="# 래미안블레스티지\n\n분석 결과...",
    )


class TestAptAnalysisRepository:
    def test_save_and_get_latest(self, repo):
        report = _make_report()
        repo.save(report)
        latest = repo.get_latest("CC001")
        assert latest is not None
        assert latest.complex_code == "CC001"
        assert latest.apt_name == "래미안블레스티지"
        assert latest.llm_insight == "이 단지는 입지가 우수합니다."

    def test_get_latest_returns_none_when_no_data(self, repo):
        assert repo.get_latest("NONEXISTENT") is None

    def test_get_history_returns_multiple_sorted(self, repo):
        r1 = _make_report()
        r1 = AptAnalysisReport(
            **{**r1.__dict__, "generated_at": "2026-05-29T10:00:00", "llm_insight": "분석1"}
        )
        r2 = _make_report()
        r2 = AptAnalysisReport(
            **{**r2.__dict__, "generated_at": "2026-05-30T12:00:00", "llm_insight": "분석2"}
        )
        repo.save(r1)
        repo.save(r2)
        history = repo.get_history("CC001", limit=10)
        assert len(history) == 2
        assert history[0].generated_at == "2026-05-30T12:00:00"

    def test_get_history_respects_limit(self, repo):
        for i in range(5):
            r = _make_report()
            r = AptAnalysisReport(
                **{**r.__dict__, "generated_at": f"2026-05-{i+1:02d}T00:00:00"}
            )
            repo.save(r)
        history = repo.get_history("CC001", limit=3)
        assert len(history) == 3
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_repository.py -v 2>&1 | tail -10
```

예상: `ModuleNotFoundError: No module named 'modules.real_estate.apt_analysis'`

- [ ] **Step 3: 패키지 + 모델 생성**

`src/modules/real_estate/apt_analysis/__init__.py` 생성 (빈 파일):
```python
```

`src/modules/real_estate/apt_analysis/models.py` 생성:

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AptAnalysisReport:
    complex_code: str
    apt_name: str
    generated_at: str               # ISO8601

    price_history: List[dict]       # {"date": str, "price": int, "area": float}
    jeonse_ratio: Optional[float]   # 전세가율 (%)
    supply_risk_summary: Optional[str]
    location_score: Optional[Dict[str, Any]]  # residential_total, investment_total, results
    commute_summary: Optional[Dict[str, int]] # mode → duration_minutes
    macro_snapshot: Dict[str, Any]

    llm_insight: str

    slack_text: str
    markdown_text: str
```

`tests/modules/real_estate/apt_analysis/__init__.py` 생성 (빈 파일):
```python
```

- [ ] **Step 4: AptAnalysisRepository 구현**

`src/modules/real_estate/apt_analysis/repository.py` 생성:

```python
import json
import sqlite3
from typing import Optional, List

from .models import AptAnalysisReport

_DDL = """
CREATE TABLE IF NOT EXISTS apt_analysis_reports (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code TEXT NOT NULL,
    apt_name     TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    report_json  TEXT NOT NULL,
    llm_insight  TEXT NOT NULL,
    slack_text   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_apt_analysis_complex
    ON apt_analysis_reports(complex_code, generated_at DESC);
"""


class AptAnalysisRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def save(self, report: AptAnalysisReport) -> None:
        import dataclasses
        self._conn.execute(
            """INSERT INTO apt_analysis_reports
               (complex_code, apt_name, generated_at, report_json, llm_insight, slack_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                report.complex_code,
                report.apt_name,
                report.generated_at,
                json.dumps(dataclasses.asdict(report), ensure_ascii=False),
                report.llm_insight,
                report.slack_text,
            )
        )
        self._conn.commit()

    def get_latest(self, complex_code: str) -> Optional[AptAnalysisReport]:
        row = self._conn.execute(
            "SELECT report_json FROM apt_analysis_reports "
            "WHERE complex_code = ? ORDER BY generated_at DESC LIMIT 1",
            (complex_code,)
        ).fetchone()
        if row is None:
            return None
        return self._from_json(row["report_json"])

    def get_history(self, complex_code: str, limit: int = 10) -> List[AptAnalysisReport]:
        rows = self._conn.execute(
            "SELECT report_json FROM apt_analysis_reports "
            "WHERE complex_code = ? ORDER BY generated_at DESC LIMIT ?",
            (complex_code, limit)
        ).fetchall()
        return [self._from_json(r["report_json"]) for r in rows]

    @staticmethod
    def _from_json(raw: str) -> AptAnalysisReport:
        data = json.loads(raw)
        return AptAnalysisReport(**data)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_repository.py -v 2>&1 | tail -10
```

예상: `4 passed`

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/apt_analysis/ \
        tests/modules/real_estate/apt_analysis/ \
        docs/features/apt-analysis/progress.md
git commit -m "feat(apt-analysis): AptAnalysisReport 모델 + AptAnalysisRepository 구현"
```

---

## Task 6: AptAnalysisOrchestrator (TDD)

**Files:**
- Create: `src/modules/real_estate/apt_analysis/orchestrator.py`
- Create: `tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py` 생성:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from unittest.mock import MagicMock, patch
from modules.real_estate.apt_analysis.models import AptAnalysisReport


def _make_mock_apt_master():
    m = MagicMock()
    m.apt_name = "래미안블레스티지"
    m.district_code = "11680"
    m.complex_code = "CC001"
    m.sigungu = "강남구"
    m.road_address = "서울특별시 강남구 도곡로 155"
    return m


def _make_mock_apt_details():
    m = MagicMock()
    m.apt_name = "래미안블레스티지"
    m.district_code = "11680"
    m.sigungu = "강남구"
    m.road_address = "서울특별시 강남구 도곡로 155"
    return m


def _make_mock_transaction():
    m = MagicMock()
    m.deal_date = "2026-05-01"
    m.price = 1_500_000_000
    m.exclusive_area = 84.0
    return m


def _make_mock_jeonse():
    m = MagicMock()
    m.deposit = 900_000_000
    m.contract_type = "jeonse"
    return m


def _build_orchestrator():
    from modules.real_estate.apt_analysis.orchestrator import AptAnalysisOrchestrator

    apt_master_repo = MagicMock()
    apt_master_repo.get_by_complex_code.return_value = _make_mock_apt_master()

    apt_details_repo = MagicMock()
    apt_details_repo.get.return_value = _make_mock_apt_details()

    tx_repo = MagicMock()
    tx_repo.get_by_complex.return_value = [_make_mock_transaction()]

    jeonse_repo = MagicMock()
    jeonse_repo.get_by_complex.return_value = [_make_mock_jeonse()]

    supply_repo = MagicMock()
    supply_repo.get_within_radius.return_value = []

    loc_repo = MagicMock()
    loc_repo.get_score.return_value = None

    macro_svc = MagicMock()
    macro_svc.fetch_latest_macro_data.return_value = {"base_rate": {"value": 3.0}, "updated_at": "2026-05-30"}

    commute_repo = MagicMock()
    commute_repo.get_all_by_origin.return_value = []

    llm = MagicMock()
    llm.generate.return_value = "이 단지는 강남 핵심 입지로 실거주·투자 모두 우수합니다."

    return AptAnalysisOrchestrator(
        apt_master_repo=apt_master_repo,
        apt_details_repo=apt_details_repo,
        tx_repo=tx_repo,
        jeonse_repo=jeonse_repo,
        supply_repo=supply_repo,
        loc_repo=loc_repo,
        macro_svc=macro_svc,
        commute_repo=commute_repo,
        llm=llm,
    ), apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, loc_repo, macro_svc, commute_repo, llm


class TestAptAnalysisOrchestrator:
    def test_analyze_returns_report_with_correct_complex_code(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        assert isinstance(report, AptAnalysisReport)
        assert report.complex_code == "CC001"
        assert report.apt_name == "래미안블레스티지"

    def test_analyze_calls_all_repositories(self):
        orch, apt_master_repo, apt_details_repo, tx_repo, jeonse_repo, loc_repo, macro_svc, commute_repo, llm = _build_orchestrator()
        orch.analyze("CC001")
        apt_master_repo.get_by_complex_code.assert_called_once_with("CC001")
        tx_repo.get_by_complex.assert_called_once_with("CC001")
        jeonse_repo.get_by_complex.assert_called_once_with("CC001")
        loc_repo.get_score.assert_called_once_with("CC001")
        macro_svc.fetch_latest_macro_data.assert_called_once()
        commute_repo.get_all_by_origin.assert_called_once()

    def test_analyze_calculates_jeonse_ratio(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        # jeonse_deposit=900M, avg_sale=1500M → ratio=60.0%
        assert report.jeonse_ratio is not None
        assert abs(report.jeonse_ratio - 60.0) < 0.1

    def test_analyze_includes_llm_insight(self):
        orch, *_ = _build_orchestrator()
        report = orch.analyze("CC001")
        assert "강남" in report.llm_insight

    def test_analyze_raises_value_error_when_complex_not_found(self):
        orch, apt_master_repo, *_ = _build_orchestrator()
        apt_master_repo.get_by_complex_code.return_value = None
        with pytest.raises(ValueError, match="단지 코드 없음"):
            orch.analyze("NONEXISTENT")

    def test_analyze_handles_missing_jeonse_gracefully(self):
        orch, _, _, _, jeonse_repo, *_ = _build_orchestrator()
        jeonse_repo.get_by_complex.return_value = []
        report = orch.analyze("CC001")
        assert report.jeonse_ratio is None

    def test_analyze_builds_commute_summary_from_cache(self):
        orch, _, _, _, _, _, _, commute_repo, _ = _build_orchestrator()
        mock_result = MagicMock()
        mock_result.mode = "transit"
        mock_result.duration_minutes = 32
        commute_repo.get_all_by_origin.return_value = [mock_result]
        report = orch.analyze("CC001")
        assert report.commute_summary is not None
        assert report.commute_summary.get("transit") == 32
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py -v 2>&1 | tail -15
```

예상: `ModuleNotFoundError: No module named 'modules.real_estate.apt_analysis.orchestrator'`

- [ ] **Step 3: AptAnalysisOrchestrator 구현**

`src/modules/real_estate/apt_analysis/orchestrator.py` 생성:

```python
from datetime import datetime, timezone
from typing import Optional

from .models import AptAnalysisReport

try:
    from core.logger import get_logger
except ImportError:
    import logging
    def get_logger(name): return logging.getLogger(name)

logger = get_logger(__name__)


class AptAnalysisOrchestrator:
    def __init__(
        self,
        apt_master_repo,
        apt_details_repo,
        tx_repo,
        jeonse_repo,
        supply_repo,
        loc_repo,
        macro_svc,
        commute_repo,
        llm,
    ):
        self._apt_master_repo = apt_master_repo
        self._apt_details_repo = apt_details_repo
        self._tx_repo = tx_repo
        self._jeonse_repo = jeonse_repo
        self._supply_repo = supply_repo
        self._loc_repo = loc_repo
        self._macro_svc = macro_svc
        self._commute_repo = commute_repo
        self._llm = llm

    def analyze(self, complex_code: str) -> AptAnalysisReport:
        apt_entry = self._apt_master_repo.get_by_complex_code(complex_code)
        if apt_entry is None:
            raise ValueError(f"단지 코드 없음: {complex_code}")

        apt_name = apt_entry.apt_name
        district_code = apt_entry.district_code

        price_history = self._collect_price_history(complex_code)
        jeonse_ratio = self._calc_jeonse_ratio(complex_code, price_history)
        supply_risk_summary = self._get_supply_risk(apt_entry)
        location_score = self._get_location_score(complex_code)
        commute_summary = self._get_commute_summary(district_code, apt_name)
        macro_snapshot = self._macro_svc.fetch_latest_macro_data()

        prompt = self._build_prompt(
            apt_name=apt_name,
            price_history=price_history,
            jeonse_ratio=jeonse_ratio,
            supply_risk_summary=supply_risk_summary,
            location_score=location_score,
            commute_summary=commute_summary,
            macro_snapshot=macro_snapshot,
        )
        llm_insight = self._llm.generate(prompt)

        generated_at = datetime.now(timezone.utc).isoformat()

        from .formatter import format_slack, format_markdown
        report = AptAnalysisReport(
            complex_code=complex_code,
            apt_name=apt_name,
            generated_at=generated_at,
            price_history=price_history,
            jeonse_ratio=jeonse_ratio,
            supply_risk_summary=supply_risk_summary,
            location_score=location_score,
            commute_summary=commute_summary,
            macro_snapshot=macro_snapshot,
            llm_insight=llm_insight,
            slack_text="",
            markdown_text="",
        )
        report.slack_text = format_slack(report)
        report.markdown_text = format_markdown(report)
        return report

    def _collect_price_history(self, complex_code: str) -> list:
        txs = self._tx_repo.get_by_complex(complex_code)
        return [
            {"date": t.deal_date, "price": t.price, "area": t.exclusive_area}
            for t in txs
        ]

    def _calc_jeonse_ratio(self, complex_code: str, price_history: list) -> Optional[float]:
        if not price_history:
            return None
        jeonse_txs = self._jeonse_repo.get_by_complex(complex_code)
        jeonse_only = [t for t in jeonse_txs if getattr(t, "contract_type", "jeonse") == "jeonse"]
        if not jeonse_only:
            return None
        avg_sale = sum(p["price"] for p in price_history) / len(price_history)
        avg_jeonse = sum(t.deposit for t in jeonse_only) / len(jeonse_only)
        if avg_sale == 0:
            return None
        return round(avg_jeonse / avg_sale * 100, 1)

    def _get_supply_risk(self, apt_entry) -> Optional[str]:
        try:
            from modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
        except ImportError:
            from src.modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer

        apt_details = self._apt_details_repo.get(getattr(apt_entry, "complex_code", None))
        if apt_details is None:
            return None

        road_address = getattr(apt_details, "road_address", "") or ""
        sigungu = getattr(apt_details, "sigungu", "") or ""
        apt_name = getattr(apt_entry, "apt_name", "")

        try:
            import os
            from modules.real_estate.geocoder import GeocoderService
            geocoder = GeocoderService(
                api_key=os.getenv("KAKAO_API_KEY", ""),
                cache_path=os.getenv("GEOCODE_CACHE_PATH", "data/geocode_cache.db"),
            )
            coords = geocoder.geocode(apt_name, getattr(apt_entry, "district_code", ""), address=road_address)
            if coords is None:
                return None
            lat, lng = coords
            analyzer = SupplyRiskAnalyzer(supply_repo=self._supply_repo)
            result = analyzer.analyze(lat=lat, lng=lng, apt_name=apt_name, sigungu=sigungu)
            return f"반경 3km 공급 {result.nearby_units:,}세대 ({result.supply_period}) — {self._risk_level(result.nearby_units)}"
        except Exception as e:
            logger.warning("[AptAnalysisOrchestrator] supply risk 조회 실패: %s", e)
            return None

    @staticmethod
    def _risk_level(units: int) -> str:
        if units >= 5000:
            return "위험"
        if units >= 2000:
            return "주의"
        return "안전"

    def _get_location_score(self, complex_code: str):
        score = self._loc_repo.get_score(complex_code)
        if score is None:
            return None
        return {
            "residential_total": score.residential_total,
            "investment_total": score.investment_total,
            "results": {
                "residential": [{"label": dr.label, "score": dr.score} for dr in score.residential_results],
                "investment": [{"label": dr.label, "score": dr.score} for dr in score.investment_results],
            },
        }

    def _get_commute_summary(self, district_code: str, apt_name: str) -> Optional[dict]:
        origin_key = f"{district_code}__{apt_name}"
        cached = self._commute_repo.get_all_by_origin(origin_key)
        if not cached:
            return None
        return {r.mode: r.duration_minutes for r in cached}

    def _build_prompt(self, apt_name, price_history, jeonse_ratio, supply_risk_summary,
                      location_score, commute_summary, macro_snapshot) -> str:
        lines = [
            f"## 단지: {apt_name}",
            "",
            "### 실거래가 히스토리 (최근 거래 기준)",
        ]
        for p in price_history[:10]:
            lines.append(f"- {p['date']}: {p['price']:,}원 ({p['area']}㎡)")

        lines += [
            "",
            f"### 전세가율: {jeonse_ratio:.1f}%" if jeonse_ratio else "### 전세가율: 데이터 없음",
            "",
            f"### 공급 리스크: {supply_risk_summary}" if supply_risk_summary else "### 공급 리스크: 데이터 없음",
            "",
        ]

        if location_score:
            lines += [
                f"### 입지 점수: 실거주 {location_score['residential_total']}점 / 투자 {location_score['investment_total']}점",
            ]

        if commute_summary:
            commute_str = " | ".join(f"{k}: {v}분" for k, v in commute_summary.items())
            lines.append(f"### 출퇴근(삼성역 기준): {commute_str}")

        rate = macro_snapshot.get("base_rate", {})
        if rate:
            lines.append(f"### 기준금리: {rate.get('value', '-')}%")

        lines += [
            "",
            "위 데이터를 종합하여 이 아파트 단지의 실거주·투자 가치를 한국어로 심층 분석하세요.",
            "강점, 약점, 매수 타이밍, 리스크 요인을 포함한 종합 의견을 작성하세요.",
        ]
        return "\n".join(lines)
```

- [ ] **Step 4: Formatter 스텁 파일 생성 (import 에러 방지)**

`src/modules/real_estate/apt_analysis/formatter.py` 생성 (다음 태스크에서 완성):

```python
from .models import AptAnalysisReport


def format_slack(report: AptAnalysisReport) -> str:
    return f"*{report.apt_name}* 심층 분석 완료"


def format_markdown(report: AptAnalysisReport) -> str:
    return f"# {report.apt_name}\n\n{report.llm_insight}"
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py -v 2>&1 | tail -15
```

예상: `7 passed`

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/apt_analysis/orchestrator.py \
        src/modules/real_estate/apt_analysis/formatter.py \
        tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py \
        docs/features/apt-analysis/progress.md
git commit -m "feat(apt-analysis): AptAnalysisOrchestrator 구현"
```

---

## Task 7: Formatter (TDD)

**Files:**
- Modify: `src/modules/real_estate/apt_analysis/formatter.py`
- Create: `tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py` 생성:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.apt_analysis.models import AptAnalysisReport
from modules.real_estate.apt_analysis.formatter import format_slack, format_markdown


def _make_report() -> AptAnalysisReport:
    return AptAnalysisReport(
        complex_code="CC001",
        apt_name="래미안블레스티지",
        generated_at="2026-05-30T12:00:00",
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km 공급 3,500세대 — 위험",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32, "car": 25},
        macro_snapshot={"base_rate": {"value": 3.0}},
        llm_insight="이 단지는 강남 핵심 입지입니다.",
        slack_text="",
        markdown_text="",
    )


class TestFormatSlack:
    def test_slack_text_contains_apt_name(self):
        report = _make_report()
        text = format_slack(report)
        assert "래미안블레스티지" in text

    def test_slack_text_contains_jeonse_ratio(self):
        report = _make_report()
        text = format_slack(report)
        assert "60.5" in text

    def test_slack_text_contains_location_scores(self):
        report = _make_report()
        text = format_slack(report)
        assert "72" in text  # residential_total
        assert "68" in text  # investment_total

    def test_slack_text_contains_llm_insight(self):
        report = _make_report()
        text = format_slack(report)
        assert "강남 핵심 입지" in text

    def test_slack_text_handles_none_jeonse_ratio(self):
        report = _make_report()
        report.jeonse_ratio = None
        text = format_slack(report)
        assert "래미안블레스티지" in text


class TestFormatMarkdown:
    def test_markdown_contains_header(self):
        report = _make_report()
        text = format_markdown(report)
        assert "# 래미안블레스티지" in text

    def test_markdown_contains_price_history(self):
        report = _make_report()
        text = format_markdown(report)
        assert "실거래가" in text

    def test_markdown_contains_llm_insight(self):
        report = _make_report()
        text = format_markdown(report)
        assert "강남 핵심 입지" in text
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py -v 2>&1 | tail -15
```

예상: 일부 assertion 실패 (스텁 구현이 너무 단순함)

- [ ] **Step 3: Formatter 완전 구현**

`src/modules/real_estate/apt_analysis/formatter.py` 를 아래로 교체:

```python
from .models import AptAnalysisReport


def format_slack(report: AptAnalysisReport) -> str:
    lines = [f"*🔬 {report.apt_name} 심층 분석* ({report.generated_at[:10]})"]
    lines.append("")

    if report.jeonse_ratio is not None:
        lines.append(f"• 전세가율: {report.jeonse_ratio:.1f}%")
    if report.supply_risk_summary:
        lines.append(f"• 공급리스크: {report.supply_risk_summary}")
    if report.location_score:
        res = report.location_score.get("residential_total", "-")
        inv = report.location_score.get("investment_total", "-")
        lines.append(f"• 입지점수: 실거주 {res}점 / 투자 {inv}점")
    if report.commute_summary:
        commute_str = " | ".join(f"{k}: {v}분" for k, v in report.commute_summary.items())
        lines.append(f"• 출퇴근: {commute_str}")

    lines.append("")
    lines.append("*AI 종합 분석*")
    lines.append(report.llm_insight[:500] + ("..." if len(report.llm_insight) > 500 else ""))
    return "\n".join(lines)


def format_markdown(report: AptAnalysisReport) -> str:
    lines = [
        f"# {report.apt_name} 심층 분석",
        f"**분석일시:** {report.generated_at[:10]}",
        "",
        "## 실거래가 히스토리",
    ]
    for p in report.price_history[:20]:
        lines.append(f"- {p['date']}: {p['price']:,}원 ({p['area']}㎡)")

    lines += ["", "## 지표 요약"]
    if report.jeonse_ratio is not None:
        lines.append(f"- 전세가율: **{report.jeonse_ratio:.1f}%**")
    if report.supply_risk_summary:
        lines.append(f"- 공급리스크: {report.supply_risk_summary}")
    if report.location_score:
        res = report.location_score.get("residential_total", "-")
        inv = report.location_score.get("investment_total", "-")
        lines.append(f"- 입지점수: 실거주 {res}점 / 투자 {inv}점")
    if report.commute_summary:
        commute_str = " | ".join(f"{k}: {v}분" for k, v in report.commute_summary.items())
        lines.append(f"- 출퇴근(삼성역 기준): {commute_str}")

    macro = report.macro_snapshot
    if macro.get("base_rate"):
        lines.append(f"- 기준금리: {macro['base_rate'].get('value', '-')}%")
    if macro.get("loan_rate"):
        lines.append(f"- 주담대금리: {macro['loan_rate'].get('value', '-')}%")

    lines += ["", "## AI 종합 분석", report.llm_insight]
    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py -v 2>&1 | tail -15
```

예상: `8 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/apt_analysis/formatter.py \
        tests/modules/real_estate/apt_analysis/test_apt_analysis_formatter.py \
        docs/features/apt-analysis/progress.md
git commit -m "feat(apt-analysis): Formatter 구현 (Slack + Markdown)"
```

---

## Task 8: API 엔드포인트 (TDD)

**Files:**
- Create: `tests/api/test_apt_analysis_api.py`
- Modify: `src/api/routers/real_estate.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/api/test_apt_analysis_api.py` 생성:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _make_mock_report():
    from modules.real_estate.apt_analysis.models import AptAnalysisReport
    return AptAnalysisReport(
        complex_code="CC001",
        apt_name="래미안블레스티지",
        generated_at="2026-05-30T12:00:00",
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km — 안전",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32},
        macro_snapshot={"base_rate": {"value": 3.0}},
        llm_insight="강남 핵심 입지 추천.",
        slack_text="*래미안블레스티지* 분석 완료",
        markdown_text="# 래미안블레스티지",
    )


class TestAptAnalyzeEndpoint:
    def test_analyze_returns_200_with_report(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn, \
             patch("api.routers.real_estate._send_slack_if_needed"):
            mock_orch = MagicMock()
            mock_orch.analyze.return_value = mock_report
            mock_build.return_value = mock_orch
            mock_repo = MagicMock()
            mock_repo_fn.return_value = mock_repo

            resp = client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["report"]["complex_code"] == "CC001"

    def test_analyze_returns_404_when_complex_not_found(self):
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo"):
            mock_orch = MagicMock()
            mock_orch.analyze.side_effect = ValueError("단지 코드 없음: NOTFOUND")
            mock_build.return_value = mock_orch

            resp = client.post("/jobs/apt/analyze", json={"complex_code": "NOTFOUND"})

        assert resp.status_code == 404

    def test_analyze_saves_to_repository(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._build_apt_analysis_orchestrator") as mock_build, \
             patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn, \
             patch("api.routers.real_estate._send_slack_if_needed"):
            mock_orch = MagicMock()
            mock_orch.analyze.return_value = mock_report
            mock_build.return_value = mock_orch
            mock_repo = MagicMock()
            mock_repo_fn.return_value = mock_repo

            client.post("/jobs/apt/analyze", json={"complex_code": "CC001", "send_slack": False})
            mock_repo.save.assert_called_once_with(mock_report)


class TestAptAnalysisGetEndpoints:
    def test_get_latest_returns_200_with_report(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_latest.return_value = mock_report
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/CC001/latest")

        assert resp.status_code == 200
        assert resp.json()["complex_code"] == "CC001"

    def test_get_latest_returns_404_when_no_report(self):
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_latest.return_value = None
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/NOTFOUND/latest")

        assert resp.status_code == 404

    def test_get_history_returns_list(self):
        mock_report = _make_mock_report()
        with patch("api.routers.real_estate._get_apt_analysis_repo") as mock_repo_fn:
            mock_repo = MagicMock()
            mock_repo.get_history.return_value = [mock_report]
            mock_repo_fn.return_value = mock_repo

            resp = client.get("/dashboard/apt/analysis/CC001")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/api/test_apt_analysis_api.py -v 2>&1 | tail -15
```

예상: route not found 관련 실패

- [ ] **Step 3: API 엔드포인트 구현**

`src/api/routers/real_estate.py` 파일 끝에 추가 (마지막 `LLMClient = LLMFactory.create` 라인 이후):

> **참고:** 파일 끝 부분에 아래 코드를 추가한다. 기존 import 목록에 Pydantic 모델이 이미 있으므로 중복 import는 생략.

```python
# ─────────────────────────────────────────────────────────────────────────────
# 개별 아파트 심층 분석
# ─────────────────────────────────────────────────────────────────────────────

class AptAnalyzeRequest(BaseModel):
    complex_code: str
    send_slack: bool = True


def _get_apt_analysis_repo():
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.apt_analysis.repository import AptAnalysisRepository
    cfg = RealEstateConfig()
    db_path = cfg.get("real_estate_db_path", "data/real_estate.db")
    return AptAnalysisRepository(db_path=db_path)


def _build_apt_analysis_orchestrator():
    import os
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.apt_analysis.orchestrator import AptAnalysisOrchestrator
    from modules.real_estate.apt_master_repository import AptMasterRepository
    from modules.real_estate.apartment_repository import ApartmentRepository
    from modules.real_estate.transaction_repository import TransactionRepository
    from modules.real_estate.jeonse.repository import JeonseRepository
    from modules.real_estate.supply.repository import SupplyRepository
    from modules.real_estate.location.location_repository import LocationRepository
    from modules.real_estate.macro.service import MacroService
    from modules.real_estate.commute.commute_repository import CommuteRepository
    from core.llm import LLMFactory

    cfg = RealEstateConfig()
    re_db = cfg.get("real_estate_db_path", "data/real_estate.db")
    commute_db = cfg.get("commute_cache_db_path", "data/commute_cache.db")

    return AptAnalysisOrchestrator(
        apt_master_repo=AptMasterRepository(db_path=re_db),
        apt_details_repo=ApartmentRepository(db_path=re_db),
        tx_repo=TransactionRepository(db_path=re_db),
        jeonse_repo=JeonseRepository(db_path=re_db),
        supply_repo=SupplyRepository(db_path=re_db),
        loc_repo=LocationRepository(db_path=re_db),
        macro_svc=MacroService(),
        commute_repo=CommuteRepository(db_path=commute_db),
        llm=LLMFactory.create(),
    )


def _send_slack_if_needed(report, send_slack: bool) -> None:
    if not send_slack:
        return
    try:
        from core.notify.slack import SlackSender
        sender = SlackSender()
        sender.send(report.slack_text)
    except Exception as e:
        logger.warning("[AptAnalyze] Slack 전송 실패: %s", e)


def _report_to_dict(report) -> dict:
    import dataclasses
    return dataclasses.asdict(report)


@router.post("/jobs/apt/analyze")
def apt_analyze(req: AptAnalyzeRequest):
    """단지 코드 기반 심층 분석 실행 + 저장 + (선택) Slack 전송."""
    try:
        orchestrator = _build_apt_analysis_orchestrator()
        report = orchestrator.analyze(req.complex_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[AptAnalyze] 분석 실패: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    repo = _get_apt_analysis_repo()
    repo.save(report)
    _send_slack_if_needed(report, req.send_slack)

    return {"status": "success", "report": _report_to_dict(report)}


@router.get("/dashboard/apt/analysis/{complex_code}/latest")
def apt_analysis_latest(complex_code: str):
    """가장 최근 심층 분석 결과 1건 반환. 없으면 404."""
    repo = _get_apt_analysis_repo()
    report = repo.get_latest(complex_code)
    if report is None:
        raise HTTPException(status_code=404, detail=f"분석 결과 없음: {complex_code}")
    return _report_to_dict(report)


@router.get("/dashboard/apt/analysis/{complex_code}")
def apt_analysis_history(complex_code: str, limit: int = 10):
    """분석 이력 목록 반환 (최신순)."""
    repo = _get_apt_analysis_repo()
    history = repo.get_history(complex_code, limit=limit)
    return [_report_to_dict(r) for r in history]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/api/test_apt_analysis_api.py -v 2>&1 | tail -15
```

예상: `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/api/routers/real_estate.py \
        tests/api/test_apt_analysis_api.py \
        docs/features/apt-analysis/progress.md
git commit -m "feat(api): POST /jobs/apt/analyze + GET /dashboard/apt/analysis 엔드포인트 추가"
```

---

## Task 9: 대시보드 Tab1 버튼 추가

**Files:**
- Modify: `src/dashboard/views/real_estate.py`

- [ ] **Step 1: `_render_apt_detail_panel` 하단에 버튼 추가**

`src/dashboard/views/real_estate.py` 에서 `_render_apt_detail_panel` 함수 내부, 실거래가 섹션(`# ── 실거래가 ──`) 바로 위에 아래 코드를 삽입한다.

현재 코드에서:
```python
    # ── 실거래가 ──────────────────────────────────────────────────────────────
    st.markdown("### 📈 최근 실거래가")
```

이 라인 바로 위에 삽입:

```python
        # ── 심층 분석 버튼 (complex_code가 있는 경우만 표시) ───────────────────────────
        _analysis_complex_code = getattr(entry, "complex_code", None) or getattr(details, "complex_code", None) if details else None
        if _analysis_complex_code:
            st.markdown("---")
            _btn_col1, _btn_col2 = st.columns(2)
            with _btn_col1:
                if st.button("🔬 심층 분석", key=f"analyze_{_analysis_complex_code}", use_container_width=True):
                    import requests as _req
                    with st.spinner("심층 분석 중... (LLM 처리 시 최대 2분 소요)"):
                        try:
                            _resp = _req.post(
                                "http://localhost:8000/jobs/apt/analyze",
                                json={"complex_code": _analysis_complex_code, "send_slack": True},
                                timeout=180,
                            )
                            if _resp.status_code == 200:
                                _rdata = _resp.json().get("report", {})
                                with st.expander("🔬 심층 분석 결과", expanded=True):
                                    st.markdown(_rdata.get("llm_insight", ""))
                                    if _rdata.get("jeonse_ratio"):
                                        st.metric("전세가율", f"{_rdata['jeonse_ratio']:.1f}%")
                                    if _rdata.get("supply_risk_summary"):
                                        st.caption(f"공급리스크: {_rdata['supply_risk_summary']}")
                            else:
                                st.error(f"분석 실패: {_resp.status_code}")
                        except Exception as _e:
                            st.error(f"서버 오류: {_e}")

            with _btn_col2:
                if st.button("📋 이전 분석 보기", key=f"prev_analysis_{_analysis_complex_code}", use_container_width=True):
                    import requests as _req
                    try:
                        _resp = _req.get(
                            f"http://localhost:8000/dashboard/apt/analysis/{_analysis_complex_code}/latest",
                            timeout=10,
                        )
                        if _resp.status_code == 200:
                            _rdata = _resp.json()
                            with st.expander(f"📋 이전 분석 ({_rdata.get('generated_at', '')[:10]})", expanded=True):
                                st.markdown(_rdata.get("llm_insight", ""))
                                if _rdata.get("jeonse_ratio"):
                                    st.metric("전세가율", f"{_rdata['jeonse_ratio']:.1f}%")
                        elif _resp.status_code == 404:
                            st.info("이전 분석 결과가 없습니다. 먼저 심층 분석을 실행하세요.")
                        else:
                            st.error(f"조회 실패: {_resp.status_code}")
                    except Exception as _e:
                        st.error(f"서버 오류: {_e}")
```

- [ ] **Step 2: 전체 테스트 스위트 실행 (회귀 확인)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/dashboard -q 2>&1 | tail -20
```

예상: 기존 회귀 없음, 신규 테스트 모두 PASS

- [ ] **Step 3: 커밋**

```bash
git add src/dashboard/views/real_estate.py \
        docs/features/apt-analysis/progress.md
git commit -m "feat(dashboard): Tab1 심층 분석 버튼 추가 (🔬 심층 분석 / 📋 이전 분석 보기)"
```

---

## Task 10: Docker Compose + Context 업데이트

**Files:**
- Modify: `docker-compose.yml`
- Create: `docs/features/apt-analysis/result.md`
- Modify: `docs/context/active_state.md`
- Modify: `docs/context/history.md`

- [ ] **Step 1: docker-compose.yml에 볼륨 마운트 추가**

`docker-compose.yml` 의 `api` 서비스 `volumes:` 섹션에서:

```yaml
    volumes:
      - ./src:/app/src
      - ./data:/app/data
      - ./tests:/app/tests
```

를 아래로 교체:

```yaml
    volumes:
      - ./src:/app/src
      - ./data:/app/data
      - ./tests:/app/tests
      - ~/.claude:/root/.claude:ro
      - /usr/local/bin/claude:/usr/local/bin/claude:ro
      # Gemini CLI 사용 시 아래 두 줄 주석 해제:
      # - ~/.config/gemini:/root/.config/gemini:ro
      # - /usr/local/bin/gemini:/usr/local/bin/gemini:ro
```

- [ ] **Step 2: result.md 작성**

`docs/features/apt-analysis/result.md` 생성:

```markdown
# Result

**완료일:** 2026-05-30

## 변경 내용

- `src/core/llm.py`: ClaudeCodeClient, GeminiCliClient, LLMFactory 확장
- `src/modules/real_estate/jeonse/repository.py`: get_by_complex() 추가
- `src/modules/real_estate/apt_master_repository.py`: get_by_complex_code() 추가
- `src/modules/real_estate/commute/commute_repository.py`: get_all_by_origin() 추가
- `src/modules/real_estate/apt_analysis/` 신규 패키지 (models, repository, orchestrator, formatter)
- `src/api/routers/real_estate.py`: POST /jobs/apt/analyze, GET /dashboard/apt/analysis 엔드포인트 추가
- `src/dashboard/views/real_estate.py`: Tab1 심층 분석 버튼 추가
- `docker-compose.yml`: claude CLI 볼륨 마운트 추가

## 테스트 결과

(테스트 실행 후 기입)

## E2E 검증

대시보드 Tab1 → 단지 선택 → 🔬 심층 분석 버튼 → 결과 확인 (수동)
```

- [ ] **Step 3: active_state.md 업데이트**

`docs/context/active_state.md` 를 읽고 현재 포커스를 `apt-analysis 완료`로 업데이트.

- [ ] **Step 4: history.md 업데이트**

`docs/context/history.md` 맨 위에 추가:

```markdown
## 2026-05-30 — 개별 아파트 심층 분석 기능

- `src/modules/real_estate/apt_analysis/` 신규 패키지 (ClaudeCodeClient/GeminiCliClient 로컬 CLI 기반)
- POST /jobs/apt/analyze + GET /dashboard/apt/analysis 엔드포인트
- Tab1 🔬 심층 분석 / 📋 이전 분석 보기 버튼 추가
- AptAnalysisRepository (real_estate.db apt_analysis_reports 테이블)
```

- [ ] **Step 5: 전체 테스트 최종 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ --ignore=tests/dashboard -q 2>&1 | tail -5
```

- [ ] **Step 6: 최종 커밋**

```bash
git add docker-compose.yml \
        docs/features/apt-analysis/result.md \
        docs/features/apt-analysis/progress.md \
        docs/context/active_state.md \
        docs/context/history.md
git commit -m "docs(sop): apt-analysis result.md + context 업데이트"
```
