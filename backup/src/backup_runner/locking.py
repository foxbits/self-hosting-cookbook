"""Cross-platform single-writer lock for backup runs."""

from __future__ import annotations

import contextlib
import os
from typing import Iterator

from .errors import LockBusy
from .settings import LOCK_FILE, ensure_dirs

try:  # POSIX runtime (Alpine)
    import fcntl
except ImportError:  # pragma: no cover - exercised on Windows test hosts
    fcntl = None

try:  # Windows test hosts
    import msvcrt
except ImportError:  # pragma: no cover - exercised on Linux
    msvcrt = None


def _lock(handle: object) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return
    if msvcrt is not None:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write("\0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    raise LockBusy("File locking is not supported on this platform")


def _unlock(handle: object) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    if msvcrt is not None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


@contextlib.contextmanager
def backup_lock() -> Iterator[None]:
    ensure_dirs()
    with open(LOCK_FILE, "a+", encoding="utf-8") as handle:
        try:
            _lock(handle)
        except (BlockingIOError, OSError) as exc:
            raise LockBusy("Another backup run is already in progress; refusing to overlap") from exc
        try:
            yield
        finally:
            _unlock(handle)
