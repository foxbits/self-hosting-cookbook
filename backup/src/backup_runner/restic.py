"""Restic operations: backup, retention, prune, check and snapshots."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from .errors import BackupError, CommandError
from .services import Service
from .settings import backup_host, env_int, now_iso
from .util import run_checked

LOG = logging.getLogger("backup")


def restic_backup(
    service: Service,
    sources: list[Path],
    json_file: Path,
    log_file: Path,
) -> tuple[str, int]:
    args = [
        "restic",
        "backup",
        "--tag",
        f"service:{service.name}",
        "--host",
        backup_host(),
        "--time",
        now_iso(),
        "--json",
    ]
    for exclude in service.excludes:
        args.extend(["--exclude", exclude])
    args.extend(str(path) for path in sources)
    try:
        with json_file.open("w", encoding="utf-8") as stdout, log_file.open("a", encoding="utf-8") as stderr:
            result = subprocess.run(args, stdout=stdout, stderr=stderr, text=True)
    except OSError as exc:
        raise CommandError(f"restic backup could not start: {exc}") from exc
    if result.returncode != 0:
        raise CommandError(f"restic backup failed (exit {result.returncode}); see {log_file}")

    snapshot_id = ""
    total_bytes = 0
    try:
        for line in json_file.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and event.get("message_type") == "summary":
                snapshot_id = str(event.get("snapshot_id") or "")
                total_bytes = int(event.get("total_bytes_processed") or 0)
    except (OSError, TypeError, ValueError):
        pass
    if not snapshot_id:
        try:
            result = run_checked(
                ["restic", "snapshots", "--tag", f"service:{service.name}", "--latest", "1", "--json"],
                what="restic snapshots",
            )
            snapshots = json.loads(result.stdout)
            if snapshots:
                snapshot = snapshots[0]
                if isinstance(snapshot, dict):
                    snapshot_id = str(snapshot.get("id") or "")
                    summary = snapshot.get("summary")
                    if isinstance(summary, dict):
                        total_bytes = int(summary.get("total_bytes_processed") or total_bytes)
        except (CommandError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError, AttributeError):
            pass
    return snapshot_id or "unknown", total_bytes


def restic_forget(service: Service) -> bool:
    result = subprocess.run(
        [
            "restic",
            "forget",
            "--tag",
            f"service:{service.name}",
            "--keep-daily",
            str(env_int("BACKUP_KEEP_DAILY", 7)),
            "--keep-weekly",
            str(env_int("BACKUP_KEEP_WEEKLY", 4)),
            "--keep-monthly",
            str(env_int("BACKUP_KEEP_MONTHLY", 12)),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        LOG.warning("Retention (restic forget) failed for %s; the new snapshot is still valid", service.name)
        return False
    return True


def restic_prune() -> None:
    result = run_checked(["restic", "prune"], what="restic prune")
    if result.stdout.strip():
        LOG.info("%s", result.stdout.strip())


def restic_check() -> None:
    percent = env_int("BACKUP_CHECK_READ_DATA_PERCENT", 1)
    result = run_checked(
        ["restic", "check", "--read-data-subset", f"{percent}%"],
        what="restic check",
    )
    if result.stdout.strip():
        LOG.info("%s", result.stdout.strip())


def restic_snapshots() -> str:
    return run_checked(["restic", "snapshots"], what="restic snapshots").stdout


def resolve_snapshot(service: Service, requested: str) -> str:
    if requested != "latest":
        return requested
    result = run_checked(
        ["restic", "snapshots", "--tag", f"service:{service.name}", "--latest", "1", "--json"],
        what="restic snapshots",
    )
    try:
        snapshots = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BackupError("restic snapshots returned invalid JSON") from exc
    if not isinstance(snapshots, list) or not snapshots:
        raise BackupError(f"No snapshot found for service {service.name}")
    snapshot = snapshots[0]
    if not isinstance(snapshot, dict) or not snapshot.get("id"):
        raise BackupError(f"No snapshot found for service {service.name}")
    return str(snapshot["id"])
