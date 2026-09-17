#!/usr/bin/env python3
"""Standalone localhost runtime for Stream Deck Agent Cockpit.

The daemon exposes named controls only. It never accepts raw command text over
HTTP and executes configured argv arrays with shell=False.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

SEMANTIC_STATES = {
    "idle",
    "running",
    "needs_attention",
    "blocked",
    "succeeded",
    "failed",
}
COARSE_STATES = {"present", "offline", "unavailable", "unknown"}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_BODY_BYTES = 64 * 1024
MAX_GESTURE_VALUE = 100
SHELL_NAMES = {"sh", "bash", "zsh", "fish", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe"}
SHELL_FLAGS = {"-c", "/c", "-command", "-encodedcommand"}
DESTRUCTIVE_TERMS = {"interrupt", "kill", "delete", "deploy", "publish", "merge", "send", "stop", "terminate", "production", "prod"}


class CockpitError(Exception):
    """An error safe to serialize to an API client."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = int(status)
        self.code = code
        self.message = message


def expand_local(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def load_config(path: str | Path) -> Dict[str, Any]:
    config_path = Path(path).expanduser().resolve()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CockpitError(HTTPStatus.NOT_FOUND, "config_not_found", str(config_path)) from exc
    except json.JSONDecodeError as exc:
        raise CockpitError(
            HTTPStatus.BAD_REQUEST,
            "invalid_config_json",
            f"{config_path}:{exc.lineno}:{exc.colno}: {exc.msg}",
        ) from exc
    if not isinstance(data, dict) or data.get("version") != 3:
        raise CockpitError(
            HTTPStatus.BAD_REQUEST,
            "unsupported_config",
            "Expected cockpit configuration version 3",
        )
    data["_configPath"] = str(config_path)
    return data


def ensure_private_token(token_file: str | Path) -> Tuple[str, Path]:
    path = Path(expand_local(str(token_file)))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass

    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if len(token) < 24:
            raise CockpitError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "weak_token_file",
                f"Token file is empty or too short: {path}",
            )
    else:
        token = secrets.token_urlsafe(36)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return token, path


def atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(expand_local(str(path)))
        self.lock = threading.RLock()
        self.data: Dict[str, Any] = {"version": 1, "sessions": {}}
        self._load()

    def _load(self) -> None:
        with self.lock:
            if not self.path.exists():
                return
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # State is cache-like; a corrupt file must not prevent startup.
                return
            if isinstance(loaded, dict) and isinstance(loaded.get("sessions"), dict):
                self.data = loaded

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            value = self.data.get("sessions", {}).get(session_id)
            return dict(value) if isinstance(value, dict) else None

    def report(
        self,
        session_id: str,
        state: str,
        *,
        label: Optional[str],
        detail: Optional[str],
        progress: Optional[float],
        ttl: int,
        source: str = "reporter",
    ) -> Dict[str, Any]:
        now = time.time()
        record: Dict[str, Any] = {
            "state": state,
            "source": source,
            "reportedAt": now,
            "expiresAt": now + ttl,
            "ttlSeconds": ttl,
        }
        if label:
            record["label"] = label
        if detail:
            record["detail"] = detail
        if progress is not None:
            record["progress"] = progress
        with self.lock:
            sessions = self.data.setdefault("sessions", {})
            sessions[session_id] = record
            atomic_write_json(self.path, self.data)
        return dict(record)

    def clear(self, session_id: str) -> bool:
        with self.lock:
            sessions = self.data.setdefault("sessions", {})
            if not isinstance(sessions, dict) or session_id not in sessions:
                return False
            sessions.pop(session_id, None)
            atomic_write_json(self.path, self.data)
            return True


class CommandRunner:
    def __init__(self, default_timeout: float = 12.0, dry_run: bool = False):
        self.default_timeout = float(default_timeout)
        self.dry_run = bool(dry_run)

    @staticmethod
    def _normalize(command: Mapping[str, Any]) -> Tuple[list[str], Optional[str], Dict[str, str], float, bool]:
        argv_raw = command.get("argv")
        if not isinstance(argv_raw, list) or not argv_raw or not all(isinstance(v, str) for v in argv_raw):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_command", "Command argv must be a non-empty string array")
        if len(argv_raw) > 128 or any(len(v) > 4096 for v in argv_raw):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_command", "Command argv exceeds configured safety bounds")
        argv = [expand_local(v) for v in argv_raw]
        executable = Path(argv[0]).name.lower()
        early_flags = {value.lower() for value in argv[1:3]}
        if executable in SHELL_NAMES and early_flags.intersection(SHELL_FLAGS):
            raise CockpitError(
                HTTPStatus.BAD_REQUEST,
                "shell_command_rejected",
                "Shell command strings are not allowed; configure a reviewed script with fixed argv",
            )

        cwd_raw = command.get("cwd")
        cwd = expand_local(cwd_raw) if isinstance(cwd_raw, str) and cwd_raw else None

        env_raw = command.get("env", {})
        if not isinstance(env_raw, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env_raw.items()):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_command", "Command env must be a string map")
        env = {k: expand_local(v) for k, v in env_raw.items()}

        timeout = float(command.get("timeoutSeconds", 0) or 0)
        detached = bool(command.get("detached", False))
        return argv, cwd, env, timeout, detached

    def run(
        self,
        command: Mapping[str, Any],
        *,
        extra_env: Optional[Mapping[str, str]] = None,
        allow_nonzero: bool = False,
    ) -> Dict[str, Any]:
        argv, cwd, configured_env, configured_timeout, detached = self._normalize(command)
        timeout = configured_timeout or self.default_timeout
        env = os.environ.copy()
        env.update(configured_env)
        if extra_env:
            env.update({str(k): str(v) for k, v in extra_env.items()})

        if self.dry_run:
            return {
                "ok": True,
                "dryRun": True,
                "executable": Path(argv[0]).name,
                "detached": detached,
            }

        try:
            if detached:
                subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    shell=False,
                )
                return {"ok": True, "detached": True, "executable": Path(argv[0]).name}

            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise CockpitError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "executable_not_found",
                f"Configured executable is unavailable: {Path(argv[0]).name}",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CockpitError(
                HTTPStatus.GATEWAY_TIMEOUT,
                "command_timeout",
                f"Configured command exceeded {timeout:g} seconds",
            ) from exc
        except OSError as exc:
            raise CockpitError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "command_start_failed",
                f"Configured command could not start: {exc.__class__.__name__}",
            ) from exc

        result = {
            "ok": completed.returncode == 0,
            "returnCode": completed.returncode,
            "executable": Path(argv[0]).name,
            "detached": False,
        }
        if completed.returncode != 0 and not allow_nonzero:
            raise CockpitError(
                HTTPStatus.BAD_GATEWAY,
                "command_failed",
                f"Configured command exited with code {completed.returncode}",
            )
        return result


class CockpitRuntime:
    def __init__(self, config: Mapping[str, Any], *, dry_run: bool = False):
        self.config = dict(config)
        self.sessions: Mapping[str, Mapping[str, Any]] = self.config.get("sessions", {})
        self.commands: Mapping[str, Mapping[str, Any]] = self.config.get("commands", {})
        self.controls: Mapping[str, Mapping[str, Any]] = self.config.get("controls", {})
        server = self.config.get("server", {})
        self.store = StateStore(server.get("stateFile", "~/.agent-cockpit/state.json"))
        self.runner = CommandRunner(server.get("commandTimeoutSeconds", 12), dry_run=dry_run)

    def list_controls(self) -> list[Dict[str, Any]]:
        return [self.control_state(control_id) for control_id in sorted(self.controls)]

    def _probe_command(self, command: Mapping[str, Any]) -> Tuple[str, str]:
        try:
            result = self.runner.run(command, allow_nonzero=True)
        except CockpitError as exc:
            if exc.code == "executable_not_found":
                return "unavailable", "probe"
            return "unavailable", "probe"
        if result.get("dryRun"):
            return "unknown", "dry-run"
        return ("present", "probe") if result.get("returnCode") == 0 else ("offline", "probe")

    def probe_session(self, session_id: str) -> Tuple[str, str]:
        session = self.sessions.get(session_id)
        if not isinstance(session, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_session", f"Unknown session: {session_id}")
        adapter = session.get("adapter", {})
        if not isinstance(adapter, Mapping):
            return "unavailable", "adapter"
        adapter_type = adapter.get("type")
        if adapter_type == "tmux":
            target = adapter.get("target")
            if not isinstance(target, str) or not target:
                return "unavailable", "tmux"
            return self._probe_command(
                {"argv": ["tmux", "has-session", "-t", target], "timeoutSeconds": 3}
            )[0], "tmux"
        if adapter_type == "command":
            probe = adapter.get("probe")
            if not isinstance(probe, Mapping):
                return "unavailable", "probe"
            return self._probe_command(probe)
        if adapter_type == "none":
            return "unknown", "none"
        return "unavailable", "adapter"

    def session_state(self, session_id: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not isinstance(session, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_session", f"Unknown session: {session_id}")

        now = time.time()
        report = self.store.get(session_id)
        if report and float(report.get("expiresAt", 0)) > now:
            result: Dict[str, Any] = {
                "sessionId": session_id,
                "label": session.get("label", session_id),
                "state": report.get("state", "unknown"),
                "semantic": True,
                "evidenceTier": "reported",
                "source": report.get("source", "reporter"),
                "reportedAt": report.get("reportedAt"),
                "expiresAt": report.get("expiresAt"),
            }
            for key in ("label", "detail", "progress"):
                if key in report:
                    result[key] = report[key]
            return result

        coarse_state, source = self.probe_session(session_id)
        result = {
            "sessionId": session_id,
            "label": session.get("label", session_id),
            "state": coarse_state,
            "semantic": False,
            "evidenceTier": "coarse" if coarse_state in {"present", "offline"} else "unknown",
            "source": source,
        }
        if report:
            result["lastReportStale"] = True
            result["lastReportedAt"] = report.get("reportedAt")
            result["lastReportedState"] = report.get("state")
        return result

    def control_state(self, control_id: str) -> Dict[str, Any]:
        control = self.controls.get(control_id)
        if not isinstance(control, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_control", f"Unknown control: {control_id}")
        kind = control.get("kind")
        base: Dict[str, Any] = {
            "controlId": control_id,
            "kind": kind,
            "title": control.get("title", control_id),
            "gestures": sorted((control.get("gestures") or {}).keys()),
        }
        if kind == "session":
            session_id = control.get("session")
            if not isinstance(session_id, str):
                raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_control", f"Session control has no session: {control_id}")
            base["session"] = self.session_state(session_id)
            base["state"] = base["session"]["state"]
            base["semantic"] = base["session"]["semantic"]
            base["source"] = base["session"]["source"]
        else:
            base.update({"state": "available", "semantic": False, "source": "config"})
        appearance = self.config.get("appearance", {})
        state_styles = appearance.get("states", {}) if isinstance(appearance, Mapping) else {}
        state_style = state_styles.get(base["state"], {}) if isinstance(state_styles, Mapping) else {}
        suffix = state_style.get("titleSuffix") if isinstance(state_style, Mapping) else None
        if isinstance(suffix, str) and suffix.strip():
            base["display"] = {"titleSuffix": suffix.strip()[:32]}
        return base

    def _session_command(self, session_id: str, name: str) -> Mapping[str, Any]:
        session = self.sessions.get(session_id)
        if not isinstance(session, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_session", f"Unknown session: {session_id}")
        commands = session.get("commands", {})
        command = commands.get(name) if isinstance(commands, Mapping) else None
        if not isinstance(command, Mapping):
            raise CockpitError(
                HTTPStatus.CONFLICT,
                "operation_not_configured",
                f"Session {session_id} has no configured {name} command",
            )
        return command

    def invoke(
        self,
        control_id: str,
        gesture: str,
        *,
        confirmed: bool = False,
        value: int = 0,
    ) -> Dict[str, Any]:
        control = self.controls.get(control_id)
        if not isinstance(control, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_control", f"Unknown control: {control_id}")
        gestures = control.get("gestures", {})
        binding = gestures.get(gesture) if isinstance(gestures, Mapping) else None
        if not isinstance(binding, Mapping):
            raise CockpitError(
                HTTPStatus.CONFLICT,
                "gesture_not_configured",
                f"Gesture {gesture} is not configured for {control_id}",
            )

        confirmation = binding.get("confirmation", "none")
        operation_preview = str(binding.get("operation") or "")
        command_preview = str(binding.get("command") or "")
        destructive_tokens = set(
            part for part in re.split(r"[^a-z0-9]+", f"{control_id} {operation_preview} {command_preview}".lower()) if part
        )
        requires_confirmation = confirmation in {"hold", "explicit"} or operation_preview == "interrupt" or bool(destructive_tokens.intersection(DESTRUCTIVE_TERMS))
        if requires_confirmation and not confirmed:
            raise CockpitError(
                HTTPStatus.CONFLICT,
                "confirmation_required",
                f"Gesture requires {confirmation if confirmation != 'none' else 'explicit'} confirmation",
            )

        try:
            bounded_value = int(value)
        except (TypeError, ValueError) as exc:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_value", "Gesture value must be an integer") from exc
        if abs(bounded_value) > MAX_GESTURE_VALUE:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_value", "Gesture value exceeds safety bound")
        extra_env = {
            "AGENT_COCKPIT_CONTROL_ID": control_id,
            "AGENT_COCKPIT_GESTURE": gesture,
            "AGENT_COCKPIT_VALUE": str(bounded_value),
        }

        operation = binding.get("operation")
        executed: list[Dict[str, Any]] = []

        if operation == "run":
            command_id = binding.get("command")
            command = self.commands.get(command_id) if isinstance(command_id, str) else None
            if not isinstance(command, Mapping):
                raise CockpitError(HTTPStatus.CONFLICT, "unknown_command", f"Unknown command: {command_id}")
            executed.append({"operation": "run", **self.runner.run(command, extra_env=extra_env)})
        elif control.get("kind") == "session":
            session_id = control.get("session")
            if not isinstance(session_id, str):
                raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_control", "Session control is missing session ID")
            if operation == "focus_or_launch":
                state, _ = self.probe_session(session_id)
                if state != "present":
                    executed.append(
                        {"operation": "launch", **self.runner.run(self._session_command(session_id, "launch"), extra_env=extra_env)}
                    )
                try:
                    focus_command = self._session_command(session_id, "focus")
                except CockpitError as exc:
                    if state == "present" or not executed:
                        raise
                    if exc.code != "operation_not_configured":
                        raise
                else:
                    executed.append({"operation": "focus", **self.runner.run(focus_command, extra_env=extra_env)})
            elif operation in {"focus", "launch", "resume", "interrupt"}:
                executed.append(
                    {
                        "operation": str(operation),
                        **self.runner.run(self._session_command(session_id, str(operation)), extra_env=extra_env),
                    }
                )
            else:
                raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_operation", f"Unsupported session operation: {operation}")
        else:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_operation", f"Unsupported operation: {operation}")

        return {
            "ok": True,
            "controlId": control_id,
            "gesture": gesture,
            "executed": executed,
            "invokedAt": time.time(),
        }

    def report(self, session_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not isinstance(session, Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_session", f"Unknown session: {session_id}")
        state = payload.get("state")
        if state not in SEMANTIC_STATES:
            raise CockpitError(
                HTTPStatus.BAD_REQUEST,
                "invalid_state",
                f"State must be one of: {', '.join(sorted(SEMANTIC_STATES))}",
            )

        label = payload.get("label")
        detail = payload.get("detail")
        if label is not None and (not isinstance(label, str) or len(label) > 120):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_label", "Label must be a string of at most 120 characters")
        if detail is not None and (not isinstance(detail, str) or len(detail) > 500):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_detail", "Detail must be a string of at most 500 characters")

        progress = payload.get("progress")
        if progress is not None:
            if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not 0 <= float(progress) <= 100:
                raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_progress", "Progress must be between 0 and 100")
            progress = float(progress)

        configured_ttl = ((session.get("progress") or {}).get("staleAfterSeconds", 180))
        ttl_raw = payload.get("ttl", configured_ttl)
        try:
            ttl = int(ttl_raw)
        except (TypeError, ValueError) as exc:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_ttl", "TTL must be an integer") from exc
        if not 5 <= ttl <= 86400:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_ttl", "TTL must be between 5 and 86400 seconds")

        record = self.store.report(
            session_id,
            str(state),
            label=label,
            detail=detail,
            progress=progress,
            ttl=ttl,
            source=str(payload.get("source") or "reporter")[:64],
        )
        return {"ok": True, "sessionId": session_id, "report": record}

    def clear_report(self, session_id: str) -> Dict[str, Any]:
        if not isinstance(self.sessions.get(session_id), Mapping):
            raise CockpitError(HTTPStatus.NOT_FOUND, "unknown_session", f"Unknown session: {session_id}")
        return {"ok": True, "sessionId": session_id, "cleared": self.store.clear(session_id)}


class CockpitHandler(BaseHTTPRequestHandler):
    runtime: CockpitRuntime
    token: str
    server_version = "AgentCockpit/3"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        return hmac.compare_digest(header[len(prefix):].strip(), self.token)

    def _require_auth(self) -> None:
        if not self._authorized():
            raise CockpitError(HTTPStatus.UNAUTHORIZED, "unauthorized", "A valid local bearer token is required")

    def _read_json(self) -> Dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_content_length", "Invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise CockpitError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large", "Request body exceeds safety bound")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body must be a JSON object") from exc
        if not isinstance(payload, dict):
            raise CockpitError(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body must be a JSON object")
        return payload

    def _segments(self) -> list[str]:
        path = urlparse(self.path).path
        return [unquote(part) for part in path.split("/") if part]

    def do_GET(self) -> None:  # noqa: N802
        try:
            parts = self._segments()
            if parts == ["v1", "health"]:
                self._send(HTTPStatus.OK, {"ok": True, "version": 3, "time": time.time()})
                return
            self._require_auth()
            if parts == ["v1", "controls"]:
                self._send(HTTPStatus.OK, {"ok": True, "controls": self.runtime.list_controls()})
                return
            if len(parts) == 3 and parts[:2] == ["v1", "controls"]:
                self._send(HTTPStatus.OK, {"ok": True, "control": self.runtime.control_state(parts[2])})
                return
            if len(parts) == 3 and parts[:2] == ["v1", "sessions"]:
                self._send(HTTPStatus.OK, {"ok": True, "session": self.runtime.session_state(parts[2])})
                return
            raise CockpitError(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except CockpitError as exc:
            self._send(exc.status, {"ok": False, "error": {"code": exc.code, "message": exc.message}})
        except Exception:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": {"code": "internal_error", "message": "Internal error"}})

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._require_auth()
            parts = self._segments()
            payload = self._read_json()
            if len(parts) == 4 and parts[:2] == ["v1", "controls"] and parts[3] == "invoke":
                result = self.runtime.invoke(
                    parts[2],
                    str(payload.get("gesture", "tap")),
                    confirmed=bool(payload.get("confirmed", False)),
                    value=payload.get("value", 0),
                )
                self._send(HTTPStatus.OK, result)
                return
            if len(parts) == 4 and parts[:2] == ["v1", "sessions"] and parts[3] == "report":
                self._send(HTTPStatus.OK, self.runtime.report(parts[2], payload))
                return
            raise CockpitError(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except CockpitError as exc:
            self._send(exc.status, {"ok": False, "error": {"code": exc.code, "message": exc.message}})
        except Exception:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": {"code": "internal_error", "message": "Internal error"}})

    def do_DELETE(self) -> None:  # noqa: N802
        try:
            self._require_auth()
            parts = self._segments()
            if len(parts) == 4 and parts[:2] == ["v1", "sessions"] and parts[3] == "report":
                self._send(HTTPStatus.OK, self.runtime.clear_report(parts[2]))
                return
            raise CockpitError(HTTPStatus.NOT_FOUND, "not_found", "Unknown endpoint")
        except CockpitError as exc:
            self._send(exc.status, {"ok": False, "error": {"code": exc.code, "message": exc.message}})
        except Exception:
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": {"code": "internal_error", "message": "Internal error"}})


def create_server(runtime: CockpitRuntime, host: str, port: int, token: str) -> ThreadingHTTPServer:
    class BoundHandler(CockpitHandler):
        pass

    BoundHandler.runtime = runtime
    BoundHandler.token = token
    server = ThreadingHTTPServer((host, port), BoundHandler)
    server.daemon_threads = True
    return server


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="~/.agent-cockpit/cockpit.json")
    parser.add_argument("--host", help="Override configured host")
    parser.add_argument("--port", type=int, help="Override configured port")
    parser.add_argument("--allow-nonlocal", action="store_true", help="Allow a non-loopback bind after explicit review")
    parser.add_argument("--dry-run", action="store_true", help="Resolve operations without executing configured commands")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        server_config = config.get("server", {})
        host = args.host or server_config.get("host", "127.0.0.1")
        port = args.port if args.port is not None else int(server_config.get("port", 39393))
        if host not in LOOPBACK_HOSTS and not args.allow_nonlocal:
            raise CockpitError(
                HTTPStatus.BAD_REQUEST,
                "nonlocal_bind_rejected",
                "Refusing non-loopback bind without --allow-nonlocal",
            )
        token, token_path = ensure_private_token(server_config.get("tokenFile", "~/.agent-cockpit/token"))
        runtime = CockpitRuntime(config, dry_run=args.dry_run)
        server = create_server(runtime, host, port, token)
    except CockpitError as exc:
        print(f"error[{exc.code}]: {exc.message}", file=sys.stderr)
        return 2

    stopping = threading.Event()

    def stop(_signum: int, _frame: Any) -> None:
        if not stopping.is_set():
            stopping.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(signum, stop)
        except (ValueError, OSError):
            pass

    actual_host, actual_port = server.server_address[:2]
    print(f"Agent Cockpit daemon listening on http://{actual_host}:{actual_port}")
    print(f"Token file: {token_path}")
    print(f"Mode: {'dry-run' if args.dry_run else 'live'}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
