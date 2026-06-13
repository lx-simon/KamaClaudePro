from __future__ import annotations

import argparse
import sys

from kama_claude.cli.commands.chat import cmd_chat
from kama_claude.cli.commands.core import cmd_core_start, cmd_core_status, cmd_core_stop
from kama_claude.cli.commands.ping import cmd_ping
from kama_claude.cli.commands.run import cmd_run
from kama_claude.cli.commands.session import (
    cmd_session_alias,
    cmd_session_cancel,
    cmd_session_history,
    cmd_session_list,
)
from kama_claude.cli.commands.trace import cmd_trace
from kama_claude.cli.commands.version import cmd_version
from kama_claude.core.config import get_config
from kama_claude.core.logging_setup import setup_logging


# CLI 主入口：解析命令行参数并分发到对应子命令
def main() -> None:
    parser = argparse.ArgumentParser(prog="kama", description="KamaClaude CLI")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("ping", help="Ping the core daemon")
    chat_parser = subparsers.add_parser("chat", help="Start a multi-turn chat session")
    chat_parser.add_argument("--session", help="Resume an existing chat session ID")

    run_parser = subparsers.add_parser("run", help="Run an agent task")
    run_parser.add_argument("--goal", required=True, help="Goal for the agent to accomplish")

    core_parser = subparsers.add_parser("core", help="Manage the core daemon")
    core_sub = core_parser.add_subparsers(dest="core_command")
    core_sub.add_parser("start", help="Start the daemon in the background")
    core_sub.add_parser("stop", help="Stop the running daemon")
    core_sub.add_parser("status", help="Show daemon status")

    session_parser = subparsers.add_parser("session", help="Manage chat sessions")
    session_sub = session_parser.add_subparsers(dest="session_command")
    session_sub.add_parser("list", help="List saved sessions")
    history_parser = session_sub.add_parser("history", help="Show session history")
    history_parser.add_argument("session_id", help="Session ID to inspect")
    history_parser.add_argument("--raw", action="store_true", help="Output raw JSON")
    alias_parser = session_sub.add_parser("alias", help="Set a short alias for a session")
    alias_parser.add_argument("session_id", help="Session ID or existing alias")
    alias_parser.add_argument("alias", help="New alias, for example work")
    cancel_parser = session_sub.add_parser("cancel", help="Cancel the currently running turn")
    cancel_parser.add_argument("session_id", help="Session ID or alias")

    trace_parser = subparsers.add_parser("trace", help="View system trace log")
    trace_parser.add_argument("run_id", nargs="?", default=None, help="Filter by run ID")
    trace_parser.add_argument("--layer", choices=["ipc", "event", "llm"], help="Filter by layer")
    trace_parser.add_argument("--direction", help="Filter by direction (e.g. CORE→LLM)")
    trace_parser.add_argument("--raw", action="store_true", help="Output raw NDJSON")
    trace_parser.add_argument("--follow", "-f", action="store_true", help="Follow new records")

    args = parser.parse_args()

    if args.version:
        cmd_version()
        return

    config = get_config()
    setup_logging(config)

    if args.command == "ping":
        cmd_ping(config)
    elif args.command == "chat":
        cmd_chat(config, session_id=args.session)
    elif args.command == "run":
        cmd_run(args.goal, config)
    elif args.command == "core":
        if args.core_command == "start":
            cmd_core_start(config)
        elif args.core_command == "stop":
            cmd_core_stop(config)
        elif args.core_command == "status":
            cmd_core_status(config)
        else:
            core_parser.print_help()
            sys.exit(1)
    elif args.command == "session":
        if args.session_command == "list":
            cmd_session_list(config)
        elif args.session_command == "history":
            cmd_session_history(args.session_id, config, raw=args.raw)
        elif args.session_command == "alias":
            cmd_session_alias(args.session_id, args.alias, config)
        elif args.session_command == "cancel":
            cmd_session_cancel(args.session_id, config)
        else:
            session_parser.print_help()
            sys.exit(1)
    elif args.command == "trace":
        cmd_trace(
            args.run_id,
            config,
            layer=args.layer,
            direction=args.direction,
            raw=args.raw,
            follow=args.follow,
        )
    else:
        parser.print_help()
        sys.exit(1)
