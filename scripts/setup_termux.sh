#!/data/data/com.termux/files/usr/bin/sh
set -eu

printf '%s\n' '==> Updating Termux packages'
pkg update -y
pkg upgrade -y

printf '%s\n' '==> Installing build/runtime dependencies'
pkg install -y python rust clang make pkg-config openssl libffi git

printf '%s\n' '==> Upgrading Python packaging tools'
python -m pip install -U pip setuptools wheel

if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' '==> Installing uv with pip'
  python -m pip install -U uv
fi

printf '%s\n' '==> Syncing project with Termux system Python'
uv python pin "$(command -v python)"
uv sync --python "$(command -v python)"

printf '%s\n' '==> Done'
printf '%s\n' 'Start core with:'
printf '%s\n' '  uv run kama-core'
printf '%s\n' 'Then open another Termux session and run:'
printf '%s\n' '  uv run kama ping'
