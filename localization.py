"""JSON localization and cross-platform Unicode font support."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import pygame
import pygame.freetype

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


def _lookup(source: dict[str, Any], key: str) -> Any:
    current: Any = source
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def tr(key: str, **values: Any) -> str:
    text = _lookup(_strings, key)
    if text is None:
        text = _lookup(_fallback, key)
    if not isinstance(text, str):
        text = key
    try:
        return text.format(**values)
    except (KeyError, ValueError):
        return text


def tr_list(key: str) -> list[str]:
    value = _lookup(_strings, key)
    if value is None:
        value = _lookup(_fallback, key)
    return [str(item) for item in value] if isinstance(value, list) else []


class UnicodeFont:
    """pygame.font-compatible wrapper backed by pygame.freetype.

    SDL_ttf can render some macOS TTC fonts as solid rectangles at certain
    sizes. pygame.freetype uses a different rendering path and avoids that bug.
    """

    def __init__(self, font: pygame.freetype.Font, size: int):
        self._font = font
        self._size = max(1, int(size))
        self._font.size = self._size
        self._font.antialiased = True
        self._font.pad = True

    def render(self, text: object, antialias: bool, color, background=None):
        """Render like pygame.font.Font.render, with a transparent background."""
        value = str(text)
        self._font.antialiased = bool(antialias)

        # Rendering some macOS TTC fonts through pygame.freetype can return a
        # solid black rectangle even when bgcolor=None. Render against pure
        # black, then mark that exact background color transparent.
        surface, _ = self._font.render(
            value,
            fgcolor=color,
            bgcolor=(0, 0, 0),
            size=self._size,
        )

        if background is None:
            surface.set_colorkey((0, 0, 0), pygame.RLEACCEL)
            try:
                return surface.convert_alpha()
            except pygame.error:
                # convert_alpha() requires an initialized display; the
                # colorkey Surface still works before one exists.
                return surface

        # Preserve pygame.font.Font.render(..., background=...) behavior.
        output = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
        if len(background) == 3:
            output.fill((*background, 255))
        else:
            output.fill(background)
        surface.set_colorkey((0, 0, 0), pygame.RLEACCEL)
        output.blit(surface, (0, 0))
        return output

    def size(self, text: object):
        rect = self._font.get_rect(str(text), size=self._size)
        return rect.width, rect.height

    def get_height(self):
        return self._font.get_sized_height(self._size)

    def get_linesize(self):
        return self._font.get_sized_height(self._size)


def _existing(paths: list[str]) -> str | None:
    for path in paths:
        if path and os.path.isfile(path):
            return path
    return None


def _mac_font_path(language: str) -> str | None:
    if language == "zh":
        return _existing([
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ])
    return _existing([
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ])


def _windows_font_path(language: str) -> str | None:
    fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    names = (
        ["msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"]
        if language == "zh"
        else ["arial.ttf", "segoeui.ttf"]
    )
    return _existing([os.path.join(fonts, name) for name in names])


def _linux_font_path(language: str) -> str | None:
    names = (
        [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        ]
        if language == "zh"
        else [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
    )
    return _existing(names)


def _font_path(language: str) -> str | None:
    if sys.platform == "darwin":
        return _mac_font_path(language)
    if sys.platform.startswith("win"):
        return _windows_font_path(language)
    return _linux_font_path(language)


def _make_freetype_font(size: int, language: str, bold: bool) -> UnicodeFont:
    pygame.freetype.init()
    path = _font_path(language)
    if path:
        ft_font = pygame.freetype.Font(path, size=max(1, int(size)))
    else:
        candidates = (
            ["PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC"]
            if language == "zh"
            else ["Arial", "Helvetica", "DejaVu Sans"]
        )
        ft_font = None
        for name in candidates:
            try:
                ft_font = pygame.freetype.SysFont(name, max(1, int(size)))
                if ft_font is not None:
                    break
            except (RuntimeError, OSError, pygame.error):
                continue
        if ft_font is None:
            ft_font = pygame.freetype.Font(None, max(1, int(size)))

    ft_font.strong = bool(bold)
    return UnicodeFont(ft_font, size)


def create_font(size: int, bold: bool = False, language: str | None = None):
    """Create one Unicode-capable font with pygame.font-compatible render()."""
    return _make_freetype_font(size, language or _language, bold)


def create_fonts(language: str | None = None):
    selected = language or _language
    return (
        create_font(30, False, selected),
        create_font(20, False, selected),
        create_font(48, True, selected),
    )


set_language(_DEFAULT_LANGUAGE)
