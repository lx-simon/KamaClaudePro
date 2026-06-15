from __future__ import annotations

import argparse
import asyncio
import json
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from kama_claude.core.config import get_config
from kama_claude.core.transport.socket_client import SocketClient

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).with_name("static")
DEFAULT_TOPICS = [
    "session.*",
    "run.*",
    "step.*",
    "tool.*",
    "llm.token",
    "llm.usage",
    "permission.*",
    "context.*",
    "subagent.*",
    "skill.*",
]


class WebState:
    def __init__(self, core_host: str, core_port: int) -> None:
        self.core_host = core_host
        self.core_port = core_port


async def _core_command(state: WebState, method: str, params: dict[str, Any]) -> dict[str, Any]:
    client = SocketClient(state.core_host, state.core_port)
    loop_task: asyncio.Task[None] | None = None
    await client.connect()
    try:
        loop_task = asyncio.create_task(client.run_event_loop())
        return await client.send_command(method, params)
    finally:
        if loop_task is not None:
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        await client.close()


class KamaWebHandler(BaseHTTPRequestHandler):
    server_version = "KamaWeb/0.0.3"

    @property
    def state(self) -> WebState:
        return self.server.state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: object) -> None:
        log.info("web %s", fmt % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC_DIR / "index.html")
        elif parsed.path == "/app.css":
            self._send_file(STATIC_DIR / "app.css")
        elif parsed.path == "/app.js":
            self._send_file(STATIC_DIR / "app.js")
        elif parsed.path == "/api/sessions":
            self._json_command("session.list", {})
        elif parsed.path == "/api/history":
            qs = parse_qs(parsed.query)
            session_id = (qs.get("session") or [""])[0]
            self._json_command("session.get_history", {"session_id": session_id})
        elif parsed.path == "/events":
            qs = parse_qs(parsed.query)
            replay = (qs.get("replay") or [None])[0]
            self._events(replay)
        else:
            self.send_error(404, "not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json()
        if parsed.path == "/api/session/create":
            self._json_command("session.create", {"mode": "chat", **body})
        elif parsed.path == "/api/session/resume":
            self._json_command("session.resume", body)
        elif parsed.path == "/api/session/send":
            self._json_command("session.send_message", body)
        elif parsed.path == "/api/session/alias":
            self._json_command("session.alias", body)
        elif parsed.path == "/api/session/cancel":
            self._json_command("session.cancel", body)
        elif parsed.path == "/api/session/close":
            self._json_command("session.close", body)
        elif parsed.path == "/api/permission/respond":
            self._json_command("permission.respond", body)
        elif parsed.path == "/api/session/compact":
            self._json_command("session.compact", body)
        else:
            self.send_error(404, "not found")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _json_command(self, method: str, params: dict[str, Any]) -> None:
        try:
            result = asyncio.run(_core_command(self.state, method, params))
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _events(self, replay_run_id: str | None) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            asyncio.run(self._event_loop(replay_run_id))
        except Exception as exc:
            payload = {"type": "core.unavailable", "error_message": str(exc)}
            try:
                self.wfile.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
            except OSError:
                pass

    async def _event_loop(self, replay_run_id: str | None) -> None:
        client = SocketClient(self.state.core_host, self.state.core_port)
        await client.connect()

        async def emit(event: dict[str, Any]) -> None:
            payload = json.dumps(event, ensure_ascii=False)
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
            self.wfile.flush()

        client.on_event(emit)
        params: dict[str, Any] = {"topics": DEFAULT_TOPICS, "scope": "global"}
        if replay_run_id:
            params["replay_from_run"] = replay_run_id
        loop_task: asyncio.Task[None] | None = None
        try:
            loop_task = asyncio.create_task(client.run_event_loop())
            await client.send_command("event.subscribe", params)
            await loop_task
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            if loop_task is not None and not loop_task.done():
                loop_task.cancel()
                try:
                    await loop_task
                except asyncio.CancelledError:
                    pass
            await client.close()

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "not found")
            return
        raw = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix in (".html", ".css"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class KamaWebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr: tuple[str, int], state: WebState) -> None:
        self.state = state
        super().__init__(addr, KamaWebHandler)


def main() -> None:
    parser = argparse.ArgumentParser(prog="kama-web", description="KamaClaude Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Web UI bind host")
    parser.add_argument("--port", type=int, default=7440, help="Web UI bind port")
    parser.add_argument("--core-host", default=None, help="Core daemon host")
    parser.add_argument("--core-port", type=int, default=None, help="Core daemon port")
    args = parser.parse_args()

    config = get_config()
    state = WebState(args.core_host or config.host, args.core_port or config.port)
    server = KamaWebServer((args.host, args.port), state)
    url = f"http://{args.host}:{args.port}"
    print(f"kama-web listening on {url}  core={state.core_host}:{state.core_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
