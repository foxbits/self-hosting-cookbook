from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backup_runner import locking
from backup_runner.errors import LockBusy


class BackupLockTests(unittest.TestCase):
    def test_lock_creates_and_releases_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock_file = Path(temp) / "backup.lock"
            with (
                patch.object(locking, "LOCK_FILE", lock_file),
                patch.object(locking, "ensure_dirs"),
            ):
                with locking.backup_lock():
                    self.assertTrue(lock_file.exists())
            self.assertTrue(lock_file.exists())

    def test_second_lock_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lock_file = Path(temp) / "backup.lock"
            with (
                patch.object(locking, "LOCK_FILE", lock_file),
                patch.object(locking, "ensure_dirs"),
            ):
                with locking.backup_lock():
                    with self.assertRaises(LockBusy):
                        with locking.backup_lock():
                            pass
