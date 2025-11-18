from __future__ import annotations

from pathlib import Path
from typing import Iterable

import flet as ft
import os

PRIMARY_BLACK = "#111111"
SECONDARY_GRAY = "#5A5A5A"
BORDER_GRAY = "#D5D5D5"
LIGHT_GRAY = "#FEFEFE"
WHITE = "#FFFFFF"
APP_BG = "#FEFEFE"
HEADER_BG = APP_BG
HERO_BG = WHITE
SUMMARY_HIGHLIGHT = "#FEFEFE"
ERROR_RED = "#B3261E"
APP_FONT = "Excalifont"
APP_FONT_ASSET = "fonts/Excalifont-Regular.ttf"
HERO_IMAGE_ASSET = "images/donothing.png"


def _resolve_assets_dir() -> Path:
    env_override = os.getenv("DNTT_ASSETS_DIR")
    if env_override:
        candidate = Path(env_override).expanduser().resolve()
        if candidate.exists():
            return candidate
    package_root = Path(__file__).resolve().parents[1]
    search_roots: Iterable[Path] = (
        package_root,
        package_root.parent,
        Path.cwd(),
    )
    for root in search_roots:
        candidate = (root / "assets").resolve()
        if candidate.exists():
            return candidate
    return (package_root / "assets").resolve()


ASSETS_DIR = _resolve_assets_dir()
APP_FONT_FILE = ASSETS_DIR / APP_FONT_ASSET
HERO_IMAGE_FILE = ASSETS_DIR / HERO_IMAGE_ASSET


def text_style(
    *,
    color: str = PRIMARY_BLACK,
    weight: ft.FontWeight | None = None,
    size: float | None = None,
    italic: bool = False,
) -> ft.TextStyle:
    return ft.TextStyle(font_family=APP_FONT, color=color, weight=weight, size=size, italic=italic)


__all__ = [
    "ASSETS_DIR",
    "APP_BG",
    "APP_FONT",
    "APP_FONT_ASSET",
    "APP_FONT_FILE",
    "BORDER_GRAY",
    "ERROR_RED",
    "HEADER_BG",
    "HERO_BG",
    "HERO_IMAGE_ASSET",
    "HERO_IMAGE_FILE",
    "LIGHT_GRAY",
    "PRIMARY_BLACK",
    "SECONDARY_GRAY",
    "SUMMARY_HIGHLIGHT",
    "WHITE",
    "text_style",
]
