"""Invalid numeric timeout settings cannot disable bounded HTTP requests."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1", "nope"])
def test_invalid_timeout(value):
    result = subprocess.run(
        [sys.executable, "-c", "import fli.search.client"],
        env={**os.environ, "GFLI_TIMEOUT": value},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "GFLI_TIMEOUT" in result.stderr
