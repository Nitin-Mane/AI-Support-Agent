"""Regression cases for the September 17 Udacity correction requests."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import main


@pytest.mark.parametrize("kb_id", [None, "", "   ", "\t\n"])
def test_missing_kb_configuration_never_calls_aws(monkeypatch, kb_id):
    client = Mock()
    monkeypatch.setattr(main, "KB_ID", kb_id)
    monkeypatch.setattr(main, "_bedrock_runtime", client)
    response = main.search_knowledge_base("Platinum benefits")
    assert "KB_ID is empty or missing" in response
    assert "Please configure KB_ID" in response
    client.retrieve.assert_not_called()


class GatewayDouble:
    def __init__(self, failure=None, fail_on_enter=False, empty=False):
        self.active = False
        self.failure = failure
        self.fail_on_enter = fail_on_enter
        self.empty = empty

    def __enter__(self):
        if self.fail_on_enter:
            raise self.failure
        self.active = True
        return self

    def __exit__(self, *args):
        self.active = False

    def list_tools_sync(self):
        if self.failure:
            raise self.failure
        return [] if self.empty else [Mock(tool_name="order-tracker___get_order")]


@pytest.fixture
def request_dependencies(monkeypatch):
    monkeypatch.setattr(main, "GATEWAY_URL", "https://example.invalid/mcp")
    monkeypatch.setattr(main, "MEMORY_ID", "")
    monkeypatch.setattr(main, "prepare_browser_driver", Mock())
    monkeypatch.setattr(main, "AgentCoreBrowser", Mock())


@pytest.mark.parametrize("failure", [TimeoutError("timeout"), ConnectionError("refused"), RuntimeError("service unavailable")])
@pytest.mark.parametrize("fail_on_enter", [False, True])
def test_gateway_failure_returns_actionable_error_without_running_agent(
    monkeypatch, request_dependencies, failure, fail_on_enter
):
    gateway = GatewayDouble(failure=failure, fail_on_enter=fail_on_enter)
    monkeypatch.setattr(main, "gateway_client", gateway)
    agent_factory = Mock()
    monkeypatch.setattr(main, "Agent", agent_factory)
    result = asyncio.run(main.invoke({"prompt": "track order ORD-001"}))
    assert result.get("error_code") == "GATEWAY_UNAVAILABLE"
    assert "Gateway" in result["error"]
    assert "retry" in result["error"].lower()
    assert "example.invalid" not in json.dumps(result)
    agent_factory.assert_not_called()
    assert not gateway.active


def test_empty_gateway_tool_list_is_not_reported_as_success(monkeypatch, request_dependencies):
    monkeypatch.setattr(main, "gateway_client", GatewayDouble(empty=True))
    result = asyncio.run(main.invoke({"prompt": "track order ORD-001"}))
    assert result.get("error_code") == "GATEWAY_UNAVAILABLE"


def test_gateway_remains_open_during_agent_tool_use(monkeypatch, request_dependencies):
    gateway = GatewayDouble()
    monkeypatch.setattr(main, "gateway_client", gateway)

    class AgentDouble:
        def __init__(self, **kwargs):
            self.messages = [{"role": "assistant", "content": [{"text": "Order found"}]}]

        async def invoke_async(self, prompt):
            assert gateway.active, "Gateway closed before the agent could use its tools"
            return SimpleNamespace(message={"content": []})

    monkeypatch.setattr(main, "Agent", AgentDouble)
    result = asyncio.run(main.invoke({"prompt": "track order ORD-001"}))
    assert result.get("response") == "Order found"
    assert not gateway.active
