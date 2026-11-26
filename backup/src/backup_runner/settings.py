"""Paths, logging and environment-backed settings."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from .errors import ConfigError

SERVICE_FILE: Final = Path("/etc/backup/services.json")
STATE_DIR: Final = Path(os.environ.get("BACKUP_STATE_DIR", "/var/lib/backup/state"))
LOG_DIR: Final = Path(os.environ.get("BACKUP_LOG_DIR", "/var/lib/backup/logs"))
LOCK_FILE: Final = Path(os.environ.get("BACKUP_LOCK_FILE", str(STATE_DIR / "backup.lock")))
STOPPED_FILE: Final = Path(
    os.environ.get("BACKUP_STOPPED_FILE", str(STATE_DIR / "stopped-containers.json"))
)
RESTORE_DIR: Final = Path(os.environ.get("BACKUP_RESTORE_DIR", "/restore"))
CRONTAB_FILE: Final = Path(os.environ.get("BACKUP_CRONTAB_FILE", "/etc/backup-crontab"))
DOCKER_SOCKET: Final = Path("/var/run/docker.sock")
MOUNT_PATHS: Final = (
    Path("/cookbook"),
    Path("/config/rclone"),
    RESTORE_DIR,
)

COMMON_ENV_KEEP_LIMITS: Final = (
    ("BACKUP_KEEP_DAILY", 7),
    ("BACKUP_KEEP_WEEKLY", 4),
    ("BACKUP_KEEP_MONTHLY", 12),
)
REQUIRED_IMAGE_COMMANDS: Final = (
    "restic",
    "rclone",
    "apprise",
    "docker",
)
HEALTHCHECK_COMMANDS: Final = (*REQUIRED_IMAGE_COMMANDS, "supercronic")

LOG = logging.getLogger("backup")


def setup_logging() -> None:
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )


def ensure_dirs() -> None:
    for path in (STATE_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    return value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    if "CHANGE_ME" in value:
        raise ConfigError(f"Environment variable {name} still contains a CHANGE_ME placeholder")
    return value


def backup_host() -> str:
    return os.environ.get("BACKUP_HOST", "home-lab").strip() or "home-lab"


def validate_common_env() -> None:
    require_env("RESTIC_REPOSITORY")
    require_env("RESTIC_PASSWORD")
    for name, default in COMMON_ENV_KEEP_LIMITS:
        if env_int(name, default) < 0:
            raise ConfigError(f"{name} must not be negative")
    percent = env_int("BACKUP_CHECK_READ_DATA_PERCENT", 1)
    if not 1 <= percent <= 100:
        raise ConfigError("BACKUP_CHECK_READ_DATA_PERCENT must be between 1 and 100")


def validate_notification_env() -> None:
    if env_bool("BACKUP_NOTIFY_ENABLED"):
        require_env("APPRISE_DISCORD_URL")


def ensure_commands() -> None:
    missing = [name for name in REQUIRED_IMAGE_COMMANDS if shutil.which(name) is None]
    if missing:
        raise ConfigError(f"Required commands not found in the backup image: {', '.join(missing)}")
