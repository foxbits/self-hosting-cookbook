"""Backup-stack exception hierarchy."""

from __future__ import annotations


class BackupError(Exception):
    """A recoverable backup-stack error."""


class ConfigError(BackupError):
    """Invalid configuration or service catalog."""


class CommandError(BackupError):
    """A child command failed."""


class LockBusy(BackupError):
    """Another backup operation holds the lock."""
