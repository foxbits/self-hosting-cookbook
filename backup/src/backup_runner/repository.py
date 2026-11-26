"""Restic repository and rclone remote preflight."""

from __future__ import annotations

import logging

from .errors import BackupError, CommandError, ConfigError
from .settings import require_env
from .util import run_checked

LOG = logging.getLogger("backup")


def repository_remote(repository: str) -> str:
    if not repository.startswith("rclone:"):
        raise ConfigError("RESTIC_REPOSITORY must use the rclone backend: rclone:<remote>:<path>")
    remote = repository[len("rclone:") :].split(":", 1)[0]
    if not remote:
        raise ConfigError(f"RESTIC_REPOSITORY does not name an rclone remote: {repository}")
    return remote


def preflight_repository() -> None:
    repository = require_env("RESTIC_REPOSITORY")
    remote = repository_remote(repository)
    LOG.info("Checking rclone remote %s:", remote)
    try:
        run_checked(["rclone", "lsd", f"{remote}:"], timeout=120, what="rclone")
    except CommandError as exc:
        raise BackupError(
            f"rclone remote {remote}: is not accessible; run make rclone-check or make rclone-reconnect"
        ) from exc
    LOG.info("Checking restic repository access")
    try:
        run_checked(["restic", "cat", "config"], timeout=120, what="restic")
    except CommandError as exc:
        raise BackupError(
            "restic repository is not initialized or is not accessible; run make init after rclone is configured"
        ) from exc
