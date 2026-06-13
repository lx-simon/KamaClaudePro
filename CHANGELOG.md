# Changelog

All notable project changes are recorded here.

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
