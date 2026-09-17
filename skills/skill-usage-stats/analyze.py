#!/usr/bin/env python3
"""Analyze Claude Code + Codex transcripts and write an HTML skill usage report."""
from __future__ import annotations

import argparse
import json
import re
import sys
import webbrowser
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HOME = Path.home()
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
CLAUDE_GLOBAL_SKILLS = HOME / ".claude" / "skills"
CLAUDE_PLUGINS = HOME / ".claude" / "plugins"
CODEX_SKILLS = HOME / ".codex" / "skills"
CODEX_PROMPTS = HOME / ".codex" / "prompts"
CODEX_SESSIONS = HOME / ".codex" / "sessions"

SLASH_TAG_RE = re.compile(r"<command-name>([^<\s]+)</command-name>")
LEADING_SLASH_RE = re.compile(r"^\s*/([A-Za-z][A-Za-z0-9_:-]{1,60})")
SKILL_PATH_LOOSE_RE = re.compile(r"/skills/([A-Za-z0-9_.-]+)/SKILL\.md")


def posix(s: str) -> str:
    """Normalize backslashes to forward slashes so cross-platform substring/regex
    checks against logged paths behave the same on macOS, Linux, and Windows."""
    return s.replace("\\", "/")


@dataclass
class SkillEntry:
    name: str
    source: str  # claude-global | claude-project | codex-global-skill | codex-global-prompt
    path: Path
    size_bytes: int = 0
    mtime: float = 0.0
    count: int = 0
    sessions: set[str] = field(default_factory=set)
    first_used: str | None = None
    last_used: str | None = None
    description: str = ""


def read_front_matter_description(skill_md: Path) -> str:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 4)
    if end == -1:
        return ""
    fm = text[4:end]
    for line in fm.splitlines():
        line = line.strip()
        if line.lower().startswith("description:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def discover_catalog(project_dirs: Iterable[Path]) -> dict[tuple[str, str], SkillEntry]:
    catalog: dict[tuple[str, str], SkillEntry] = {}

    def add_skill_dir(root: Path, source: str) -> None:
        if not root.exists():
            return
        for child in root.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            skill_md = child / "SKILL.md"
            if not skill_md.exists():
                continue
            size = sum(p.stat().st_size for p in child.rglob("*") if p.is_file())
            entry = SkillEntry(
                name=child.name,
                source=source,
                path=child,
                size_bytes=size,
                mtime=skill_md.stat().st_mtime,
                description=read_front_matter_description(skill_md),
            )
            catalog[(source, child.name)] = entry

    def add_prompt_dir(root: Path, source: str) -> None:
        if not root.exists():
            return
        for child in root.iterdir():
            if not child.is_file() or child.suffix != ".md":
                continue
            name = child.stem
            st = child.stat()
            entry = SkillEntry(
                name=name,
                source=source,
                path=child,
                size_bytes=st.st_size,
                mtime=st.st_mtime,
                description=read_front_matter_description(child),
            )
            catalog[(source, name)] = entry

    add_skill_dir(CLAUDE_GLOBAL_SKILLS, "claude-global")
    add_skill_dir(CODEX_SKILLS, "codex-global-skill")
    add_prompt_dir(CODEX_PROMPTS, "codex-global-prompt")

    # plugins under ~/.claude/plugins/ — both marketplaces/ and cache/
    if CLAUDE_PLUGINS.exists():
        plugin_seen: set[tuple[str, str]] = set()
        for skill_md in CLAUDE_PLUGINS.rglob("skills/*/SKILL.md"):
            # parent dirs: ... / <plugin_or_marketplace> / .../ skills / <name> / SKILL.md
            name = skill_md.parent.name
            parts = skill_md.parts
            # plugin_namespace: the dir 1 level above the `skills` segment, or
            # the immediate parent of `skills` if no version segment.
            ns = ""
            try:
                skills_idx = len(parts) - 1 - parts[::-1].index("skills")
                if skills_idx >= 1:
                    candidate = parts[skills_idx - 1]
                    # if candidate looks like a version (digits, hash), step up one
                    if re.fullmatch(r"\d+\.\d+\.\d+|[0-9a-f]{8,}", candidate) and skills_idx >= 2:
                        candidate = parts[skills_idx - 2]
                    ns = candidate
            except ValueError:
                pass
            display = f"{ns}:{name}" if ns and ns != name else name
            key = ("claude-plugin", display)
            if key in plugin_seen:
                continue
            plugin_seen.add(key)
            skill_root = skill_md.parent
            size = sum(p.stat().st_size for p in skill_root.rglob("*") if p.is_file())
            catalog[key] = SkillEntry(
                name=display,
                source="claude-plugin",
                path=skill_root,
                size_bytes=size,
                mtime=skill_md.stat().st_mtime,
                description=read_front_matter_description(skill_md),
            )

    seen_project_roots: set[Path] = set()
    for cwd in project_dirs:
        # skip HOME — ~/.claude/skills is the global dir, not a project dir
        if cwd.resolve() == HOME.resolve():
            continue
        proj_skills = cwd / ".claude" / "skills"
        if proj_skills.exists() and proj_skills not in seen_project_roots:
            seen_project_roots.add(proj_skills)
            for child in proj_skills.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                skill_md = child / "SKILL.md"
                if not skill_md.exists():
                    continue
                size = sum(p.stat().st_size for p in child.rglob("*") if p.is_file())
                # tag the project for disambiguation
                key = ("claude-project", f"{cwd.name}:{child.name}")
                catalog[key] = SkillEntry(
                    name=f"{child.name}  [{cwd.name}]",
                    source="claude-project",
                    path=child,
                    size_bytes=size,
                    mtime=skill_md.stat().st_mtime,
                    description=read_front_matter_description(skill_md),
                )

    return catalog


def decode_cwd_from_project_dir(name: str) -> Path:
    # Claude Code encodes cwd in dir name by replacing `/` with `-`. We can't
    # reverse perfectly (dashes in actual paths collide), so we approximate by
    # leading `-` -> `/` and remaining as best-guess. Good enough for project
    # skill discovery.
    if name.startswith("-"):
        return Path("/" + name[1:].replace("-", "/"))
    return Path(name)


def iter_jsonl(path: Path) -> Iterable[dict]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def record_hit(
    catalog: dict[tuple[str, str], SkillEntry],
    keys: list[tuple[str, str]],
    timestamp: str | None,
    session: str | None,
) -> None:
    for key in keys:
        entry = catalog.get(key)
        if entry is None:
            continue
        entry.count += 1
        if session:
            entry.sessions.add(session)
        if timestamp:
            if not entry.first_used or timestamp < entry.first_used:
                entry.first_used = timestamp
            if not entry.last_used or timestamp > entry.last_used:
                entry.last_used = timestamp
        return  # only credit first matching source


def claude_skill_keys(name: str, catalog: dict, project_skill_names: dict[str, set[str]], cwd_name: str | None) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if cwd_name and cwd_name in project_skill_names and name in project_skill_names[cwd_name]:
        keys.append(("claude-project", f"{cwd_name}:{name}"))
    if ("claude-global", name) in catalog:
        keys.append(("claude-global", name))
    return keys


def codex_command_keys(name: str, catalog: dict) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if ("codex-global-prompt", name) in catalog:
        keys.append(("codex-global-prompt", name))
    if ("codex-global-skill", name) in catalog:
        keys.append(("codex-global-skill", name))
    return keys


def keys_from_skill_md_path(path: str, name: str, catalog: dict) -> list[tuple[str, str]]:
    """Pick the right catalog entry based on where the SKILL.md lives."""
    p = posix(path)
    if "/.claude/plugins/" in p:
        # try namespaced match first
        for (src, key) in catalog.keys():
            if src == "claude-plugin" and (key == name or key.endswith(":" + name)):
                return [(src, key)]
    if "/.codex/" in p:
        if ("codex-global-skill", name) in catalog:
            return [("codex-global-skill", name)]
    if "/.claude/" in p and "/plugins/" not in p:
        if ("claude-global", name) in catalog:
            return [("claude-global", name)]
    # fallback by name across any source
    for src in ("claude-global", "claude-plugin", "codex-global-skill", "codex-global-prompt"):
        for (s, k) in catalog.keys():
            if s == src and (k == name or k.endswith(":" + name)):
                return [(s, k)]
    return []


def scan_claude(
    catalog: dict[tuple[str, str], SkillEntry],
    since_ts: str | None,
    project_filter: str | None,
) -> tuple[int, int]:
    if not CLAUDE_PROJECTS.exists():
        return (0, 0)

    project_skill_names: dict[str, set[str]] = defaultdict(set)
    for (src, key) in catalog.keys():
        if src == "claude-project" and ":" in key:
            cwd_name, skill_name = key.split(":", 1)
            project_skill_names[cwd_name].add(skill_name)

    files = 0
    events = 0
    for proj_dir in CLAUDE_PROJECTS.iterdir():
        if not proj_dir.is_dir():
            continue
        cwd_name = proj_dir.name
        if project_filter and project_filter not in cwd_name:
            continue
        # cwd guess for project-skill matching
        cwd_guess = decode_cwd_from_project_dir(cwd_name)
        cwd_basename = cwd_guess.name
        for jsonl in proj_dir.glob("*.jsonl"):
            files += 1
            for evt in iter_jsonl(jsonl):
                ts = evt.get("timestamp")
                if since_ts and ts and ts < since_ts:
                    continue
                session = evt.get("sessionId") or evt.get("session_id")
                msg = evt.get("message") or {}
                role = msg.get("role")
                content = msg.get("content")
                # tool_use blocks: Skill (explicit), Read (auto-load SKILL.md), Bash (cat/sed SKILL.md)
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        bname = block.get("name")
                        binput = block.get("input") or {}
                        if bname == "Skill":
                            skill_name = binput.get("skill") or ""
                            if skill_name:
                                keys = claude_skill_keys(skill_name, catalog, project_skill_names, cwd_basename)
                                if keys:
                                    record_hit(catalog, keys, ts, session)
                                    events += 1
                        elif bname == "Read":
                            fp = binput.get("file_path") or ""
                            m = SKILL_PATH_LOOSE_RE.search(posix(fp))
                            if m:
                                keys = keys_from_skill_md_path(fp, m.group(1), catalog)
                                if keys:
                                    record_hit(catalog, keys, ts, session)
                                    events += 1
                        elif bname == "Bash":
                            cmd = binput.get("command") or ""
                            seen: set[str] = set()
                            for m in SKILL_PATH_LOOSE_RE.finditer(posix(cmd)):
                                if m.group(1) in seen:
                                    continue
                                seen.add(m.group(1))
                                keys = keys_from_skill_md_path(cmd, m.group(1), catalog)
                                if keys:
                                    record_hit(catalog, keys, ts, session)
                                    events += 1
                # Slash command tags in user text
                user_text = ""
                if isinstance(content, str):
                    user_text = content
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_text += block.get("text") or ""
                # only user-role messages can invoke a slash command; assistant
                # echoes of "<command-name>" should not be counted.
                if role == "user" and user_text and "<command-name>" in user_text:
                    for m in SLASH_TAG_RE.findall(user_text):
                        skill_name = m.lstrip("/")
                        keys = claude_skill_keys(skill_name, catalog, project_skill_names, cwd_basename)
                        if keys:
                            record_hit(catalog, keys, ts, session)
                            events += 1
    return (files, events)


def scan_codex(
    catalog: dict[tuple[str, str], SkillEntry],
    since_ts: str | None,
    project_filter: str | None,
) -> tuple[int, int]:
    if not CODEX_SESSIONS.exists():
        return (0, 0)
    files = 0
    events = 0
    for jsonl in CODEX_SESSIONS.rglob("rollout-*.jsonl"):
        files += 1
        session = jsonl.stem
        session_cwd: str | None = None
        for evt in iter_jsonl(jsonl):
            ts = evt.get("timestamp")
            if since_ts and ts and ts < since_ts:
                continue
            if evt.get("type") == "session_meta":
                session_cwd = (evt.get("payload") or {}).get("cwd")
                if project_filter and session_cwd and project_filter not in session_cwd:
                    break
                continue
            if project_filter and session_cwd and project_filter not in session_cwd:
                break
            payload = evt.get("payload") or {}
            ptype = payload.get("type")
            # 1) user message with leading slash command
            if ptype == "message" and payload.get("role") == "user":
                for block in payload.get("content") or []:
                    if not isinstance(block, dict) or block.get("type") != "input_text":
                        continue
                    text = block.get("text") or ""
                    m = LEADING_SLASH_RE.match(text)
                    if m:
                        name = m.group(1)
                        keys = codex_command_keys(name, catalog)
                        if keys:
                            record_hit(catalog, keys, ts, session)
                            events += 1
            # 2) function_call (exec_command / shell) that reads a SKILL.md
            elif ptype == "function_call":
                fname = payload.get("name") or ""
                if fname not in ("exec_command", "shell", "apply_patch"):
                    continue
                args_raw = payload.get("arguments") or ""
                seen: set[str] = set()
                for m in SKILL_PATH_LOOSE_RE.finditer(posix(args_raw)):
                    if m.group(1) in seen:
                        continue
                    seen.add(m.group(1))
                    keys = keys_from_skill_md_path(args_raw, m.group(1), catalog)
                    if keys:
                        record_hit(catalog, keys, ts, session)
                        events += 1
    return (files, events)


def days_between(iso_ts: str | None, now: datetime) -> int | None:
    dt = parse_iso(iso_ts)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days


def canonical_name(name: str) -> str:
    # strip `[project]` suffix and namespace prefix to merge variants of the
    # same skill installed in multiple sources.
    n = name.split("  [")[0]
    if ":" in n:
        n = n.split(":", 1)[1]
    return n.strip().lower()


def recommend(count: int, days_since: int, mtime_days: int) -> tuple[str, str]:
    """Return (verdict, reason). verdict in {KEEP, REVIEW, DELETE}."""
    if count == 0:
        if mtime_days <= 30:
            return ("KEEP", f"recently installed ({mtime_days}d ago); likely intentional")
        if mtime_days > 60:
            return ("DELETE", f"never used; installed {mtime_days}d ago")
        return ("REVIEW", f"never used; installed {mtime_days}d ago")
    if days_since < 0:
        return ("REVIEW", "no last-used timestamp")
    if days_since <= 30:
        return ("KEEP", f"active ({count}x, last {days_since}d ago)")
    if days_since <= 90:
        return ("KEEP", f"recent ({count}x, last {days_since}d ago)")
    if days_since <= 180:
        return ("REVIEW", f"used {count}x but stale ({days_since}d)")
    return ("DELETE", f"used {count}x long ago ({days_since}d since)")


def merge_same_name(rows: list[dict]) -> list[dict]:
    by_canon: dict[str, dict] = {}
    for r in rows:
        c = canonical_name(r["name"])
        if c in by_canon:
            agg = by_canon[c]
            agg["count"] += r["count"]
            agg["sessions"] += r["sessions"]
            agg["size_kb"] += r["size_kb"]
            agg["sources"].append(r["source"])
            agg["paths"].append(r["path"])
            agg["source_counts"][r["source"]] = agg["source_counts"].get(r["source"], 0) + r["count"]
            # earliest first_used / latest last_used
            if r["first_used"] and (not agg["first_used"] or r["first_used"] < agg["first_used"]):
                agg["first_used"] = r["first_used"]
            if r["last_used"] and (not agg["last_used"] or r["last_used"] > agg["last_used"]):
                agg["last_used"] = r["last_used"]
            # prefer non-empty description
            if not agg["description"] and r["description"]:
                agg["description"] = r["description"]
            # display name keeps the cleanest variant (drop project suffix)
            cleaned = r["name"].split("  [")[0]
            if len(cleaned) < len(agg["name"]):
                agg["name"] = cleaned
            agg["mtime_days"] = min(agg["mtime_days"], r["mtime_days"])
        else:
            by_canon[c] = {
                "name": r["name"].split("  [")[0],
                "sources": [r["source"]],
                "paths": [r["path"]],
                "count": r["count"],
                "sessions": r["sessions"],
                "first_used": r["first_used"],
                "last_used": r["last_used"],
                "size_kb": r["size_kb"],
                "description": r["description"],
                "mtime_days": r["mtime_days"],
                "source_counts": {r["source"]: r["count"]},
            }
    return list(by_canon.values())


def build_html(entries: list[SkillEntry], meta: dict) -> str:
    now = datetime.now(timezone.utc)
    raw_rows = []
    for e in entries:
        days = days_between(e.last_used, now)
        mtime_days = int((now.timestamp() - e.mtime) / 86400) if e.mtime else 9999
        raw_rows.append({
            "name": e.name,
            "source": e.source,
            "count": e.count,
            "sessions": len(e.sessions),
            "first_used": e.first_used or "",
            "last_used": e.last_used or "",
            "days_since": days if days is not None else -1,
            "size_kb": round(e.size_bytes / 1024, 1),
            "path": str(e.path),
            "description": e.description,
            "mtime_days": mtime_days,
        })
    rows = merge_same_name(raw_rows)
    for r in rows:
        r["size_kb"] = round(r["size_kb"], 1)
        days_since = -1
        if r["last_used"]:
            d = days_between(r["last_used"], now)
            days_since = d if d is not None else -1
        r["days_since"] = days_since
        verdict, reason = recommend(r["count"], days_since, r["mtime_days"])
        r["verdict"] = verdict
        r["reason"] = reason
    rows.sort(key=lambda r: (-r["count"], r["days_since"] if r["days_since"] >= 0 else 99999))
    rows_json = json.dumps(rows, ensure_ascii=False)

    meta_lines = "".join(
        f"<li><b>{k}:</b> {v}</li>" for k, v in meta.items()
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Skill Usage Stats</title>
<style>
  :root {{
    --bg: #0f1115;
    --panel: #161a22;
    --text: #e6e6e6;
    --muted: #8a93a6;
    --accent: #7aa2f7;
    --warn: #e0af68;
    --bad: #f7768e;
    --good: #9ece6a;
    --border: #232936;
  }}
  body {{ background: var(--bg); color: var(--text); font: 14px/1.5 -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 24px; }}
  h1 {{ margin-top: 0; font-size: 22px; }}
  .meta {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }}
  .meta ul {{ margin: 0; padding-left: 18px; color: var(--muted); }}
  .controls {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }}
  input, select {{ background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #1c2230; cursor: pointer; user-select: none; position: sticky; top: 0; }}
  th:hover {{ color: var(--accent); }}
  tr:hover td {{ background: #1a1f2a; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; border: 1px solid var(--border); color: var(--muted); }}
  .pill.cg {{ color: var(--accent); border-color: #2c3d6a; }}
  .pill.cp {{ color: var(--good); border-color: #2c5a3a; }}
  .pill.cpl {{ color: #bb9af7; border-color: #4a3a6a; }}
  .pill.cxs {{ color: var(--warn); border-color: #6a5a2c; }}
  .pill.cxp {{ color: #c0caf5; border-color: #3a3a6a; }}
  .verdict {{ font-weight: 700; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
  .verdict.KEEP {{ background: #1e3a2a; color: var(--good); }}
  .verdict.REVIEW {{ background: #3a3220; color: var(--warn); }}
  .verdict.DELETE {{ background: #3a2230; color: var(--bad); }}
  .stale {{ color: var(--bad); }}
  .never {{ color: var(--bad); font-weight: 600; }}
  .ok {{ color: var(--good); }}
  .muted {{ color: var(--muted); }}
  .desc {{ color: var(--muted); font-size: 12px; max-width: 480px; }}
  .actions {{ margin-bottom: 12px; }}
  button {{ background: var(--accent); color: #0f1115; border: 0; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; }}
</style>
</head>
<body>
<h1>Skill Usage Stats</h1>
<div class="meta"><ul>{meta_lines}</ul></div>
<div class="controls">
  <input id="q" placeholder="filter by name / description / path..." size="40" />
  <select id="src">
    <option value="">all sources</option>
    <option value="claude-global">claude-global</option>
    <option value="claude-project">claude-project</option>
    <option value="claude-plugin">claude-plugin</option>
    <option value="codex-global-skill">codex-global-skill</option>
    <option value="codex-global-prompt">codex-global-prompt</option>
  </select>
  <select id="verd">
    <option value="">all verdicts</option>
    <option value="KEEP">KEEP</option>
    <option value="REVIEW">REVIEW</option>
    <option value="DELETE">DELETE</option>
  </select>
  <label><input type="checkbox" id="zero" /> only zero-use</label>
  <label><input type="checkbox" id="stale" /> only stale (&gt;90d or never)</label>
  <span class="muted" id="counter"></span>
</div>
<table id="t">
<thead>
<tr>
  <th data-k="name">name</th>
  <th data-k="verdict">verdict</th>
  <th data-k="sources">sources</th>
  <th data-k="count">count</th>
  <th data-k="sessions">sessions</th>
  <th data-k="last_used">last used</th>
  <th data-k="days_since">days since</th>
  <th data-k="size_kb">size (KB)</th>
  <th data-k="description">description</th>
</tr>
</thead>
<tbody></tbody>
</table>
<script>
const ROWS = {rows_json};
const SRC_CLASS = {{
  "claude-global": "cg",
  "claude-project": "cp",
  "claude-plugin": "cpl",
  "codex-global-skill": "cxs",
  "codex-global-prompt": "cxp",
}};
function esc(s) {{ return (s || "").replace(/[<>&]/g, c => ({{"<":"&lt;",">":"&gt;","&":"&amp;"}}[c])); }}
let sortKey = "count";
let sortDir = -1;
function render() {{
  const q = document.getElementById("q").value.toLowerCase();
  const src = document.getElementById("src").value;
  const verd = document.getElementById("verd").value;
  const zeroOnly = document.getElementById("zero").checked;
  const staleOnly = document.getElementById("stale").checked;
  const filtered = ROWS.filter(r => {{
    if (src && !r.sources.includes(src)) return false;
    if (verd && r.verdict !== verd) return false;
    if (zeroOnly && r.count !== 0) return false;
    if (staleOnly && !(r.count === 0 || r.days_since > 90)) return false;
    if (!q) return true;
    return (r.name + " " + r.description + " " + r.paths.join(" ")).toLowerCase().includes(q);
  }});
  filtered.sort((a, b) => {{
    let va = a[sortKey], vb = b[sortKey];
    if (sortKey === "sources") {{ va = a.sources.join(","); vb = b.sources.join(","); }}
    if (va === vb) return 0;
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * sortDir;
    return String(va).localeCompare(String(vb)) * sortDir;
  }});
  const tbody = document.querySelector("#t tbody");
  tbody.innerHTML = filtered.map(r => {{
    const pills = r.sources.map(s => `<span class="pill ${{SRC_CLASS[s] || ''}}">${{s}}</span>`).join(" ");
    let daysCell;
    if (r.count === 0) daysCell = '<span class="never">never</span>';
    else if (r.days_since > 90) daysCell = `<span class="stale">${{r.days_since}}d</span>`;
    else daysCell = `<span class="ok">${{r.days_since}}d</span>`;
    const last = r.last_used ? r.last_used.slice(0, 10) : '<span class="muted">—</span>';
    const pathHtml = r.paths.map(p => `<div class="muted" style="font-size:11px">${{esc(p)}}</div>`).join("");
    return `<tr>
      <td><b>${{esc(r.name)}}</b>${{pathHtml}}</td>
      <td><span class="verdict ${{r.verdict}}">${{r.verdict}}</span><div class="muted" style="font-size:11px">${{esc(r.reason)}}</div></td>
      <td>${{pills}}</td>
      <td>${{r.count}}</td>
      <td>${{r.sessions}}</td>
      <td>${{last}}</td>
      <td>${{daysCell}}</td>
      <td>${{r.size_kb}}</td>
      <td class="desc">${{esc(r.description)}}</td>
    </tr>`;
  }}).join("");
  document.getElementById("counter").textContent = `${{filtered.length}} / ${{ROWS.length}} skills`;
}}
document.querySelectorAll("th").forEach(th => {{
  th.addEventListener("click", () => {{
    const k = th.dataset.k;
    if (sortKey === k) sortDir = -sortDir;
    else {{ sortKey = k; sortDir = (k === "name" || k === "sources" || k === "description" || k === "last_used" || k === "verdict") ? 1 : -1; }}
    render();
  }});
}});
["q","src","verd","zero","stale"].forEach(id => {{
  const el = document.getElementById(id);
  el.addEventListener(el.tagName === "INPUT" && el.type !== "checkbox" ? "input" : "change", render);
}});
render();
</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Skill usage stats dashboard")
    p.add_argument("--days", type=int, default=0, help="lookback window in days (0 = all time)")
    p.add_argument("--project", default=None, help="substring filter on cwd")
    p.add_argument("--out", default=str(HOME / ".claude" / "skill-stats.html"))
    p.add_argument("--no-open", action="store_true")
    args = p.parse_args(argv)

    since_ts: str | None = None
    if args.days > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - args.days * 86400
        since_ts = datetime.fromtimestamp(cutoff, timezone.utc).isoformat().replace("+00:00", "Z")

    project_dirs: list[Path] = []
    if CLAUDE_PROJECTS.exists():
        for d in CLAUDE_PROJECTS.iterdir():
            if d.is_dir():
                project_dirs.append(decode_cwd_from_project_dir(d.name))

    catalog = discover_catalog(project_dirs)

    cc_files, cc_events = scan_claude(catalog, since_ts, args.project)
    cx_files, cx_events = scan_codex(catalog, since_ts, args.project)

    entries = sorted(catalog.values(), key=lambda e: (-e.count, e.name.lower()))
    meta = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lookback_days": args.days or "all",
        "project_filter": args.project or "(none)",
        "catalog_size": len(entries),
        "claude_transcripts_scanned": cc_files,
        "claude_invocations_counted": cc_events,
        "codex_transcripts_scanned": cx_files,
        "codex_invocations_counted": cx_events,
        "zero_use_skills": sum(1 for e in entries if e.count == 0),
        "note": "Counts both explicit calls (Skill tool / slash command) and auto-triggered loads (Read or shell access to SKILL.md). Each tool event credits the skill once.",
    }
    html_text = build_html(entries, meta)

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    print(f"wrote {out_path}")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    if not args.no_open:
        webbrowser.open(out_path.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
