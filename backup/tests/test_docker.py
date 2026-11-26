from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import docker_ctl
from backup_runner.errors import BackupError, CommandError
from backup_runner.services import Service, StopConfig


class DockerStateTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / "stopped-containers.json"
        self.state_dir = self.root
        self.patcher_file = patch.object(docker_ctl, "STOPPED_FILE", self.state)
        self.patcher_dir = patch.object(docker_ctl, "STATE_DIR", self.state_dir)
        self.patcher_file.start()
        self.patcher_dir.start()

    def tearDown(self) -> None:
        self.patcher_dir.stop()
        self.patcher_file.stop()
        self.temp.cleanup()


class DockerStateTests(DockerStateTestBase):
    def test_save_and_load_round_trip(self) -> None:
        entries = [{"id": "abc", "project": "actual", "service": "actual_server"}]
        docker_ctl.save_stopped(entries)
        self.assertEqual(docker_ctl.load_stopped(), entries)

    def test_invalid_state_file_is_ignored(self) -> None:
        self.state.write_text("{", encoding="utf-8")
        self.assertEqual(docker_ctl.load_stopped(), [])

    def test_non_list_state_file_is_ignored(self) -> None:
        self.state.write_text(json.dumps({"id": "abc"}), encoding="utf-8")
        self.assertEqual(docker_ctl.load_stopped(), [])


class StopStartTests(DockerStateTestBase):
    def _service(self) -> Service:
        return Service(
            "actual",
            "Actual",
            stop=StopConfig(project="actual", services=("actual_server",)),
        )

    def test_stop_without_stop_config_is_noop(self) -> None:
        service = Service("actual", "Actual")
        with patch("backup_runner.docker_ctl.run_checked") as run:
            docker_ctl.stop_service(service)
        run.assert_not_called()

    def test_stop_records_then_stops_running_container(self) -> None:
        listed = subprocess.CompletedProcess(["docker"], 0, stdout="abc\n", stderr="")
        inspect = subprocess.CompletedProcess(["docker"], 0, stdout="true\n", stderr="")
        stopped = subprocess.CompletedProcess(["docker"], 0, stdout="abc\n", stderr="")
        with (
            patch("backup_runner.docker_ctl.run_checked", return_value=listed),
            patch("backup_runner.docker_ctl.subprocess.run", side_effect=[inspect, stopped]) as run,
        ):
            docker_ctl.stop_service(self._service())
        self.assertEqual(
            docker_ctl.load_stopped(),
            [{"id": "abc", "project": "actual", "service": "actual_server"}],
        )
        self.assertEqual(run.call_args_list[1].args[0][:2], ["docker", "stop"])

    def test_stop_skips_already_stopped_container(self) -> None:
        listed = subprocess.CompletedProcess(["docker"], 0, stdout="abc\n", stderr="")
        inspect = subprocess.CompletedProcess(["docker"], 0, stdout="false\n", stderr="")
        with (
            patch("backup_runner.docker_ctl.run_checked", return_value=listed),
            patch("backup_runner.docker_ctl.subprocess.run", return_value=inspect) as run,
        ):
            docker_ctl.stop_service(self._service())
        self.assertEqual(docker_ctl.load_stopped(), [])
        self.assertEqual(run.call_count, 1)

    def test_stop_failure_keeps_recovery_entry(self) -> None:
        listed = subprocess.CompletedProcess(["docker"], 0, stdout="abc\n", stderr="")
        inspect = subprocess.CompletedProcess(["docker"], 0, stdout="true\n", stderr="")
        failed = subprocess.CompletedProcess(["docker"], 1, stdout="", stderr="no")
        with (
            patch("backup_runner.docker_ctl.run_checked", return_value=listed),
            patch("backup_runner.docker_ctl.subprocess.run", side_effect=[inspect, failed]),
        ):
            with self.assertRaises(CommandError):
                docker_ctl.stop_service(self._service())
        self.assertEqual(len(docker_ctl.load_stopped()), 1)

    def test_start_removes_state_on_success(self) -> None:
        docker_ctl.save_stopped([{"id": "abc", "project": "actual", "service": "actual_server"}])
        started = subprocess.CompletedProcess(["docker"], 0)
        with patch("backup_runner.docker_ctl.subprocess.run", return_value=started):
            self.assertTrue(docker_ctl.start_stopped())
        self.assertEqual(docker_ctl.load_stopped(), [])

    def test_start_keeps_state_on_failure(self) -> None:
        docker_ctl.save_stopped([{"id": "abc", "project": "actual", "service": "actual_server"}])
        failed = subprocess.CompletedProcess(["docker"], 1)
        with patch("backup_runner.docker_ctl.subprocess.run", return_value=failed):
            self.assertFalse(docker_ctl.start_stopped())
        self.assertEqual(len(docker_ctl.load_stopped()), 1)

    def test_recover_without_state_is_noop(self) -> None:
        with patch("backup_runner.docker_ctl.start_stopped") as start:
            docker_ctl.recover_stopped()
        start.assert_not_called()


class DockerCheckTests(unittest.TestCase):
    def test_check_docker_ok(self) -> None:
        with patch("backup_runner.docker_ctl.run_checked") as run:
            docker_ctl.check_docker()
        run.assert_called_once()

    def test_check_docker_wraps_failure(self) -> None:
        with patch("backup_runner.docker_ctl.run_checked", side_effect=CommandError("no socket")):
            with self.assertRaises(BackupError):
                docker_ctl.check_docker()
