from __future__ import annotations

import json
import struct

import pytest

from app.core.clients.kiro import (
    KiroAccountCredentials,
    KiroStreamEvent,
    KiroUpstreamError,
    _parse_aws_event_stream_message,
    build_kiro_headers,
    parse_kiro_json_event,
)

pytestmark = pytest.mark.unit


def test_build_kiro_headers_include_bearer_and_machine_id():
    headers = build_kiro_headers(
        access_token="access",
        host="q.us-east-1.amazonaws.com",
        machine_id="machine-123",
        api_name="codewhispererstreaming",
        sdk_version="1.0.34",
        mode="m/E",
        kiro_version="0.11.107",
        system_version="Darwin",
        node_version="22.0.0",
    )

    assert headers["Authorization"] == "Bearer access"
    assert "KiroIDE-0.11.107-machine-123" in headers["User-Agent"]
    assert headers["x-amzn-codewhisperer-optout"] == "true"
    assert headers["Host"] == "q.us-east-1.amazonaws.com"


def test_build_kiro_headers_without_machine_id():
    headers = build_kiro_headers(
        access_token="tok",
        host="q.us-east-1.amazonaws.com",
    )
    assert "KiroIDE-" in headers["User-Agent"]
    # No machine id suffix
    assert "KiroIDE-0.11.107 " in headers["User-Agent"]


def test_parse_kiro_json_event_text_delta():
    events = parse_kiro_json_event({"type": "assistantResponseEvent", "content": "hi"})
    assert events == [KiroStreamEvent(type="text", text="hi")]


def test_parse_kiro_json_event_empty_content_returns_nothing():
    events = parse_kiro_json_event({"type": "assistantResponseEvent", "content": ""})
    assert events == []


def test_parse_kiro_json_event_usage():
    events = parse_kiro_json_event({"type": "usageEvent", "inputTokens": 10, "outputTokens": 5})
    assert len(events) == 1
    assert events[0].type == "usage"
    assert events[0].input_tokens == 10
    assert events[0].output_tokens == 5


def test_parse_kiro_json_event_thinking():
    events = parse_kiro_json_event({"type": "thinkingEvent", "content": "reasoning..."})
    assert len(events) == 1
    assert events[0].type == "thinking"
    assert events[0].is_thinking is True
    assert events[0].text == "reasoning..."


def test_parse_kiro_json_event_unknown_returns_empty():
    events = parse_kiro_json_event({"type": "someUnknownEvent", "data": "x"})
    assert events == []


def _build_aws_event_stream_frame(payload: bytes, event_type: str) -> bytes:
    """Build a minimal AWS event-stream binary frame for testing."""
    # Encode the :event-type header
    header_name = b":event-type"
    header_value = event_type.encode("utf-8")
    # Header format: 1-byte name length, name, 1-byte type (7=string), 2-byte value length, value
    header_blob = (
        bytes([len(header_name)])
        + header_name
        + bytes([7])
        + struct.pack(">H", len(header_value))
        + header_value
    )
    headers_length = len(header_blob)
    total_length = 12 + headers_length + len(payload) + 4  # prelude + headers + payload + trailing CRC
    prelude = struct.pack(">II", total_length, headers_length)
    prelude_crc = b"\x00\x00\x00\x00"  # placeholder CRC (not validated in parser)
    message_crc = b"\x00\x00\x00\x00"
    return prelude + prelude_crc + header_blob + payload + message_crc


def test_parse_aws_event_stream_message_extracts_event_type():
    payload = json.dumps({"content": "hello"}).encode("utf-8")
    frame = _build_aws_event_stream_frame(payload, "assistantResponseEvent")

    headers, extracted_payload, total_length = _parse_aws_event_stream_message(frame)

    assert headers.get(":event-type") == "assistantResponseEvent"
    assert json.loads(extracted_payload) == {"content": "hello"}
    assert total_length == len(frame)


def test_parse_aws_event_stream_message_raises_on_short_buffer():
    with pytest.raises(ValueError, match="too short"):
        _parse_aws_event_stream_message(b"\x00\x00\x00\x10")  # only 4 bytes
