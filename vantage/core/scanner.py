"""Filesystem scanner: walks a repo, classifies files, and extracts metrics."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterator, List, Optional

from .languages import (
    IGNORE_DIRS, language_for, extract_generic, extract_python_symbols,
)
from .model import RepoStats, SourceFile

MAX_FILE_BYTES = 2_000_000  # skip huge generated files
SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".c",
    ".h", ".cpp", ".cc", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".sh", ".bash", ".zsh", ".lua", ".sql", ".html", ".css", ".vue", ".r",
    ".m", ".dart",
}


def load_ignore(root: Path) -> List[str]:
    """Read a .vantageignore file (gitignore-style globs) if present."""
    patterns: List[str] = []
    f = root / ".vantageignore"
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns


def _ignored(rel: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(rel, p.rstrip("/")) or
               fnmatch.fnmatch(rel, p.rstrip("/") + "/*")
               for p in patterns)


def iter_source_files(root: Path) -> Iterator[Path]:
    patterns = load_ignore(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() not in SOURCE_EXTS:
                continue
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            rel = str(p.relative_to(root))
            if _ignored(rel, patterns):
                continue
            yield p


def _count_lines(text: str) -> tuple:
    loc = 0
    blank = 0
    comment = 0
    in_block = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            blank += 1
            continue
        if in_block:
            comment += 1
            if "*/" in line:
                in_block = False
            continue
        if s.startswith("#") or s.startswith("//") or s.startswith("--"):
            comment += 1
            continue
        if s.startswith("/*") or s.startswith("<!--"):
            comment += 1
            if "*/" in line or "-->" in line:
                pass
            else:
                in_block = True
            continue
        loc += 1
    return loc, blank, comment


def scan_file(path: Path) -> Optional[SourceFile]:
    language = language_for(path)
    if not language:
        return None
    try:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
    except OSError:
        return None
    loc, blank, comment = _count_lines(text)
    sf = SourceFile(
        path=path, language=language, loc=loc, blank=blank,
        comment=comment, size_bytes=len(data),
    )
    if language == "Python":
        sf.symbols, sf.imports, sf.references = extract_python_symbols(text, path)
    else:
        sf.symbols, sf.imports, sf.references = extract_generic(path, text, language)
    sf.max_complexity = max((s.complexity for s in sf.symbols), default=1)
    return sf


def scan_repo(root: Path) -> RepoStats:
    stats = RepoStats(root=root)
    for p in iter_source_files(root):
        sf = scan_file(p)
        if sf is None:
            continue
        stats.files.append(sf)
        stats.file_count += 1
        stats.total_loc += sf.loc
        stats.language_counts[sf.language] = stats.language_counts.get(sf.language, 0) + 1
        stats.language_loc[sf.language] = stats.language_loc.get(sf.language, 0) + sf.loc
    return stats
