# Windows and OpenAI notes

KamaClaude now supports Python 3.12 and 3.13. The default `.python-version` is 3.13, while `pyproject.toml` allows both versions with `requires-python = ">=3.12,<3.14"`.

## Install and run

Use uv 0.4 or newer:

```bash
uv sync
uv run kama-core
```

The same commands work on Linux and Windows. On Windows, `kama-core` falls back to standard signal handlers when `asyncio.add_signal_handler` is unavailable.

## Anthropic configuration

Anthropic remains the default provider:

```bash
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

## OpenAI configuration

Set the provider to `openai` and supply an OpenAI API key:

```bash
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

The equivalent TOML configuration is:

```toml
[llm]
provider = "openai"
default_model = "gpt-4o-mini"
```
