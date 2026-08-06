"""Persistent user settings for Basketball Brawl."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass


@dataclass
class GameSettings:
    fullscreen: bool = False
    master_volume: int = 80
    show_fps: bool = False

    def normalize(self) -> None:
        self.fullscreen = bool(self.fullscreen)
        self.master_volume = max(0, min(100, int(self.master_volume)))
        self.show_fps = bool(self.show_fps)


def _settings_path() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".basketball_brawl")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "settings.json")


def load_settings() -> GameSettings:
    settings = GameSettings()
    path = _settings_path()
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        settings.fullscreen = data.get("fullscreen", settings.fullscreen)
        settings.master_volume = data.get("master_volume", settings.master_volume)
        settings.show_fps = data.get("show_fps", settings.show_fps)
    except (OSError, ValueError, TypeError):
        pass
    settings.normalize()
    return settings


def save_settings(settings: GameSettings) -> None:
    settings.normalize()
    path = _settings_path()
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(asdict(settings), file, indent=2)
    os.replace(temp_path, path)
