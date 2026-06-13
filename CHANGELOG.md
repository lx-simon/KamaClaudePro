# Changelog

All notable project changes are recorded here.

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
