from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from backup_runner import commands
from backup_runner.errors import BackupError, ConfigError
from backup_runner.services import Service


class CommandTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Service("actual", "Actual", "files")
        self.config = {"actual": self.service}
        self.lock = patch("backup_runner.commands.backup_lock", return_value=nullcontext())
        self.lock.start()

    def tearDown(self) -> None:
        self.lock.stop()


class RunAllCommandTests(CommandTestBase):
    def test_runs_selected_services(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.preflight_global"),
            patch("backup_runner.commands.selected_services", return_value=[self.service]),
            patch("backup_runner.commands.run_all_services", return_value=0) as run,
            patch("backup_runner.commands.notify") as notify,
        ):
            self.assertEqual(commands.cmd_run_all(), 0)
        run.assert_called_once_with([self.service])
        notify.assert_not_called()

    def test_preflight_failure_is_notified_and_reraised(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.preflight_global", side_effect=ConfigError("bad config")),
            patch("backup_runner.commands.notify", return_value=True) as notify,
        ):
            with self.assertRaises(ConfigError):
                commands.cmd_run_all()
        self.assertEqual(notify.call_args.args[0], "failure")
        self.assertIn("bad config", notify.call_args.args[2])


class RunOneCommandTests(CommandTestBase):
    def test_runs_one_service(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.check_docker"),
            patch("backup_runner.commands.preflight_repository"),
            patch("backup_runner.commands.resolve_sources"),
            patch("backup_runner.commands.run_one_service", return_value=True) as run,
        ):
            self.assertEqual(commands.cmd_run_one("actual"), 0)
        run.assert_called_once_with(self.service)

    def test_unknown_service_raises(self) -> None:
        with patch("backup_runner.commands.load_services", return_value=self.config):
            with self.assertRaises(ConfigError):
                commands.cmd_run_one("missing")

    def test_preflight_failure_is_notified_and_reraised(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.check_docker", side_effect=BackupError("no docker")),
            patch("backup_runner.commands.notify", return_value=True) as notify,
        ):
            with self.assertRaises(BackupError):
                commands.cmd_run_one("actual")
        self.assertEqual(notify.call_args.args[0], "failure")
        self.assertIn("no docker", notify.call_args.args[2])


class PreflightCommandTests(CommandTestBase):
    def test_preflight_calls_all(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.preflight_all") as preflight,
        ):
            self.assertEqual(commands.cmd_preflight(), 0)
        preflight.assert_called_once_with(self.config)


class SnapshotCommandTests(unittest.TestCase):
    def test_snapshots_writes_stdout(self) -> None:
        output = io.StringIO()
        with (
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.restic_snapshots", return_value="snapshots\n"),
            patch("backup_runner.commands.sys.stdout", output),
        ):
            self.assertEqual(commands.cmd_snapshots(), 0)
        self.assertEqual(output.getvalue(), "snapshots\n")


class CheckCommandTests(CommandTestBase):
    def test_check_runs_retention_prune_and_verify(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.preflight_repository"),
            patch("backup_runner.commands.selected_services", return_value=[self.service]) as selected,
            patch("backup_runner.commands.restic_forget") as forget,
            patch("backup_runner.commands.restic_prune") as prune,
            patch("backup_runner.commands.restic_check") as check,
            patch("backup_runner.commands.notify", return_value=True),
        ):
            self.assertEqual(commands.cmd_check(), 0)
        selected.assert_called_once_with(self.config, require=False)
        forget.assert_called_once_with(self.service)
        prune.assert_called_once()
        check.assert_called_once()

    def test_check_notification_failure_returns_one(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.preflight_repository"),
            patch("backup_runner.commands.selected_services", return_value=[]),
            patch("backup_runner.commands.restic_prune"),
            patch("backup_runner.commands.restic_check"),
            patch("backup_runner.commands.notify", return_value=False),
        ):
            self.assertEqual(commands.cmd_check(), 1)

    def test_check_failure_is_notified_and_reraised(self) -> None:
        with (
            patch("backup_runner.commands.load_services", return_value=self.config),
            patch("backup_runner.commands.validate_common_env"),
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.preflight_repository", side_effect=BackupError("auth")),
            patch("backup_runner.commands.notify", return_value=True) as notify,
        ):
            with self.assertRaises(BackupError):
                commands.cmd_check()
        self.assertEqual(notify.call_args.args[0], "failure")


class RestoreCommandTests(CommandTestBase):
    def test_restore_runs_restic_and_logs_dump_paths(self) -> None:
        service = Service("vaultwarden", "Vaultwarden", "files", databases=("vaultwarden",))
        config = {"vaultwarden": service}
        with tempfile.TemporaryDirectory() as temp:
            with (
                patch("backup_runner.commands.load_services", return_value=config),
                patch("backup_runner.commands.validate_common_env"),
                patch("backup_runner.commands.validate_notification_env"),
                patch("backup_runner.commands.ensure_commands"),
                patch("backup_runner.commands.preflight_repository"),
                patch("backup_runner.commands.resolve_snapshot", return_value="abc") as resolve,
                patch("backup_runner.commands.RESTORE_DIR", Path(temp)),
                patch("backup_runner.commands.run_checked") as run,
                patch("backup_runner.commands.notify") as notify,
            ):
                self.assertEqual(commands.cmd_restore("vaultwarden", "latest"), 0)
                self.assertTrue((Path(temp) / "vaultwarden").is_dir())
        resolve.assert_called_once_with(service, "latest")
        self.assertEqual(run.call_args.args[0][:2], ["restic", "restore"])
        notify.assert_not_called()

    def test_unknown_service_raises(self) -> None:
        with patch("backup_runner.commands.load_services", return_value=self.config):
            with self.assertRaises(ConfigError):
                commands.cmd_restore("missing", "latest")


class NotifyAndInitTests(unittest.TestCase):
    def test_notify_test_disabled_raises(self) -> None:
        with (
            patch("backup_runner.commands.validate_notification_env"),
            patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "false"}, clear=True),
        ):
            with self.assertRaises(ConfigError):
                commands.cmd_notify_test()

    def test_notify_test_sends_info(self) -> None:
        with (
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.notify", return_value=True) as notify,
            patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "true"}, clear=True),
        ):
            self.assertEqual(commands.cmd_notify_test(), 0)
        self.assertEqual(notify.call_args.args[0], "info")

    def test_notify_test_failure_raises(self) -> None:
        with (
            patch("backup_runner.commands.validate_notification_env"),
            patch("backup_runner.commands.notify", return_value=False),
            patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "true"}, clear=True),
        ):
            with self.assertRaises(BackupError):
                commands.cmd_notify_test()

    def test_init_runs_restic_init(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"RESTIC_REPOSITORY": "rclone:icloud:x", "RESTIC_PASSWORD": "secret"},
                clear=True,
            ),
            patch("backup_runner.commands.ensure_commands"),
            patch("backup_runner.commands.run_checked") as run,
        ):
            self.assertEqual(commands.cmd_init(), 0)
        self.assertEqual(run.call_args.args[0], ["restic", "init"])
