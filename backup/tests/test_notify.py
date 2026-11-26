from __future__ import annotations

import os
import subprocess
import unittest
from unittest.mock import patch

from backup_runner import notify


class NotificationTests(unittest.TestCase):
    def test_disabled_returns_success_without_running(self) -> None:
        with (
            patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "false"}, clear=True),
            patch("backup_runner.notify.subprocess.run") as run,
        ):
            self.assertTrue(notify.notify("info", "title", "body"))
        run.assert_not_called()

    def test_success_can_be_suppressed(self) -> None:
        env = {"BACKUP_NOTIFY_ENABLED": "true", "BACKUP_NOTIFY_ON_SUCCESS": "false"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("backup_runner.notify.subprocess.run") as run,
        ):
            self.assertTrue(notify.notify("success", "title", "body"))
        run.assert_not_called()

    def test_missing_url_returns_false(self) -> None:
        with (
            patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "true"}, clear=True),
            patch("backup_runner.notify.subprocess.run") as run,
        ):
            self.assertFalse(notify.notify("failure", "title", "body"))
        run.assert_not_called()

    def test_truncates_body_and_passes_expected_arguments(self) -> None:
        env = {"BACKUP_NOTIFY_ENABLED": "true", "APPRISE_DISCORD_URL": "discord://id/token"}
        completed = subprocess.CompletedProcess(["apprise"], 0)
        body = "x" * (notify.MAX_BODY_CHARS + 200)
        with (
            patch.dict(os.environ, env, clear=True),
            patch("backup_runner.notify.subprocess.run", return_value=completed) as run,
        ):
            self.assertTrue(notify.notify("info", "Title", body))
        args = run.call_args.args[0]
        self.assertEqual(args[0:2], ["apprise", "-t"])
        self.assertEqual(args[2], "Title")
        self.assertEqual(args[3], "-b")
        self.assertEqual(len(args[4]), notify.MAX_BODY_CHARS)
        self.assertEqual(args[5:], ["-n", "info", "discord://id/token"])

    def test_apprise_failure_returns_false(self) -> None:
        env = {"BACKUP_NOTIFY_ENABLED": "true", "APPRISE_DISCORD_URL": "discord://id/token"}
        completed = subprocess.CompletedProcess(["apprise"], 1)
        with (
            patch.dict(os.environ, env, clear=True),
            patch("backup_runner.notify.subprocess.run", return_value=completed),
        ):
            self.assertFalse(notify.notify("failure", "Title", "body"))

    def test_spawn_error_returns_false(self) -> None:
        env = {"BACKUP_NOTIFY_ENABLED": "true", "APPRISE_DISCORD_URL": "discord://id/token"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("backup_runner.notify.subprocess.run", side_effect=OSError("spawn failed")),
        ):
            self.assertFalse(notify.notify("failure", "Title", "body"))
