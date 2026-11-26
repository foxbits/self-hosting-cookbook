"""Command implementations for the backup CLI and container entrypoints."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import time

from .docker_ctl import check_docker, recover_stopped
from .errors import BackupError, ConfigError
from .locking import backup_lock
from .notify import notify
from .repository import preflight_repository
from .restic import restic_check, restic_forget, restic_prune, restic_snapshots, resolve_snapshot
from .runner import preflight_all, preflight_global, run_all_services, run_one_service
from .services import load_services, resolve_sources, selected_services
from .settings import (
    CRONTAB_FILE,
    DOCKER_SOCKET,
    HEALTHCHECK_COMMANDS,
    MOUNT_PATHS,
    RESTORE_DIR,
    SERVICE_FILE,
    ensure_commands,
    ensure_dirs,
    env_bool,
    require_env,
    validate_common_env,
    validate_notification_env,
)
from .util import run_checked

LOG = logging.getLogger("backup")


def cmd_run_all() -> int:
    config = load_services()
    with backup_lock():
        try:
            preflight_global()
            services = selected_services(config)
        except Exception as exc:  # noqa: BLE001 - report preflight failure once
            notify("failure", "Backup preflight FAILED", f"The backup preflight failed: {exc}")
            raise
        return run_all_services(services)


def cmd_run_one(name: str) -> int:
    config = load_services()
    service = config.get(name)
    if service is None:
        raise ConfigError(f"Unknown backup service: {name}")
    with backup_lock():
        validate_common_env()
        validate_notification_env()
        ensure_commands()
        try:
            check_docker()
            preflight_repository()
            resolve_sources(service)
        except Exception as exc:  # noqa: BLE001 - report the preflight failure
            notify("failure", f"Backup FAILED: {name}", f"The backup did not start: {exc}")
            raise
        return 0 if run_one_service(service) else 1


def cmd_preflight() -> int:
    config = load_services()
    with backup_lock():
        preflight_all(config)
    return 0


def cmd_snapshots() -> int:
    validate_common_env()
    ensure_commands()
    sys.stdout.write(restic_snapshots())
    return 0


def cmd_check() -> int:
    config = load_services()
    with backup_lock():
        validate_common_env()
        validate_notification_env()
        ensure_commands()
        try:
            preflight_repository()
            services = selected_services(config, require=False)
            for service in services:
                restic_forget(service)
            restic_prune()
            restic_check()
        except Exception as exc:  # noqa: BLE001 - report maintenance failure
            notify("failure", "Backup check FAILED", f"The repository maintenance failed: {exc}")
            raise
        if not notify("success", "Backup check OK", "restic prune and restic check completed successfully."):
            return 1
    return 0


def cmd_restore(name: str, requested: str) -> int:
    config = load_services()
    service = config.get(name)
    if service is None:
        raise ConfigError(f"Unknown backup service: {name}")
    with backup_lock():
        validate_common_env()
        validate_notification_env()
        ensure_commands()
        try:
            preflight_repository()
            snapshot_id = resolve_snapshot(service, requested)
            target = RESTORE_DIR / name
            target.mkdir(parents=True, exist_ok=True)
            LOG.info("Restoring snapshot %s for %s into %s", snapshot_id, name, target)
            run_checked(["restic", "restore", snapshot_id, "--target", str(target)], what="restic restore")
        except Exception as exc:  # noqa: BLE001 - report restore failure
            notify("failure", f"Restore FAILED: {name}", f"restic restore failed: {exc}")
            raise

        LOG.info("Restored paths keep their absolute prefixes below %s: /cookbook.", target)
        LOG.info("Restore is non-destructive; the live service was not modified.")
    return 0


def cmd_notify_test() -> int:
    validate_notification_env()
    if not env_bool("BACKUP_NOTIFY_ENABLED"):
        raise ConfigError("Notifications are disabled; set BACKUP_NOTIFY_ENABLED=true first")
    if not notify("info", "Backup notification test", "The backup stack can reach Apprise and Discord."):
        raise BackupError("The test notification could not be delivered")
    return 0


def cmd_init() -> int:
    require_env("RESTIC_REPOSITORY")
    require_env("RESTIC_PASSWORD")
    ensure_commands()
    run_checked(["restic", "init"], what="restic init")
    LOG.info("Restic repository initialized")
    return 0


def cmd_healthcheck() -> int:
    missing = [name for name in HEALTHCHECK_COMMANDS if shutil.which(name) is None]
    if missing:
        print(f"missing commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    if not os.environ.get("RESTIC_REPOSITORY") or not os.environ.get("RESTIC_PASSWORD"):
        print("restic environment is incomplete", file=sys.stderr)
        return 1
    for path in MOUNT_PATHS:
        if not path.is_dir():
            print(f"missing mount: {path}", file=sys.stderr)
            return 1
    if not DOCKER_SOCKET.exists():
        print("missing docker socket", file=sys.stderr)
        return 1
    if not SERVICE_FILE.is_file():
        print(f"missing service catalog: {SERVICE_FILE}", file=sys.stderr)
        return 1
    try:
        load_services(SERVICE_FILE)
    except BackupError as exc:
        print(f"invalid service catalog: {exc}", file=sys.stderr)
        return 1
    try:
        run_checked(["docker", "info"], timeout=30, what="docker")
    except BackupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def build_crontab_lines() -> list[str]:
    lines = [f"{require_env('BACKUP_CRON')} python3 -m backup_runner run-all"]
    if env_bool("BACKUP_CHECK_ENABLED", True):
        lines.append(f"{require_env('BACKUP_CHECK_CRON')} python3 -m backup_runner check")
    return lines


def cmd_entrypoint() -> int:
    ensure_dirs()
    try:
        recover_stopped()
    except Exception as exc:  # noqa: BLE001 - do not block startup on recovery
        LOG.warning("Container recovery reported a problem: %s", exc)

    if env_bool("BACKUP_SCHEDULE_ENABLED"):
        lines = build_crontab_lines()
        CRONTAB_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        LOG.info("Starting automatic backup scheduler")
        LOG.info("Schedule:")
        for line in lines:
            LOG.info("  %s", line)
        os.execvp("supercronic", ["supercronic", str(CRONTAB_FILE)])
        return 0

    LOG.info("Automatic backups are disabled (BACKUP_SCHEDULE_ENABLED=false)")
    LOG.info("Manual use: docker compose exec backup python3 -m backup_runner run-all")
    while True:
        time.sleep(3600)
