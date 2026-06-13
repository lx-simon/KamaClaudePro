# KamaClaude Quick Guide

## Version

Check the current version:

```bash
uv run kama --version
```

Current release: `0.0.3`.

Project changes are tracked in `CHANGELOG.md`.

## Install

Recommended cross-platform sync:

```bash
python scripts/uv_sync.py
```

Linux/macOS/WSL shortcut:

```bash
sh scripts/uv_sync.sh
```

Termux:

```bash
sh scripts/setup_termux.sh
```

The project supports Python `>=3.11,<3.14`, so Python 3.11, 3.12, and 3.13 are valid.

## Configure Model API

Copy the template:

```bash
cp .env.example .env
```

Edit `.env` and uncomment exactly one provider block.

OpenAI-compatible example:

```env
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
```

Anthropic example:

```env
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

## Start

Terminal 1:

```bash
uv run kama-core
```

Terminal 2:

```bash
uv run kama ping
```

One-shot task:

```bash
uv run kama run --goal "summarize README.md"
```

Chat:

```bash
uv run kama chat
```

TUI:

```bash
uv run kama-tui
```

Web UI:

```bash
uv run kama-web
# open http://127.0.0.1:7440
```

The Web UI uses the same `kama-core` daemon as CLI and TUI. It adds no extra runtime dependency and talks to core through the existing JSON-RPC socket plus Server-Sent Events.

## Sessions

List sessions:

```bash
uv run kama session list
```

Set an alias:

```bash
uv run kama session alias sess-abc123 work
```

Resume by alias in CLI:

```bash
uv run kama chat --session work
```

Resume by alias in TUI:

```bash
uv run kama-tui --session work
```

View history:

```bash
uv run kama session history work
```

Cancel the currently running turn:

```bash
uv run kama session cancel work
```

In TUI, press `Ctrl+C` while the agent is running to cancel. Press `Ctrl+Q` to quit and preserve the session.

## TUI Shortcuts

```text
Enter                         send message
Shift+Enter / Alt+Enter       insert newline
Ctrl+J                        insert newline
Ctrl+C                        cancel running turn, or quit if idle
Ctrl+Q                        quit and preserve session
/                             open skill completion
/compact                      compact current session context
```

Permission prompt shortcuts:

```text
y / 1     allow once
a / 2     always allow
n / 3     deny once
d / 4     always deny
Up/Down   choose option
Enter     confirm
```

## Command To Code Map

```text
uv run kama-core
  -> pyproject.toml [project.scripts].kama-core
  -> kama_claude.core.app:run
  -> src/kama_claude/core/app.py

uv run kama ping
  -> kama_claude.cli.main:main
  -> cli/commands/ping.py
  -> transport/socket_client.py
  -> core/app.py _ping_handler

uv run kama run --goal "..."
  -> cli/commands/run.py
  -> core/app.py _agent_run_handler
  -> session/manager.py send_message
  -> runner.py AgentRunner.run_and_capture
  -> loop.py AgentLoop.run

uv run kama chat
  -> cli/commands/chat.py
  -> session.create / session.send_message RPC
  -> same AgentRunner and AgentLoop path

uv run kama-tui
  -> kama_claude.tui.__main__:main
  -> tui/app.py KamaTuiApp
  -> socket_client.py
  -> session.* RPC and event.subscribe

uv run kama-web
  -> kama_claude.web.__main__:main
  -> stdlib ThreadingHTTPServer
  -> web/static/index.html, app.css, app.js
  -> SocketClient session.* RPC and event.subscribe

uv run kama session list
  -> cli/commands/session.py cmd_session_list
  -> core/app.py _session_list_handler
  -> session/manager.py list_sessions

uv run kama session alias <session> <alias>
  -> cli/commands/session.py cmd_session_alias
  -> core/app.py _session_alias_handler
  -> session/manager.py set_alias

uv run kama session cancel <session>
  -> cli/commands/session.py cmd_session_cancel
  -> core/app.py _session_cancel_handler
  -> session/manager.py cancel
```

## MCP Template

Minimal MCP example:

```text
examples/mcp_minimal/server.py
examples/mcp_minimal/README.md
```

Configure in `.kama/config.toml`:

```toml
[mcp]
servers = [
  { name = "demo", transport = "stdio", command = "python", args = ["examples/mcp_minimal/server.py"] }
]
```

Tools are registered as:

```text
demo__hello
demo__add
demo__now
```

## SkillOpt

SkillOpt is best used as an offline skill optimizer, not as a required KamaClaude runtime dependency. Let SkillOpt generate a reviewed `best_skill.md`, then place it in `.kama/skills/<name>.md` or `~/.kama/skills/<name>.md` and invoke it with `/name` in CLI, TUI, or Web UI.

Details: `docs/skillopt-analysis.md`.

## Troubleshooting

If TUI crashes and mouse movement prints strange characters, reset terminal mode:

```bash
reset
```

or:

```bash
stty sane
```

If `uv sync` chooses an unexpected Python, use:

```bash
python scripts/uv_sync.py
```

This selects a compatible Python and pins `.python-version` to a portable version string.

If you see this log:

```text
anthropic stream parser failed ... using non-streaming fallback
```

it means the Anthropic SDK stream accumulator hit a known edge case and KamaClaude retried the same request with non-streaming `messages.create`. The run should continue normally, but that single response will not stream token-by-token.
