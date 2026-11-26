"""Small reusable helpers: subprocess execution, env expansion and formatting."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Optional, Sequence

from .errors import CommandError, ConfigError

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def run_checked(
    args: Sequence[str],
    *,
    timeout: Optional[int] = None,
    env: Optional[dict[str, str]] = None,
    what: Optional[str] = None,
) -> subprocess.CompletedProcess[str]:
    label = what or args[0]
    try:
        result = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        raise CommandError(f"{label}: command not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandError(f"{label}: timed out") from exc
    if result.returncode != 0:
        detail_lines = (result.stderr or result.stdout or "").strip().splitlines()
        detail = " | ".join(detail_lines[-5:])
        message = f"{label} failed (exit {result.returncode})"
        if detail:
            message = f"{message}: {detail}"
        raise CommandError(message)
    return result


def expand_env(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        default = match.group(2)
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return default
        raise ConfigError(f"Environment variable {name} is not set (referenced in services.json)")

    return _ENV_PATTERN.sub(replace, value)


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"
