"""
conftest.py - pytest configuration and shared fixtures.

Workaround: Python 3.13 on Windows wraps sys.stdout/stderr in _Py3Utf8Output,
which causes "Bad file descriptor" OSErrors during pytest teardown. Replacing
with a standard io.TextIOWrapper before pytest captures avoids this.
"""
import io
import sys


def _fix_py313_streams() -> None:
    if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and not isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


_fix_py313_streams()
