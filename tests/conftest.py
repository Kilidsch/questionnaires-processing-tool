"""Shared fixtures for headless GUI tests.

Qt runs on the "offscreen" platform, so no window is shown. PyQt5 aborts the
process (qFatal, exit code 0xC0000409 on Windows) on an exception raised in a Qt
callback such as ``resizeEvent`` when ``sys.excepthook`` is Python's default,
and the traceback may not reach the output. ``qt_errors`` installs a hook that
records these exceptions instead, and fails the test with their tracebacks.
"""

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qt_app():
    from PyQt5 import QtWidgets as qtWid

    return qtWid.QApplication.instance() or qtWid.QApplication([])


@pytest.fixture
def qt_errors(qt_app, monkeypatch):
    """Exceptions raised in Qt callbacks during the test; the test fails if any."""
    errors = []
    monkeypatch.setattr(
        sys, "excepthook", lambda *exc: errors.append("".join(traceback.format_exception(*exc)))
    )
    yield errors
    if errors:
        pytest.fail("exception in a Qt callback:\n" + "\n".join(errors))
