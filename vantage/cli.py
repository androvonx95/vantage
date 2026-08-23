"""Vantage command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.scanner import scan_repo
from .analytics.git_stats import analyze_git
from .analytics.quality import scan_quality
from .graph.knowledge_graph import build_graph, render_html
from .ui import display
from . import __version__


def _load(path: Path):
    display.print_banner()
    with display.spinner("Scanning repository…") as prog:
        prog.add_task("scan", total=None)
        stats = scan_repo(path)
    return stats


def cmd_overview(args):
    stats = _load(args.path)
    git = analyze_git(args.path)
    display.print_overview(stats, git)
    display.print_ai_status(_ai_cfg())


def cmd_insights(args):
    stats = _load(args.path)
    git = analyze_git(args.path)
    display.print_git(git)
    display.print_overview(stats, git)


def cmd_scan(args):
    stats = _load(args.path)
    with display.spinner("Running security & quality scan…") as prog:
        prog.add_task("scan", total=None)
        report = scan_quality(stats)
    display.print_quality(report)


def cmd_map(args):
    stats = _load(args.path)
    with display.spinner("Building knowledge graph…") as prog:
        prog.add_task("graph", total=None)
        g = build_graph(stats)
    out = args.output or (args.path / "vantage-map.html")
    out = Path(out)
    render_html(g, out)
    display.success(f"Interactive map written to {out}  ({g.meta['files']} nodes, {g.meta['edges']} edges)")
    display.console.print("[#8aa0c2]Open it in a browser. Tip: use the search box to filter.[/#8aa0c2]")


def _ai_cfg():
    from .ai.provider import AIConfig
    return AIConfig.load()


def cmd_ai(args):
    from .ai import provider as ai
    cfg = ai.AIConfig.load()
    if args.ai_action == "setup":
        display.console.print("Configure the AI backend (local-first by default).")
        provider = input("Provider [ollama/openai] (default ollama): ").strip() or "ollama"
        if provider == "ollama":
            cfg.provider = "ollama"
            cfg.base_url = input("Ollama base URL (default http://localhost:11434): ").strip() or "http://localhost:11434"
            cfg.model = input("Model (default llama3.1:latest): ").strip() or "llama3.1:latest"
            cfg.enabled = True
        else:
            cfg.provider = "openai"
            cfg.base_url = input("API base URL (default https://api.openai.com/v1): ").strip() or "https://api.openai.com/v1"
            cfg.model = input("Model (default gpt-4o-mini): ").strip() or "gpt-4o-mini"
            cfg.api_key = input("API key: ").strip()
            cfg.enabled = bool(cfg.api_key)
        cfg.save()
        display.success(f"Saved to {ai.CONFIG_PATH}")
        return
    if not cfg.enabled:
        display.error("AI is not configured. Run `vantage ai setup` first.")
        return
    if args.ai_action == "explain":
        snippet = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(errors="replace")
        display.console.print(ai.explain(snippet, cfg))
    elif args.ai_action == "doc":
        p = Path(args.file)
        display.console.print(ai.summarize_file(p, cfg))
    elif args.ai_action == "test":
        p = Path(args.file)
        display.console.print(ai.generate_tests(p, cfg))
    elif args.ai_action == "review":
        diff = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(errors="replace")
        display.console.print(ai.review_diff(diff, cfg))
    elif args.ai_action == "pr":
        diff = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(errors="replace")
        display.console.print(ai.pr_description(diff, cfg))
    elif args.ai_action == "status":
        display.print_ai_status(cfg)


def cmd_score(args):
    stats = _load(args.path)
    git = analyze_git(args.path)
    with display.spinner("Scoring codebase health…") as prog:
        prog.add_task("score", total=None)
        report = scan_quality(stats)
    from .analytics.health import compute_health
    result = compute_health(stats, git, report)
    display.print_score(result)


def cmd_doctor(args):
    display.print_banner()
    from .ai.provider import AIConfig
    cfg = AIConfig.load()
    checks = [
        ("Python", sys.version.split()[0]),
        ("Git CLI", "ok" if _which("git") else "missing"),
        ("AI backend", f"{cfg.provider} ({'enabled' if cfg.enabled else 'disabled'})"),
    ]
    t = display.console.table if hasattr(display.console, "table") else None
    table = __import__("rich.table", fromlist=["Table"]).Table(title="🩺 Doctor")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    for k, v in checks:
        table.add_row(k, v)
    display.console.print(table)
    display.console.print("[#8aa0c2]Tip: `vantage ai setup` to enable local AI via Ollama.[/#8aa0c2]")


def _which(name: str) -> bool:
    import shutil
    return shutil.which(name) is not None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vantage", description="⛰ Vantage — offline-first command center for your codebase.")
    p.add_argument("--version", action="version", version=f"vantage {__version__}")
    sub = p.add_subparsers(dest="command")

    def add_path(sp):
        sp.add_argument("path", nargs="?", default=Path.cwd(), type=Path,
                        help="Repository path (default: current directory)")

    add_path(sub.add_parser("overview", help="Dashboard: overview + languages + contributors"))
    add_path(sub.add_parser("insights", help="Git intelligence & repo insights"))
    add_path(sub.add_parser("scan", help="Security & quality scan"))
    add_path(sub.add_parser("score", help="Codebase health score (0-100)"))
    m = sub.add_parser("map", help="Generate an interactive HTML knowledge graph")
    add_path(m)
    m.add_argument("-o", "--output", default=None, help="Output HTML path")

    ai = sub.add_parser("ai", help="AI features (local LLMs via Ollama or OpenAI-compatible)")
    ai.add_argument("ai_action", choices=["setup", "status", "doc", "test", "review", "pr", "explain"])
    ai.add_argument("file", nargs="?", default="-", help="File or '-' for stdin")

    sub.add_parser("doctor", help="Check environment")

    overview = sub.add_parser("dashboard", help="Same as overview")
    add_path(overview)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.command or "overview"
    dispatch = {
        "overview": cmd_overview, "dashboard": cmd_overview,
        "insights": cmd_insights, "scan": cmd_scan, "score": cmd_score,
        "map": cmd_map, "ai": cmd_ai, "doctor": cmd_doctor,
    }
    try:
        dispatch[cmd](args)
    except KeyboardInterrupt:
        display.error("Interrupted.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
