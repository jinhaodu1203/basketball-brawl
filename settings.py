"""Persistent user settings for Basketball Brawl."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass


@dataclass
class GameSettings:
    fullscreen: bool = False
    master_volume: int = 80
    music_volume: int = 100
    sfx_volume: int = 100
    show_fps: bool = False
    language: str = "en"

    def normalize(self) -> None:
        self.fullscreen = bool(self.fullscreen)
        self.master_volume = max(0, min(100, int(self.master_volume)))
        self.music_volume = max(0, min(100, int(self.music_volume)))
        self.sfx_volume = max(0, min(100, int(self.sfx_volume)))
        self.show_fps = bool(self.show_fps)
        self.language = self.language if self.language in ("en", "zh") else "en"


def _legacy_settings_dir() -> str:
    """The dotfile location used by every build before the Windows port."""
    return os.path.join(os.path.expanduser("~"), ".basketball_brawl")


def _settings_dir() -> str:
    """Per-platform save location.

    Windows expects user data under %APPDATA% rather than a dotfile in the
    profile root; that is also the directory Steam Cloud is pointed at. Other
    platforms keep the original location so existing macOS saves stay valid.
    """
    if sys.platform.startswith("win"):
        roaming = os.environ.get("APPDATA")
        if roaming:
            return os.path.join(roaming, "HOOP HAVOC")
    return _legacy_settings_dir()


def _settings_path() -> str:
    base_dir = _settings_dir()
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "settings.json")


def _read_settings_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("settings file is not a JSON object")
    return data


def _load_settings_data() -> dict:
    """Read the current settings file, falling back to the legacy location.

    A player upgrading from a pre-port build keeps their settings: the old file
    is read once and the next save writes to the new location. The legacy file
    is left in place rather than deleted, so downgrading still works.
    """
    try:
        return _read_settings_file(_settings_path())
    except (OSError, ValueError, TypeError):
        pass

    legacy = os.path.join(_legacy_settings_dir(), "settings.json")
    if os.path.abspath(legacy) != os.path.abspath(_settings_path()):
        try:
            return _read_settings_file(legacy)
        except (OSError, ValueError, TypeError):
            pass

    return {}


def load_settings() -> GameSettings:
    settings = GameSettings()
    data = _load_settings_data()
    settings.fullscreen = data.get("fullscreen", settings.fullscreen)
    settings.master_volume = data.get("master_volume", settings.master_volume)
    settings.music_volume = data.get("music_volume", settings.music_volume)
    settings.sfx_volume = data.get("sfx_volume", settings.sfx_volume)
    settings.show_fps = data.get("show_fps", settings.show_fps)
    settings.language = data.get("language", settings.language)
    settings.normalize()
    return settings


def _write_settings_file(base_dir: str, payload: dict) -> None:
    os.makedirs(base_dir, exist_ok=True)
    path = os.path.join(base_dir, "settings.json")
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    os.replace(temp_path, path)


def save_settings(settings: GameSettings) -> bool:
    """Persist settings, returning whether anything reached disk.

    %APPDATA% can be redirected to OneDrive or locked down by policy, so the
    write is allowed to fail over to the legacy dotfile directory. Losing the
    settings file is not worth crashing the game on exit, so a total failure is
    reported through the return value instead of an exception.
    """
    settings.normalize()
    payload = asdict(settings)

    candidates = [_settings_dir()]
    legacy = _legacy_settings_dir()
    if os.path.abspath(legacy) != os.path.abspath(candidates[0]):
        candidates.append(legacy)

    for base_dir in candidates:
        try:
            _write_settings_file(base_dir, payload)
            return True
        except (OSError, ValueError, TypeError):
            continue
    return False
