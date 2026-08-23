"""Data models for Vantage: lightweight, dependency-free representations of a codebase."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class CodeSymbol:
    """A named entity discovered inside a source file (function, class, etc.)."""

    name: str
    kind: str  # function | class | method | interface | struct | const | var
    line: int = 0
    end_line: int = 0
    doc: Optional[str] = None
    complexity: int = 1
    exported: bool = True


@dataclass
class SourceFile:
    path: Path
    language: str
    loc: int = 0
    blank: int = 0
    comment: int = 0
    size_bytes: int = 0
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    # symbols this file references in other files (best-effort, by name)
    references: Set[str] = field(default_factory=set)
    # raw metrics
    max_complexity: int = 1
    todo_count: int = 0
    has_secret: bool = False

    @property
    def rel(self) -> str:
        return str(self.path)


@dataclass
class RepoStats:
    root: Path
    file_count: int = 0
    total_loc: int = 0
    language_counts: Dict[str, int] = field(default_factory=dict)
    language_loc: Dict[str, int] = field(default_factory=dict)
    files: List[SourceFile] = field(default_factory=list)

    def top_languages(self, n: int = 8) -> List[tuple]:
        return sorted(self.language_loc.items(), key=lambda kv: kv[1], reverse=True)[:n]
