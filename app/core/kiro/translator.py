from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any
from uuid import uuid4

from app.core.clients.kiro import KIRO_MODEL
from app.core.openai.requests import ResponsesRequest
from app.core.types import JsonObject, JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping

MINIMAL_FALLBACK_USER_CONTENT = "."


def responses_to_kiro_payload(req: ResponsesRequest) -> dict[str, Any]:
    """Translate a ResponsesRequest into a Kiro conversationState payload.

    Forces modelId to KIRO_MODEL regardless of the downstream requested model.
    """
    instructions = (req.instructions or "").strip()
    current_text, images, tool_results, history = _responses_input_to_kiro(req.input, instructions)

    if not current_text and not images and not tool_results:
        current_text = MINIMAL_FALLBACK_USER_CONTENT

    current_message: dict[str, Any] = {
        "content": current_text,
        "modelId": KIRO_MODEL,
        "origin": "AI_EDITOR",
    }
    if images:
        current_message["images"] = images

    tools = _responses_tools_to_kiro(req.tools or [])
    if tools or tool_results:
        current_message["userInputMessageContext"] = {
            "tools": tools,
            "toolResults": tool_results,
        }

    conversation_state: dict[str, Any] = {
        "chatTriggerType": "MANUAL",
        "agentTaskType": "vibe",
        "agentContinuationId": uuid4().hex,
        "conversationId": _conversation_id(req, instructions),
        "currentMessage": {"userInputMessage": current_message},
    }
    if history:
        conversation_state["history"] = history

    payload: dict[str, Any] = {"conversationState": conversation_state}
    max_tokens = getattr(req, "max_output_tokens", None)
    if max_tokens:
        payload["inferenceConfig"] = {"maxTokens": max_tokens}
    return payload


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _responses_input_to_kiro(
    input_value: JsonValue,
    instructions: str,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse ResponsesRequest.input into (current_text, images, tool_results, history).

    - current_text: the user's current message text (instructions prepended)
    - images: list of Kiro image objects for the current turn
    - tool_results: list of Kiro toolResult objects for the current turn
    - history: list of prior conversation turns
    """
    items: list[JsonValue]
    if isinstance(input_value, str):
        items = [{"type": "message", "role": "user", "content": input_value}]
    elif is_json_list(input_value):
        items = list(input_value)
    else:
        items = []

    current_parts: list[str] = []
    if instructions:
        current_parts.append(instructions)
    images: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    for item in items:
        if not is_json_mapping(item):
            if isinstance(item, str):
                current_parts.append(item)
            continue
        item_type = item.get("type")
        role = item.get("role")

        if item_type == "function_call_output":
            # Tool result from a previous function call
            call_id = str(item.get("call_id") or item.get("tool_call_id") or "")
            output = item.get("output") or ""
            tool_results.append({
                "toolUseId": call_id,
                "content": [{"text": str(output)}],
            })
            continue

        if item_type == "message" or role in ("user", "assistant", "system"):
            content = item.get("content")
            text = _text_from_content(content)
            if role == "assistant":
                history.append({
                    "userInputMessage": {"content": ""},
                    "assistantResponseMessage": {"content": text},
                })
            elif role == "system":
                if text and not instructions:
                    current_parts.insert(0, text)
            else:
                # user message — treat as current turn text
                current_parts.append(text)
                # Extract images from content parts
                if is_json_list(content):
                    for part in content:
                        if is_json_mapping(part):
                            img = _image_from_part(part)
                            if img:
                                images.append(img)
            continue

        # Plain string item
        if isinstance(item, str):
            current_parts.append(item)

    current_text = "\n\n".join(p for p in current_parts if p).strip()
    return current_text, images, tool_results, history


def _text_from_content(value: JsonValue) -> str:
    """Extract plain text from a content value (string or array of parts)."""
    if isinstance(value, str):
        return value
    if is_json_list(value):
        parts: list[str] = []
        for part in value:
            if isinstance(part, str):
                parts.append(part)
            elif is_json_mapping(part):
                part_type = part.get("type")
                if part_type in ("text", "input_text", "output_text"):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "\n".join(parts)
    return ""


def _image_from_part(part: Mapping[str, JsonValue]) -> dict[str, Any] | None:
    """Convert an image content part to a Kiro image object, or None if not an image."""
    part_type = part.get("type")
    if part_type not in ("image_url", "input_image"):
        return None
    image_url = part.get("image_url")
    if is_json_mapping(image_url):
        url = image_url.get("url")
        if isinstance(url, str):
            return {"format": "URL", "source": url}
    if isinstance(image_url, str):
        return {"format": "URL", "source": image_url}
    return None


def _responses_tools_to_kiro(tools: list[JsonValue]) -> list[dict[str, Any]]:
    """Convert OpenAI-style tool definitions to Kiro tool specifications."""
    kiro_tools: list[dict[str, Any]] = []
    for tool in tools:
        if not is_json_mapping(tool):
            continue
        tool_type = tool.get("type")
        if tool_type == "function":
            fn = tool.get("function")
            if not is_json_mapping(fn):
                continue
            name = fn.get("name")
            description = fn.get("description") or ""
            parameters = fn.get("parameters") or {}
            kiro_tools.append({
                "toolSpec": {
                    "name": str(name) if name else "",
                    "description": str(description),
                    "inputSchema": {"json": parameters},
                }
            })
        # Other tool types (file_search, web_search, etc.) are not supported by Kiro
    return kiro_tools


def _conversation_id(req: ResponsesRequest, instructions: str) -> str:
    """Derive a stable conversation ID from the request context."""
    key = f"{req.model}:{instructions[:64]}:{req.previous_response_id or ''}"
    return sha256(key.encode()).hexdigest()[:32]
