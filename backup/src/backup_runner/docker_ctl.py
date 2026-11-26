"""Docker socket checks and stop/start recovery state."""

from __future__ import annotations

import json
import logging
import os
import subprocess

from .errors import BackupError, CommandError
from .services import Service
from .settings import STATE_DIR, STOPPED_FILE
from .util import run_checked

LOG = logging.getLogger("backup")


def check_docker() -> None:
    try:
        run_checked(["docker", "info"], timeout=30, what="docker")
    except CommandError as exc:
        raise BackupError("Cannot reach the Docker socket; check /var/run/docker.sock and its permissions") from exc


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
