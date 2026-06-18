# Changelog

All notable project changes are recorded here.

## Unreleased - 2026-06-15

### Added

- Added `uv run kama session close <session_id-or-alias>` to close idle sessions from the CLI.
- Added TUI queued input while the agent is running. Press Enter during a running turn to queue the message for the next turn without interrupting the current run.
- Added TUI `/now <guidance>` command. While a turn is running, it cancels the current run, places the guidance at the front of the queue, and sends it as soon as cancellation cleanup completes.
- Added Web UI session close support through `/api/session/close` and a `Close` button.
- Added Web UI session status display and closed/running session styling.
- Added Termux-safe sync defaults in `scripts/setup_termux.sh`: `UV_LINK_MODE=copy`, `UV_PYTHON_DOWNLOADS=never`, `ANDROID_API_LEVEL` inferred from Python platform tags, and `uv sync --no-dev --python "$(command -v python)"`.
- Added Termux detection to `scripts/uv_sync.py` so Android uses the system Python and avoids default dev dependency sync unless explicitly requested.

### Changed

- Changed TUI startup banner to ASCII text to avoid mojibake on Windows terminals and narrow/mobile terminals.
- Changed chat session resume behavior so a closed chat session can be reopened as `waiting_for_input`; one-shot sessions remain closed.
- Changed Web UI core calls and SSE subscription to start the socket read loop before waiting for JSON-RPC responses.
- Rewrote `docs/termux.md` as readable UTF-8 Chinese with Android/Termux troubleshooting and examples.

### Fixed

- Fixed `uv run kama session list` hanging by starting the socket client read loop for one-shot CLI session commands.
- Fixed `session.list` internal error by importing `SessionListCommand` in the core app.
- Fixed TUI alias resume display by replacing aliases with the real session ID and syncing returned session status.
- Fixed TUI closed state display so closed sessions show `closed` instead of `disconnected`.
- Fixed Web UI API calls and event stream hanging because socket responses were never read.
- Fixed TUI prompt being disabled during model thinking; input now remains editable and can queue follow-up messages.
- Reverted risky manual printable-character insertion in TUI input to avoid Chinese IME replacement/duplication behavior.
- Fixed mojibake in Chinese comments and documentation by rewriting affected files as UTF-8.
- Fixed Termux `jiter`/`maturin` build failure by exporting `ANDROID_API_LEVEL` from Python `sysconfig.get_platform()`, so the wheel tag matches Termux Python supported tags.

### Usage Examples

```powershell
uv run kama session list
uv run kama session list <session_id-or-alias>
uv run kama session alias <chat-session-id> work
uv run kama session close work
uv run kama-tui --session work
```

TUI queued guidance examples:

```text
?? follow-up ??????????????? run
/now ?????????????????? run?????????????
```

Termux setup example:

```sh
sh scripts/setup_termux.sh
# or manually:
UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

Web UI example:

```powershell
uv run kama core start
uv run kama-web
# open http://127.0.0.1:7440
```

### Verified

- `python -m compileall src scripts tests`
- `uv run pytest tests/unit/test_session_manager.py tests/unit/test_socket_client.py tests/unit/test_tui_app.py -q` -> `33 passed`
- Termux: `ANDROID_API_LEVEL=24` allowed `jiter==0.15.0` to build; using device SDK `29` produced an incompatible `android_29` wheel for this Termux Python.

## 0.0.3 - 2026-06-14

### Added

- Added Web UI entry point: `uv run kama-web`.
- Added stdlib-based Web UI server under `src/kama_claude/web/__main__.py`. It serves static files and talks to `kama-core` through the existing JSON-RPC socket client.
- Added Web UI static assets under `src/kama_claude/web/static/`: `index.html`, `app.css`, and `app.js`.
- Added Web UI support for session list, create/resume, message send, streaming tokens, run/tool/session event display, permission responses, alias setting, compaction, and cancellation.
- Added package metadata for Web UI static assets so packaged builds can include the browser files.
- Added SkillOpt analysis documentation under `docs/skillopt-analysis.md`.

### Changed

- Bumped project version from `0.0.2` to `0.0.3`.
- Updated README quick start with `uv run kama-web`.
- Updated `docs/quick-guide.md` with Web UI commands, code-path mapping, SkillOpt notes, and current release version.
- Rewrote `docs/termux.md` into readable Chinese and clarified that Termux should sync with `uv sync --python "$(command -v python)"` or `sh scripts/setup_termux.sh`.

### Fixed

- Fixed Web UI event stream behavior when `kama-core` is unavailable by emitting a `core.unavailable` SSE event instead of failing silently.
- Fixed a Web UI session metadata separator that could render poorly in some terminals/editors.


### Fixed

- Fixed mojibake in Chinese comments and documentation by rewriting affected files as UTF-8.
- Fixed `docs/termux.md` and TUI/CLI source comments so Chinese text remains readable across Windows, Termux, and editors.
- Fixed Termux `jiter`/`maturin` build failure by exporting `ANDROID_API_LEVEL` from Python `sysconfig.get_platform()`, so the wheel tag matches Termux Python supported tags.

### Usage Examples

```bash
python scripts/uv_sync.py      # Windows / Linux / WSL portable sync
sh scripts/uv_sync.sh          # shell shortcut
sh scripts/setup_termux.sh     # Android Termux setup

uv run kama-core               # start core daemon
uv run kama-web                # start Web UI on http://127.0.0.1:7440
uv run kama chat --session work
uv run kama session alias <session_id> work
uv run kama session cancel work
```

### Command To Python Code

```text
uv run kama-web
  -> pyproject.toml [project.scripts].kama-web
  -> kama_claude.web.__main__:main
  -> ThreadingHTTPServer serves web/static files
  -> SocketClient calls session.* RPC and subscribes to events
```

### SkillOpt Notes

- SkillOpt should be used as an offline optimizer that generates reviewed skill markdown such as `best_skill.md`.
- Put the generated skill into `.kama/skills/<name>.md`, `.kama/skills/<name>/SKILL.md`, or `~/.kama/skills/<name>.md`.
- Invoke the skill through `/name` in CLI, TUI, or Web UI.
- Do not make SkillOpt a required KamaClaude runtime dependency yet, because its optimizer/evaluation dependencies may be too heavy for Termux.

### Verified

- `python -m compileall -q src scripts tests`
- `uv lock --check`
- `uv run kama --version` -> `0.0.3`
- `uv run kama-web --help`
- `uv run pytest tests/unit/test_session_manager.py tests/unit/test_session_store.py tests/unit/test_llm_provider.py tests/unit/test_tui_app.py tests/unit/test_commands_events.py` -> `50 passed`

## 0.0.2 - 2026-06-13

### Added

- Added version control for release display. `uv run kama --version` now reports `0.0.2`.
- Added changelog tracking in `CHANGELOG.md`.
- Added running turn cancellation through `session.cancel`, CLI `uv run kama session cancel <session>`, and TUI `Ctrl+C` while the agent is running.
- Added session aliases. Use `uv run kama session alias <session_id-or-alias> <alias>` to name a session, then restore it with `uv run kama chat --session <alias>` or `uv run kama-tui --session <alias>`.
- Added Python environment sync helpers: `python scripts/uv_sync.py` and `sh scripts/uv_sync.sh`.
- Added minimal MCP template under `examples/mcp_minimal/`.
- Added core code map documentation under `docs/core-code-map.md`.
- Expanded `.env.example` with commented interface templates for Anthropic, OpenAI, compatible gateways, DeepSeek, OpenRouter, and local OpenAI-compatible services.

### Changed

- Lowered Python requirement to `>=3.11,<3.14` so the project can run on Python 3.11, 3.12, and 3.13.
- Updated Ruff and mypy targets to Python 3.11.
- Updated Termux setup to use Termux system Python explicitly.

### Fixed

- Replaced Python 3.12-only `type Alias = ...` syntax with Python 3.11-compatible type aliases.
- Fixed Anthropic streaming `IndexError` failure by falling back to non-streaming `messages.create` when the SDK stream accumulator crashes.

### Verified

- `python -m compileall -q src scripts tests/unit/test_llm_provider.py`
- `uv run pytest tests/unit/test_llm_provider.py tests/unit/test_session_store.py tests/unit/test_session_manager.py`

## 0.0.1 - Initial

- Initial local Agent runtime with core daemon, CLI/TUI clients, session persistence, tools, permissions, event stream, trace, compaction, skills, subagents, and MCP support.
