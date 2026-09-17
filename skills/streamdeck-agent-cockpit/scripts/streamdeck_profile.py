#!/usr/bin/env python3
"""Safely add owned launcher or Agent Cockpit actions on one Stream Deck v3 page.

This is deliberately narrow: it never edits the profile registry, page list, or
any page other than the explicit page manifest supplied by the caller. The
Stream Deck application must be closed before running it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

OPEN_ACTION_UUID = "com.elgato.streamdeck.system.open"
COCKPIT_PLUGIN_UUID = "com.cskwork.agent-cockpit"
COCKPIT_ACTION_UUID = f"{COCKPIT_PLUGIN_UUID}.control"


def parse_control(value: str) -> Tuple[str, Path, str]:
    try:
        coordinate, payload = value.split("=", 1)
        launcher, title = payload.rsplit("|", 1)
        row, column = coordinate.split(",", 1)
        if not (row.isdigit() and column.isdigit()):
            raise ValueError
        title = title.strip()
        if not title:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "control must be ROW,COLUMN=LAUNCHER|TITLE"
        ) from exc
    return f"{int(row)},{int(column)}", Path(launcher).expanduser().resolve(), title


def parse_plugin_control(value: str) -> Tuple[str, str, str]:
    try:
        coordinate, payload = value.split("=", 1)
        control_id, title = payload.rsplit("|", 1)
        row, column = coordinate.split(",", 1)
        control_id = control_id.strip()
        title = title.strip()
        if not (row.isdigit() and column.isdigit()):
            raise ValueError
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,127}", control_id):
            raise ValueError
        if not title:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "plugin control must be ROW,COLUMN=CONTROL_ID|TITLE"
        ) from exc
    return f"{int(row)},{int(column)}", control_id, title


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-root", required=True, type=Path)
    parser.add_argument("--profile-name", default="Default Profile")
    parser.add_argument("--page-id", required=True, help="Existing page UUID")
    parser.add_argument(
        "--control",
        action="append",
        default=[],
        type=parse_control,
        help="ROW,COLUMN=LAUNCHER|TITLE; repeat for each action",
    )
    parser.add_argument(
        "--plugin-control",
        action="append",
        default=[],
        type=parse_plugin_control,
        help="ROW,COLUMN=CONTROL_ID|TITLE; add an owned Agent Cockpit action",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("/private/tmp/streamdeck-agent-cockpit-profile-backups"),
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace only owned Agent Cockpit or built-in Open actions at requested keys",
    )
    args = parser.parse_args(argv)
    if not args.control and not args.plugin_control:
        parser.error("at least one --control or --plugin-control is required")
    return args


def keyed_controller(manifest: Dict[str, Any]) -> Dict[str, Any]:
    controllers = manifest.get("Controllers")
    if not isinstance(controllers, list):
        raise RuntimeError("profile manifest has no Controllers array")
    for controller in controllers:
        if isinstance(controller, dict) and controller.get("Type") == "Keypad":
            return controller
    raise RuntimeError("profile manifest has no Keypad controller")


def open_action(launcher: Path, title: str) -> Dict[str, Any]:
    if not launcher.is_file():
        raise RuntimeError(f"launcher does not exist: {launcher}")
    return {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": "Open",
        "Resources": None,
        "Settings": {"path": json.dumps(str(launcher))},
        "State": 0,
        "States": [
            {
                "FontFamily": "",
                "FontSize": 11,
                "FontStyle": "",
                "FontUnderline": False,
                "OutlineThickness": 2,
                "ShowTitle": True,
                "Title": title,
                "TitleAlignment": "bottom",
                "TitleColor": "#ffffff",
            }
        ],
        "UUID": OPEN_ACTION_UUID,
    }


def plugin_action(control_id: str, title: str) -> Dict[str, Any]:
    return {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": "Agent Cockpit Control",
        "Plugin": {
            "Name": "Agent Cockpit",
            "UUID": COCKPIT_PLUGIN_UUID,
            "Version": "0.1.0.0",
        },
        "Resources": None,
        "Settings": {
            "controlId": control_id,
            "daemonUrl": "http://127.0.0.1:39393",
            "tokenFile": "~/.agent-cockpit/token",
            "holdMs": 650,
            "pollMs": 1500,
        },
        "State": 0,
        "States": [
            {
                "FontFamily": "",
                "FontSize": 12,
                "FontStyle": "",
                "FontUnderline": False,
                "OutlineThickness": 2,
                "ShowTitle": False,
                "Title": title,
                "TitleAlignment": "middle",
                "TitleColor": "#ffffff",
            }
        ],
        "UUID": COCKPIT_ACTION_UUID,
    }


def backup_named_profile(profile_root: Path, backup_dir: Path, profile_name: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", profile_name).strip(".-") or "profile"
    destination = backup_dir.expanduser().resolve() / f"{safe_name}-{stamp}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"backup already exists: {destination}")
    shutil.copytree(profile_root, destination)
    return destination


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    profile_root = args.profile_root.expanduser().resolve()
    if not profile_root.is_dir():
        print(f"error: profile root does not exist: {profile_root}", file=sys.stderr)
        return 2

    try:
        uuid.UUID(args.page_id)
    except ValueError:
        print(f"error: page id is not a UUID: {args.page_id}", file=sys.stderr)
        return 2

    profiles_dir = profile_root / "Profiles"
    page_dir = profiles_dir / args.page_id
    if page_dir.resolve().parent != profiles_dir.resolve():
        print(f"error: page id escapes the profile: {args.page_id}", file=sys.stderr)
        return 2
    page_manifest_path = page_dir / "manifest.json"
    if not page_manifest_path.is_file():
        print(f"error: page manifest does not exist: {page_manifest_path}", file=sys.stderr)
        return 2

    try:
        root_manifest_path = profile_root / "manifest.json"
        root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
        if root_manifest.get("Name") != args.profile_name:
            raise RuntimeError(
                f"profile name mismatch: expected {args.profile_name!r}, "
                f"found {root_manifest.get('Name')!r}"
            )
        manifest = json.loads(page_manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise RuntimeError("page manifest is not a JSON object")
        controller = keyed_controller(manifest)
        actions = controller.get("Actions")
        if actions is None:
            actions = {}
            controller["Actions"] = actions
        if not isinstance(actions, dict):
            raise RuntimeError("page Keypad Actions is not an object")

        controls: Iterable[Tuple[str, Path, str]] = args.control
        parsed_open = list(controls)
        parsed_plugin = list(args.plugin_control)
        parsed = [
            ("open", coordinate, launcher, title)
            for coordinate, launcher, title in parsed_open
        ] + [
            ("plugin", coordinate, control_id, title)
            for coordinate, control_id, title in parsed_plugin
        ]
        seen_coordinates = set()
        for kind, coordinate, payload, _title in parsed:
            if coordinate in seen_coordinates:
                raise RuntimeError(f"duplicate page key: {coordinate}")
            seen_coordinates.add(coordinate)
            if coordinate in actions:
                if not args.replace:
                    raise RuntimeError(f"page key is already occupied: {coordinate}")
                existing = actions[coordinate]
                existing_uuid = existing.get("UUID") if isinstance(existing, dict) else None
                allowed = {OPEN_ACTION_UUID} if kind == "open" else {OPEN_ACTION_UUID, COCKPIT_ACTION_UUID}
                if existing_uuid not in allowed:
                    raise RuntimeError(
                        f"page key is occupied by an unrelated action: {coordinate}"
                    )
            if kind == "open" and not payload.is_file():
                raise RuntimeError(f"launcher does not exist: {payload}")

        backup = backup_named_profile(profile_root, args.backup_dir, args.profile_name)
        for kind, coordinate, payload, title in parsed:
            actions[coordinate] = (
                open_action(payload, title)
                if kind == "open"
                else plugin_action(payload, title)
            )

        temporary = page_manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, page_manifest_path)
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "ok": True,
        "pageManifest": str(page_manifest_path),
        "backup": str(backup),
        "added": [coordinate for _kind, coordinate, _payload, _title in parsed],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
