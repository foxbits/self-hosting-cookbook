from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from backup_runner import restic
from backup_runner.errors import BackupError, CommandError
from backup_runner.services import Service


def completed(args: list[str], code: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, code, stdout=stdout, stderr="")


class ResticBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.json_file = self.root / "actual.json"
        self.log_file = self.root / "actual.log"
        self.service = Service("actual", "Actual", "files", excludes=("/data/cache",))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_parses_summary_and_builds_command(self) -> None:
        def fake_run(args: list[str], stdout=None, stderr=None, text: Optional[bool] = None):
            assert stdout is not None
            stdout.write('{"message_type":"summary","snapshot_id":"abc","total_bytes_processed":2048}\n')
            return completed(args)

        source = Path("/data")
        with patch("backup_runner.restic.subprocess.run", side_effect=fake_run) as run:
            snapshot_id, total = restic.restic_backup(
                self.service,
                [source],
                self.json_file,
                self.log_file,
            )
        self.assertEqual((snapshot_id, total), ("abc", 2048))
        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["restic", "backup", "--tag"])
        self.assertIn("service:actual", args)
        self.assertIn("--exclude", args)
        self.assertIn("/data/cache", args)
        self.assertIn(str(source), args)

    def test_falls_back_to_snapshot_lookup_without_summary(self) -> None:
        with (
            patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"])),
            patch(
                "backup_runner.restic.run_checked",
                return_value=completed(
                    ["restic"],
                    stdout=json.dumps([{"id": "fallback", "summary": {"total_bytes_processed": 10}}]),
                ),
            ),
        ):
            self.assertEqual(
                restic.restic_backup(self.service, [Path("/data")], self.json_file, self.log_file),
                ("fallback", 10),
            )

    def test_fallback_handles_missing_summary_object(self) -> None:
        with (
            patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"])),
            patch(
                "backup_runner.restic.run_checked",
                return_value=completed(["restic"], stdout=json.dumps([{"id": "fallback", "summary": None}])),
            ),
        ):
            self.assertEqual(
                restic.restic_backup(self.service, [Path("/data")], self.json_file, self.log_file),
                ("fallback", 0),
            )

    def test_fallback_handles_non_object_snapshot(self) -> None:
        with (
            patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"])),
            patch(
                "backup_runner.restic.run_checked",
                return_value=completed(["restic"], stdout=json.dumps([42])),
            ),
        ):
            self.assertEqual(
                restic.restic_backup(self.service, [Path("/data")], self.json_file, self.log_file),
                ("unknown", 0),
            )

    def test_unknown_snapshot_when_no_summary_or_lookup(self) -> None:
        with (
            patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"])),
            patch("backup_runner.restic.run_checked", side_effect=CommandError("no snapshots")),
        ):
            self.assertEqual(
                restic.restic_backup(self.service, [Path("/data")], self.json_file, self.log_file),
                ("unknown", 0),
            )

    def test_nonzero_exit_raises(self) -> None:
        with patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"], 2)):
            with self.assertRaises(CommandError):
                restic.restic_backup(self.service, [Path("/data")], self.json_file, self.log_file)


class ResticMaintenanceTests(unittest.TestCase):
    def test_forget_uses_retention_environment(self) -> None:
        env = {"BACKUP_KEEP_DAILY": "3", "BACKUP_KEEP_WEEKLY": "2", "BACKUP_KEEP_MONTHLY": "5"}
        service = Service("actual", "Actual", "files")
        with (
            patch.dict(os.environ, env, clear=True),
            patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"])) as run,
        ):
            self.assertTrue(restic.restic_forget(service))
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("--keep-daily") + 1], "3")
        self.assertEqual(args[args.index("--keep-weekly") + 1], "2")
        self.assertEqual(args[args.index("--keep-monthly") + 1], "5")

    def test_forget_failure_returns_false(self) -> None:
        service = Service("actual", "Actual", "files")
        with patch("backup_runner.restic.subprocess.run", return_value=completed(["restic"], 1)):
            self.assertFalse(restic.restic_forget(service))

    def test_prune_and_check_commands(self) -> None:
        with patch("backup_runner.restic.run_checked", return_value=completed(["restic"])) as run:
            restic.restic_prune()
            with patch.dict(os.environ, {"BACKUP_CHECK_READ_DATA_PERCENT": "5"}, clear=True):
                restic.restic_check()
        self.assertEqual(run.call_args_list[0].args[0], ["restic", "prune"])
        self.assertEqual(run.call_args_list[1].args[0], ["restic", "check", "--read-data-subset", "5%"])

    def test_snapshots_returns_stdout(self) -> None:
        with patch("backup_runner.restic.run_checked", return_value=completed(["restic"], stdout="snapshots\n")):
            self.assertEqual(restic.restic_snapshots(), "snapshots\n")


class SnapshotResolutionTests(unittest.TestCase):
    def test_explicit_snapshot_is_returned_unchanged(self) -> None:
        self.assertEqual(restic.resolve_snapshot(Service("actual", "Actual", "files"), "deadbeef"), "deadbeef")

    def test_latest_resolves_first_snapshot(self) -> None:
        result = completed(["restic"], stdout=json.dumps([{"id": "abc"}]))
        with patch("backup_runner.restic.run_checked", return_value=result):
            self.assertEqual(restic.resolve_snapshot(Service("actual", "Actual", "files"), "latest"), "abc")

    def test_latest_without_snapshot_raises(self) -> None:
        result = completed(["restic"], stdout="[]")
        with patch("backup_runner.restic.run_checked", return_value=result):
            with self.assertRaises(BackupError):
                restic.resolve_snapshot(Service("actual", "Actual", "files"), "latest")

    def test_invalid_snapshot_json_raises(self) -> None:
        result = completed(["restic"], stdout="{")
        with patch("backup_runner.restic.run_checked", return_value=result):
            with self.assertRaises(BackupError):
                restic.resolve_snapshot(Service("actual", "Actual", "files"), "latest")

    def test_non_list_snapshot_response_raises(self) -> None:
        result = completed(["restic"], stdout=json.dumps({"id": "abc"}))
        with patch("backup_runner.restic.run_checked", return_value=result):
            with self.assertRaises(BackupError):
                restic.resolve_snapshot(Service("actual", "Actual", "files"), "latest")

    def test_snapshot_without_id_raises(self) -> None:
        result = completed(["restic"], stdout=json.dumps([{"short_id": "abc"}]))
        with patch("backup_runner.restic.run_checked", return_value=result):
            with self.assertRaises(BackupError):
                restic.resolve_snapshot(Service("actual", "Actual", "files"), "latest")
