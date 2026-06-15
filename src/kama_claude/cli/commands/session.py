from __future__ import annotations

import asyncio
import json
import sys

from kama_claude.core.config import KamaConfig
from kama_claude.core.transport.socket_client import IpcError, SocketClient


async def _send(config: KamaConfig, method: str, params: dict[str, object]) -> dict[str, object]:
    client = SocketClient(config.host, config.port)
    loop_task: asyncio.Task[None] | None = None
    try:
        await client.connect()
        loop_task = asyncio.create_task(client.run_event_loop())
        result = await client.send_command(method, params)
        return result
    finally:
        if loop_task is not None:
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        await client.close()


def cmd_session_list(config: KamaConfig, session_id: str | None = None) -> None:
    try:
        params: dict[str, object] = {}
        if session_id:
            params["session_id"] = session_id
        result = asyncio.run(_send(config, "session.list", params))
    except (ConnectionRefusedError, OSError):
        print(f"error: core not running ({config.host}:{config.port})", file=sys.stderr)
        sys.exit(1)
    except IpcError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    sessions = result.get("sessions", [])
    if not sessions:
        print("session not found" if session_id else "no sessions")
        return
    for item in sessions:
        if not isinstance(item, dict):
            continue
        sid = item.get("session_id", "")
        status = item.get("status", "")
        mode = item.get("mode", "")
        updated = item.get("updated_at", "")
        runs = item.get("run_count", 0)
        title = item.get("title", "")
        alias = item.get("alias", "")
        alias_part = f" @{alias}" if alias else ""
        print(f"{sid}{alias_part}  {status:<17} {mode:<8} runs={runs:<3} updated={updated}  {title}")


def cmd_session_alias(session_id: str, alias: str, config: KamaConfig) -> None:
    try:
        result = asyncio.run(
            _send(config, "session.alias", {"session_id": session_id, "alias": alias})
        )
    except (ConnectionRefusedError, OSError):
        print(f"error: core not running ({config.host}:{config.port})", file=sys.stderr)
        sys.exit(1)
    except IpcError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"alias set: {result.get('session_id')} @{result.get('alias')}")


def cmd_session_cancel(session_id: str, config: KamaConfig) -> None:
    try:
        result = asyncio.run(_send(config, "session.cancel", {"session_id": session_id}))
    except (ConnectionRefusedError, OSError):
        print(f"error: core not running ({config.host}:{config.port})", file=sys.stderr)
        sys.exit(1)
    except IpcError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"cancelled: {session_id} ({result.get('cancelled')})")


def cmd_session_history(session_id: str, config: KamaConfig, *, raw: bool = False) -> None:
    try:
        result = asyncio.run(_send(config, "session.get_history", {"session_id": session_id}))
    except (ConnectionRefusedError, OSError):
        print(f"error: core not running ({config.host}:{config.port})", file=sys.stderr)
        sys.exit(1)
    except IpcError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    messages = result.get("messages", [])
    if raw:
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        return
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "?")
        content = msg.get("content", "")
        print(f"[{role}]")
        if isinstance(content, str):
            print(content)
        else:
            print(json.dumps(content, ensure_ascii=False, indent=2))
        print()
