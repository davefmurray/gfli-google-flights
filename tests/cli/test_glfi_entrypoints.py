"""Exercise installed GLFI entry points, not only the Typer app object."""

import os
import subprocess
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

import pytest


def test_only_glfi_console_scripts_are_registered():
    scripts = {
        entry.name
        for entry in distribution("glfi").entry_points
        if entry.group == "console_scripts"
    }
    assert scripts == {"glfi", "glfi-mcp", "glfi-mcp-http"}


@pytest.mark.parametrize("args", [[], ["--help"], ["--version"], ["airports", "Jacksonville"]])
def test_installed_cli(args):
    command = str(Path(sysconfig.get_path("scripts")) / "glfi")
    result = subprocess.run(
        [command, *args],
        capture_output=True,
        text=True,
        timeout=20,
        env={**os.environ, "NO_COLOR": "1"},
    )
    assert result.returncode == 0, result.stderr
    if args == ["--version"]:
        assert result.stdout.strip() == f"glfi {distribution('glfi').version}"
    elif args and args[0] == "airports":
        assert "JAX" in result.stdout
    else:
        assert "GLFI" in result.stdout
