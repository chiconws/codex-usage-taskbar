from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RateLimitSnapshot
from .normalizer import normalize_account, normalize_rate_limits


class CodexAppServerError(RuntimeError):
    """A recoverable failure while reading the Codex app-server."""


class CodexAppServerClient:
    """Read account rate limits through the locally installed Codex CLI."""

    def __init__(
        self,
        command: Sequence[str] | str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._command = command
        self.timeout = timeout

    def set_command(self, command: Sequence[str] | str | None) -> None:
        self._command = command

    def read_rate_limits(self) -> RateLimitSnapshot:
        return self.read_usage()

    def read_usage(self) -> RateLimitSnapshot:
        command = self._resolve_command()
        try:
            process = subprocess.Popen(
                [*command, "app-server", "-c", 'service_tier="flex"'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise CodexAppServerError("Codex executable was not found") from exc
        except OSError as exc:
            raise CodexAppServerError(f"Could not start Codex app-server: {exc}") from exc

        lines: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(
            target=_read_lines,
            args=(process.stdout, lines),
            daemon=True,
        )
        reader.start()

        try:
            self._send(
                process,
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": "codex-usage-taskbar",
                            "version": "0.1.0",
                        },
                        "capabilities": {},
                    },
                },
            )
            self._wait_for_response(lines, 1)
            self._send(process, {"method": "initialized"})
            try:
                self._send(process, {"id": 2, "method": "account/read", "params": {}})
                account_payload = self._wait_for_response(lines, 2)
            except CodexAppServerError:
                account_payload = None
            self._send(
                process, {"id": 3, "method": "account/rateLimits/read", "params": None}
            )
            result = self._wait_for_response(lines, 3)
            if not isinstance(result, Mapping):
                raise CodexAppServerError("Codex returned an invalid rate-limit response")
            snapshot = normalize_rate_limits(result, datetime.now(timezone.utc))
            return replace(snapshot, account=normalize_account(account_payload or {}))
        except CodexAppServerError:
            raise
        except (BrokenPipeError, OSError) as exc:
            raise CodexAppServerError(f"Codex app-server stopped unexpectedly: {exc}") from exc
        finally:
            _close_process(process)

    def _resolve_command(self) -> list[str]:
        if self._command is not None:
            if isinstance(self._command, str):
                return [self._command]
            return list(self._command)

        executable = shutil.which("codex") or shutil.which("codex.cmd")
        if executable is None:
            raise CodexAppServerError("Codex executable was not found")
        return _wrap_windows_script(executable)

    def _send(self, process: subprocess.Popen[str], message: Mapping[str, Any]) -> None:
        if process.stdin is None:
            raise CodexAppServerError("Codex app-server stdin is unavailable")
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    def _wait_for_response(
        self, lines: queue.Queue[str | None], request_id: int
    ) -> Mapping[str, Any]:
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CodexAppServerError("Codex app-server request timed out")
            try:
                line = lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise CodexAppServerError("Codex app-server request timed out") from exc
            if line is None:
                raise CodexAppServerError("Codex app-server exited before responding")
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CodexAppServerError("Codex app-server returned malformed JSON") from exc
            if not isinstance(message, Mapping) or message.get("id") != request_id:
                continue
            error = message.get("error")
            if isinstance(error, Mapping):
                detail = error.get("message")
                raise CodexAppServerError(str(detail or "Codex app-server request failed"))
            result = message.get("result")
            if not isinstance(result, Mapping):
                raise CodexAppServerError("Codex app-server returned an invalid response")
            return result


def _read_lines(stream: Any, lines: queue.Queue[str | None]) -> None:
    try:
        for line in stream:
            lines.put(line)
    finally:
        lines.put(None)


def _close_process(process: subprocess.Popen[str]) -> None:
    if process.stdin is not None:
        try:
            process.stdin.close()
        except OSError:
            pass
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)


def _wrap_windows_script(executable: str) -> list[str]:
    suffix = Path(executable).suffix.lower()
    if os.name != "nt" or suffix not in {".cmd", ".bat", ".ps1"}:
        return [executable]
    if suffix == ".ps1":
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", executable]
    return ["cmd.exe", "/d", "/s", "/c", executable]
