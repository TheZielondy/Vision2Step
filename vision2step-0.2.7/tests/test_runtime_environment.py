"""Tests for secret removal without breaking Windows subprocess startup."""

from __future__ import annotations

import unittest

from vision2step.runtime_environment import sanitized_runtime_environment


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_windows_runtime_state_is_preserved_and_secrets_are_removed(self) -> None:
        source = {
            "PATH": r"C:\Python312;C:\Windows\System32",
            "SYSTEMROOT": r"C:\Windows",
            "WINDIR": r"C:\Windows",
            "COMSPEC": r"C:\Windows\System32\cmd.exe",
            "USERPROFILE": r"C:\Users\Kaan",
            "APPDATA": r"C:\Users\Kaan\AppData\Roaming",
            "LOCALAPPDATA": r"C:\Users\Kaan\AppData\Local",
            "VIRTUAL_ENV": r"C:\project\.venv",
            "VISION2STEP_CAD_TIMEOUT": "120",
            "ANTHROPIC_API_KEY": "secret",
            "SERVICE_TOKEN": "secret",
            "PYTHONPATH": r"C:\untrusted",
            "PYTHONSTARTUP": r"C:\untrusted\startup.py",
        }

        result = sanitized_runtime_environment(source)

        self.assertEqual(result["USERPROFILE"], source["USERPROFILE"])
        self.assertEqual(result["APPDATA"], source["APPDATA"])
        self.assertEqual(result["LOCALAPPDATA"], source["LOCALAPPDATA"])
        self.assertEqual(result["COMSPEC"], source["COMSPEC"])
        self.assertEqual(result["VIRTUAL_ENV"], source["VIRTUAL_ENV"])
        self.assertEqual(result["VISION2STEP_CAD_TIMEOUT"], "120")
        self.assertNotIn("ANTHROPIC_API_KEY", result)
        self.assertNotIn("SERVICE_TOKEN", result)
        self.assertNotIn("PYTHONPATH", result)
        self.assertNotIn("PYTHONSTARTUP", result)


if __name__ == "__main__":
    unittest.main()
