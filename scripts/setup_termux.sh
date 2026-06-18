#!/data/data/com.termux/files/usr/bin/sh
set -eu

printf '%s
' '==> Updating Termux packages'
pkg update -y
pkg upgrade -y

printf '%s
' '==> Installing build/runtime dependencies'
pkg install -y python rust clang make pkg-config openssl libffi git

printf '%s
' '==> Upgrading Python packaging tools'
python -m pip install -U pip setuptools wheel

if ! command -v uv >/dev/null 2>&1; then
  printf '%s
' '==> Installing uv with pip'
  python -m pip install -U uv
fi

TERMUX_PYTHON="$(command -v python)"
export UV_LINK_MODE=copy
export UV_PYTHON_DOWNLOADS=never
if [ -z "${ANDROID_API_LEVEL:-}" ]; then
  ANDROID_API_LEVEL="$($TERMUX_PYTHON - <<'PY'
import re
import sysconfig
platform = sysconfig.get_platform()
match = re.match(r"android-(\d+)-", platform)
print(match.group(1) if match else "24")
PY
)"
  export ANDROID_API_LEVEL
fi

printf '%s
' '==> Syncing project with Termux system Python'
printf '%s
' "    python: $TERMUX_PYTHON"
printf '%s
' "    ANDROID_API_LEVEL: $ANDROID_API_LEVEL"
uv python pin "$TERMUX_PYTHON"
uv sync --no-dev --python "$TERMUX_PYTHON"

printf '%s
' '==> Done'
printf '%s
' 'Start core with:'
printf '%s
' '  uv run kama-core'
printf '%s
' 'Then open another Termux session and run:'
printf '%s
' '  uv run kama ping'
