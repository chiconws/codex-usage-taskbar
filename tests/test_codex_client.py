from __future__ import annotations

import sys
import subprocess
from pathlib import Path

import pytest

from codex_usage_taskbar.codex_client import CodexAppServerClient, CodexAppServerError


FAKE_SERVER = Path(__file__).parent / "support" / "fake_app_server.py"


def make_client(mode: str, timeout: float = 1.0) -> CodexAppServerClient:
    return CodexAppServerClient(
        command=[sys.executable, str(FAKE_SERVER), mode],
        timeout=timeout,
    )


def test_client_completes_handshake_and_reads_rate_limits():
    snapshot = make_client("success").read_rate_limits()

    assert [window.label for window in snapshot.windows] == ["5 hours", "Weekly"]
    assert [window.remaining_percent for window in snapshot.windows] == [38, 74]


def test_client_reads_account_metadata_with_usage():
    snapshot = make_client("success").read_usage()

    assert snapshot.account is not None
    assert snapshot.account.email == "codex@example.com"
    assert snapshot.account.plan_type == "plus"


def test_client_returns_usage_when_account_request_fails():
    snapshot = make_client("account-error").read_usage()

    assert snapshot.account is None
    assert [window.remaining_percent for window in snapshot.windows] == [38, 74]


def test_client_suppresses_console_window_when_starting_server(monkeypatch):
    original_popen = subprocess.Popen
    captured = {}

    def capturing_popen(*args, **kwargs):
        captured.update(kwargs)
        return original_popen(*args, **kwargs)

    monkeypatch.setattr("codex_usage_taskbar.codex_client.subprocess.Popen", capturing_popen)

    make_client("success").read_rate_limits()

    assert captured["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_client_surfaces_server_errors_without_leaking_payloads():
    with pytest.raises(CodexAppServerError, match="not authenticated"):
        make_client("error").read_rate_limits()


def test_client_times_out_when_server_does_not_respond():
    with pytest.raises(CodexAppServerError, match="timed out"):
        make_client("silent", timeout=0.1).read_rate_limits()


def test_client_reports_missing_executable():
    client = CodexAppServerClient(command=[str(Path("does-not-exist.exe"))])

    with pytest.raises(CodexAppServerError, match="executable was not found"):
        client.read_rate_limits()
