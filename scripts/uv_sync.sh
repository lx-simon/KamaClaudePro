#!/usr/bin/env sh
set -eu

python_cmd=""
for candidate in python python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    python_cmd="$candidate"
    break
  fi
done

if [ -z "$python_cmd" ]; then
  printf '%s\n' 'python not found. Install Python 3.11, 3.12, or 3.13 first.' >&2
  exit 1
fi

exec "$python_cmd" scripts/uv_sync.py "$@"
