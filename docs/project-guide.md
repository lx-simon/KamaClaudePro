# KamaClaude 项目介绍与扩展手册

本文面向使用者和二次开发者，说明 KamaClaude 是什么、支持哪些平台、如何配置模型 API、如何使用和恢复 session、如何添加 skill、如何接 MCP，以及如何扩展新的工具和能力。

## 1. 项目是什么

KamaClaude 是一个本地 AI Agent 运行时。它把一个类 Claude Code / Codex 的 Agent 工作流拆成几个清晰模块：

- Core daemon：常驻核心进程，负责会话、Agent Loop、模型调用、工具调用、权限审批、事件广播。
- CLI：命令行客户端，用来启动任务、聊天、查看 session、查看 trace。
- TUI：终端界面，用来实时观察模型输出、工具调用、权限审批和上下文状态。
- Tools：本地工具，例如读文件、列目录、写文件、执行 shell、保存笔记、任务管理。
- Skills：用 Markdown 定义的工作流提示词，可以通过 `/skill 参数` 调用。
- MCP：接入外部 MCP server，把外部工具统一注册进 Agent 工具系统。
- Session：持久化多轮会话，保存 thread、notes、runs 和事件。

## 2. 支持平台

当前目标平台：

- Linux
- Windows
- Android Termux

Python 版本：

- Python 3.12
- Python 3.13

推荐包管理器：

- uv 0.4 或更新版本

Windows 和 Linux 一般可以直接：

```bash
uv sync
uv run kama-core
```

Termux 需要先安装编译工具链，因为 Android 上 `pydantic-core`、`jiter` 等 Rust 扩展经常需要源码编译。参考：

```text
docs/termux.md
scripts/setup_termux.sh
```

Termux 推荐：

```sh
pkg install -y python rust clang make pkg-config openssl libffi git
python -m pip install -U pip setuptools wheel uv
uv sync --python "$(command -v python)"
```

## 3. 支持哪些模型 API

当前支持两类 provider：

- Anthropic
- OpenAI

### 3.1 Anthropic

`.env`：

```bash
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

如果使用 Anthropic 协议兼容网关，可以设置：

```bash
ANTHROPIC_BASE_URL=https://your-anthropic-compatible-endpoint
```

### 3.2 OpenAI

`.env`：

```bash
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

也可以换成其他 OpenAI Chat Completions 兼容模型名。

### 3.3 TOML 配置

也可以写入 `~/.kama/config.toml` 或项目 `.kama/config.toml`：

```toml
[llm]
provider = "openai"
default_model = "gpt-4o-mini"
```

API Key 不建议写到 TOML，建议放 `.env` 或系统环境变量。

## 4. 基础启动方式

启动 core：

```bash
uv run kama-core
```

另开终端：

```bash
uv run kama ping
```

单次任务：

```bash
uv run kama run --goal "说明这个项目如何运行"
```

多轮聊天：

```bash
uv run kama chat
```

TUI：

```bash
uv run kama-tui
```

不用 uv 时：

```bash
python -m pip install -e .
python -m kama_claude.core
python -m kama_claude.cli ping
python -m kama_claude.cli chat
python -m kama_claude.tui
```

## 5. Session 如何保存和恢复

### 5.1 session 保存在哪里

默认保存目录：

```text
~/.kama/sessions/<session_id>/
```

每个 session 目录里通常有：

```text
meta.json       # session 元信息：id、状态、标题、run 列表
thread.jsonl    # 多轮消息历史
notes.md        # note_save 保存的持久笔记
runs/           # 每次 run 的 events.jsonl 等运行产物
```

### 5.2 查看已有 session

先启动 core：

```bash
uv run kama-core
```

另开终端：

```bash
uv run kama session list
```

输出示例：

```text
sess-abc123def456  waiting_for_input chat     runs=3   updated=...  我的任务标题
```

### 5.3 查看某个 session 历史

```bash
uv run kama session history sess-abc123def456
```

查看原始 JSON：

```bash
uv run kama session history sess-abc123def456 --raw
```

### 5.4 恢复 CLI chat session

```bash
uv run kama chat --session sess-abc123def456
```

### 5.5 恢复 TUI session

```bash
uv run kama-tui --session sess-abc123def456
```

如果还想回放某次 run 的事件：

```bash
uv run kama-tui --session sess-abc123def456 --replay run-xxxx
```

### 5.6 为什么以前 TUI 关掉后找不回

旧实现里：

- TUI 每次启动都会 `session.create`。
- TUI 退出时还会 `session.close`。
- core 重启后只记内存里的 session，不会自动从磁盘恢复。

现在已补：

- `session.list`
- `session.resume`
- `kama session list`
- `kama session history`
- `kama chat --session ...`
- `kama-tui --session ...`
- TUI 退出时保留 session，不再自动关闭。

## 6. Skill 如何配置和使用

Skill 是 Markdown 文件，不需要额外注册。

搜索优先级：

1. 项目本地：`.kama/skills`
2. 用户全局：`~/.kama/skills`
3. 内置：`src/kama_claude/core/skills/builtin`

支持两种结构：

```text
.kama/skills/review.md
.kama/skills/review/SKILL.md
```

示例：`.kama/skills/explain.md`

```markdown
---
name: explain
description: 解释指定文件或模块的作用
allowed_tools:
  - read_file
  - list_dir
---

你是一位代码讲解助手。

请解释用户指定的目标：

$ARGUMENTS

要求：
1. 先说明整体作用
2. 再说明关键文件或函数
3. 最后给出使用建议
```

使用：

```text
/explain src/kama_claude/core/runner.py
```

CLI：

```bash
uv run kama run --goal "/explain src/kama_claude/core/runner.py"
```

TUI 中输入 `/` 会触发 skill 补全。

`allowed_tools` 是工具白名单。如果不写，默认不限制工具。即使允许 `bash` 或 `write_file`，仍然会走权限审批。

## 7. MCP 如何接入

MCP server 在配置文件的 `[mcp]` 中配置。当前支持：

- `stdio`
- `tcp`

### 7.1 stdio MCP 示例

`.kama/config.toml`：

```toml
[mcp]
servers = [
  { name = "demo", transport = "stdio", command = "python", args = ["mcp_server.py"] }
]
```

也可以配置环境变量：

```toml
[mcp]
servers = [
  { name = "demo", transport = "stdio", command = "node", args = ["server.js"], env = { API_KEY = "xxx" } }
]
```

### 7.2 tcp MCP 示例

```toml
[mcp]
servers = [
  { name = "remote", transport = "tcp", host = "127.0.0.1", port = 3000 }
]
```

core 启动时会连接这些 MCP server，调用 `tools/list` 发现工具，然后把工具注册进本地 ToolRegistry。

启动：

```bash
uv run kama-core
```

日志里会看到：

```text
mcp: server 'demo' connected, N tool(s) discovered
```

## 8. 如何扩展新的本地工具

本地工具继承 `BaseTool`：

```python
from pydantic import BaseModel, ConfigDict

from kama_claude.core.tools.base import BaseTool, ToolResult


class EchoParams(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str


class EchoTool(BaseTool):
    name = "echo"
    description = "Echo input text."
    params_model = EchoParams
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to echo."},
        },
        "required": ["text"],
    }

    async def invoke(self, params: dict[str, object]) -> ToolResult:
        p = EchoParams.model_validate(params)
        return ToolResult(content=p.text)
```

然后在 `AgentRunner._build_registry()` 中注册：

```python
from kama_claude.core.tools.builtin.echo import EchoTool

registry.register(EchoTool())
```

建议同时添加：

- 参数模型测试
- 工具 invoke 测试
- 权限策略测试，如果工具有风险
- 文档说明

如果工具涉及文件写入、shell、网络、外部服务，建议接入权限审批，或者至少在工具内部做路径和参数校验。

## 9. 如何扩展新的模型 Provider

当前 provider 在：

```text
src/kama_claude/core/llm/provider.py
```

协议接口在：

```text
src/kama_claude/core/llm/base.py
```

新增 provider 的基本步骤：

1. 实现一个类，提供 `async chat(...) -> LlmResponse`。
2. 把模型响应转换成统一的 `LlmResponse`。
3. 流式输出时发布 `LlmTokenEvent`。
4. 结束后发布 `LlmUsageEvent`。
5. 工具调用转换成 `ToolCallBlock`。
6. 在 `create_provider(provider, model)` 中增加分支。
7. 在 `LlmConfig` 和文档里说明 provider 名称。

`LlmResponse` 统一结构：

```python
LlmResponse(
    stop_reason="end_turn" | "tool_use" | "max_tokens",
    tool_calls=[...],
    text="...",
    usage=UsageStats(...),
)
```

## 10. 如何扩展新的 CLI 命令

CLI 入口：

```text
src/kama_claude/cli/main.py
```

命令实现放在：

```text
src/kama_claude/cli/commands/
```

新增命令步骤：

1. 新建 `src/kama_claude/cli/commands/foo.py`。
2. 实现 `cmd_foo(config)`。
3. 在 `main.py` 里添加 argparse 子命令。
4. 在分发逻辑里调用 `cmd_foo`。

如果需要和 core 通信，使用 `SocketClient` 调 JSON-RPC。

## 11. 如何扩展新的 IPC 协议

协议定义：

```text
src/kama_claude/core/bus/commands.py
src/kama_claude/core/bus/events.py
```

server 注册：

```text
src/kama_claude/core/app.py
```

新增命令步骤：

1. 在 `commands.py` 增加 Command / Result pydantic model。
2. 加入 `Command` 联合类型。
3. 在 `CoreApp` 中实现 handler。
4. `server.register("method.name", handler)`。
5. CLI/TUI 使用 `SocketClient.send_command()` 调用。
6. 添加集成测试。

## 12. 如何扩展事件显示

事件定义在：

```text
src/kama_claude/core/bus/events.py
```

TUI 渲染在：

```text
src/kama_claude/tui/app.py
```

CLI run/chat 渲染在：

```text
src/kama_claude/cli/commands/run.py
src/kama_claude/cli/commands/chat.py
```

新增事件后，通常要：

1. 在 `events.py` 定义事件模型。
2. 在合适业务点 `await bus.publish(...)`。
3. TUI `_handle_event_inner()` 增加分支渲染。
4. CLI printer 按需增加显示。
5. trace 会自动记录 event bus 事件。

## 13. 推荐扩展方向

可以按下面路线扩展：

- Session 管理：增加 TUI session 列表选择器、最近 session 自动恢复、session 重命名。
- Provider：增加 DeepSeek、OpenRouter、Ollama、本地模型等 provider。
- Tools：增加 grep/search、git diff、apply patch、HTTP 请求、数据库查询等工具。
- MCP：增加常用 MCP server 模板和健康检查。
- Skills：做项目专用 skill，例如 `/bugfix`、`/write-test`、`/api-doc`、`/termux-debug`。
- 权限：细化工具权限策略，例如按路径、命令、MCP server 分级审批。
- TUI：增加 session sidebar、run timeline、tool 输出搜索、MCP 工具面板。
- 记忆：把 `notes.md` 扩展为可搜索、可删除、可打标签的长期记忆。

## 14. 快速查找路径

常用源码路径：

```text
src/kama_claude/core/app.py              # core daemon 和 IPC handler
src/kama_claude/core/runner.py           # AgentRunner，组装 provider/tools/session
src/kama_claude/core/loop.py             # Agent loop
src/kama_claude/core/llm/provider.py      # Anthropic/OpenAI provider
src/kama_claude/core/tools/base.py        # 工具基类
src/kama_claude/core/tools/builtin/       # 内置工具
src/kama_claude/core/skills/loader.py     # skill 加载器
src/kama_claude/core/mcp/                 # MCP client/server manager/tool wrapper
src/kama_claude/core/session/             # session 持久化和管理
src/kama_claude/tui/app.py                # TUI
src/kama_claude/cli/main.py               # CLI 入口
```

文档路径：

```text
docs/usage-manual.md       # 使用手册
docs/termux.md             # Termux 运行手册
docs/project-guide.md      # 项目介绍和扩展手册
```
