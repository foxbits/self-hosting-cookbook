from __future__ import annotations

import os
import subprocess
import unittest
from unittest.mock import patch

from backup_runner import util
from backup_runner.errors import CommandError, ConfigError


class ExpandEnvTests(unittest.TestCase):
    def test_substitutes_environment_value(self) -> None:
        with patch.dict(os.environ, {"VOLUME": "fusionauth_config"}, clear=True):
            self.assertEqual(util.expand_env("/docker-volumes/${VOLUME}/_data"), "/docker-volumes/fusionauth_config/_data")

    def test_uses_default_when_missing(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(util.expand_env("${VOLUME:-fallback}"), "fallback")

    def test_environment_wins_over_default(self) -> None:
        with patch.dict(os.environ, {"VOLUME": "real"}, clear=True):
            self.assertEqual(util.expand_env("${VOLUME:-fallback}"), "real")

    def test_missing_without_default_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError):
                util.expand_env("${VOLUME}")


class RunCheckedTests(unittest.TestCase):
    def test_returns_successful_process(self) -> None:
        completed = subprocess.CompletedProcess(["echo"], 0, stdout="ok", stderr="")
        with patch("backup_runner.util.subprocess.run", return_value=completed) as run:
            result = util.run_checked(["echo", "ok"], timeout=5, env={"A": "B"})
        self.assertEqual(result.stdout, "ok")
        run.assert_called_once_with(
            ["echo", "ok"],
            capture_output=True,
            text=True,
            timeout=5,
            env={"A": "B"},
        )

    def test_includes_stderr_tail_on_failure(self) -> None:
        completed = subprocess.CompletedProcess(["tool"], 2, stdout="", stderr="line1\nline2\n")
        with patch("backup_runner.util.subprocess.run", return_value=completed):
            with self.assertRaises(CommandError) as caught:
                util.run_checked(["tool"], what="tool")
        self.assertIn("tool failed (exit 2)", str(caught.exception))
        self.assertIn("line1 | line2", str(caught.exception))

    def test_missing_command_is_wrapped(self) -> None:
        with patch("backup_runner.util.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(CommandError) as caught:
                util.run_checked(["missing"])
        self.assertIn("command not found", str(caught.exception))

    def test_timeout_is_wrapped(self) -> None:
        with patch("backup_runner.util.subprocess.run", side_effect=subprocess.TimeoutExpired(["tool"], 1)):
            with self.assertRaises(CommandError) as caught:
                util.run_checked(["tool"], timeout=1)
        self.assertIn("timed out", str(caught.exception))


class HumanBytesTests(unittest.TestCase):
    def test_formats_units(self) -> None:
        self.assertEqual(util.human_bytes(0), "0 B")
        self.assertEqual(util.human_bytes(1024), "1.0 KiB")
        self.assertEqual(util.human_bytes(123456789), "117.7 MiB")
