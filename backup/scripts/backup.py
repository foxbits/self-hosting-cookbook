#!/usr/bin/env python3
"""Backup runner for the home-lab stack."""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

SERVICE_FILE = Path("/etc/backup/services.json")
STATE_DIR = Path(os.environ.get("BACKUP_STATE_DIR", "/var/lib/backup/state"))
STAGING_ROOT = Path(os.environ.get("BACKUP_STAGING_ROOT", "/var/lib/backup/staging"))
LOG_DIR = Path(os.environ.get("BACKUP_LOG_DIR", "/var/lib/backup/logs"))
LOCK_FILE = Path(os.environ.get("BACKUP_LOCK_FILE", str(STATE_DIR / "backup.lock")))
STOPPED_FILE = Path(os.environ.get("BACKUP_STOPPED_FILE", str(STATE_DIR / "stopped-containers.json")))

LOG = logging.getLogger("backup")

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DB_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KINDS = {"files", "env_configs", "postgres_cluster"}


class BackupError(Exception):
    """A recoverable backup-stack error."""


class ConfigError(BackupError):
    """Invalid configuration or service catalog."""


class CommandError(BackupError):
    """A child command failed."""


class LockBusy(BackupError):
    """Another backup operation holds the lock."""


@dataclass(frozen=True)
class StopConfig:
    project: str
    services: tuple[str, ...]


@dataclass(frozen=True)
class Service:
    name: str
    description: str
    kind: str
    sources: tuple[Path, ...] = ()
    optional_sources: tuple[Path, ...] = ()
    excludes: tuple[str, ...] = ()
    databases: tuple[str, ...] = ()
    stop: Optional[StopConfig] = None
    root: Optional[Path] = None
    env_excludes: tuple[Path, ...] = ()


def setup_logging() -> None:
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stdout,
    )


def ensure_dirs() -> None:
    for path in (STATE_DIR, STAGING_ROOT, LOG_DIR):
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
    for name, default in (
        ("BACKUP_KEEP_DAILY", 7),
        ("BACKUP_KEEP_WEEKLY", 4),
        ("BACKUP_KEEP_MONTHLY", 12),
    ):
        if env_int(name, default) < 0:
            raise ConfigError(f"{name} must not be negative")
    percent = env_int("BACKUP_CHECK_READ_DATA_PERCENT", 1)
    if not 1 <= percent <= 100:
        raise ConfigError("BACKUP_CHECK_READ_DATA_PERCENT must be between 1 and 100")


def validate_notification_env() -> None:
    if env_bool("BACKUP_NOTIFY_ENABLED"):
        require_env("APPRISE_DISCORD_URL")


def ensure_commands() -> None:
    required = (
        "restic",
        "rclone",
        "apprise",
        "pg_dump",
        "pg_dumpall",
        "pg_restore",
        "pg_isready",
        "psql",
        "docker",
    )
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        raise ConfigError(f"Required commands not found in the backup image: {', '.join(missing)}")


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


def _string_list(item: dict[str, Any], key: str) -> list[str]:
    value = item.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise ConfigError(f"services.json: {item.get('name', '<unnamed>')}.{key} must be a list of strings")
    return value


def _parse_stop(item: dict[str, Any]) -> Optional[StopConfig]:
    raw = item.get("stop")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"services.json: {item.get('name')}.stop must be an object")
    project = raw.get("project")
    services = raw.get("services")
    if not isinstance(project, str) or not project.strip():
        raise ConfigError(f"services.json: {item.get('name')}.stop.project must be a non-empty string")
    if not isinstance(services, list) or not services or not all(isinstance(s, str) and s for s in services):
        raise ConfigError(f"services.json: {item.get('name')}.stop.services must be a non-empty list of strings")
    return StopConfig(project=project.strip(), services=tuple(services))


def load_services() -> dict[str, Service]:
    if not SERVICE_FILE.is_file():
        raise ConfigError(f"Service catalog not found: {SERVICE_FILE}")
    try:
        data = json.loads(SERVICE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read {SERVICE_FILE}: {exc}") from exc
    if data.get("version") != 1:
        raise ConfigError("services.json: unsupported version")
    items = data.get("services")
    if not isinstance(items, list):
        raise ConfigError("services.json: services must be a list")

    allowed = {
        "name",
        "description",
        "type",
        "sources",
        "optional_sources",
        "excludes",
        "databases",
        "stop",
        "root",
        "env_excludes",
    }
    services: dict[str, Service] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError("services.json: each service must be an object")
        unknown = set(item) - allowed
        if unknown:
            raise ConfigError(f"services.json: unknown field(s) for {item.get('name')}: {', '.join(sorted(unknown))}")
        name = item.get("name")
        if not isinstance(name, str) or not _NAME_PATTERN.match(name):
            raise ConfigError(f"services.json: invalid service name: {name!r}")
        if name in services:
            raise ConfigError(f"services.json: duplicate service name: {name}")
        kind = item.get("type", "files")
        if not isinstance(kind, str) or kind not in _KINDS:
            raise ConfigError(f"services.json: {name}.type must be one of {', '.join(sorted(_KINDS))}")
        description = item.get("description", name)
        if not isinstance(description, str):
            raise ConfigError(f"services.json: {name}.description must be a string")

        sources = tuple(Path(expand_env(value)) for value in _string_list(item, "sources"))
        optional_sources = tuple(Path(expand_env(value)) for value in _string_list(item, "optional_sources"))
        excludes = tuple(expand_env(value) for value in _string_list(item, "excludes"))
        databases = tuple(_string_list(item, "databases"))
        stop = _parse_stop(item)
        root = Path(expand_env(item["root"])) if isinstance(item.get("root"), str) else None
        env_excludes = tuple(Path(expand_env(value)) for value in _string_list(item, "env_excludes"))

        for database in databases:
            if not _DB_PATTERN.match(database):
                raise ConfigError(f"services.json: {name}.databases contains an invalid name: {database!r}")

        if kind == "files":
            if "root" in item or "env_excludes" in item:
                raise ConfigError(f"services.json: {name}.root/env_excludes are only valid for env_configs")
            if not sources and not databases:
                raise ConfigError(f"services.json: {name} needs sources or databases")
        elif kind == "env_configs":
            if root is None or not root.is_absolute():
                raise ConfigError(f"services.json: {name}.root must be an absolute path")
            if sources or optional_sources or excludes or databases or stop:
                raise ConfigError(f"services.json: {name} must not define files sources, excludes, databases or stop")
        else:
            if sources or optional_sources or excludes or databases or stop or root is not None or env_excludes:
                raise ConfigError(f"services.json: {name} must not define files/database/stop fields")

        services[name] = Service(
            name=name,
            description=description,
            kind=kind,
            sources=sources,
            optional_sources=optional_sources,
            excludes=excludes,
            databases=databases,
            stop=stop,
            root=root,
            env_excludes=env_excludes,
        )
    return services


def selected_services(config: dict[str, Service], *, require: bool = True) -> list[Service]:
    raw = os.environ.get("BACKUP_SERVICES", "").strip()
    if not raw:
        if require:
            raise ConfigError("BACKUP_SERVICES is empty")
        return []
    names = raw.split()
    missing = [name for name in names if name not in config]
    if missing:
        raise ConfigError(f"BACKUP_SERVICES contains unknown service(s): {', '.join(missing)}")
    seen: set[str] = set()
    ordered: list[Service] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            ordered.append(config[name])
    return ordered


def collect_env_sources(service: Service) -> list[Path]:
    if service.root is None or not service.root.is_dir():
        raise BackupError(f"{service.name}: root directory does not exist: {service.root}")
    excluded = {str(path) for path in service.env_excludes}
    sources: list[Path] = []
    root_env = service.root / ".env"
    if root_env.is_file() and str(root_env) not in excluded:
        sources.append(root_env)
    for child in sorted(service.root.glob("*/.env")):
        if child.is_file() and str(child) not in excluded:
            sources.append(child)
    if not sources:
        raise BackupError(f"{service.name}: no .env files found under {service.root}")
    return sources


def resolve_sources(service: Service) -> list[Path]:
    if service.kind == "env_configs":
        return collect_env_sources(service)
    if service.kind == "postgres_cluster":
        return []
    sources: list[Path] = []
    for source in service.sources:
        if not source.exists():
            raise BackupError(f"{service.name}: required source does not exist: {source}")
        sources.append(source)
    for source in service.optional_sources:
        if source.exists():
            sources.append(source)
        else:
            LOG.warning("%s: optional source not found, skipping: %s", service.name, source)
    if not sources and not service.databases:
        raise BackupError(f"{service.name}: no sources were resolved")
    return sources


@contextlib.contextmanager
def backup_lock() -> Iterator[None]:
    ensure_dirs()
    with open(LOCK_FILE, "a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LockBusy("Another backup run is already in progress; refusing to overlap") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def notify(kind: str, title: str, body: str) -> bool:
    if not env_bool("BACKUP_NOTIFY_ENABLED"):
        return True
    if kind == "success" and not env_bool("BACKUP_NOTIFY_ON_SUCCESS", True):
        return True
    url = os.environ.get("APPRISE_DISCORD_URL", "").strip()
    if not url or "CHANGE_ME" in url:
        LOG.warning("APPRISE_DISCORD_URL is not configured; skipping notification: %s", title)
        return False
    body = body[:1800]
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


def check_docker() -> None:
    try:
        run_checked(["docker", "info"], timeout=30, what="docker")
    except CommandError as exc:
        raise BackupError("Cannot reach the Docker socket; check /var/run/docker.sock and its permissions") from exc


def preflight_repository() -> None:
    repository = require_env("RESTIC_REPOSITORY")
    if not repository.startswith("rclone:"):
        raise ConfigError("RESTIC_REPOSITORY must use the rclone backend: rclone:<remote>:<path>")
    remote = repository[len("rclone:") :].split(":", 1)[0]
    if not remote:
        raise ConfigError(f"RESTIC_REPOSITORY does not name an rclone remote: {repository}")
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


def pg_config() -> dict[str, str]:
    return {
        "host": require_env("BACKUP_PG_HOST"),
        "port": require_env("BACKUP_PG_PORT"),
        "user": require_env("BACKUP_PG_USER"),
        "password": require_env("BACKUP_PG_PASSWORD"),
    }


def pg_env(password: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    return env


def check_pg_server() -> None:
    cfg = pg_config()
    try:
        run_checked(
            [
                "pg_isready",
                "-h",
                cfg["host"],
                "-p",
                cfg["port"],
                "-U",
                cfg["user"],
                "-d",
                "postgres",
            ],
            timeout=30,
            what="pg_isready",
        )
    except CommandError as exc:
        raise BackupError(f"PostgreSQL is not ready at {cfg['host']}:{cfg['port']}") from exc


def check_databases(service: Service) -> None:
    if not service.databases:
        return
    cfg = pg_config()
    env = pg_env(cfg["password"])
    for database in service.databases:
        result = run_checked(
            [
                "psql",
                "--no-password",
                "-h",
                cfg["host"],
                "-p",
                cfg["port"],
                "-U",
                cfg["user"],
                "-d",
                "postgres",
                "-tAc",
                f"SELECT 1 FROM pg_database WHERE datname = '{database}'",
            ],
            env=env,
            what=f"psql ({database})",
        )
        if result.stdout.strip() != "1":
            raise BackupError(f"PostgreSQL database {database} (needed by {service.name}) does not exist")


def dump_databases(service: Service, staging: Path) -> None:
    if not service.databases:
        return
    cfg = pg_config()
    env = pg_env(cfg["password"])
    for database in service.databases:
        LOG.info("Dumping PostgreSQL database %s", database)
        run_checked(
            [
                "pg_dump",
                "--no-password",
                "-h",
                cfg["host"],
                "-p",
                cfg["port"],
                "-U",
                cfg["user"],
                "-Fc",
                "-f",
                str(staging / f"{database}.dump"),
                database,
            ],
            env=env,
            what=f"pg_dump ({database})",
        )


def dump_cluster(staging: Path) -> None:
    cfg = pg_config()
    env = pg_env(cfg["password"])
    LOG.info("Dumping PostgreSQL globals")
    run_checked(
        [
            "pg_dumpall",
            "--no-password",
            "-h",
            cfg["host"],
            "-p",
            cfg["port"],
            "-U",
            cfg["user"],
            "--globals-only",
            "-f",
            str(staging / "globals.sql"),
        ],
        env=env,
        what="pg_dumpall --globals-only",
    )
    LOG.info("Dumping all PostgreSQL databases")
    run_checked(
        [
            "pg_dumpall",
            "--no-password",
            "-h",
            cfg["host"],
            "-p",
            cfg["port"],
            "-U",
            cfg["user"],
            "-f",
            str(staging / "all-databases.sql"),
        ],
        env=env,
        what="pg_dumpall",
    )


def load_stopped() -> list[dict[str, str]]:
    if not STOPPED_FILE.is_file():
        return []
    try:
        data = json.loads(STOPPED_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOG.warning("Cannot read %s: %s", STOPPED_FILE, exc)
        return []
    if not isinstance(data, list):
        LOG.warning("Ignoring invalid state file: %s", STOPPED_FILE)
        return []
    return [entry for entry in data if isinstance(entry, dict) and "id" in entry]


def save_stopped(entries: list[dict[str, str]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STOPPED_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries), encoding="utf-8")
    os.replace(tmp, STOPPED_FILE)


def stop_service(service: Service) -> None:
    if service.stop is None:
        return
    project = service.stop.project
    entries = load_stopped()
    matched = 0
    for compose_service in service.stop.services:
        result = run_checked(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--filter",
                f"label=com.docker.compose.service={compose_service}",
            ],
            what="docker ps",
        )
        for container_id in result.stdout.split():
            inspect = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", container_id],
                capture_output=True,
                text=True,
            )
            if inspect.returncode != 0 or inspect.stdout.strip() != "true":
                continue
            matched += 1
            entry = {"id": container_id, "project": project, "service": compose_service}
            entries.append(entry)
            save_stopped(entries)
            LOG.info("Stopping container %s (%s/%s)", container_id, project, compose_service)
            stop = subprocess.run(
                ["docker", "stop", "--time", "30", container_id],
                capture_output=True,
                text=True,
            )
            if stop.returncode != 0:
                raise CommandError(f"Failed to stop container {container_id}")
    if matched == 0:
        LOG.warning(
            "No running containers matched project=%s services=%s; they may already be stopped or the project name differs",
            project,
            ",".join(service.stop.services),
        )


def start_stopped() -> bool:
    entries = load_stopped()
    if not entries:
        return True
    remaining: list[dict[str, str]] = []
    for entry in entries:
        container_id = str(entry.get("id", ""))
        project = str(entry.get("project", ""))
        compose_service = str(entry.get("service", ""))
        if not container_id:
            continue
        LOG.info("Starting container %s (%s/%s)", container_id, project, compose_service)
        result = subprocess.run(["docker", "start", container_id], capture_output=True, text=True)
        if result.returncode != 0:
            LOG.warning("Could not start container %s (%s/%s)", container_id, project, compose_service)
            remaining.append(entry)
    save_stopped(remaining)
    return not remaining


def recover_stopped() -> None:
    if not load_stopped():
        return
    LOG.info("Recovering containers stopped by an interrupted backup run")
    if not start_stopped():
        LOG.warning("Some containers from the interrupted run could not be restarted")


def restic_backup(service: Service, sources: list[Path], json_file: Path, log_file: Path) -> tuple[str, int]:
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
            if event.get("message_type") == "summary":
                snapshot_id = str(event.get("snapshot_id") or "")
                total_bytes = int(event.get("total_bytes_processed") or 0)
    except OSError:
        pass
    if not snapshot_id:
        try:
            result = run_checked(
                ["restic", "snapshots", "--tag", f"service:{service.name}", "--latest", "1", "--json"],
                what="restic snapshots",
            )
            snapshots = json.loads(result.stdout)
            if snapshots:
                snapshot_id = str(snapshots[0].get("id") or "")
                total_bytes = int(snapshots[0].get("summary", {}).get("total_bytes_processed") or total_bytes)
        except (CommandError, json.JSONDecodeError, KeyError, IndexError, TypeError):
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
    if not snapshots:
        raise BackupError(f"No snapshot found for service {service.name}")
    return str(snapshots[0]["id"])


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def run_one_service(service: Service) -> bool:
    ensure_dirs()
    staging = STAGING_ROOT / service.name
    log_file = LOG_DIR / f"{service.name}.log"
    json_file = LOG_DIR / f"{service.name}.json"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
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
        if service.kind == "postgres_cluster":
            check_pg_server()
            dump_cluster(staging)
            sources = [staging]
        elif service.databases:
            check_pg_server()
            check_databases(service)
            dump_databases(service, staging)
            sources.append(staging)
        if not sources:
            raise BackupError("no sources were resolved")
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
        shutil.rmtree(staging, ignore_errors=True)
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
    for path in (Path("/cookbook"), Path("/docker-volumes"), Path("/restore"), Path("/config/rclone")):
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
    need_pg = False
    for service in services:
        resolve_sources(service)
        if service.kind == "postgres_cluster" or service.databases:
            need_pg = True
    if need_pg:
        check_pg_server()
        for service in services:
            if service.databases:
                check_databases(service)
    LOG.info("Preflight OK for: %s", " ".join(service.name for service in services))


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
            target = Path("/restore") / name
            target.mkdir(parents=True, exist_ok=True)
            LOG.info("Restoring snapshot %s for %s into %s", snapshot_id, name, target)
            run_checked(["restic", "restore", snapshot_id, "--target", str(target)], what="restic restore")
        except Exception as exc:  # noqa: BLE001 - report restore failure
            notify("failure", f"Restore FAILED: {name}", f"restic restore failed: {exc}")
            raise

        LOG.info(
            "Restored paths keep their absolute prefixes below %s: /cookbook, /docker-volumes, /sources and /var/lib/backup/staging.",
            target,
        )
        if service.kind == "postgres_cluster":
            staging = target / "var/lib/backup/staging/datastore-sql"
            LOG.info("Full cluster dump: %s", staging / "all-databases.sql")
            LOG.info("Globals dump: %s", staging / "globals.sql")
            LOG.info(
                "Full restore example: PGPASSWORD=<password> psql -h %s -U %s -f %s",
                os.environ.get("BACKUP_PG_HOST", "datastore-sql"),
                os.environ.get("BACKUP_PG_USER", "postgres"),
                staging / "all-databases.sql",
            )
        for database in service.databases:
            dump = target / "var/lib/backup/staging" / name / f"{database}.dump"
            LOG.info("Database dump: %s", dump)
            LOG.info(
                "Restore example: PGPASSWORD=<password> pg_restore -h %s -U %s -d %s --clean --if-exists %s",
                os.environ.get("BACKUP_PG_HOST", "datastore-sql"),
                os.environ.get("BACKUP_PG_USER", "postgres"),
                database,
                dump,
            )
        LOG.info("Restore is non-destructive; the live services were not modified.")
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
    required = ("restic", "rclone", "apprise", "pg_dump", "pg_restore", "psql", "docker", "supercronic")
    missing = [name for name in required if shutil.which(name) is None]
    if missing:
        print(f"missing commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    if not os.environ.get("RESTIC_REPOSITORY") or not os.environ.get("RESTIC_PASSWORD"):
        print("restic environment is incomplete", file=sys.stderr)
        return 1
    for path in (Path("/cookbook"), Path("/docker-volumes"), Path("/config/rclone"), Path("/restore")):
        if not path.is_dir():
            print(f"missing mount: {path}", file=sys.stderr)
            return 1
    if not Path("/var/run/docker.sock").exists():
        print("missing docker socket", file=sys.stderr)
        return 1
    if not SERVICE_FILE.is_file():
        print(f"missing service catalog: {SERVICE_FILE}", file=sys.stderr)
        return 1
    try:
        load_services()
    except BackupError as exc:
        print(f"invalid service catalog: {exc}", file=sys.stderr)
        return 1
    try:
        run_checked(["docker", "info"], timeout=30, what="docker")
    except BackupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def cmd_entrypoint() -> int:
    ensure_dirs()
    try:
        recover_stopped()
    except Exception as exc:  # noqa: BLE001 - do not block startup on recovery
        LOG.warning("Container recovery reported a problem: %s", exc)

    if env_bool("BACKUP_SCHEDULE_ENABLED"):
        cron = require_env("BACKUP_CRON")
        lines = [f"{cron} python3 /usr/local/bin/backup.py run-all"]
        if env_bool("BACKUP_CHECK_ENABLED", True):
            check_cron = require_env("BACKUP_CHECK_CRON")
            lines.append(f"{check_cron} python3 /usr/local/bin/backup.py check")
        crontab = Path("/etc/backup-crontab")
        crontab.write_text("\n".join(lines) + "\n", encoding="utf-8")
        LOG.info("Starting automatic backup scheduler")
        LOG.info("Schedule:")
        for line in lines:
            LOG.info("  %s", line)
        os.execvp("supercronic", ["supercronic", str(crontab)])
        return 0

    LOG.info("Automatic backups are disabled (BACKUP_SCHEDULE_ENABLED=false)")
    LOG.info("Manual use: docker compose exec backup python3 /usr/local/bin/backup.py run-all")
    while True:
        time.sleep(3600)


def usage() -> None:
    print(
        "Usage: backup.py <command> [args]\n\n"
        "Commands:\n"
        "  run-all                 Back up every service listed in BACKUP_SERVICES\n"
        "  run <service>           Back up one service\n"
        "  preflight               Validate configuration, sources, repository and databases\n"
        "  snapshots               List restic snapshots\n"
        "  check                   Apply retention, prune and verify repository data\n"
        "  restore <service> [id]  Restore a service snapshot (default: latest)\n"
        "  notify-test             Send an Apprise test notification\n"
        "  init                    Initialize the restic repository\n"
        "  entrypoint              Container entrypoint (scheduler or idle)\n"
        "  healthcheck             Container healthcheck"
    )


def main(argv: Sequence[str]) -> int:
    setup_logging()
    ensure_dirs()
    if not argv:
        usage()
        return 1
    command = argv[0]
    try:
        if command == "run-all":
            return cmd_run_all()
        if command == "run":
            if len(argv) < 2:
                usage()
                return 1
            return cmd_run_one(argv[1])
        if command == "preflight":
            return cmd_preflight()
        if command == "snapshots":
            return cmd_snapshots()
        if command == "check":
            return cmd_check()
        if command == "restore":
            if len(argv) < 2:
                usage()
                return 1
            return cmd_restore(argv[1], argv[2] if len(argv) > 2 else "latest")
        if command == "notify-test":
            return cmd_notify_test()
        if command == "init":
            return cmd_init()
        if command == "entrypoint":
            return cmd_entrypoint()
        if command == "healthcheck":
            return cmd_healthcheck()
        usage()
        return 1
    except LockBusy as exc:
        LOG.warning("%s", exc)
        return 1
    except BackupError as exc:
        LOG.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        LOG.warning("Interrupted")
        return 130
    except Exception:  # noqa: BLE001 - last-resort guard
        LOG.exception("Unexpected backup-stack failure")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
