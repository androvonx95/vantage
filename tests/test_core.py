"""Tests for Vantage core analysis."""

from pathlib import Path

from vantage.core.model import RepoStats, SourceFile, CodeSymbol
from vantage.core.languages import language_for, extract_python_symbols, extract_generic
from vantage.core.scanner import scan_file
from vantage.analytics.quality import scan_quality, SECRET_PATTERNS
import re


def test_language_detection():
    assert language_for(Path("foo.py")) == "Python"
    assert language_for(Path("foo.ts")) == "TypeScript"
    assert language_for(Path("foo.unknown")) is None


def test_python_symbol_extraction():
    src = '''
"""Module doc."""
import os
from pathlib import Path

def hello(name):
    """Greet."""
    if name:
        return f"hi {name}"
    return "hi"

class Widget:
    def draw(self):
        return 1
'''
    symbols, imports, refs = extract_python_symbols(src, Path("x.py"))
    names = {s.name for s in symbols}
    assert "hello" in names
    assert "Widget" in names
    kinds = {s.name: s.kind for s in symbols}
    assert kinds["Widget"] == "class"
    assert kinds["hello"] == "function"
    assert any("os" in imp for imp in imports)
    # complexity should be > 1 because of the if
    hello = next(s for s in symbols if s.name == "hello")
    assert hello.complexity >= 2


def test_generic_extraction():
    src = "function add(a, b) { return a + b; }\nclass Foo {}\n"
    symbols, imports, refs = extract_generic(Path("x.js"), src, "JavaScript")
    names = {s.name for s in symbols}
    assert "add" in names
    assert "Foo" in names


def test_secret_pattern_detection():
    line = 'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
    matched = any(p.search(line) for _, p in SECRET_PATTERNS)
    assert matched


def test_scan_file(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def f():\n    return 1\n")
    sf = scan_file(f)
    assert sf is not None
    assert sf.language == "Python"
    assert sf.loc == 2
    assert any(s.name == "f" for s in sf.symbols)


def test_quality_scan_finds_secret(tmp_path):
    f = tmp_path / "leak.py"
    f.write_text('password = "supersecretvalue123"\n')
    stats = RepoStats(root=tmp_path)
    sf = scan_file(f)
    stats.files.append(sf)
    report = scan_quality(stats)
    assert any(fnd.category == "secret" for fnd in report.secrets)


def test_quality_scan_finds_todo(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("# TODO: refactor this mess\nx = 1\n")
    stats = RepoStats(root=tmp_path)
    stats.files.append(scan_file(f))
    report = scan_quality(stats)
    assert any(fnd.category == "todo" for fnd in report.todos)
