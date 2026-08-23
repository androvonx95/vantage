<p align="center">
  <img src="https://raw.githubusercontent.com/androvonx95/vantage/main/assets/banner.svg" alt="Vantage banner" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/androvonx95/vantage/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen" alt="build"></a>
  <a href="https://github.com/androvonx95/vantage/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license"></a>
  <a href="https://pypi.org/project/vantage/"><img src="https://img.shields.io/badge/pypi-v0.1.0-orange" alt="pypi"></a>
  <a href="https://github.com/androvonx95/vantage"><img src="https://img.shields.io/github/stars/androvonx95/vantage?style=social" alt="stars"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-indigo" alt="python">
  <img src="https://img.shields.io/badge/dependencies-zero%20core-0a0" alt="deps">
</p>

<h1 align="center">⛰ Vantage</h1>
<p align="center"><b>The offline-first command center for your codebase.</b></p>

<p align="center">
  Turn any repository into an <b>interactive knowledge graph</b>, get instant
  <b>git intelligence</b> (bus-factor, churn, contributors), run a <b>security &amp; quality
  scan</b> (secrets, complexity hotspots, dead code), and unlock <b>local-AI superpowers</b>
  — all from a single beautiful CLI. <b>No data leaves your machine</b> unless you opt in.
</p>

---

## ✨ Why Vantage?

- 🧭 **Interactive knowledge graph** — see how every file connects at a glance (`vantage map`).
- 📈 **Git intelligence** — bus-factor, churn hotspots, contributor breakdown, repo age.
- 🛡 **Security & quality scan** — detect leaked secrets, complexity bombs, TODOs, dead code.
- 🤖 **Optional AI, your way** — runs on **local Ollama** or any **OpenAI-compatible API**. No vendor lock-in.
- 🪶 **Zero-config, zero-core-deps** — a single `pip install` and you're ready. Core uses only the standard library + Rich.
- 🔒 **Private by default** — everything runs locally. Your code never touches a server.

## 🚀 Install

```bash
pip install vantage
```

That's it — the core has **no required dependencies** beyond `rich`.

> Want the optional AI networking niceties? `pip install vantage[ai]`

## 🖥 Usage

```bash
vantage                 # launch the dashboard (overview)
vantage insights        # git intelligence + repo insights
vantage scan            # security & quality scan
vantage score           # codebase health score (0-100) + breakdown
vantage map             # generate interactive HTML knowledge graph
vantage ai setup        # configure local AI (Ollama by default)
vantage ai doc file.py  # AI summarizes a file
vantage ai test file.py # AI writes tests for a file
vantage ai review -     # AI reviews a diff from stdin
vantage ai pr -         # AI writes a PR description from a diff
vantage doctor          # environment check
```

### 📛 Ignoring paths

Drop a `.vantageignore` file (gitignore-style globs) in your repo to skip
files/dirs from scanning and graph-building — handy for excluding test fixtures
or generated code.

### Example: the knowledge graph

```bash
vantage map
# => Interactive map written to ./vantage-map.html (312 nodes, 540 edges)
```

Open the HTML in any browser. Search to filter, click nodes to inspect, drag to explore.

<p align="center">
  <em>(Screenshot of a Vantage knowledge graph — thousands of files, instantly navigable.)</em>
</p>

## 🤖 AI features (optional)

Vantage's AI layer works **offline-first**:

```bash
# 1. Install Ollama and pull a model
ollama pull llama3.1

# 2. Point Vantage at it
vantage ai setup        # choose "ollama", defaults just work

# 3. Use it
vantage ai explain - < messy.py
git diff | vantage ai review -
```

Prefer a cloud model? `setup` also supports any OpenAI-compatible endpoint
(set `VANTAGE_AI_KEY`, `VANTAGE_AI_BASE`, `VANTAGE_AI_MODEL`).

## 🧩 How it works

| Feature | Backend | Leaves machine? |
| --- | --- | --- |
| Knowledge graph | AST + import analysis | ❌ never |
| Git intelligence | `git` CLI | ❌ never |
| Quality scan | regex + heuristics | ❌ never |
| AI features | Ollama / your API | ✅ only if you enable |

Vantage classifies source files by extension, extracts symbols with the Python
`ast` module (and a robust regex extractor for JS/TS/Go/Rust/Java/C#/Ruby/…),
resolves import edges best-effort, and renders a force-directed graph with
[vis-network](https://visjs.org/).

## 🗺 Roadmap

- [ ] Symbol-level graph (functions/classes as nodes)
- [ ] Architecture diagram export (Mermaid / SVG)
- [ ] Historical churn heatmap over time
- [ ] `vantage serve` — local web dashboard
- [ ] Team features & **Vantage Cloud** (continuous monitoring, alerts)

## 💸 Monetization & sponsorship

Vantage core is and will stay **free & open-source (MIT)**. The project is
funded by:

- ❤️ **GitHub Sponsors** — back the maintainers, get your name in the README.
- ☁️ **Vantage Cloud** (planned) — a hosted companion for teams that want
  *continuous* codebase monitoring, drift alerts, and shared configs across
  repositories. The local CLI remains the source of truth.

If Vantage saves you time (or embarrassment from a leaked key), consider
[sponsoring](https://github.com/sponsors/androvonx95) ⭐ and starring the repo.

## 📜 License

[MIT](LICENSE) © Vantage Contributors

---

<p align="center">Built with ⛰ and a lot of <code>ast</code>.</p>
