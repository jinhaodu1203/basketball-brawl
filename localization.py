"""Lightweight JSON localization manager for Basketball Brawl."""

from __future__ import annotations

import json
import os
from typing import Any

import pygame

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LANG_DIR = os.path.join(_BASE_DIR, "lang")
_DEFAULT_LANGUAGE = "en"
_SUPPORTED = ("en", "zh")
_language = _DEFAULT_LANGUAGE
_strings: dict[str, Any] = {}
_fallback: dict[str, Any] = {}


def _load_file(language: str) -> dict[str, Any]:
    path = os.path.join(_LANG_DIR, f"{language}.json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def set_language(language: str) -> str:
    """Activate a supported language and return the normalized code."""
    global _language, _strings, _fallback
    normalized = language if language in _SUPPORTED else _DEFAULT_LANGUAGE
    _fallback = _load_file(_DEFAULT_LANGUAGE)
    _strings = _load_file(normalized)
    _language = normalized
    return normalized


def get_language() -> str:
    return _language


def supported_languages() -> tuple[str, ...]:
    return _SUPPORTED


def tr(key: str, **values: Any) -> str:
    """Translate a dotted key, falling back to English and then the key itself."""
    def lookup(source: dict[str, Any]) -> Any:
        current: Any = source
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    text = lookup(_strings)
    if text is None:
        text = lookup(_fallback)
    if not isinstance(text, str):
        text = key
    try:
        return text.format(**values)
    except (KeyError, ValueError):
        return text



def tr_list(key: str) -> list[str]:
    """Translate a list-valued key."""
    def lookup(source: dict[str, Any]) -> Any:
        current: Any = source
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    value = lookup(_strings)
    if value is None:
        value = lookup(_fallback)
    return [str(item) for item in value] if isinstance(value, list) else []


def _find_font_name(language: str) -> str | None:
    # Use installed system fonts only; no font files are bundled or redistributed.
    candidates = (
        ["PingFang SC", "Hiragino Sans GB", "Heiti SC", "Arial Unicode MS"]
        if language == "zh"
        else ["Arial", "Helvetica", "DejaVu Sans"]
    )
    installed = {name.lower(): name for name in pygame.font.get_fonts()}
    for candidate in candidates:
        normalized = candidate.lower().replace(" ", "")
        if normalized in installed:
            return installed[normalized]
    return None


def create_fonts(language: str | None = None):
    """Return UI fonts that can display the selected language."""
    language = language or _language
    font_name = _find_font_name(language)
    return (
        pygame.font.SysFont(font_name, 30),
        pygame.font.SysFont(font_name, 20),
        pygame.font.SysFont(font_name, 48, bold=True),
    )


set_language(_DEFAULT_LANGUAGE)
