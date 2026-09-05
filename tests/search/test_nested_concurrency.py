"""Nested date/return expansions must not wait on their own saturated pool."""

import subprocess
import sys


def test_nested_maps_do_not_deadlock():
    # A subprocess timeout catches deadlocks without leaving blocked pytest threads.
    script = """
from fli.search._concurrency import configure_concurrency, parallel_map, shutdown_executor
configure_concurrency(2)
try:
    result = parallel_map(lambda x: parallel_map(lambda y: x + y, [1, 2]), [10, 20, 30])
    assert result == [[11, 12], [21, 22], [31, 32]]
    try:
        parallel_map(lambda x: parallel_map(lambda y: 1 / y, [0, 1]), [1, 2])
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError('Nested errors must propagate')
    assert parallel_map(lambda x: x + 1, [1, 2]) == [2, 3]
finally:
    shutdown_executor()
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
