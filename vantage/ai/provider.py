"""Optional AI module.

Works fully offline with Ollama, or with any OpenAI-compatible API.
No hard dependency: uses urllib from the standard library. If you install
the optional `ai` extra (`pip install vantage[ai]`) we use `requests`
automatically when available, otherwise fall back to urllib.
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

CONFIG_PATH = Path.home() / ".config" / "vantage" / "config.json"


@dataclass
class AIConfig:
    provider: str = "ollama"  # ollama | openai
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:latest"
    api_key: str = ""
    enabled: bool = False

    @classmethod
    def load(cls) -> "AIConfig":
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, OSError):
                pass
        # environment overrides
        return cls(
            provider=os.environ.get("VANTAGE_AI_PROVIDER", "ollama"),
            base_url=os.environ.get("VANTAGE_AI_BASE", "http://localhost:11434"),
            model=os.environ.get("VANTAGE_AI_MODEL", "llama3.1:latest"),
            api_key=os.environ.get("VANTAGE_AI_KEY", ""),
            enabled=bool(os.environ.get("VANTAGE_AI_KEY") or
                         os.environ.get("VANTAGE_AI_PROVIDER") == "ollama"),
        )

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    try:
        import requests  # optional extra
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        return r.json()
    except ImportError:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())


def _chat(cfg: AIConfig, system: str, user: str, max_tokens: int = 1024) -> str:
    if cfg.provider == "ollama":
        url = f"{cfg.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": cfg.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": max_tokens},
        }
        data = _post_json(url, payload, {"Content-Type": "application/json"})
        return data.get("message", {}).get("content", "").strip()
    # openai-compatible
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    data = _post_json(url, payload, headers)
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


# ---- High level helpers -------------------------------------------------

def summarize_file(path: Path, cfg: Optional[AIConfig] = None) -> str:
    cfg = cfg or AIConfig.load()
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text[:6000]
    return _chat(cfg,
        "You are a senior engineer. Summarize what this source file does in 3-5 concise bullet points.",
        f"File: {path.name}\n\n{text}")


def generate_tests(path: Path, cfg: Optional[AIConfig] = None) -> str:
    cfg = cfg or AIConfig.load()
    text = path.read_text(encoding="utf-8", errors="replace")[:8000]
    return _chat(cfg,
        "Write a thorough unit test file (framework appropriate to the language) for the code below. Output only code.",
        f"File: {path.name}\n\n{text}")


def review_diff(diff: str, cfg: Optional[AIConfig] = None) -> str:
    cfg = cfg or AIConfig.load()
    return _chat(cfg,
        "Act as a strict code reviewer. List concrete issues, risks, and suggestions for this git diff. Be concise.",
        diff[:12000])


def pr_description(diff: str, cfg: Optional[AIConfig] = None) -> str:
    cfg = cfg or AIConfig.load()
    return _chat(cfg,
        "Write a clear pull-request title and description (markdown) summarizing this diff for teammates.",
        diff[:12000])


def explain(snippet: str, cfg: Optional[AIConfig] = None) -> str:
    cfg = cfg or AIConfig.load()
    return _chat(cfg,
        "Explain this code clearly for a mid-level developer. Use short paragraphs.",
        snippet[:6000])
