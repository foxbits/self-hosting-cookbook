"""Per-service backup execution and global preflight."""

from __future__ import annotations

import logging
import os
import signal
import time
from typing import Any, Optional

from .docker_ctl import check_docker, start_stopped, stop_service
from .errors import ConfigError
from .notify import notify
from .repository import preflight_repository
from .restic import restic_backup, restic_forget
from .services import Service, resolve_sources, selected_services
from .settings import (
    LOG_DIR,
    MOUNT_PATHS,
    backup_host,
    ensure_commands,
    ensure_dirs,
    env_bool,
    require_env,
    validate_common_env,
    validate_notification_env,
)
from .util import human_bytes

LOG = logging.getLogger("backup")


def run_one_service(service: Service) -> bool:
    ensure_dirs()
    log_file = LOG_DIR / f"{service.name}.log"
    json_file = LOG_DIR / f"{service.name}.json"
    log_file.write_text("", encoding="utf-8")
    json_file.write_text("", encoding="utf-8")

    start = time.monotonic()
    error: Optional[Exception] = None
    snapshot_id = "unknown"
    total_bytes = 0
    restart_ok = True
    previous_handlers: dict[int, Any] = {}

    def terminate(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    for sig in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[sig] = signal.signal(sig, terminate)

    try:
        sources = resolve_sources(service)
        stop_service(service)
        snapshot_id, total_bytes = restic_backup(service, sources, json_file, log_file)
        if not restic_forget(service):
            LOG.warning("Retention failed for %s; the new snapshot is still valid", service.name)
    except Exception as exc:  # noqa: BLE001 - per-service failure isolation
        error = exc
    finally:
        try:
            restart_ok = start_stopped()
        except Exception as exc:  # noqa: BLE001 - never mask the original failure
            LOG.error("Could not restart containers after %s: %s", service.name, exc)
            restart_ok = False
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)

    duration = int(time.monotonic() - start)
    if error is not None:
        note = "" if restart_ok else " Some containers could not be restarted; check docker ps."
        LOG.error("Backup failed for %s: %s%s", service.name, error, note)
        notify(
            "failure",
            f"Backup FAILED: {service.name}",
            f"Service: {service.name}\nDetail: {error}{note}\nDuration: {duration}s\nHost: {backup_host()}",
        )
        return False
    if not restart_ok:
        LOG.error("Backup for %s completed but some containers could not be restarted", service.name)
        notify(
            "failure",
            f"Backup WARNING: {service.name}",
            f"Backup data was written, but a stopped container could not be restarted.\n"
            f"Service: {service.name}\nDuration: {duration}s\nCheck: docker ps",
        )
        return False

    size = human_bytes(total_bytes)
    LOG.info("Backup OK for %s: snapshot %s (%s, %s)", service.name, snapshot_id, size, duration)
    if not notify(
        "success",
        f"Backup OK: {service.name}",
        f"Service: {service.name}\nSnapshot: {snapshot_id}\nSize: {size}\nDuration: {duration}s\nHost: {backup_host()}",
    ):
        LOG.warning("Backup succeeded for %s, but the success notification failed", service.name)
        return False
    return True


def run_all_services(services: list[Service]) -> int:
    failures: list[str] = []
    for service in services:
        LOG.info("==> Backing up %s", service.name)
        if run_one_service(service):
            LOG.info("==> Backup OK: %s", service.name)
        else:
            LOG.error("==> Backup FAILED: %s", service.name)
            failures.append(service.name)
    if failures:
        notify(
            "failure",
            "Backup run FAILED",
            f"{len(failures)} service(s) failed: {', '.join(failures)}. Check docker logs backup for details.",
        )
        return 1
    LOG.info("==> All backups completed successfully")
    return 0


def preflight_global() -> None:
    validate_common_env()
    validate_notification_env()
    ensure_commands()
    if not os.environ.get("BACKUP_SERVICES", "").strip():
        raise ConfigError("BACKUP_SERVICES is empty")
    for path in MOUNT_PATHS:
        if not path.is_dir():
            raise ConfigError(f"Required mount is missing: {path}")
    if env_bool("BACKUP_SCHEDULE_ENABLED"):
        require_env("BACKUP_CRON")
    if env_bool("BACKUP_CHECK_ENABLED", True):
        require_env("BACKUP_CHECK_CRON")
    check_docker()
    preflight_repository()
    LOG.info("Global preflight OK")


def preflight_all(config: dict[str, Service]) -> None:
    preflight_global()
    services = selected_services(config)
    for service in services:
        resolve_sources(service)
    LOG.info("Preflight OK for: %s", " ".join(service.name for service in services))
