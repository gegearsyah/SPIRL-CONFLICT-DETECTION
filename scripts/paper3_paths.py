"""Paths for the standalone **BTC research** GitHub bundle.

Layout (repo root = parent of ``scripts/``)::

    <repo>/
      scripts/
      real-data-lab/
      trusted-adr-lab/
      research/          # legacy Paper 3 + experiment D artifacts
      state-orchestration-lab/
      .spirl/config.json   # copy from ``config.example.json``; see README

If you still keep a full **SPIRAL-RESEARCH** checkout elsewhere and want MCP
paths to resolve there, set ``SPIRAL_REPO_ROOT`` to that directory; otherwise
``repo_root()`` defaults to this repo root (``btc_root()``).
"""
from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "btc_root",
    "repo_root",
    "spirl_config_path",
    "mcp_json_path",
    "research_dir",
]


def btc_root() -> Path:
    """Repository root (parent of ``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    """SPIRAL-RESEARCH root when ``SPIRAL_REPO_ROOT`` is set; else same as ``btc_root()``."""
    raw = os.environ.get("SPIRAL_REPO_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return btc_root()


def spirl_config_path() -> Path:
    return repo_root() / ".spirl" / "config.json"


def mcp_json_path() -> Path:
    return repo_root() / ".cursor" / "mcp.json"


def research_dir() -> Path:
    return btc_root() / "research"
