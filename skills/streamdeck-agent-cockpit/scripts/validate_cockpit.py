#!/usr/bin/env python3
"""Validate Stream Deck Agent Cockpit configuration version 3.

This validator is intentionally dependency-free. The JSON Schema is supplied
for editors; this script adds security and cross-reference checks that schema
alone cannot express.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,95}$")
TMUX_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
ENV_REF_RE = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
OPERATIONS = {"focus_or_launch", "focus", "launch", "resume", "interrupt", "run"}
GESTURES = {"tap", "longPress", "dialPress", "dialLeft", "dialRight"}
CONFIRMATIONS = {"none", "hold", "explicit"}
SEMANTIC_SOURCES = {"reporter", "adapter"}
PROGRESS_SOURCES = SEMANTIC_SOURCES | {"coarse", "none"}
SHELL_NAMES = {"sh", "bash", "zsh", "fish", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe"}
SHELL_FLAGS = {"-c", "/c", "-command", "-encodedcommand"}
SECRET_PATTERNS = [
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}", re.I),
    re.compile(r"\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[=:]\s*[^$\s{][^\s]{5,}", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
]
DESTRUCTIVE_WORDS = {"interrupt", "kill", "delete", "deploy", "publish", "merge", "send", "stop", "terminate", "production", "prod"}
PHYSICAL_KEYS = {"row", "column", "coordinates", "keyindex", "physicalkey", "physicalposition"}


class Findings:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")


def is_secret_literal(value: str) -> bool:
    if ENV_REF_RE.fullmatch(value.strip()):
        return False
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def walk_keys(value: Any, path: str = "$", findings: Optional[Findings] = None) -> None:
    if findings is None:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            child_path = f"{path}.{key}"
            if lowered in PHYSICAL_KEYS:
                findings.error(child_path, "physical key coordinates do not belong in configuration v3")
            walk_keys(child, child_path, findings)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_keys(child, f"{path}[{index}]", findings)


def validate_id(value: Any, path: str, findings: Findings) -> bool:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        findings.error(path, "must match ^[a-z0-9][a-z0-9._-]{1,95}$")
        return False
    return True


def validate_command(
    command: Any,
    path: str,
    findings: Findings,
    *,
    allow_shell: bool,
) -> None:
    if not isinstance(command, dict):
        findings.error(path, "must be an object")
        return
    allowed = {"argv", "cwd", "env", "timeoutSeconds", "detached"}
    for key in command:
        if key not in allowed:
            findings.error(f"{path}.{key}", "unknown command property")

    argv = command.get("argv")
    if not isinstance(argv, list) or not argv:
        findings.error(f"{path}.argv", "must be a non-empty array")
        return
    if len(argv) > 128:
        findings.error(f"{path}.argv", "must contain at most 128 arguments")
    for index, arg in enumerate(argv):
        arg_path = f"{path}.argv[{index}]"
        if not isinstance(arg, str):
            findings.error(arg_path, "must be a string")
        elif len(arg) > 4096:
            findings.error(arg_path, "must be at most 4096 characters")
        elif is_secret_literal(arg):
            findings.error(arg_path, "appears to contain a literal credential; use an environment/keychain reference")

    if argv and isinstance(argv[0], str):
        executable = Path(argv[0]).name.lower()
        flags = {str(v).lower() for v in argv[1:3] if isinstance(v, str)}
        if executable in SHELL_NAMES and flags.intersection(SHELL_FLAGS) and not allow_shell:
            findings.error(path, "shell command strings are rejected; use a reviewed script plus fixed argv")

    cwd = command.get("cwd")
    if cwd is not None and not isinstance(cwd, str):
        findings.error(f"{path}.cwd", "must be a string")

    env = command.get("env", {})
    if not isinstance(env, dict):
        findings.error(f"{path}.env", "must be an object")
    else:
        for key, value in env.items():
            env_path = f"{path}.env.{key}"
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                findings.error(env_path, "invalid environment variable name")
            if not isinstance(value, str):
                findings.error(env_path, "must be a string")
            elif any(word in str(key).lower() for word in ("key", "token", "secret", "password")) and not ENV_REF_RE.fullmatch(value):
                findings.error(env_path, "credential-like environment values must use ${ENV_VAR} references")
            elif is_secret_literal(value):
                findings.error(env_path, "appears to contain a literal credential")

    timeout = command.get("timeoutSeconds")
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= float(timeout) <= 300):
        findings.error(f"{path}.timeoutSeconds", "must be between 1 and 300")
    if "detached" in command and not isinstance(command["detached"], bool):
        findings.error(f"{path}.detached", "must be boolean")


def operation_is_destructive(operation: str, command_id: Optional[str]) -> bool:
    if operation == "interrupt":
        return True
    text = f"{operation} {command_id or ''}".lower().replace("_", "-")
    tokens = set(re.split(r"[^a-z0-9]+", text))
    return bool(tokens.intersection(DESTRUCTIVE_WORDS))


def validate(data: Any, *, allow_nonlocal: bool = False, allow_shell: bool = False) -> Findings:
    findings = Findings()
    if not isinstance(data, dict):
        findings.error("$", "root must be an object")
        return findings

    walk_keys(data, findings=findings)
    serialized_lower = json.dumps(data, ensure_ascii=False).lower()
    if "streamdeck-mcp" in serialized_lower or "streamdeck_mcp" in serialized_lower:
        findings.error("$", "configuration introduces a streamdeck-mcp dependency; the core runtime must be standalone")
    if '"agentdeck"' in serialized_lower:
        findings.error("$", "configuration introduces an AgentDeck runtime dependency; use a local session adapter instead")

    allowed_root = {"$schema", "version", "server", "sessions", "commands", "controls", "appearance"}
    for key in data:
        if key not in allowed_root:
            findings.error(f"$.{key}", "unknown root property")

    if data.get("version") != 3:
        findings.error("$.version", "must equal 3")

    server = data.get("server")
    if not isinstance(server, dict):
        findings.error("$.server", "must be an object")
    else:
        host = server.get("host")
        if not isinstance(host, str):
            findings.error("$.server.host", "must be a string")
        elif host not in LOOPBACK and not allow_nonlocal:
            findings.error("$.server.host", "must be loopback unless --allow-nonlocal is explicitly used")
        port = server.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
            findings.error("$.server.port", "must be an integer from 1024 through 65535")
        for name in ("tokenFile", "stateFile"):
            value = server.get(name)
            if not isinstance(value, str) or not value.strip():
                findings.error(f"$.server.{name}", "must be a non-empty path string")
        timeout = server.get("commandTimeoutSeconds", 12)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= float(timeout) <= 300:
            findings.error("$.server.commandTimeoutSeconds", "must be between 1 and 300")

    commands = data.get("commands")
    if not isinstance(commands, dict):
        findings.error("$.commands", "must be an object")
        commands = {}
    else:
        for command_id, command in commands.items():
            if validate_id(command_id, f"$.commands.{command_id}", findings):
                validate_command(command, f"$.commands.{command_id}", findings, allow_shell=allow_shell)

    sessions = data.get("sessions")
    if not isinstance(sessions, dict):
        findings.error("$.sessions", "must be an object")
        sessions = {}
    else:
        for session_id, session in sessions.items():
            path = f"$.sessions.{session_id}"
            validate_id(session_id, path, findings)
            if not isinstance(session, dict):
                findings.error(path, "must be an object")
                continue
            allowed = {"label", "agent", "adapter", "commands", "progress"}
            for key in session:
                if key not in allowed:
                    findings.error(f"{path}.{key}", "unknown session property")
            if not isinstance(session.get("label"), str) or not 1 <= len(session.get("label", "")) <= 64:
                findings.error(f"{path}.label", "must be a string of 1 through 64 characters")
            if not isinstance(session.get("agent"), str) or not session.get("agent"):
                findings.error(f"{path}.agent", "must be a non-empty string")

            adapter = session.get("adapter")
            if not isinstance(adapter, dict):
                findings.error(f"{path}.adapter", "must be an object")
            else:
                adapter_type = adapter.get("type")
                if adapter_type == "tmux":
                    target = adapter.get("target")
                    if not isinstance(target, str) or not TMUX_RE.fullmatch(target):
                        findings.error(f"{path}.adapter.target", "invalid tmux target")
                elif adapter_type == "command":
                    validate_command(adapter.get("probe"), f"{path}.adapter.probe", findings, allow_shell=allow_shell)
                elif adapter_type != "none":
                    findings.error(f"{path}.adapter.type", "must be tmux, command, or none")

            session_commands = session.get("commands")
            if not isinstance(session_commands, dict):
                findings.error(f"{path}.commands", "must be an object")
            else:
                for name, command in session_commands.items():
                    if name not in {"launch", "focus", "resume", "interrupt"}:
                        findings.error(f"{path}.commands.{name}", "unknown session command")
                    else:
                        validate_command(command, f"{path}.commands.{name}", findings, allow_shell=allow_shell)

            progress = session.get("progress")
            if not isinstance(progress, dict):
                findings.error(f"{path}.progress", "must be an object")
            else:
                source = progress.get("source")
                if source not in PROGRESS_SOURCES:
                    findings.error(f"{path}.progress.source", f"must be one of {sorted(PROGRESS_SOURCES)}")
                stale = progress.get("staleAfterSeconds")
                if isinstance(stale, bool) or not isinstance(stale, int) or not 5 <= stale <= 86400:
                    findings.error(f"{path}.progress.staleAfterSeconds", "must be an integer from 5 through 86400")
                if source == "coarse":
                    findings.warn(f"{path}.progress.source", "coarse state may show only present/offline/unavailable")

    controls = data.get("controls")
    if not isinstance(controls, dict) or not controls:
        findings.error("$.controls", "must be a non-empty object")
        controls = {}
    else:
        for control_id, control in controls.items():
            path = f"$.controls.{control_id}"
            validate_id(control_id, path, findings)
            if not isinstance(control, dict):
                findings.error(path, "must be an object")
                continue
            allowed = {"kind", "session", "title", "gestures"}
            for key in control:
                if key not in allowed:
                    findings.error(f"{path}.{key}", "unknown control property")
            kind = control.get("kind")
            if kind not in {"session", "command"}:
                findings.error(f"{path}.kind", "must be session or command")
            session_id = control.get("session")
            if kind == "session":
                if not isinstance(session_id, str) or session_id not in sessions:
                    findings.error(f"{path}.session", "must reference a configured session")
            title = control.get("title")
            if not isinstance(title, str) or not 1 <= len(title) <= 64:
                findings.error(f"{path}.title", "must be a string of 1 through 64 characters")
            gestures = control.get("gestures")
            if not isinstance(gestures, dict) or not gestures:
                findings.error(f"{path}.gestures", "must be a non-empty object")
                continue
            for gesture, binding in gestures.items():
                bind_path = f"{path}.gestures.{gesture}"
                if gesture not in GESTURES:
                    findings.error(bind_path, f"unsupported gesture; choose from {sorted(GESTURES)}")
                if not isinstance(binding, dict):
                    findings.error(bind_path, "must be an object")
                    continue
                for key in binding:
                    if key not in {"operation", "command", "confirmation"}:
                        findings.error(f"{bind_path}.{key}", "unknown operation property")
                operation = binding.get("operation")
                if operation not in OPERATIONS:
                    findings.error(f"{bind_path}.operation", f"must be one of {sorted(OPERATIONS)}")
                    continue
                command_id = binding.get("command")
                if operation == "run":
                    if not isinstance(command_id, str) or command_id not in commands:
                        findings.error(f"{bind_path}.command", "run must reference a configured command")
                elif command_id is not None:
                    findings.error(f"{bind_path}.command", "command is valid only for operation=run")
                if kind != "session" and operation != "run":
                    findings.error(bind_path, "non-session controls may use operation=run only")
                confirmation = binding.get("confirmation", "none")
                if confirmation not in CONFIRMATIONS:
                    findings.error(f"{bind_path}.confirmation", f"must be one of {sorted(CONFIRMATIONS)}")
                if operation_is_destructive(str(operation), command_id if isinstance(command_id, str) else None):
                    if confirmation not in {"hold", "explicit"}:
                        findings.error(bind_path, "destructive operation requires hold or explicit confirmation")
                    if gesture == "tap":
                        findings.warn(bind_path, "destructive operation is mapped to tap; prefer longPress")

            if kind == "session" and isinstance(session_id, str) and session_id in sessions:
                session_commands = sessions[session_id].get("commands", {}) if isinstance(sessions[session_id], dict) else {}
                tap = gestures.get("tap") if isinstance(gestures, dict) else None
                if isinstance(tap, dict) and tap.get("operation") == "focus_or_launch":
                    if "launch" not in session_commands:
                        findings.error(path, "focus_or_launch requires the session launch command")
                    if "focus" not in session_commands:
                        findings.warn(path, "focus_or_launch has no focus command; launch may not foreground a terminal")

    appearance = data.get("appearance")
    if appearance is not None and not isinstance(appearance, dict):
        findings.error("$.appearance", "must be an object")

    return findings


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--allow-nonlocal", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    path = Path(os.path.expandvars(os.path.expanduser(args.config)))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: config not found: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {path}:{exc.lineno}:{exc.colno}: {exc.msg}", file=sys.stderr)
        return 2

    findings = validate(data, allow_nonlocal=args.allow_nonlocal, allow_shell=False)
    if args.json_output:
        print(json.dumps({"valid": not findings.errors, "errors": findings.errors, "warnings": findings.warnings}, indent=2))
    else:
        for item in findings.errors:
            print(f"ERROR: {item}")
        for item in findings.warnings:
            print(f"WARN:  {item}")
        if not findings.errors:
            print(f"VALID: {path} ({len(findings.warnings)} warning(s))")
        else:
            print(f"INVALID: {path} ({len(findings.errors)} error(s), {len(findings.warnings)} warning(s))")
    return 1 if findings.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
