"""PostgreSQL readiness checks and logical dumps."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .errors import BackupError, CommandError
from .services import Service
from .settings import require_env
from .util import run_checked

LOG = logging.getLogger("backup")


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
