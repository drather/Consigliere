import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from unittest.mock import patch, MagicMock
from modules.automation.service import AutomationService


def test_list_executions_returns_formatted_data():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "id": "exec-001",
                "workflowId": "wf001",
                "workflowData": {"name": "Real Estate News Insight"},
                "status": "success",
                "startedAt": "2026-06-06T06:00:05.000Z",
                "stoppedAt": "2026-06-06T06:00:15.000Z",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        service = AutomationService(n8n_url="http://localhost:5678", api_key="test-key")
        result = service.list_executions(limit=50)

    assert len(result) == 1
    row = result[0]
    assert row["workflowName"] == "Real Estate News Insight"
    assert row["status"] == "success"
    assert row["duration_sec"] == 10.0
    assert row["startedAt"] == "2026-06-06 15:00:05"  # UTC+9
    assert row["stoppedAt"] == "2026-06-06 15:00:15"


def test_list_executions_passes_status_param():
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        service = AutomationService(n8n_url="http://localhost:5678", api_key="test-key")
        service.list_executions(limit=10, status="error")

        call_args = mock_client.get.call_args
        params = call_args[1].get("params") or call_args.kwargs.get("params", {})
        assert params.get("status") == "error"
        assert params.get("limit") == 10


def test_list_executions_returns_empty_on_network_error():
    with patch("httpx.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection refused")

        service = AutomationService(n8n_url="http://localhost:5678", api_key="test-key")
        result = service.list_executions()

    assert result == []


def test_format_execution_handles_missing_stopped_at():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "id": "exec-002",
                "workflowId": "wf002",
                "workflowData": {"name": "Running Workflow"},
                "status": "running",
                "startedAt": "2026-06-06T08:00:00.000Z",
                "stoppedAt": None,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        service = AutomationService(n8n_url="http://localhost:5678", api_key="test-key")
        result = service.list_executions()

    assert result[0]["stoppedAt"] is None
    assert result[0]["duration_sec"] is None
    assert result[0]["status"] == "running"
