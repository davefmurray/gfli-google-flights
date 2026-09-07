"""Smoke-test a distribution in a disposable environment, outside the source tree.

Requires uv on PATH. No Google requests, publication, or global installation.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CORE_CHECK = """
import importlib.metadata
from pathlib import Path
import fli
from fli.models import Airport, Airline
assert 'site-packages' in str(Path(fli.__file__).resolve())
assert importlib.metadata.version('gfli')
files = importlib.metadata.distribution('gfli').files
assert any(str(p).endswith('/licenses/LICENSE.txt') for p in files)
assert any(str(p).endswith('/licenses/NOTICE') for p in files)
assert Airport.TRI.name == 'TRI'
assert Airline.W4.name == 'W4'
"""

MCP_CHECK = """
import asyncio
import sysconfig
import threading
import time
from pathlib import Path
import httpx
import uvicorn
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fli.mcp.server import mcp

expected = {'search_flights', 'search_dates', 'find_airports', 'get_booking_options',
            'save_search_preset', 'run_search_preset', 'manage_search_presets'}

async def check():
    command = str(Path(sysconfig.get_path('scripts')) / 'gfli-mcp')
    async with Client(StdioTransport(command=command, args=[]), timeout=30) as client:
        assert {t.name for t in await client.list_tools()} == expected
        result = await client.call_tool('find_airports', {'query': 'Jacksonville'})
        assert not result.is_error and 'JAX' in str(result)
    server = uvicorn.Server(uvicorn.Config(mcp.http_app(), host='127.0.0.1',
                                         port=0, log_level='warning'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started:
            if time.monotonic() > deadline:
                raise RuntimeError('HTTP server failed to start')
            await asyncio.sleep(0.05)
        port = server.servers[0].sockets[0].getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        async with httpx.AsyncClient() as http:
            response = await http.get(base + '/health')
            assert response.status_code == 200
            assert response.json() == {'status': 'ok', 'service': 'gfli'}
        async with Client(base + '/mcp/', timeout=30) as client:
            assert {t.name for t in await client.list_tools()} == expected
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive(), 'HTTP server did not stop'

asyncio.run(check())
"""


def verify(artifact: Path, *, python: str, mcp: bool) -> None:
    """Install and exercise one artifact without inheriting the source import path."""
    artifact = artifact.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="gfli-install-") as temporary:
        root = Path(temporary)
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("GFLI_") or key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
                env.pop(key)
        env["HOME"] = str(root)
        env["TERM"] = "xterm-256color"

        def run(args: list[str], *, expected: int = 0) -> str:
            result = subprocess.run(
                args, cwd=root, env=env, capture_output=True, text=True, timeout=180
            )
            if result.returncode != expected:
                raise RuntimeError(
                    f"{args[0]} exited {result.returncode}:\n{result.stdout}\n{result.stderr}"
                )
            return result.stdout + result.stderr

        venv = root / "venv"
        run(["uv", "venv", "--python", python, str(venv)])
        binaries = venv / ("Scripts" if os.name == "nt" else "bin")
        executable = str(binaries / ("python.exe" if os.name == "nt" else "python"))
        requirement = f"gfli{'[mcp]' if mcp else ''} @ {artifact.as_uri()}"
        run(["uv", "pip", "install", "--python", executable, requirement])
        run(["uv", "pip", "check", "--python", executable])
        run([executable, "-c", CORE_CHECK])
        cli = str(binaries / "gfli")
        assert "gfli" in run([cli, "--version"])
        run([cli, "--help"])
        assert "JAX" in run([cli, "airports", "Jacksonville"])
        diagnostics = json.loads(run([cli, "doctor", "--json"]))
        assert diagnostics["success"]
        assert any(
            c["name"] == "provider" and c["status"] == "skipped" for c in diagnostics["checks"]
        )
        from datetime import date, timedelta

        day = (date.today() + timedelta(days=30)).isoformat()
        run(
            [
                cli,
                "save",
                "install-check",
                "--",
                "JAX",
                "JFK",
                day,
                "--no-overnight-layovers",
                "--exclude-layover",
                "ATL",
            ]
        )
        stored = json.loads(run([cli, "presets", "show", "install-check"]))
        assert stored["preset"]["filters"]["layover_restrictions"]["exclude_overnight"]
        run([cli, "presets", "delete", "install-check"])
        if mcp:
            run([executable, "-c", MCP_CHECK])
        else:
            for entry in ("gfli-mcp", "gfli-mcp-http"):
                output = run([str(binaries / entry)], expected=1)
                assert "MCP dependencies are not installed" in output
        print(f"PASS: {artifact.name}, {'MCP + CLI' if mcp else 'core CLI'}, {python}")


def main() -> None:
    """Parse the artifact and interpreter to verify."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--mcp", action="store_true")
    args = parser.parse_args()
    verify(args.artifact, python=args.python, mcp=args.mcp)


if __name__ == "__main__":
    main()
