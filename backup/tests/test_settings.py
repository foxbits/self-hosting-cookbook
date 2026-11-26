from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import settings
from backup_runner.errors import ConfigError


class EnvHelperTests(unittest.TestCase):
    def test_env_bool_accepts_truthy_values(self) -> None:
        for value in ("1", "true", "YES", "y", "on"):
            with self.subTest(value=value), patch.dict(os.environ, {"FLAG": value}, clear=True):
                self.assertTrue(settings.env_bool("FLAG"))

    def test_env_bool_default_and_falsey(self) -> None:
        with patch.dict(os.environ, {"FLAG": "false"}, clear=True):
            self.assertFalse(settings.env_bool("FLAG"))
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(settings.env_bool("FLAG", True))

    def test_env_int_rejects_non_integer(self) -> None:
        with patch.dict(os.environ, {"COUNT": "many"}, clear=True):
            with self.assertRaises(ConfigError):
                settings.env_int("COUNT", 1)

    def test_require_env_rejects_empty_and_placeholder(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                settings.require_env("VALUE")
        with patch.dict(os.environ, {"VALUE": "CHANGE_ME"}, clear=True):
            with self.assertRaises(ConfigError):
                settings.require_env("VALUE")

    def test_backup_host_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(settings.backup_host(), "home-lab")
        with patch.dict(os.environ, {"BACKUP_HOST": "server"}, clear=True):
            self.assertEqual(settings.backup_host(), "server")


class ValidationTests(unittest.TestCase):
    def test_common_env_accepts_valid_values(self) -> None:
        with patch.dict(
            os.environ,
            {"RESTIC_REPOSITORY": "rclone:icloud:backup", "RESTIC_PASSWORD": "secret"},
            clear=True,
        ):
            settings.validate_common_env()

    def test_common_env_rejects_negative_retention(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RESTIC_REPOSITORY": "rclone:icloud:backup",
                "RESTIC_PASSWORD": "secret",
                "BACKUP_KEEP_DAILY": "-1",
            },
            clear=True,
        ):
            with self.assertRaises(ConfigError):
                settings.validate_common_env()

    def test_common_env_rejects_bad_read_percent(self) -> None:
        with patch.dict(
            os.environ,
            {
                "RESTIC_REPOSITORY": "rclone:icloud:backup",
                "RESTIC_PASSWORD": "secret",
                "BACKUP_CHECK_READ_DATA_PERCENT": "0",
            },
            clear=True,
        ):
            with self.assertRaises(ConfigError):
                settings.validate_common_env()

    def test_notifications_require_url_when_enabled(self) -> None:
        with patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "true"}, clear=True):
            with self.assertRaises(ConfigError):
                settings.validate_notification_env()

    def test_notifications_can_be_disabled(self) -> None:
        with patch.dict(os.environ, {"BACKUP_NOTIFY_ENABLED": "false"}, clear=True):
            settings.validate_notification_env()


class FilesystemTests(unittest.TestCase):
    def test_ensure_dirs_creates_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.object(settings, "STATE_DIR", root / "state"),
                patch.object(settings, "STAGING_ROOT", root / "staging"),
                patch.object(settings, "LOG_DIR", root / "logs"),
            ):
                settings.ensure_dirs()
            self.assertTrue((root / "state").is_dir())
            self.assertTrue((root / "staging").is_dir())
            self.assertTrue((root / "logs").is_dir())

    def test_ensure_commands_reports_missing(self) -> None:
        with patch("backup_runner.settings.shutil.which", side_effect=lambda name: None if name == "restic" else "/bin/x"):
            with self.assertRaises(ConfigError) as caught:
                settings.ensure_commands()
        self.assertIn("restic", str(caught.exception))

    def test_now_iso_is_utc_iso8601(self) -> None:
        value = settings.now_iso()
        self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
