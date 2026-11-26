from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import postgres
from backup_runner.errors import BackupError, CommandError, ConfigError
from backup_runner.services import Service


class PgConfigTests(unittest.TestCase):
    def test_pg_config_requires_all_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                postgres.pg_config()

    def test_pg_env_sets_password_and_preserves_environment(self) -> None:
        with patch.dict(os.environ, {"EXISTING": "1"}, clear=True):
            env = postgres.pg_env("secret")
        self.assertEqual(env["PGPASSWORD"], "secret")
        self.assertEqual(env["EXISTING"], "1")


class PgCommandTests(unittest.TestCase):
    def test_check_pg_server_builds_ready_command(self) -> None:
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        with (
            patch("backup_runner.postgres.pg_config", return_value=cfg),
            patch("backup_runner.postgres.run_checked") as run,
        ):
            postgres.check_pg_server()
        self.assertEqual(
            run.call_args.args[0],
            ["pg_isready", "-h", "db", "-p", "5432", "-U", "postgres", "-d", "postgres"],
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_check_pg_server_wraps_failure(self) -> None:
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        with (
            patch("backup_runner.postgres.pg_config", return_value=cfg),
            patch("backup_runner.postgres.run_checked", side_effect=CommandError("down")),
        ):
            with self.assertRaises(BackupError):
                postgres.check_pg_server()

    def test_check_databases_requires_existing_database(self) -> None:
        service = Service("vaultwarden", "Vaultwarden", "files", databases=("vaultwarden",))
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        completed = subprocess.CompletedProcess(["psql"], 0, stdout="1\n", stderr="")
        with (
            patch("backup_runner.postgres.pg_config", return_value=cfg),
            patch("backup_runner.postgres.run_checked", return_value=completed) as run,
        ):
            postgres.check_databases(service)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "psql")
        self.assertIn("SELECT 1 FROM pg_database WHERE datname = 'vaultwarden'", command)
        self.assertEqual(run.call_args.kwargs["env"]["PGPASSWORD"], "secret")

    def test_check_databases_rejects_missing_database(self) -> None:
        service = Service("vaultwarden", "Vaultwarden", "files", databases=("vaultwarden",))
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        completed = subprocess.CompletedProcess(["psql"], 0, stdout="\n", stderr="")
        with (
            patch("backup_runner.postgres.pg_config", return_value=cfg),
            patch("backup_runner.postgres.run_checked", return_value=completed),
        ):
            with self.assertRaises(BackupError):
                postgres.check_databases(service)

    def test_dump_databases_writes_dump_path(self) -> None:
        service = Service("fusionauth", "FusionAuth", "files", databases=("fusionauth",))
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp)
            with (
                patch("backup_runner.postgres.pg_config", return_value=cfg),
                patch("backup_runner.postgres.run_checked") as run,
            ):
                postgres.dump_databases(service, staging)
            command = run.call_args.args[0]
            self.assertEqual(command[0], "pg_dump")
            self.assertEqual(command[-1], "fusionauth")
            self.assertIn(str(staging / "fusionauth.dump"), command)

    def test_dump_cluster_writes_globals_and_full_dump(self) -> None:
        cfg = {"host": "db", "port": "5432", "user": "postgres", "password": "secret"}
        with tempfile.TemporaryDirectory() as temp:
            staging = Path(temp)
            with (
                patch("backup_runner.postgres.pg_config", return_value=cfg),
                patch("backup_runner.postgres.run_checked") as run,
            ):
                postgres.dump_cluster(staging)
            commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(commands), 2)
        self.assertIn("--globals-only", commands[0])
        self.assertIn(str(staging / "globals.sql"), commands[0])
        self.assertNotIn("--globals-only", commands[1])
        self.assertIn(str(staging / "all-databases.sql"), commands[1])
