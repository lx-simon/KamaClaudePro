# KamaClaude Termux 运行手册

本文说明如何在 Android 的 Termux 中运行 KamaClaude。

## 1. 问题原因

如果你在 Termux 中执行：

```sh
uv run kama-core
```

看到类似错误：

```text
Failed to build `maturin`
Rust not found, installing into a temporary directory
Computed rustc target triple: aarch64-unknown-linux-android
Target triple not supported by rustup: aarch64-unknown-linux-android
```

原因是：

- KamaClaude 依赖 `pydantic`。
- `pydantic` 依赖 Rust 扩展包 `pydantic-core`。
- Android/Termux 平台经常没有可直接下载的 `pydantic-core` wheel。
- uv 会尝试源码编译 `pydantic-core`。
- 源码编译需要 Rust。
- 如果系统没有 Rust，构建工具会尝试用 rustup 临时安装。
- rustup 不支持 Termux 的 `aarch64-unknown-linux-android` 目标，所以失败。

解决方法是：不要让 maturin/rustup 临时安装 Rust，而是先用 Termux 的 `pkg` 安装 Termux 适配过的 Rust 工具链。

## 2. 推荐安装步骤

在 Termux 中进入项目目录：

```sh
cd ~/KamaClaude
```

执行项目提供的脚本：

```sh
sh scripts/setup_termux.sh
```

脚本会安装：

- python
- rust
- clang
- make
- pkg-config
- openssl
- libffi
- git
- uv

然后执行：

```sh
uv sync --python "$(command -v python)"
```

这会强制 uv 使用 Termux 自带 Python，而不是下载普通 Linux Python。

## 3. 手动安装步骤

如果不想用脚本，可以手动执行：

```sh
pkg update -y
pkg upgrade -y
pkg install -y python rust clang make pkg-config openssl libffi git
python -m pip install -U pip setuptools wheel uv
uv sync --python "$(command -v python)"
```

注意：在 Termux 中推荐使用：

```sh
uv sync --python "$(command -v python)"
```

不要优先使用：

```sh
uv sync --python 3.13
```

因为后者可能让 uv 下载自己的 Python，而 Termux 上更稳的是使用 Termux 包管理器安装的 Python。

## 4. 配置 API Key

复制配置模板：

```sh
cp .env.example .env
```

使用 Anthropic：

```sh
KAMA_LLM_PROVIDER=anthropic
KAMA_LLM_DEFAULT_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...
```

使用 OpenAI：

```sh
KAMA_LLM_PROVIDER=openai
KAMA_LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

如果使用兼容 Anthropic 协议的代理地址，也可以设置：

```sh
ANTHROPIC_BASE_URL=https://your-anthropic-compatible-endpoint
```

## 5. 启动 core

前台启动：

```sh
uv run kama-core
```

看到类似日志说明启动成功：

```text
kama-core 0.0.1 listening addr=127.0.0.1:7437
```

这个 Termux 会话不要关闭。

另开一个 Termux 会话，进入项目目录：

```sh
cd ~/KamaClaude
uv run kama ping
```

成功时会看到：

```text
pong server=0.0.1 uptime=... latency=...
```

## 6. 使用方式

单次任务：

```sh
uv run kama run --goal "说明这个项目如何运行"
```

多轮聊天：

```sh
uv run kama chat
```

TUI：

```sh
uv run kama-tui
```

Termux 屏幕较小时，TUI 可能显示不舒服。推荐先使用：

```sh
uv run kama chat
```

## 7. 常见问题

### 7.1 仍然提示 Rust not found

确认 Rust 已安装：

```sh
rustc --version
cargo --version
```

如果没有输出，执行：

```sh
pkg install -y rust clang make pkg-config
```

然后重新同步：

```sh
uv sync --python "$(command -v python)"
```

### 7.2 构建 openssl 相关包失败

安装 openssl 和 pkg-config：

```sh
pkg install -y openssl pkg-config
```

然后重新执行：

```sh
uv sync --python "$(command -v python)"
```

### 7.3 uv 下载的 Python 不适合 Termux

删除虚拟环境后，强制使用 Termux Python：

```sh
rm -rf .venv
uv sync --python "$(command -v python)"
```

### 7.4 构建太慢

Termux 上源码编译 Rust 扩展会比较慢，尤其是第一次构建 `pydantic-core` 和 `jiter`。只要不是报错，可以耐心等待。

### 7.5 hardlink warning

看到这个 warning 通常可以忽略：

```text
Failed to hardlink files; falling back to full copy
```

这是缓存目录和目标目录可能不在同一个文件系统导致的性能提示，不是安装失败原因。

## 8. 最小命令清单

全新 Termux 环境下，最少执行：

```sh
pkg update -y
pkg install -y python rust clang make pkg-config openssl libffi git
python -m pip install -U pip setuptools wheel uv
cd ~/KamaClaude
uv sync --python "$(command -v python)"
cp .env.example .env
uv run kama-core
```

另开一个 Termux 会话：

```sh
cd ~/KamaClaude
uv run kama ping
uv run kama chat
```
