"""Rich-based terminal rendering for Vantage reports."""

from __future__ import annotations

from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from ..core.model import RepoStats
from ..analytics.git_stats import GitAnalysis
from ..analytics.quality import QualityReport, Finding
from ..ai.provider import AIConfig

console = Console()


def print_banner() -> None:
    console.print(
        Panel(
            "[bold #6366f1]⛰ VANTAGE[/bold #6366f1]  [#8aa0c2]offline-first command center for your codebase[/#8aa0c2]",
            border_style="#6366f1",
        )
    )


def print_overview(stats: RepoStats, git: GitAnalysis) -> None:
    table = Table(title="📊 Repository Overview", expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")
    table.add_row("Path", str(stats.root))
    table.add_row("Files analyzed", str(stats.file_count))
    table.add_row("Total LOC", f"{stats.total_loc:,}")
    table.add_row("Languages", str(len(stats.language_loc)))
    if git.is_repo:
        table.add_row("Commits", f"{git.total_commits:,}")
        table.add_row("Contributors", str(len(git.contributors)))
        table.add_row("Bus factor", f"{git.bus_factor:.2f}")
        table.add_row("Commits (30d)", str(git.commits_last_30d))
    console.print(table)

    lang = Table(title="🌐 Languages", expand=True)
    lang.add_column("Language", style="cyan")
    lang.add_column("Files", justify="right")
    lang.add_column("LOC", justify="right", style="bold")
    for name, loc in stats.top_languages():
        lang.add_row(name, str(stats.language_counts[name]), f"{loc:,}")
    console.print(lang)

    if git.is_repo and git.contributors:
        c = Table(title="👥 Top Contributors", expand=True)
        c.add_column("Author", style="cyan")
        c.add_column("Commits", justify="right", style="bold")
        for name, n in git.contributors[:10]:
            c.add_row(name, str(n))
        console.print(c)


def print_git(git: GitAnalysis) -> None:
    if not git.is_repo:
        console.print("[yellow]Not a git repository.[/yellow]")
        return
    console.print(f"[bold]Commits:[/bold] {git.total_commits:,}  "
                  f"[bold]Contributors:[/bold] {len(git.contributors)}  "
                  f"[bold]Bus factor:[/bold] {git.bus_factor:.2f}")
    console.print(f"[bold]Active days:[/bold] {git.active_days}  "
                  f"[bold]Last 30d commits:[/bold] {git.commits_last_30d}  "
                  f"[bold]Repo age:[/bold] {git.oldest_commit_days} days")
    t = Table(title="🔥 Most-churned files", expand=True)
    t.add_column("File", style="cyan")
    t.add_column("Commits touching", justify="right", style="bold")
    for path, n in git.file_churn[:15]:
        t.add_row(path, str(n))
    console.print(t)


def _sev_color(sev: str) -> str:
    return {"critical": "red", "high": "orange_red1", "medium": "yellow",
            "low": "grey50"}.get(sev, "white")


def print_quality(report: QualityReport) -> None:
    counts = {
        "Secrets": len(report.secrets),
        "Complexity hotspots": len(report.hotspots),
        "TODO/FIXME": len(report.todos),
        "Large files": len(report.large_files),
        "Possible dead code": len(report.dead_code),
        "Undocumented": len(report.low_doc),
    }
    console.print(Panel("[bold]🛡 Security & Quality Scan[/bold]", border_style="cyan"))
    for k, v in counts.items():
        color = "red" if (k == "Secrets" and v) else ("yellow" if v else "green")
        console.print(f"  [{color}]• {k}: {v}[/{color}]")

    def section(title: str, items: List[Finding], limit: int = 15):
        if not items:
            return
        console.print(f"\n[bold]{title}[/bold]")
        t = Table(expand=True)
        t.add_column("Severity", style="bold")
        t.add_column("File", style="cyan")
        t.add_column("Line", justify="right")
        t.add_column("Detail")
        for f in items[:limit]:
            t.add_row(f"[{_sev_color(f.severity)}]{f.severity}[/{_sev_color(f.severity)}]",
                      f.file, str(f.line), f.message)
        console.print(t)

    section("🔐 Secrets (CRITICAL)", report.secrets)
    section("🔥 Complexity hotspots", report.hotspots)
    section("🧟 Possible dead code", report.dead_code)
    section("📝 TODO / FIXME", report.todos)


def print_ai_status(cfg: AIConfig) -> None:
    if cfg.enabled:
        console.print(f"[green]AI enabled[/green] · provider={cfg.provider} · model={cfg.model}")
    else:
        console.print("[yellow]AI disabled[/yellow] — set it up with `vantage ai setup` "
                      "(uses local Ollama or any OpenAI-compatible API).")


def spinner(msg: str):
    return Progress(SpinnerColumn(), TextColumn(msg), console=console, transient=True)


def error(msg: str) -> None:
    console.print(f"[red]✗ {msg}[/red]")


def success(msg: str) -> None:
    console.print(f"[green]✓ {msg}[/green]")
