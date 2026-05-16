from __future__ import annotations

import pytest

from app.core.clients.kiro import KIRO_MODEL
from app.core.kiro.translator import responses_to_kiro_payload
from app.core.openai.requests import ResponsesRequest

pytestmark = pytest.mark.unit


def _req(**kwargs):
    """Build a ResponsesRequest with required fields defaulted."""
    kwargs.setdefault("instructions", "")
    return ResponsesRequest.model_validate(kwargs)


def test_responses_text_forces_claude_sonnet_46():
    req = _req(model="gpt-5.5", input="hello", instructions="be brief")

    payload = responses_to_kiro_payload(req)

    current = payload["conversationState"]["currentMessage"]["userInputMessage"]
    assert current["modelId"] == KIRO_MODEL
    assert "be brief" in current["content"]
    assert "hello" in current["content"]


def test_responses_tool_result_maps_to_kiro_context():
    req = _req(
        model="gpt-5.5",
        input=[{"type": "function_call_output", "call_id": "call_1", "output": "done"}],
    )

    payload = responses_to_kiro_payload(req)

    context = payload["conversationState"]["currentMessage"]["userInputMessage"]["userInputMessageContext"]
    assert context["toolResults"][0]["toolUseId"] == "call_1"
    assert context["toolResults"][0]["content"][0]["text"] == "done"


def test_responses_function_tool_maps_to_kiro_tool_spec():
    req = _req(
        model="gpt-5.5",
        input="hi",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    payload = responses_to_kiro_payload(req)

    context = payload["conversationState"]["currentMessage"]["userInputMessage"]["userInputMessageContext"]
    assert context["tools"][0]["toolSpec"]["name"] == "get_weather"
    assert context["tools"][0]["toolSpec"]["description"] == "Get weather"


def test_responses_empty_input_uses_fallback():
    req = _req(model="gpt-5.5", input="")

    payload = responses_to_kiro_payload(req)

    current = payload["conversationState"]["currentMessage"]["userInputMessage"]
    assert current["content"] == "."


def test_responses_instructions_prepended_to_content():
    req = _req(model="gpt-5.5", input="user message", instructions="system prompt")

    payload = responses_to_kiro_payload(req)

    content = payload["conversationState"]["currentMessage"]["userInputMessage"]["content"]
    assert content.index("system prompt") < content.index("user message")


def test_responses_model_id_always_forced_regardless_of_requested_model():
    for model in ("gpt-4o", "o3", "claude-opus-4.5", "gpt-5.5"):
        req = _req(model=model, input="hi")
        payload = responses_to_kiro_payload(req)
        current = payload["conversationState"]["currentMessage"]["userInputMessage"]
        assert current["modelId"] == KIRO_MODEL, f"Expected {KIRO_MODEL} for model={model}"


def test_responses_conversation_id_is_stable():
    req = _req(model="gpt-5.5", input="hi", instructions="be brief")

    payload1 = responses_to_kiro_payload(req)
    payload2 = responses_to_kiro_payload(req)

    assert (
        payload1["conversationState"]["conversationId"]
        == payload2["conversationState"]["conversationId"]
    )


def test_responses_assistant_history_item_goes_to_history():
    req = _req(
        model="gpt-5.5",
        input=[
            {"type": "message", "role": "assistant", "content": "I am the assistant"},
            {"type": "message", "role": "user", "content": "follow up"},
        ],
    )

    payload = responses_to_kiro_payload(req)

    history = payload["conversationState"].get("history", [])
    assert len(history) == 1
    assert history[0]["assistantResponseMessage"]["content"] == "I am the assistant"
    current = payload["conversationState"]["currentMessage"]["userInputMessage"]["content"]
    assert "follow up" in current
