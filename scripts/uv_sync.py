#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, NamedTuple

SUPPORTED = ((3, 13), (3, 12), (3, 11))
DEFAULT = "3.11"
ROOT = Path(__file__).resolve().parents[1]


class PythonChoice(NamedTuple):
    sync_request: str
    pin_request: str


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def uv_exe() -> str:
    exe = shutil.which("uv")
    if exe is None:
        raise SystemExit("uv not found. Install it first: python -m pip install -U uv")
    return exe


def uv_can_find(uv: str, version: str) -> bool:
    result = run([uv, "python", "find", version], check=False)
    return result.returncode == 0


def parse_version(text: str) -> tuple[int, int] | None:
    parts = text.strip().split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def version_str(version: tuple[int, int]) -> str:
    return f"{version[0]}.{version[1]}"


def compatible(version: tuple[int, int] | None) -> bool:
    return version is not None and (3, 11) <= version < (3, 14)


def python_version(executable: str) -> tuple[int, int] | None:
    result = subprocess.run(
        [executable, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return None
    return parse_version(result.stdout)


def current_python_candidates() -> Iterable[str]:
    yield sys.executable
    for name in ("python", "python3"):
        exe = shutil.which(name)
        if exe:
            yield exe


def is_termux() -> bool:
    return Path("/data/data/com.termux/files/usr/bin/python").exists()


def choose_python(uv: str) -> PythonChoice:
    if is_termux():
        python = shutil.which("python") or sys.executable
        version = python_version(python)
        if compatible(version):
            assert version is not None
            return PythonChoice(sync_request=python, pin_request=version_str(version))

    for executable in current_python_candidates():
        version = python_version(executable)
        if compatible(version):
            assert version is not None
            return PythonChoice(sync_request=executable, pin_request=version_str(version))

    for major, minor in SUPPORTED:
        request = f"{major}.{minor}"
        if uv_can_find(uv, request):
            return PythonChoice(sync_request=request, pin_request=request)

    supported = ", ".join(f"{major}.{minor}" for major, minor in SUPPORTED)
    print(f"No installed Python {supported} found; installing {DEFAULT} with uv.")
    subprocess.run([uv, "python", "install", DEFAULT], cwd=ROOT, check=True)
    return PythonChoice(sync_request=DEFAULT, pin_request=DEFAULT)


def main() -> None:
    uv = uv_exe()
    choice = choose_python(uv)
    print(f"Using Python {choice.sync_request} for uv sync")
    subprocess.run([uv, "python", "pin", choice.pin_request], cwd=ROOT, check=True)
    args = [uv, "sync", "--python", choice.sync_request, *sys.argv[1:]]
    if is_termux() and "--dev" not in sys.argv[1:] and "--all-groups" not in sys.argv[1:]:
        args.insert(2, "--no-dev")
    env = None
    if is_termux():
        import os
        env = os.environ.copy()
        env.setdefault("UV_LINK_MODE", "copy")
        env.setdefault("UV_PYTHON_DOWNLOADS", "never")
        if "ANDROID_API_LEVEL" not in env:
            level_result = subprocess.run(
                [
                    choice.sync_request,
                    "-c",
                    "import re, sysconfig; m=re.match(r'android-(\\d+)-', sysconfig.get_platform()); print(m.group(1) if m else '24')",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            env["ANDROID_API_LEVEL"] = level_result.stdout.strip() or "24"
    subprocess.run(args, cwd=ROOT, check=True, env=env)


if __name__ == "__main__":
    main()
