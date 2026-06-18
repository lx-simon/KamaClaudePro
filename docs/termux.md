# KamaClaude Termux 运行手册

本文说明如何在 Android Termux 中安装和运行 KamaClaude，并尽量避免 `uv sync` 触发错误的 Python 下载、硬链接失败或不必要的 dev 依赖构建。

## 推荐安装

进入项目目录后运行：

```sh
sh scripts/setup_termux.sh
```

脚本会安装：

```text
python rust clang make pkg-config openssl libffi git uv
```

并强制使用 Termux 自带 Python：

```sh
uv python pin "$(command -v python)"
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

关键点：

- `--python "$(command -v python)"`：避免 uv 下载普通 Linux Python。
- `UV_PYTHON_DOWNLOADS=never`：禁止 uv 自动下载 Python，减少 Android 不兼容问题。
- `UV_LINK_MODE=copy`：避免 Termux/Android 文件系统 hardlink 警告或失败。
- `--no-dev`：手机默认只安装运行依赖，不安装 pytest、ruff、mypy 等开发依赖。

如果你确实要在 Termux 上跑测试，可以手动执行：

```sh
uv sync --dev --python "$(command -v python)"
```

## 手动安装

```sh
pkg update -y
pkg upgrade -y
pkg install -y python rust clang make pkg-config openssl libffi git
python -m pip install -U pip setuptools wheel uv
uv python pin "$(command -v python)"
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

不要优先使用：

```sh
uv sync --python 3.13
```

这可能让 uv 下载自己的 CPython。Termux 更稳的做法是使用 `pkg install python` 提供的系统 Python。

## 配置 API

复制环境变量模板：

```sh
cp .env.example .env
```

OpenAI 或兼容网关示例：

```env
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
```

Anthropic 示例：

```env
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_BASE_URL=https://your-anthropic-compatible-endpoint
```

## 启动

第一个 Termux 会话启动 core：

```sh
uv run kama-core
```

第二个 Termux 会话测试连接：

```sh
uv run kama ping
```

常用入口：

```sh
uv run kama chat
uv run kama run --goal "说明这个项目如何运行"
uv run kama-tui
uv run kama-web
```

Web UI 默认地址：

```text
http://127.0.0.1:7440
```

如果在手机浏览器打开，确保浏览器和 Termux 在同一台设备上。Web UI 不增加额外 Python 运行时依赖，它复用 `kama-core`，通过本地 JSON-RPC 和 SSE 接收事件。

## 常见问题

### uv 选择了错误的 Python

执行：

```sh
uv python pin "$(command -v python)"
UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

如果虚拟环境已经创建错了，可以删除后重来：

```sh
rm -rf .venv
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

### Rust 或 maturin 构建失败

安装 Termux 的 Rust 和编译工具：

```sh
pkg install -y rust clang make pkg-config
rustc --version
cargo --version
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

### OpenSSL 或 libffi 构建失败

安装系统库：

```sh
pkg install -y openssl libffi pkg-config
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
```

### hardlink warning

如果看到：

```text
Failed to hardlink files; falling back to full copy
```

通常可以忽略。想减少这类提示，设置：

```sh
export UV_LINK_MODE=copy
```

### TUI 显示不舒服

手机终端屏幕较小，TUI 可能不如桌面舒服。可以优先使用：

```sh
uv run kama chat
```

或启动 Web UI：

```sh
uv run kama-web
```

## 最小命令清单

```sh
pkg update -y
pkg install -y python rust clang make pkg-config openssl libffi git
python -m pip install -U pip setuptools wheel uv
cd ~/KamaClaudePro
ANDROID_API_LEVEL="$(python -c 'import re, sysconfig; m=re.match(r"android-(\\d+)-", sysconfig.get_platform()); print(m.group(1) if m else "24")')" UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never uv sync --no-dev --python "$(command -v python)"
cp .env.example .env
uv run kama-core
```

另开一个 Termux 会话：

```sh
cd ~/KamaClaudePro
uv run kama ping
uv run kama chat
```
