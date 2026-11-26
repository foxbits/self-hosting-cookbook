from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import runner
from backup_runner.errors import CommandError, ConfigError
from backup_runner.services import Service


class RunnerTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.staging = self.root / "staging"
        self.logs = self.root / "logs"
        self.staging.mkdir()
        self.logs.mkdir()
        self.patchers = [
            patch.object(runner, "STAGING_ROOT", self.staging),
            patch.object(runner, "LOG_DIR", self.logs),
            patch("backup_runner.runner.ensure_dirs"),
            patch("backup_runner.runner.signal.signal", return_value=None),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def service(self, **kwargs: object) -> Service:
        defaults = {"name": "actual", "description": "Actual", "kind": "files"}
        defaults.update(kwargs)
        return Service(**defaults)  # type: ignore[arg-type]


class RunOneServiceTests(RunnerTestBase):
    def test_success_path(self) -> None:
        service = self.service()
        source = self.root / "source"
        source.mkdir()
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[source]),
            patch("backup_runner.runner.stop_service") as stop,
            patch("backup_runner.runner.start_stopped", return_value=True),
            patch("backup_runner.runner.restic_backup", return_value=("snap", 2048)) as backup,
            patch("backup_runner.runner.restic_forget", return_value=True),
            patch("backup_runner.runner.notify", return_value=True) as notify,
        ):
            result = runner.run_one_service(service)
        self.assertTrue(result)
        stop.assert_called_once_with(service)
        self.assertEqual(backup.call_args.args[1], [source])
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[0], "success")
        self.assertFalse((self.staging / "actual").exists())

    def test_backup_failure_isolated_and_reported(self) -> None:
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[Path("/data")]),
            patch("backup_runner.runner.stop_service"),
            patch("backup_runner.runner.start_stopped", return_value=True),
            patch("backup_runner.runner.restic_backup", side_effect=CommandError("boom")),
            patch("backup_runner.runner.notify", return_value=True) as notify,
        ):
            result = runner.run_one_service(self.service())
        self.assertFalse(result)
        self.assertEqual(notify.call_args.args[0], "failure")
        self.assertIn("boom", notify.call_args.args[2])

    def test_restart_failure_marks_backup_failed(self) -> None:
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[Path("/data")]),
            patch("backup_runner.runner.stop_service"),
            patch("backup_runner.runner.start_stopped", return_value=False),
            patch("backup_runner.runner.restic_backup", return_value=("snap", 1)),
            patch("backup_runner.runner.restic_forget", return_value=True),
            patch("backup_runner.runner.notify", return_value=True) as notify,
        ):
            result = runner.run_one_service(self.service())
        self.assertFalse(result)
        self.assertEqual(notify.call_args.args[0], "failure")
        self.assertIn("WARNING", notify.call_args.args[1])

    def test_success_notification_failure_marks_backup_failed(self) -> None:
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[Path("/data")]),
            patch("backup_runner.runner.stop_service"),
            patch("backup_runner.runner.start_stopped", return_value=True),
            patch("backup_runner.runner.restic_backup", return_value=("snap", 1)),
            patch("backup_runner.runner.restic_forget", return_value=True),
            patch("backup_runner.runner.notify", return_value=False),
        ):
            self.assertFalse(runner.run_one_service(self.service()))

    def test_database_service_adds_staging_directory(self) -> None:
        service = self.service(databases=("actual",))
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[Path("/data")]),
            patch("backup_runner.runner.stop_service"),
            patch("backup_runner.runner.start_stopped", return_value=True),
            patch("backup_runner.runner.check_pg_server") as check_server,
            patch("backup_runner.runner.check_databases") as check_db,
            patch("backup_runner.runner.dump_databases") as dump,
            patch("backup_runner.runner.restic_backup", return_value=("snap", 1)) as backup,
            patch("backup_runner.runner.restic_forget", return_value=True),
            patch("backup_runner.runner.notify", return_value=True),
        ):
            self.assertTrue(runner.run_one_service(service))
        check_server.assert_called_once()
        check_db.assert_called_once_with(service)
        dump.assert_called_once_with(service, self.staging / "actual")
        self.assertIn(self.staging / "actual", backup.call_args.args[1])

    def test_cluster_service_uses_only_staging(self) -> None:
        service = self.service(kind="postgres_cluster")
        with (
            patch("backup_runner.runner.resolve_sources", return_value=[]),
            patch("backup_runner.runner.stop_service"),
            patch("backup_runner.runner.start_stopped", return_value=True),
            patch("backup_runner.runner.check_pg_server") as check_server,
            patch("backup_runner.runner.dump_cluster") as dump,
            patch("backup_runner.runner.restic_backup", return_value=("snap", 1)) as backup,
            patch("backup_runner.runner.restic_forget", return_value=True),
            patch("backup_runner.runner.notify", return_value=True),
        ):
            self.assertTrue(runner.run_one_service(service))
        check_server.assert_called_once()
        dump.assert_called_once_with(self.staging / "actual")
        self.assertEqual(backup.call_args.args[1], [self.staging / "actual"])


class RunAllTests(unittest.TestCase):
    def test_returns_failure_summary(self) -> None:
        services = [Service("one", "", "files"), Service("two", "", "files")]
        with (
            patch("backup_runner.runner.run_one_service", side_effect=[True, False]) as run,
            patch("backup_runner.runner.notify") as notify,
        ):
            self.assertEqual(runner.run_all_services(services), 1)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(notify.call_args.args[0], "failure")
        self.assertIn("two", notify.call_args.args[2])

    def test_returns_success(self) -> None:
        services = [Service("one", "", "files")]
        with patch("backup_runner.runner.run_one_service", return_value=True):
            self.assertEqual(runner.run_all_services(services), 0)


class PreflightTests(unittest.TestCase):
    def test_global_preflight_checks_all_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            mounts = (Path(temp),)
            with (
                patch.dict("os.environ", {"BACKUP_SERVICES": "actual"}, clear=True),
                patch("backup_runner.runner.MOUNT_PATHS", mounts),
                patch("backup_runner.runner.validate_common_env"),
                patch("backup_runner.runner.validate_notification_env"),
                patch("backup_runner.runner.ensure_commands"),
                patch("backup_runner.runner.env_bool", return_value=False),
                patch("backup_runner.runner.check_docker") as check_docker,
                patch("backup_runner.runner.preflight_repository") as preflight_repo,
            ):
                runner.preflight_global()
        check_docker.assert_called_once()
        preflight_repo.assert_called_once()

    def test_global_preflight_rejects_missing_mount(self) -> None:
        with (
            patch.dict("os.environ", {"BACKUP_SERVICES": "actual"}, clear=True),
            patch("backup_runner.runner.MOUNT_PATHS", (Path("/definitely-missing"),)),
            patch("backup_runner.runner.validate_common_env"),
            patch("backup_runner.runner.validate_notification_env"),
            patch("backup_runner.runner.ensure_commands"),
            patch("backup_runner.runner.env_bool", return_value=False),
        ):
            with self.assertRaises(ConfigError):
                runner.preflight_global()

    def test_all_preflight_checks_databases(self) -> None:
        service = Service("actual", "", "files", databases=("actual",))
        with (
            patch("backup_runner.runner.preflight_global") as global_check,
            patch("backup_runner.runner.selected_services", return_value=[service]),
            patch("backup_runner.runner.resolve_sources"),
            patch("backup_runner.runner.check_pg_server") as check_server,
            patch("backup_runner.runner.check_databases") as check_db,
        ):
            runner.preflight_all({"actual": service})
        global_check.assert_called_once()
        check_server.assert_called_once()
        check_db.assert_called_once_with(service)

    def test_all_preflight_skips_postgres_when_not_needed(self) -> None:
        service = Service("actual", "", "files")
        with (
            patch("backup_runner.runner.preflight_global"),
            patch("backup_runner.runner.selected_services", return_value=[service]),
            patch("backup_runner.runner.resolve_sources"),
            patch("backup_runner.runner.check_pg_server") as check_server,
        ):
            runner.preflight_all({"actual": service})
        check_server.assert_not_called()
