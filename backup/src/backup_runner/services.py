"""Service catalog parsing, validation and source resolution."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .errors import BackupError, ConfigError
from .settings import SERVICE_FILE

LOG = logging.getLogger("backup")

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class StopConfig:
    project: str
    services: tuple[str, ...]


@dataclass(frozen=True)
class Service:
    name: str
    description: str
    sources: tuple[Path, ...] = ()
    optional_sources: tuple[Path, ...] = ()
    stop: Optional[StopConfig] = None


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

    allowed = {"name", "description", "sources", "optional_sources", "stop"}
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
        description = item.get("description", name)
        if not isinstance(description, str):
            raise ConfigError(f"services.json: {name}.description must be a string")

        sources = tuple(Path(value) for value in _string_list(item, "sources"))
        optional_sources = tuple(Path(value) for value in _string_list(item, "optional_sources"))
        stop = _parse_stop(item)

        if not sources:
            raise ConfigError(f"services.json: {name} needs sources")

        services[name] = Service(
            name=name,
            description=description,
            sources=sources,
            optional_sources=optional_sources,
            stop=stop,
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


def resolve_sources(service: Service) -> list[Path]:
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
    if not sources:
        raise BackupError(f"{service.name}: no sources were resolved")
    return sources
