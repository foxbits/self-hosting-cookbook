"""Command-line parser and dispatch."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Sequence

from . import commands
from .errors import BackupError, LockBusy
from .settings import ensure_dirs, setup_logging

LOG = logging.getLogger("backup")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backup_runner",
        description="Home-lab restic backup orchestration.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-all", help="Back up every service listed in BACKUP_SERVICES")

    run_parser = subparsers.add_parser("run", help="Back up one service")
    run_parser.add_argument("service")

    subparsers.add_parser("preflight", help="Validate configuration, sources and repository")
    subparsers.add_parser("snapshots", help="List restic snapshots")
    subparsers.add_parser("check", help="Apply retention, prune and verify repository data")

    restore_parser = subparsers.add_parser("restore", help="Restore a service snapshot")
    restore_parser.add_argument("service")
    restore_parser.add_argument("snapshot", nargs="?", default="latest")

    subparsers.add_parser("notify-test", help="Send an Apprise test notification")
    subparsers.add_parser("init", help="Initialize the restic repository")
    subparsers.add_parser("entrypoint", help="Container entrypoint (scheduler or idle)")
    subparsers.add_parser("healthcheck", help="Container healthcheck")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    setup_logging()
    ensure_dirs()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run-all":
            return commands.cmd_run_all()
        if args.command == "run":
            return commands.cmd_run_one(args.service)
        if args.command == "preflight":
            return commands.cmd_preflight()
        if args.command == "snapshots":
            return commands.cmd_snapshots()
        if args.command == "check":
            return commands.cmd_check()
        if args.command == "restore":
            return commands.cmd_restore(args.service, args.snapshot)
        if args.command == "notify-test":
            return commands.cmd_notify_test()
        if args.command == "init":
            return commands.cmd_init()
        if args.command == "entrypoint":
            return commands.cmd_entrypoint()
        if args.command == "healthcheck":
            return commands.cmd_healthcheck()
        parser.error(f"unknown command: {args.command}")
    except LockBusy as exc:
        LOG.warning("%s", exc)
        return 1
    except BackupError as exc:
        LOG.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        LOG.warning("Interrupted")
        return 130
    except Exception:  # noqa: BLE001 - last-resort guard
        LOG.exception("Unexpected backup-stack failure")
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
