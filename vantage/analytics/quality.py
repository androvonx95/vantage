"""Security & quality scanning: secrets, TODOs, complexity, dead code."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from ..core.model import RepoStats, SourceFile

SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]")),
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("Generic API Key", re.compile(r"(?i)(api[_-]?key|apikey|secret|token|passwd|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}")),
    ("Google API", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Stripe Key", re.compile(r"sk_live_[0-9A-Za-z]{24,}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Hex Secret", re.compile(r"(?i)secret\s*[:=]\s*['\"][0-9a-f]{32,}['\"]")),
]

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK|BUG|DEPRECATED)\b")

# words that frequently appear in false-positive "password" matches
FALSE_POSITIVE = {"password_hash", "passwordfield", "oldpassword", "newpassword",
                  "getpassword", "setpassword", "password_reset", "placeholder"}


@dataclass
class Finding:
    file: str
    line: int
    severity: str  # critical | high | medium | low
    category: str
    message: str


@dataclass
class QualityReport:
    secrets: List[Finding] = field(default_factory=list)
    todos: List[Finding] = field(default_factory=list)
    hotspots: List[Finding] = field(default_factory=list)
    large_files: List[Finding] = field(default_factory=list)
    dead_code: List[Finding] = field(default_factory=list)
    low_doc: List[Finding] = field(default_factory=list)


def _all_symbol_names(stats: RepoStats) -> Set[str]:
    names: Set[str] = set()
    for f in stats.files:
        for s in f.symbols:
            names.add(s.name)
    return names


def scan_quality(stats: RepoStats) -> QualityReport:
    report = QualityReport()
    global_refs: Set[str] = set()
    for f in stats.files:
        global_refs |= f.references

    for f in stats.files:
        text = ""
        try:
            text = f.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()

        # secrets
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(fp in low for fp in FALSE_POSITIVE):
                continue
            for label, pat in SECRET_PATTERNS:
                if pat.search(line):
                    report.secrets.append(Finding(
                        file=f.rel, line=i, severity="critical",
                        category="secret", message=f"Possible {label} exposed",
                    ))
                    f.has_secret = True
                    break

        # todos
        for i, line in enumerate(lines, 1):
            m = TODO_PATTERN.search(line)
            if m:
                msg = line.strip()[:80]
                report.todos.append(Finding(
                    file=f.rel, line=i, severity="low",
                    category="todo", message=msg,
                ))
                f.todo_count += 1

        # complexity hotspots
        for s in f.symbols:
            if s.complexity >= 12:
                report.hotspots.append(Finding(
                    file=f.rel, line=s.line, severity="high" if s.complexity >= 20 else "medium",
                    category="complexity", message=f"{s.kind} '{s.name}' complexity={s.complexity}",
                ))

        # large files
        if f.loc > 800:
            report.large_files.append(Finding(
                file=f.rel, line=1, severity="low",
                category="size", message=f"{f.loc} lines ({f.language})",
            ))

        # low documentation ratio for code-bearing languages
        if f.language in ("Python", "JavaScript", "TypeScript", "Go", "Rust", "Java"):
            if f.loc > 150 and f.comment == 0 and not f.symbols:
                report.low_doc.append(Finding(
                    file=f.rel, line=1, severity="low",
                    category="docs", message="Large file with no comments or recognized symbols",
                ))

    # dead code: defined symbols never referenced anywhere
    defined: Dict[str, List[str]] = {}
    for f in stats.files:
        for s in f.symbols:
            if s.kind == "class" or s.exported:
                defined.setdefault(s.name, []).append(f.rel)
    for name, locations in defined.items():
        if name in ("main", "init", "test", "setup", "__init__", "run"):
            continue
        if name not in global_refs and len(locations) == 1:
            report.dead_code.append(Finding(
                file=locations[0], line=0, severity="low",
                category="deadcode", message=f"Symbol '{name}' appears unused across the repo",
            ))

    return report
