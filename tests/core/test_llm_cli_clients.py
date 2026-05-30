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

    def test_generate_json_fallback_on_non_json(self):
        from core.llm import GeminiCliClient
        client = GeminiCliClient()
        mock_result = MagicMock()
        mock_result.stdout = "이 단지는 유망합니다."
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json("테스트")
        assert "insight" in result
        assert result["insight"] == "이 단지는 유망합니다."

    def test_get_last_usage_returns_zero_token_usage(self):
        from core.llm import GeminiCliClient, TokenUsage
        client = GeminiCliClient()
        usage = client.get_last_usage()
        assert isinstance(usage, TokenUsage)
        assert usage.input_tokens == 0


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
