from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import anthropic
import httpx
import openai

from kama_claude.core.bus.events import LlmModelSelectedEvent, LlmTokenEvent, LlmUsageEvent
from kama_claude.core.events.bus import EventBus
from kama_claude.core.llm.types import LlmResponse, ToolCallBlock, UsageStats

_MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-sonnet-4-6": 200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "claude-opus-4-7": 200_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
}

_MAX_STREAM_RETRIES = 3
_RETRY_BACKOFF_S = (1.0, 2.0, 4.0)

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Use the available tools to complete the user's goal. "
    "When the goal is fully achieved, respond with a final answer and do not call any more tools."
)


def _context_window(model: str) -> int:
    return _MODEL_CONTEXT_WINDOWS.get(model, 200_000)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)

    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            parts.append(str(block))
            continue
        btype = block.get("type")
        if btype == "text":
            parts.append(str(block.get("text", "")))
        elif btype == "tool_result":
            parts.append(str(block.get("content", "")))
        elif btype == "thinking":
            parts.append(str(block.get("thinking", "")))
    return "\n".join(p for p in parts if p)


def _json_loads_object(value: str) -> dict[str, object]:
    loaded = json.loads(value or "{}")
    return loaded if isinstance(loaded, dict) else {}


def _stream_index(value: object) -> int | None:
    try:
        index = int(value) if value is not None else 0
    except (TypeError, ValueError):
        return None
    return index if index >= 0 else None


def _openai_tool_schema(schema: dict[str, object]) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema.get("description", ""),
            "parameters": schema.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _openai_messages(messages: list[dict[str, object]], system: str) -> list[dict[str, object]]:
    converted: list[dict[str, object]] = [{"role": "system", "content": system}]
    for msg in messages:
        role = str(msg.get("role", "user"))
        content = msg.get("content", "")
        if role == "assistant" and isinstance(content, list):
            assistant: dict[str, object] = {
                "role": "assistant",
                "content": _as_text(content) or None,
            }
            tool_calls: list[dict[str, object]] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(
                                    block.get("input", {}),
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    )
            if tool_calls:
                assistant["tool_calls"] = tool_calls
            converted.append(assistant)
        elif role == "user" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    converted.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block.get("content", "")),
                        }
                    )
            text = _as_text(content)
            if text:
                converted.append({"role": "user", "content": text})
        else:
            converted.append({"role": role, "content": _as_text(content)})
    return converted


class AnthropicProvider:
    def __init__(self, model: str, client: Any = None) -> None:
        if client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise SystemExit("ANTHROPIC_API_KEY not set")
            self._client: Any = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self._client = client
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, object]],
        tool_schemas: list[dict[str, object]],
        bus: EventBus,
        run_id: str,
        *,
        step: int = 0,
        system: str | None = None,
    ) -> LlmResponse:
        await bus.publish(
            LlmModelSelectedEvent(run_id=run_id, model=self._model, strategy="static", ts=_now())
        )

        system_blocks: list[dict[str, object]] = [
            {
                "type": "text",
                "text": system or _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            },
        ]

        tools: list[dict[str, object]] = list(tool_schemas)
        if tools:
            last = dict(tools[-1])
            last["cache_control"] = {"type": "ephemeral"}
            tools = tools[:-1] + [last]

        kwargs: dict[str, object] = {
            "model": self._model,
            "max_tokens": 8192,
            "system": system_blocks,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        text_parts: list[str] = []
        final_message: Any = None

        for attempt in range(1, _MAX_STREAM_RETRIES + 1):
            text_parts = []
            try:
                async with self._client.messages.stream(**kwargs) as stream:
                    async for text in stream.text_stream:
                        if attempt == 1:
                            await bus.publish(LlmTokenEvent(run_id=run_id, token=text, ts=_now()))
                        text_parts.append(text)
                    final_message = await stream.get_final_message()
                break
            except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError) as exc:
                if attempt == _MAX_STREAM_RETRIES:
                    log.error(
                        "stream failed after %d attempts run_id=%s step=%d: %s",
                        _MAX_STREAM_RETRIES,
                        run_id,
                        step,
                        exc,
                    )
                    raise
                delay = _RETRY_BACKOFF_S[attempt - 1]
                log.warning(
                    "stream dropped (attempt %d/%d) run_id=%s step=%d: %s; retrying in %.0fs",
                    attempt,
                    _MAX_STREAM_RETRIES,
                    run_id,
                    step,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

        assert final_message is not None

        usage = final_message.usage
        cache_read: int = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create: int = getattr(usage, "cache_creation_input_tokens", 0) or 0
        context_pct = usage.input_tokens / _context_window(self._model)

        await bus.publish(
            LlmUsageEvent(
                run_id=run_id,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_input_tokens=cache_read,
                cache_creation_input_tokens=cache_create,
                context_pct=context_pct,
                ts=_now(),
            )
        )

        tool_calls: list[ToolCallBlock] = []
        thinking_blocks: list[dict[str, object]] = []
        for block in final_message.content:
            if block.type == "tool_use":
                tool_calls.append(
                    ToolCallBlock(id=block.id, name=block.name, input=dict(block.input))
                )
            elif block.type == "thinking":
                thinking_blocks.append(
                    {"type": "thinking", "thinking": block.thinking, "signature": block.signature}
                )

        return LlmResponse(
            stop_reason=final_message.stop_reason or "end_turn",
            tool_calls=tool_calls,
            text="".join(text_parts),
            thinking_blocks=thinking_blocks,
            usage=UsageStats(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_read_input_tokens=cache_read,
                cache_creation_input_tokens=cache_create,
                context_pct=context_pct,
            ),
        )


class OpenAIProvider:
    def __init__(self, model: str, client: Any = None) -> None:
        if client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise SystemExit("OPENAI_API_KEY not set")
            self._client: Any = openai.AsyncOpenAI(api_key=api_key)
        else:
            self._client = client
        self._model = model

    async def chat(
        self,
        messages: list[dict[str, object]],
        tool_schemas: list[dict[str, object]],
        bus: EventBus,
        run_id: str,
        *,
        step: int = 0,
        system: str | None = None,
    ) -> LlmResponse:
        await bus.publish(
            LlmModelSelectedEvent(run_id=run_id, model=self._model, strategy="static", ts=_now())
        )
        kwargs: dict[str, object] = {
            "model": self._model,
            "messages": _openai_messages(messages, system or _SYSTEM_PROMPT),
            "max_tokens": 8192,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tool_schemas:
            kwargs["tools"] = [_openai_tool_schema(schema) for schema in tool_schemas]

        text_parts: list[str] = []
        stop_reason = "end_turn"
        usage: Any = None
        tool_deltas: dict[int, dict[str, str]] = {}

        for attempt in range(1, _MAX_STREAM_RETRIES + 1):
            text_parts = []
            tool_deltas = {}
            usage = None
            try:
                stream = await self._client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    usage = getattr(chunk, "usage", None) or usage
                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    choice = choices[0]
                    finish_reason = getattr(choice, "finish_reason", None)
                    if finish_reason == "tool_calls":
                        stop_reason = "tool_use"
                    elif finish_reason == "length":
                        stop_reason = "max_tokens"
                    elif finish_reason:
                        stop_reason = "end_turn"

                    delta = getattr(choice, "delta", None)
                    if delta is None:
                        continue
                    content = getattr(delta, "content", None)
                    if content:
                        if attempt == 1:
                            await bus.publish(
                                LlmTokenEvent(run_id=run_id, token=content, ts=_now())
                            )
                        text_parts.append(content)
                    for tc in getattr(delta, "tool_calls", None) or []:
                        idx = _stream_index(getattr(tc, "index", 0))
                        if idx is None:
                            log.warning(
                                "ignoring OpenAI tool_call delta with invalid index run_id=%s step=%d",
                                run_id,
                                step,
                            )
                            continue
                        current = tool_deltas.setdefault(
                            idx,
                            {"id": "", "name": "", "arguments": ""},
                        )
                        tc_id = getattr(tc, "id", None)
                        if tc_id:
                            current["id"] = tc_id
                        function = getattr(tc, "function", None)
                        if function is not None:
                            name = getattr(function, "name", None)
                            arguments = getattr(function, "arguments", None)
                            if name:
                                current["name"] += name
                            if arguments:
                                current["arguments"] += arguments
                break
            except (
                httpx.RemoteProtocolError,
                httpx.ReadError,
                httpx.ConnectError,
                openai.APIConnectionError,
                openai.APITimeoutError,
            ) as exc:
                if attempt == _MAX_STREAM_RETRIES:
                    log.error(
                        "openai stream failed after %d attempts run_id=%s step=%d: %s",
                        _MAX_STREAM_RETRIES,
                        run_id,
                        step,
                        exc,
                    )
                    raise
                delay = _RETRY_BACKOFF_S[attempt - 1]
                log.warning(
                    "openai stream dropped (attempt %d/%d) run_id=%s step=%d: %s; "
                    "retrying in %.0fs",
                    attempt,
                    _MAX_STREAM_RETRIES,
                    run_id,
                    step,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        context_pct = input_tokens / _context_window(self._model)
        await bus.publish(
            LlmUsageEvent(
                run_id=run_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=0,
                context_pct=context_pct,
                ts=_now(),
            )
        )

        tool_calls = [
            ToolCallBlock(
                id=tc["id"],
                name=tc["name"],
                input=_json_loads_object(tc["arguments"]),
            )
            for _, tc in sorted(tool_deltas.items())
            if tc["id"] and tc["name"]
        ]
        return LlmResponse(
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            text="".join(text_parts),
            usage=UsageStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                context_pct=context_pct,
            ),
        )


def create_provider(provider: str, model: str) -> AnthropicProvider | OpenAIProvider:
    normalized = provider.lower().strip()
    if normalized == "anthropic":
        return AnthropicProvider(model)
    if normalized == "openai":
        return OpenAIProvider(model)
    raise SystemExit(f"Unsupported LLM provider: {provider!r}")
