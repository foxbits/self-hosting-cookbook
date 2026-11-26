from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import cli, commands
from backup_runner.errors import ConfigError


class ParserTests(unittest.TestCase):
    def test_run_command(self) -> None:
        args = cli.build_parser().parse_args(["run", "actual"])
        self.assertEqual((args.command, args.service), ("run", "actual"))

    def test_restore_defaults_to_latest(self) -> None:
        args = cli.build_parser().parse_args(["restore", "actual"])
        self.assertEqual((args.command, args.service, args.snapshot), ("restore", "actual", "latest"))

    def test_restore_accepts_snapshot(self) -> None:
        args = cli.build_parser().parse_args(["restore", "actual", "abc123"])
        self.assertEqual(args.snapshot, "abc123")


class DispatchTests(unittest.TestCase):
    def test_run_all_dispatch(self) -> None:
        with (
            patch("backup_runner.cli.setup_logging"),
            patch("backup_runner.cli.ensure_dirs"),
            patch("backup_runner.cli.commands.cmd_run_all", return_value=0) as command,
        ):
            self.assertEqual(cli.main(["run-all"]), 0)
        command.assert_called_once()

    def test_run_dispatch(self) -> None:
        with (
            patch("backup_runner.cli.setup_logging"),
            patch("backup_runner.cli.ensure_dirs"),
            patch("backup_runner.cli.commands.cmd_run_one", return_value=0) as command,
        ):
            self.assertEqual(cli.main(["run", "actual"]), 0)
        command.assert_called_once_with("actual")

    def test_restore_dispatch(self) -> None:
        with (
            patch("backup_runner.cli.setup_logging"),
            patch("backup_runner.cli.ensure_dirs"),
            patch("backup_runner.cli.commands.cmd_restore", return_value=0) as command,
        ):
            self.assertEqual(cli.main(["restore", "actual", "abc"]), 0)
        command.assert_called_once_with("actual", "abc")

    def test_backup_error_returns_one(self) -> None:
        with (
            patch("backup_runner.cli.setup_logging"),
            patch("backup_runner.cli.ensure_dirs"),
            patch("backup_runner.cli.commands.cmd_run_all", side_effect=ConfigError("bad")),
        ):
            self.assertEqual(cli.main(["run-all"]), 1)


class HealthcheckTests(unittest.TestCase):
    def test_healthcheck_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "services.json"
            catalog.write_text("{}", encoding="utf-8")
            socket = root / "docker.sock"
            socket.write_text("", encoding="utf-8")
            with (
                patch("backup_runner.commands.shutil.which", return_value="/bin/tool"),
                patch("backup_runner.commands.MOUNT_PATHS", (root,)),
                patch("backup_runner.commands.DOCKER_SOCKET", socket),
                patch("backup_runner.commands.SERVICE_FILE", catalog),
                patch("backup_runner.commands.load_services") as load,
                patch("backup_runner.commands.run_checked") as run,
                patch.dict(os.environ, {"RESTIC_REPOSITORY": "rclone:icloud:x", "RESTIC_PASSWORD": "p"}, clear=True),
            ):
                self.assertEqual(commands.cmd_healthcheck(), 0)
        load.assert_called_once_with(catalog)
        run.assert_called_once()

    def test_healthcheck_reports_missing_command(self) -> None:
        with patch("backup_runner.commands.shutil.which", return_value=None):
            self.assertEqual(commands.cmd_healthcheck(), 1)


class EntrypointTests(unittest.TestCase):
    def test_build_crontab_lines(self) -> None:
        env = {"BACKUP_CRON": "30 3 * * *", "BACKUP_CHECK_CRON": "0 4 * * 0"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                commands.build_crontab_lines(),
                [
                    "30 3 * * * python3 -m backup_runner run-all",
                    "0 4 * * 0 python3 -m backup_runner check",
                ],
            )

    def test_entrypoint_writes_crontab_and_execs_supercronic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            crontab = Path(temp) / "crontab"
            env = {
                "BACKUP_SCHEDULE_ENABLED": "true",
                "BACKUP_CRON": "30 3 * * *",
                "BACKUP_CHECK_ENABLED": "false",
            }
            with (
                patch("backup_runner.commands.ensure_dirs"),
                patch("backup_runner.commands.recover_stopped"),
                patch("backup_runner.commands.CRONTAB_FILE", crontab),
                patch("backup_runner.commands.os.execvp") as execvp,
                patch.dict(os.environ, env, clear=True),
            ):
                self.assertEqual(commands.cmd_entrypoint(), 0)
            self.assertEqual(crontab.read_text(encoding="utf-8"), "30 3 * * * python3 -m backup_runner run-all\n")
            execvp.assert_called_once_with("supercronic", ["supercronic", str(crontab)])
