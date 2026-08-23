"""Compute a 0-100 "health score" for a codebase from its analysis."""

from __future__ import annotations

from ..core.model import RepoStats
from .git_stats import GitAnalysis
from .quality import QualityReport


def compute_health(stats: RepoStats, git: GitAnalysis, report: QualityReport) -> dict:
    """Return a dict with an overall score and a breakdown of components."""
    if stats.file_count == 0:
        return {"score": 0, "components": {}}

    loc = max(stats.total_loc, 1)

    # Security: leaked secrets are heavily penalized.
    security = max(0, 100 - min(len(report.secrets) * 25, 60))

    # Maintainability: weighted penalty for hotspots, dead code, and huge files.
    hotspots = len(report.hotspots)
    dead = len(report.dead_code)
    large = len(report.large_files)
    maintainability = max(0, 100 - (hotspots * 3 + dead * 2 + large * 5))

    # Documentation: comment ratio (docstrings aren't counted as comments, so
    # we give a neutral baseline and reward comments while penalizing TODO debt.
    comment_ratio = sum(f.comment for f in stats.files) / loc
    todo_pressure = len(report.todos) / (loc / 1000)
    documentation = max(0, min(100, 50 + int(comment_ratio * 150) - int(todo_pressure * 5)))

    # Bus factor: closer to 1.0 (few people) is riskier. We floor at 40 so a
    # freshly-started solo project isn't scored as catastrophically as an
    # abandoned single-maintainer codebase.
    if git.is_repo and git.contributors:
        bus = max(40, 100 - int(git.bus_factor * 100))
    else:
        bus = 50  # unknown

    score = round(0.35 * security + 0.30 * maintainability +
                  0.20 * documentation + 0.15 * bus)
    score = max(0, min(100, score))
    return {
        "score": score,
        "components": {
            "Security": security,
            "Maintainability": maintainability,
            "Documentation": documentation,
            "Bus factor": bus,
        },
    }


def grade(score: int) -> str:
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"
