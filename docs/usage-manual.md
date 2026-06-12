# KamaClaude 使用手册

本文说明 KamaClaude 在 Linux 和 Windows 下的安装、配置、启动、调用和日常使用方式。项目支持 Python 3.12 和 Python 3.13，可以使用 uv，也可以直接使用系统 Python 启动。

Android Termux 用户请先阅读 [Termux 运行手册](termux.md)。Termux 需要先安装 Rust/clang 等编译工具，否则 `pydantic-core` 可能无法构建。

项目能力、session 恢复、Skill、MCP 和工具扩展请阅读 [项目介绍与扩展手册](project-guide.md)。

## 1. 运行环境

基础要求：

- Python 3.12 或 Python 3.13
- Anthropic API Key 或 OpenAI API Key
- 推荐使用 uv 0.4 或更新版本管理依赖
- 也支持直接使用系统 Python，但需要先安装依赖

检查版本：

```bash
python --version
```

Windows PowerShell 中也可以使用：

```powershell
py --version
```

如果使用 uv：

```bash
uv --version
```

## 2. 安装依赖

### 2.1 使用 uv 安装

在项目根目录执行：

```bash
uv sync
```

指定 Python 3.13：

```bash
uv sync --python 3.13
```

指定 Python 3.12：

```bash
uv sync --python 3.12
```

验证 CLI：

```bash
uv run kama --version
```

### 2.2 使用系统 Python 安装

如果不使用 uv，可以直接把项目安装到当前系统 Python 环境。

建议先创建虚拟环境。

Linux/macOS：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

如果你确定要直接安装到系统 Python，不创建虚拟环境，也可以执行：

```bash
python -m pip install -e .
```

Windows PowerShell：

```powershell
py -3.13 -m pip install -e .
```

验证安装：

```bash
python -m kama_claude.cli --version
```

如果安装了 console scripts，也可以直接运行：

```bash
kama --version
```

## 3. 配置方式

配置优先级从低到高为：

1. 程序内置默认值
2. `~/.kama/config.toml`
3. 项目根目录 `.kama/config.toml`
4. 项目根目录 `.env`
5. 系统环境变量

通常建议本地开发使用 `.env`。

### 3.1 创建 `.env`

Linux/macOS：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

### 3.2 使用 Anthropic

Anthropic 是默认 provider：

```bash
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

### 3.3 使用 OpenAI

切换到 OpenAI：

```bash
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

也可以使用其他 OpenAI 模型名，例如：

```bash
KAMA_LLM_DEFAULT_MODEL=gpt-4o
```

### 3.4 使用 TOML 配置

可以在 `~/.kama/config.toml` 或 `.kama/config.toml` 中写：

```toml
[core]
host = "127.0.0.1"
port = 7437

[llm]
provider = "openai"
default_model = "gpt-4o-mini"

[agent]
max_steps = 20

[logging]
level = "INFO"
file = "~/.kama/logs/core.log"
format = "text"
```

API Key 建议放在 `.env` 或系统环境变量中，不建议写入 TOML。

## 4. 启动方式

KamaClaude 是 daemon + client 架构：

- `kama-core`: 核心 daemon，负责 agent loop、模型调用、工具调用、权限审批和事件流。
- `kama`: 命令行客户端，用来 ping、run、chat、管理 core、查看 trace。
- `kama-tui`: 终端 UI 客户端，用来查看和操作运行过程。

## 5. 使用 uv 启动

### 5.1 前台启动 core

适合调试：

```bash
uv run kama-core
```

默认监听：

```text
127.0.0.1:7437
```

停止方式：按 `Ctrl+C`。

### 5.2 后台启动 core

```bash
uv run kama core start
```

查看状态：

```bash
uv run kama core status
```

停止：

```bash
uv run kama core stop
```

### 5.3 检查连接

```bash
uv run kama ping
```

成功时会看到类似输出：

```text
pong server=0.0.1 uptime=1234ms latency=2ms
```

### 5.4 单次任务

```bash
uv run kama run --goal "阅读 README.md，总结这个项目的核心功能"
```

### 5.5 多轮聊天

```bash
uv run kama chat
```

进入后在提示符中输入问题：

```text
> 帮我分析这个项目的目录结构
```

退出方式：按 `Ctrl+C`，或发送 EOF。

### 5.6 启动 TUI

先启动 core：

```bash
uv run kama core start
```

再启动 TUI：

```bash
uv run kama-tui
```

回放某次 run：

```bash
uv run kama-tui --replay RUN_ID
```

## 6. 使用系统 Python 启动

如果已经通过 `python -m pip install -e .` 安装依赖，可以不用 uv，直接通过 Python 模块入口启动。

### 6.1 前台启动 core

Linux/macOS：

```bash
python -m kama_claude.core
```

Windows PowerShell：

```powershell
python -m kama_claude.core
```

如果 Windows 上 `python` 不指向 3.13，可以使用：

```powershell
py -3.13 -m kama_claude.core
```

停止方式：按 `Ctrl+C`。

### 6.2 使用 Python 调用 CLI

查看版本：

```bash
python -m kama_claude.cli --version
```

检查 core：

```bash
python -m kama_claude.cli ping
```

单次任务：

```bash
python -m kama_claude.cli run --goal "说明这个项目如何启动"
```

多轮聊天：

```bash
python -m kama_claude.cli chat
```

查看 trace：

```bash
python -m kama_claude.cli trace
```

Windows 指定 Python 3.13：

```powershell
py -3.13 -m kama_claude.cli ping
py -3.13 -m kama_claude.cli run --goal "说明这个项目如何启动"
py -3.13 -m kama_claude.cli chat
```

### 6.3 使用 Python 启动 TUI

Linux/macOS：

```bash
python -m kama_claude.tui
```

Windows PowerShell：

```powershell
python -m kama_claude.tui
```

指定 Python 3.13：

```powershell
py -3.13 -m kama_claude.tui
```

回放某次 run：

```bash
python -m kama_claude.tui --replay RUN_ID
```

### 6.4 使用安装后的脚本命令

如果 `pip install -e .` 后脚本目录已经加入 PATH，也可以直接使用：

```bash
kama-core
kama ping
kama run --goal "总结 README.md"
kama chat
kama-tui
```

如果提示 `kama` 或 `kama-core` 不存在，说明 Python 的 Scripts/bin 目录没有加入 PATH。此时直接使用 `python -m kama_claude.cli ...` 和 `python -m kama_claude.core` 最稳。

## 7. 修改监听地址和端口

`.env` 中配置：

```bash
KAMA_HOST=127.0.0.1
KAMA_PORT=7437
```

Linux/macOS 临时指定端口：

```bash
KAMA_PORT=8000 python -m kama_claude.core
```

Windows PowerShell：

```powershell
$env:KAMA_PORT = "8000"
python -m kama_claude.core
```

uv 方式同理：

```bash
KAMA_PORT=8000 uv run kama-core
```

## 8. 权限审批

Agent 可能调用以下工具：

- `read_file`: 读取文件
- `list_dir`: 查看目录
- `write_file`: 写文件
- `bash`: 执行 shell 命令
- `note_save`: 保存会话记忆
- `task_create` / `task_update` / `task_list` / `task_get`: 任务管理

当需要审批时，chat/TUI 会显示权限请求。

CLI chat 中的审批选项：

```text
y = allow once
a = always allow
n = deny once
d = always deny
```

含义：

- `y`: 本次允许
- `a`: 当前会话中总是允许该类操作
- `n`: 本次拒绝
- `d`: 当前会话中总是拒绝该类操作

## 9. Trace 和日志

默认 trace 文件：

```text
~/.kama/traces/daemon.jsonl
```

uv 方式查看 trace：

```bash
uv run kama trace
uv run kama trace RUN_ID
uv run kama trace --layer llm
uv run kama trace --raw
uv run kama trace --follow
```

系统 Python 方式查看 trace：

```bash
python -m kama_claude.cli trace
python -m kama_claude.cli trace RUN_ID
python -m kama_claude.cli trace --layer llm
python -m kama_claude.cli trace --raw
python -m kama_claude.cli trace --follow
```

默认 core 日志：

```text
~/.kama/logs/core.log
```

Linux/macOS：

```bash
tail -f ~/.kama/logs/core.log
```

Windows PowerShell：

```powershell
Get-Content $HOME\.kama\logs\core.log -Wait
```

TUI 日志：

```text
~/.kama/logs/tui.log
```

## 10. 常见流程

### 10.1 uv + Anthropic

```bash
uv sync
cp .env.example .env
```

`.env`：

```bash
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

启动并调用：

```bash
uv run kama core start
uv run kama ping
uv run kama run --goal "总结 README.md"
```

### 10.2 uv + OpenAI

```bash
uv sync
cp .env.example .env
```

`.env`：

```bash
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

启动并调用：

```bash
uv run kama core start
uv run kama ping
uv run kama chat
```

### 10.3 系统 Python + OpenAI

Linux/macOS：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
cp .env.example .env
```

`.env`：

```bash
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

启动并调用：

```bash
python -m kama_claude.core
```

另开一个终端：

```bash
python -m kama_claude.cli ping
python -m kama_claude.cli run --goal "说明这个项目如何运行"
```

Windows PowerShell：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
Copy-Item .env.example .env
python -m kama_claude.core
```

另开一个 PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m kama_claude.cli ping
python -m kama_claude.cli run --goal "说明这个项目如何运行"
```

## 11. 常见问题

### 11.1 可以不用 uv 吗？

可以。先执行：

```bash
python -m pip install -e .
```

然后使用：

```bash
python -m kama_claude.core
python -m kama_claude.cli ping
python -m kama_claude.cli run --goal "你的任务"
python -m kama_claude.cli chat
python -m kama_claude.tui
```

### 11.2 `core not running`

说明 core daemon 没启动。先启动：

```bash
uv run kama-core
```

或：

```bash
python -m kama_claude.core
```

### 11.3 `ANTHROPIC_API_KEY not set`

当前 provider 是 Anthropic，但没有配置 key。检查 `.env`：

```bash
KAMA_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### 11.4 `OPENAI_API_KEY not set`

当前 provider 是 OpenAI，但没有配置 key。检查 `.env`：

```bash
KAMA_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 11.5 切换 provider 后还是旧配置

core 启动后不会自动重新读取 `.env`。修改 provider、model、key 后，需要重启 core。

uv 后台方式：

```bash
uv run kama core stop
uv run kama core start
```

前台方式：按 `Ctrl+C` 停掉，然后重新启动。

### 11.6 `kama` 命令不存在

如果你用系统 Python 安装后找不到 `kama`，可以直接用模块方式：

```bash
python -m kama_claude.cli ping
```

Windows：

```powershell
py -3.13 -m kama_claude.cli ping
```

## 12. 开发和验证

uv 方式：

```bash
uv run pytest tests/unit -v
uv run pytest tests -v
uv run ruff check src tests scripts
uv run mypy src
```

系统 Python 方式：

```bash
python -m pytest tests/unit -v
python -m pytest tests -v
python -m ruff check src tests scripts
python -m mypy src
```

Windows 如果没有 `make`，直接使用上面的 `python -m ...` 或 `uv run ...` 命令即可。
