"""Language detection and lightweight symbol extraction.

Vantage is deliberately dependency-free for its core. We use:
  * The Python `ast` module for deep, accurate Python analysis.
  * A small, robust regex extractor for other common languages
    (JS/TS, Go, Rust, Java, C/C++, Ruby, etc.) so the tool works
    everywhere without native parsers.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .model import CodeSymbol, SourceFile

# extension -> (language, comment tokens)
LANG_MAP: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    ".py": ("Python", ("#",)),
    ".js": ("JavaScript", ("//", "/*", "*/")),
    ".jsx": ("JavaScript", ("//", "/*", "*/")),
    ".ts": ("TypeScript", ("//", "/*", "*/")),
    ".tsx": ("TypeScript", ("//", "/*", "*/")),
    ".go": ("Go", ("//", "/*", "*/")),
    ".rs": ("Rust", ("//", "/*", "*/")),
    ".java": ("Java", ("//", "/*", "*/")),
    ".kt": ("Kotlin", ("//", "/*", "*/")),
    ".c": ("C", ("//", "/*", "*/")),
    ".h": ("C", ("//", "/*", "*/")),
    ".cpp": ("C++", ("//", "/*", "*/")),
    ".cc": ("C++", ("//", "/*", "*/")),
    ".hpp": ("C++", ("//", "/*", "*/")),
    ".cs": ("C#", ("//", "/*", "*/")),
    ".rb": ("Ruby", ("#",)),
    ".php": ("PHP", ("#", "//", "/*", "*/")),
    ".swift": ("Swift", ("//", "/*", "*/")),
    ".scala": ("Scala", ("//", "/*", "*/")),
    ".sh": ("Shell", ("#",)),
    ".bash": ("Shell", ("#",)),
    ".zsh": ("Shell", ("#",)),
    ".lua": ("Lua", ("--",)),
    ".sql": ("SQL", ("--", "/*", "*/")),
    ".html": ("HTML", ("<!--", "-->")),
    ".css": ("CSS", ("/*", "*/")),
    ".vue": ("Vue", ("<!--", "-->")),
    ".r": ("R", ("#",)),
    ".m": ("Objective-C", ("//", "/*", "*/")),
    ".dart": ("Dart", ("//", "/*", "*/")),
}

# Files we never want to treat as source even if extension matches
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".tox",
    "target", "vendor", ".idea", ".vscode", "site-packages",
    ".next", ".cargo", "bin", "obj", "coverage",
}

IMPORT_PATTERNS = {
    "Python": re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"),
    "JavaScript": re.compile(r"^\s*(?:import\s+.+?\s+from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))"),
    "TypeScript": re.compile(r"^\s*(?:import\s+.+?\s+from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))"),
    "Go": re.compile(r'^\s*import\s+(?:\([^)]*\)|"([^"]+)")'),
    "Rust": re.compile(r'^\s*use\s+([\w:]+)'),
    "Java": re.compile(r"^\s*import\s+([\w.]+)"),
    "Ruby": re.compile(r"^\s*(?:require|require_relative)\s+['\"]([^'\"]+)['\"]"),
    "PHP": re.compile(r"^\s*(?:use|require|include)(?:_once)?\s+([\w\\]+|['\"][^'\"]+['\"])"),
    "C#": re.compile(r"^\s*using\s+([\w.]+)"),
    "Shell": re.compile(r"^\s*(?:\.\s+|source\s+)([\w./-]+)"),
}

# Generic symbol extractors (best-effort, language agnostic-ish)
RE_DEF = {
    "Python": re.compile(r"^\s*(?:def|class|async\s+def)\s+([A-Za-z_]\w*)"),
    "JavaScript": re.compile(r"^\s*(?:function\s+([A-Za-z_$][\w$]*)|(?:const|let|var|class|function)\s+([A-Za-z_$][\w$]*)\s*[=(:])"),
    "TypeScript": re.compile(r"^\s*(?:function\s+([A-Za-z_$][\w$]*)|(?:export\s+)?(?:const|let|var|class|interface|type|function)\s+([A-Za-z_$][\w$]*))"),
    "Go": re.compile(r"^\s*(?:func\s+(?:\([^)]*\)\s+)?([A-Za-z_]\w*)|type\s+([A-Za-z_]\w*)\s)"),
    "Rust": re.compile(r"^\s*(?:fn\s+([A-Za-z_]\w*)|struct\s+([A-Za-z_]\w*)|impl\s+([A-Za-z_]\w*)|trait\s+([A-Za-z_]\w*))"),
    "Java": re.compile(r"^\s*(?:public|private|protected|static|\s)*\s(?:class|interface|enum)\s+([A-Za-z_]\w*)"),
    "Ruby": re.compile(r"^\s*(?:def\s+([A-Za-z_]\w*)|class\s+([A-Za-z_]\w*)|module\s+([A-Za-z_]\w*))"),
    "C#": re.compile(r"^\s*(?:public|private|protected|internal|static|\s)*\s(?:class|interface|struct|enum)\s+([A-Za-z_]\w*)"),
    "PHP": re.compile(r"^\s*(?:function\s+([A-Za-z_]\w*)|class\s+([A-Za-z_]\w*))"),
    "Swift": re.compile(r"^\s*(?:func\s+([A-Za-z_]\w*)|class\s+([A-Za-z_]\w*)|struct\s+([A-Za-z_]\w*))"),
    "C": re.compile(r"^\s*(?:[A-Za-z_].*?\s+)([A-Za-z_]\w*)\s*\("),
    "C++": re.compile(r"^\s*(?:[A-Za-z_].*?\s+)([A-Za-z_]\w*)\s*\("),
}


def language_for(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    return LANG_MAP.get(ext, (None,))[0]


def extract_python_symbols(src: str, path: Path) -> Tuple[List[CodeSymbol], List[str], Set[str]]:
    symbols: List[CodeSymbol] = []
    imports: List[str] = []
    refs: Set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return symbols, imports, refs

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            # crude cyclomatic-ish complexity: count decision points
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With,
                                      ast.Try, ast.ExceptHandler, ast.BoolOp,
                                      ast.comprehension, ast.IfExp)):
                    complexity += 1
            symbols.append(CodeSymbol(
                name=node.name,
                kind="class" if isinstance(node, ast.ClassDef) else "function",
                line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                doc=(doc.splitlines()[0] if doc else None),
                complexity=complexity,
                exported=not node.name.startswith("_"),
            ))
    # collect referenced call names (best-effort cross-file refs)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                refs.add(func.id)
            elif isinstance(func, ast.Attribute):
                refs.add(func.attr)
    return symbols, imports, refs


def extract_generic(path: Path, src: str, language: str):
    symbols: List[CodeSymbol] = []
    imports: List[str] = []
    refs: Set[str] = set()
    def_re = RE_DEF.get(language)
    imp_re = IMPORT_PATTERNS.get(language)
    call_re = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
    for i, line in enumerate(src.splitlines(), start=1):
        if imp_re:
            m = imp_re.match(line)
            if m:
                val = m.group(1) or m.group(2) or m.group(3)
                if val:
                    imports.append(val.strip().strip("\"'"))
        if def_re:
            m = def_re.match(line)
            if m:
                name = next((g for g in m.groups() if g), None)
                if name and len(name) > 1:
                    kind = "class" if re.search(r"\b(class|struct|interface|trait|enum|module|type|impl)\b", line) else "function"
                    symbols.append(CodeSymbol(name=name, kind=kind, line=i, end_line=i))
        for cm in call_re.finditer(line):
            refs.add(cm.group(1))
    return symbols, imports, refs
