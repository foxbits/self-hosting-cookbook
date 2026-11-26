from __future__ import annotations

import os
import unittest
from unittest.mock import call, patch

from backup_runner import repository
from backup_runner.errors import BackupError, CommandError, ConfigError


class RepositoryRemoteTests(unittest.TestCase):
    def test_returns_remote(self) -> None:
        self.assertEqual(repository.repository_remote("rclone:icloud:backups/home"), "icloud")

    def test_rejects_non_rclone_repository(self) -> None:
        with self.assertRaises(ConfigError):
            repository.repository_remote("/mnt/backup")

    def test_rejects_missing_remote(self) -> None:
        with self.assertRaises(ConfigError):
            repository.repository_remote("rclone:")


class RepositoryPreflightTests(unittest.TestCase):
    def test_checks_rclone_then_restic(self) -> None:
        with (
            patch.dict(os.environ, {"RESTIC_REPOSITORY": "rclone:icloud:backups"}, clear=True),
            patch("backup_runner.repository.run_checked") as run,
        ):
            repository.preflight_repository()
        self.assertEqual(
            run.call_args_list,
            [
                call(["rclone", "lsd", "icloud:"], timeout=120, what="rclone"),
                call(["restic", "cat", "config"], timeout=120, what="restic"),
            ],
        )

    def test_rclone_failure_is_wrapped(self) -> None:
        with (
            patch.dict(os.environ, {"RESTIC_REPOSITORY": "rclone:icloud:backups"}, clear=True),
            patch("backup_runner.repository.run_checked", side_effect=CommandError("auth")),
        ):
            with self.assertRaises(BackupError) as caught:
                repository.preflight_repository()
        self.assertIn("rclone remote", str(caught.exception))

    def test_restic_failure_is_wrapped(self) -> None:
        with (
            patch.dict(os.environ, {"RESTIC_REPOSITORY": "rclone:icloud:backups"}, clear=True),
            patch(
                "backup_runner.repository.run_checked",
                side_effect=[None, CommandError("not initialized")],
            ),
        ):
            with self.assertRaises(BackupError) as caught:
                repository.preflight_repository()
        self.assertIn("restic repository", str(caught.exception))
