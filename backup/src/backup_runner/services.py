"""Service catalog parsing, validation and source resolution."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from .errors import BackupError, ConfigError
from .settings import SERVICE_FILE
from .util import expand_env

LOG = logging.getLogger("backup")

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DB_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KINDS = {"files", "env_configs", "postgres_cluster"}


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


def _is_absolute_catalog_path(value: str) -> bool:
    """Accept POSIX container paths even when tests run on Windows."""

    return PurePosixPath(value).is_absolute() or Path(value).is_absolute()


def load_services(path: Optional[Path] = None) -> dict[str, Service]:
    catalog = path or SERVICE_FILE
    if not catalog.is_file():
        raise ConfigError(f"Service catalog not found: {catalog}")
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot read {catalog}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError("services.json: root must be an object")
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
        root_raw = expand_env(item["root"]) if isinstance(item.get("root"), str) else None
        root = Path(root_raw) if root_raw is not None else None
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
            if root_raw is None or not _is_absolute_catalog_path(root_raw):
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


def selected_services(
    config: dict[str, Service],
    *,
    raw: Optional[str] = None,
    require: bool = True,
) -> list[Service]:
    if raw is None:
        raw = os.environ.get("BACKUP_SERVICES", "")
    names = raw.split()
    if not names:
        if require:
            raise ConfigError("BACKUP_SERVICES is empty")
        return []
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
