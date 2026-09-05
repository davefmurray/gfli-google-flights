"""Doctor is offline by default and remains usable with invalid configuration."""

import json
import os
import subprocess
import sysconfig
from pathlib import Path
from unittest.mock import Mock

import pytest

from fli.cli.doctor import diagnose


def test_offline_doctor_never_searches(monkeypatch, tmp_path):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path / "presets"))
    monkeypatch.setattr(
        "fli.search.SearchFlights.search", lambda *args, **kwargs: pytest.fail("Network")
    )
    result = diagnose()
    assert result["success"]
    assert next(c for c in result["checks"] if c["name"] == "provider")["status"] == "skipped"
    assert not (tmp_path / "presets").exists()


@pytest.mark.parametrize("timeout", ["nan", "0", "not-a-number"])
def test_real_entrypoint_handles_invalid_timeout_and_redacts_secrets(timeout, tmp_path):
    command = str(Path(sysconfig.get_path("scripts")) / "glfi")
    result = subprocess.run(
        [command, "doctor", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
        env={
            **os.environ,
            "GLFI_TIMEOUT": timeout,
            "GLFI_SOCS_COOKIE": "secret-cookie",
            "GLFI_PRESET_DIR": str(tmp_path),
        },
    )
    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert not payload["success"]
    assert "secret-cookie" not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_missing_mcp_is_optional_warning(monkeypatch, tmp_path):
    from importlib.util import find_spec

    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path))
    monkeypatch.setattr(
        "fli.cli.doctor.importlib.util.find_spec",
        lambda name: None if name in ("fastmcp", "mcp") else find_spec(name),
    )
    result = diagnose()
    assert result["success"]
    assert next(c for c in result["checks"] if c["name"] == "mcp")["status"] == "warning"


def test_provider_probe_is_explicit(monkeypatch, tmp_path):
    monkeypatch.setenv("GLFI_PRESET_DIR", str(tmp_path))
    search = Mock(return_value=[])
    monkeypatch.setattr("fli.search.SearchFlights.search", search)
    result = diagnose(check_provider=True)
    assert result["success"]
    assert search.call_count == 1
    assert next(c for c in result["checks"] if c["name"] == "provider")["status"] == "ok"
