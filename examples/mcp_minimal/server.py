from __future__ import annotations

import json
import sys
from datetime import datetime
from typing import Any, Callable


JsonObject = dict[str, Any]
ToolHandler = Callable[[JsonObject], str]


TOOLS: dict[str, JsonObject] = {
    "hello": {
        "name": "hello",
        "description": "Say hello to someone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name to greet.",
                    "default": "world",
                },
            },
            "required": [],
        },
    },
    "add": {
        "name": "add",
        "description": "Add two numbers and return the result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number."},
                "b": {"type": "number", "description": "Second number."},
            },
            "required": ["a", "b"],
        },
    },
    "now": {
        "name": "now",
        "description": "Return the current local datetime.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
}


def hello(args: JsonObject) -> str:
    name = str(args.get("name") or "world")
    return f"Hello, {name}!"


def add(args: JsonObject) -> str:
    a = float(args["a"])
    b = float(args["b"])
    result = a + b
    if result.is_integer():
        return str(int(result))
    return str(result)


def now(args: JsonObject) -> str:
    return datetime.now().isoformat(timespec="seconds")


HANDLERS: dict[str, ToolHandler] = {
    "hello": hello,
    "add": add,
    "now": now,
}


def ok(request_id: Any, result: JsonObject) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, code: int, message: str) -> JsonObject:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def tool_text(text: str) -> JsonObject:
    return {"content": [{"type": "text", "text": text}], "isError": False}


def handle_request(message: JsonObject) -> JsonObject | None:
    method = message.get("method")
    params = message.get("params") or {}
    request_id = message.get("id")

    if request_id is None:
        return None

    if method == "initialize":
        return ok(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "minimal-mcp-template", "version": "0.1.0"},
            },
        )

    if method == "tools/list":
        return ok(request_id, {"tools": list(TOOLS.values())})

    if method == "tools/call":
        name = str(params.get("name", ""))
        arguments = params.get("arguments") or {}
        if name not in HANDLERS:
            return error(request_id, -32602, f"unknown tool: {name}")
        try:
            return ok(request_id, tool_text(HANDLERS[name](arguments)))
        except Exception as exc:
            return error(request_id, -32000, f"tool failed: {exc}")

    return error(request_id, -32601, f"method not found: {method}")


def write_message(message: JsonObject) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            write_message(error(None, -32700, f"parse error: {exc}"))
            continue

        response = handle_request(message)
        if response is not None:
            write_message(response)


if __name__ == "__main__":
    main()
