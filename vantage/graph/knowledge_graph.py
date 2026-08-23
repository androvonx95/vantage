"""Builds a codebase knowledge graph (files + imports + references) and renders
a self-contained, interactive HTML visualization using vis-network."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from ..core.model import RepoStats

NODE_LIMIT = 1500  # keep the browser happy on giant repos


@dataclass
class GraphData:
    nodes: List[dict] = field(default_factory=list)
    edges: List[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def _resolve_import(target: str, from_file: Path, root: Path) -> str:
    """Best-effort resolution of an import string to a repo-relative path."""
    t = target.strip().strip("\"'")
    if not t or t.startswith((".", "/")) is False and (
        t.startswith("http") or t.startswith("@") or "/" not in t and "." not in t
    ):
        pass
    # Python-style module
    cand = root / (t.replace(".", "/") + ".py")
    if cand.exists():
        return str(cand.relative_to(root))
    cand = root / (t.replace(".", "/") + "/__init__.py")
    if cand.exists():
        return str(cand.relative_to(root))
    # relative JS/TS style
    if t.startswith("."):
        base = from_file.parent
        raw = t
        while raw.startswith("."):
            raw = raw[1:]
            if raw.startswith("/"):
                raw = raw[1:]
            else:
                base = base.parent
        cand = base / raw
        for ext in (".ts", ".tsx", ".js", ".jsx", ".json"):
            if (cand.with_suffix(ext)).exists():
                return str((cand.with_suffix(ext)).relative_to(root))
        if cand.exists():
            return str(cand.relative_to(root))
    return t  # unresolved -> keep as label


def build_graph(stats: RepoStats) -> GraphData:
    g = GraphData()
    root = stats.root
    files = stats.files[:NODE_LIMIT]
    file_set: Set[str] = {f.rel for f in files}

    # group color by top-level dir
    groups: Dict[str, int] = {}
    color_palette = [
        "#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#3b82f6",
    ]

    def group_of(rel: str) -> int:
        top = rel.split("/", 1)[0] if "/" in rel else rel
        if top not in groups:
            groups[top] = len(groups) % len(color_palette)
        return groups[top]

    node_ids: Dict[str, int] = {}
    nid = 0
    for f in files:
        nid += 1
        node_ids[f.rel] = nid
        size = 8 + min(f.loc // 40, 40)
        g.nodes.append({
            "id": nid,
            "label": f.path.name,
            "title": f"{f.rel}\n{f.language} · {f.loc} LOC · {len(f.symbols)} symbols",
            "group": group_of(f.rel),
            "size": size,
            "path": f.rel,
        })

    edge_set: Set[tuple] = set()
    for f in files:
        src = node_ids.get(f.rel)
        if src is None:
            continue
        for imp in f.imports:
            resolved = _resolve_import(imp, f.path, root)
            if resolved in node_ids:
                dst = node_ids[resolved]
                key = (src, dst)
                if key not in edge_set:
                    edge_set.add(key)
                    g.edges.append({"from": src, "to": dst, "arrows": "to", "color": {"opacity": 0.35}})
            else:
                # unresolved external dependency -> virtual node
                vkey = "ext:" + resolved
                if vkey not in node_ids:
                    nid += 1
                    node_ids[vkey] = nid
                    g.nodes.append({
                        "id": nid, "label": resolved.split("/")[-1][:24],
                        "title": f"external: {resolved}", "group": "ext",
                        "size": 6, "path": "", "shape": "diamond",
                    })
                key = (src, node_ids[vkey])
                if key not in edge_set:
                    edge_set.add(key)
                    g.edges.append({"from": src, "to": node_ids[vkey],
                                    "dashes": True, "color": {"opacity": 0.25}})

    g.meta = {
        "root": str(root),
        "files": len(g.nodes),
        "edges": len(g.edges),
        "total_loc": stats.total_loc,
        "groups": {k: color_palette[v] for k, v in groups.items()},
        "ext_color": "#64748b",
    }
    return g


def render_html(g: GraphData, out: Path) -> Path:
    from .template import HTML_TEMPLATE
    payload = json.dumps({
        "nodes": g.nodes, "edges": g.edges, "meta": g.meta,
    }, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("/*__DATA__*/", payload)
    html = html.replace("__ROOT__", g.meta.get("root", ""))
    html = html.replace("__FILES__", str(g.meta.get("files", 0)))
    html = html.replace("__EDGES__", str(g.meta.get("edges", 0)))
    html = html.replace("__LOC__", str(g.meta.get("total_loc", 0)))
    out.write_text(html, encoding="utf-8")
    return out
