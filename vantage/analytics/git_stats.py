"""Git intelligence: contributors, churn, bus-factor, code age, activity."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class GitAnalysis:
    is_repo: bool = False
    total_commits: int = 0
    contributors: List[Tuple[str, int]] = field(default_factory=list)
    bus_factor: float = 0.0  # fraction of contributors responsible for 50% of commits
    file_churn: List[Tuple[str, int]] = field(default_factory=list)
    oldest_commit_days: int = 0
    newest_commit_days: int = 0
    commits_last_30d: int = 0
    active_days: int = 0


def _run(root: Path, args: List[str]) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True,
            text=True, timeout=60,
        )
        if out.returncode != 0:
            return None
        return out.stdout
    except (subprocess.SubprocessError, OSError):
        return None


def analyze_git(root: Path) -> GitAnalysis:
    res = GitAnalysis()
    if _run(root, ["rev-parse", "--is-inside-work-tree"]) is None:
        return res
    res.is_repo = True

    commits = _run(root, ["rev-list", "--all", "--count"])
    if commits and commits.strip().isdigit():
        res.total_commits = int(commits.strip())

    contr = _run(root, ["shortlog", "-sne", "--all"])
    if contr:
        pairs = []
        for line in contr.strip().splitlines():
            if "\t" in line:
                cnt, name = line.split("\t", 1)
                pairs.append((name.strip(), int(cnt.strip())))
        res.contributors = sorted(pairs, key=lambda x: x[1], reverse=True)
        total = sum(c for _, c in res.contributors) or 1
        cum = 0
        needed = 0
        for _, c in res.contributors:
            cum += c
            needed += 1
            if cum >= total * 0.5:
                break
        res.bus_factor = needed / max(len(res.contributors), 1)

    churn = _run(root, ["log", "--all", "--name-only", "--pretty=format:"])
    if churn:
        counts: Dict[str, int] = defaultdict(int)
        for ln in churn.splitlines():
            ln = ln.strip()
            if ln and not ln.startswith('"'):
                counts[ln] += 1
        res.file_churn = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:50]

    first = _run(root, ["log", "--reverse", "--format=%ct", "--all"])
    last = _run(root, ["log", "-1", "--format=%ct", "--all"])
    import time
    now = time.time()
    if first:
        lines = [l for l in first.splitlines() if l.strip().isdigit()]
        if lines:
            res.oldest_commit_days = int((now - int(lines[0])) / 86400)
    if last and last.strip().isdigit():
        res.newest_commit_days = int((now - int(last.strip())) / 86400)

    recent = _run(root, ["log", "--since=30 days ago", "--oneline"])
    if recent:
        res.commits_last_30d = len([l for l in recent.splitlines() if l.strip()])

    adays = _run(root, ["log", "--format=%ad", "--date=short", "--all"])
    if adays:
        res.active_days = len(set(l.strip() for l in adays.splitlines() if l.strip()))

    return res
