"""Discord/Apprise notifications."""

from __future__ import annotations

import logging
import os
import subprocess

from .settings import env_bool

LOG = logging.getLogger("backup")
MAX_BODY_CHARS = 1800


def notify(kind: str, title: str, body: str) -> bool:
    if not env_bool("BACKUP_NOTIFY_ENABLED"):
        return True
    if kind == "success" and not env_bool("BACKUP_NOTIFY_ON_SUCCESS", True):
        return True
    url = os.environ.get("APPRISE_DISCORD_URL", "").strip()
    if not url or "CHANGE_ME" in url:
        LOG.warning("APPRISE_DISCORD_URL is not configured; skipping notification: %s", title)
        return False
    body = body[:MAX_BODY_CHARS]
    try:
        result = subprocess.run(
            ["apprise", "-t", title, "-b", body, "-n", kind, url],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        LOG.warning("Notification failed for %s: %s", title, exc)
        return False
    if result.returncode != 0:
        LOG.warning("Notification failed for %s (apprise exit %s)", title, result.returncode)
        return False
    LOG.info("Notification sent: %s", title)
    return True
