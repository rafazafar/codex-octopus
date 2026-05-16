from __future__ import annotations

import json
import struct
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from app.core.types import JsonObject, JsonValue

KIRO_MODEL = "claude-sonnet-4.6"

# Default Kiro/CodeWhisperer generation endpoints (tried in order)
_DEFAULT_ENDPOINTS = [
    "https://q.us-east-1.amazonaws.com/streaming/generateAssistantResponse",
    "https://codewhisperer.us-east-1.amazonaws.com/generateAssistantResponse",
]


@dataclass(frozen=True)
class KiroAccountCredentials:
    account_id: str
    access_token: str
    machine_id: str | None = None
    profile_arn: str | None = None


@dataclass(frozen=True)
class KiroStreamEvent:
    type: str  # "text" | "thinking" | "tool_use" | "usage" | "error"
    text: str | None = None
    is_thinking: bool = False
    tool_use: dict[str, Any] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    credits: float | None = None
    error: str | None = None


class KiroUpstreamError(Exception):
    def __init__(self, message: str, *, status: int | None = None, code: str = "upstream_error") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


def build_kiro_headers(
    *,
    access_token: str,
    host: str,
    machine_id: str | None = None,
    api_name: str = "codewhispererstreaming",
    sdk_version: str = "1.0.34",
    mode: str = "m/E",
    kiro_version: str = "0.11.107",
    system_version: str = "Linux",
    node_version: str = "22.0.0",
) -> dict[str, str]:
    machine_suffix = f"-{machine_id}" if machine_id else ""
    user_agent = (
        f"KiroIDE-{kiro_version}{machine_suffix} "
        f"aws-sdk-js-v3/{sdk_version} "
        f"ua/2.1 os/linux lang/js md/nodejs#{node_version} "
        f"api/{api_name} m/{mode}"
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.amazon.eventstream",
        "Host": host,
        "User-Agent": user_agent,
        "x-amzn-codewhisperer-optout": "true",
    }


def parse_kiro_json_event(event: Mapping[str, Any]) -> list[KiroStreamEvent]:
    """Parse a single decoded Kiro JSON event into zero or more KiroStreamEvents."""
    event_type = event.get("type") or event.get("event")
    if event_type == "assistantResponseEvent":
        content = event.get("content") or ""
        if content:
            return [KiroStreamEvent(type="text", text=str(content))]
        return []
    if event_type == "messageMetadataEvent":
        return []
    if event_type == "codeReferenceEvent":
        return []
    if event_type == "followupPromptEvent":
        return []
    if event_type == "thinkingEvent":
        content = event.get("content") or ""
        if content:
            return [KiroStreamEvent(type="thinking", text=str(content), is_thinking=True)]
        return []
    if event_type == "toolUseEvent":
        return [KiroStreamEvent(type="tool_use", tool_use=dict(event))]
    if event_type == "usageEvent":
        return [
            KiroStreamEvent(
                type="usage",
                input_tokens=int(event.get("inputTokens") or 0) or None,
                output_tokens=int(event.get("outputTokens") or 0) or None,
            )
        ]
    if event_type in {"error", "internalServerException", "throttlingException", "validationException"}:
        return [KiroStreamEvent(type="error", error=str(event.get("message") or event_type))]
    # Unknown event — ignore
    return []


# ---------------------------------------------------------------------------
# AWS binary event-stream parsing
# ---------------------------------------------------------------------------

def _parse_event_headers(blob: bytes) -> dict[str, str]:
    """Parse AWS event-stream header blob into a dict of header name -> value."""
    headers: dict[str, str] = {}
    pos = 0
    while pos < len(blob):
        name_len = blob[pos]
        pos += 1
        name = blob[pos : pos + name_len].decode("utf-8")
        pos += name_len
        header_type = blob[pos]
        pos += 1
        if header_type == 7:  # string
            value_len = struct.unpack(">H", blob[pos : pos + 2])[0]
            pos += 2
            value = blob[pos : pos + value_len].decode("utf-8")
            pos += value_len
            headers[name] = value
        else:
            # Skip unknown header types — advance past value length
            break
    return headers


def _parse_aws_event_stream_message(buffer: bytes) -> tuple[dict[str, str], bytes, int]:
    """Parse one AWS event-stream message from buffer.

    Returns (headers, payload, total_length).
    Raises ValueError if buffer is too short.
    """
    if len(buffer) < 12:
        raise ValueError("Buffer too short for event-stream prelude")
    total_length = struct.unpack(">I", buffer[0:4])[0]
    headers_length = struct.unpack(">I", buffer[4:8])[0]
    if len(buffer) < total_length:
        raise ValueError(f"Buffer too short: need {total_length}, have {len(buffer)}")
    headers_blob = buffer[12 : 12 + headers_length]
    payload = buffer[12 + headers_length : total_length - 4]
    headers = _parse_event_headers(headers_blob)
    return headers, payload, total_length


async def _iter_aws_event_stream_bytes(
    response: aiohttp.ClientResponse,
) -> AsyncIterator[KiroStreamEvent]:
    """Iterate over AWS binary event-stream frames from an aiohttp response."""
    buf = bytearray()
    async for chunk in response.content.iter_any():
        buf.extend(chunk)
        while len(buf) >= 12:
            try:
                headers, payload, total_length = _parse_aws_event_stream_message(bytes(buf))
            except ValueError:
                break
            buf = buf[total_length:]
            event_type_header = headers.get(":event-type") or headers.get(":exception-type") or ""
            if not payload:
                continue
            try:
                data = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if event_type_header:
                data["type"] = event_type_header
            for event in parse_kiro_json_event(data):
                yield event


async def stream_kiro_generation(
    payload: Mapping[str, JsonValue],
    credentials: KiroAccountCredentials,
    *,
    session: aiohttp.ClientSession | None = None,
    endpoints: list[str] | None = None,
) -> AsyncIterator[KiroStreamEvent]:
    """Stream a Kiro generation request, yielding KiroStreamEvents."""
    urls = endpoints or _DEFAULT_ENDPOINTS
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        last_error: Exception | None = None
        for url in urls:
            from urllib.parse import urlparse as _urlparse
            host = _urlparse(url).netloc
            headers = build_kiro_headers(
                access_token=credentials.access_token,
                host=host,
                machine_id=credentials.machine_id,
            )
            try:
                async with session.post(url, json=dict(payload), headers=headers) as response:
                    if response.status >= 400:
                        body = await response.text()
                        last_error = KiroUpstreamError(
                            f"Kiro upstream error: HTTP {response.status}",
                            status=response.status,
                            code="auth_error" if response.status in {401, 403} else "upstream_error",
                        )
                        if response.status in {401, 403}:
                            raise last_error
                        continue
                    async for event in _iter_aws_event_stream_bytes(response):
                        yield event
                    return
            except KiroUpstreamError:
                raise
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise KiroUpstreamError(f"All Kiro endpoints failed: {last_error}") from last_error
    finally:
        if own_session:
            await session.close()
