# HOOP HAVOC audio manager

from __future__ import annotations

import os
import pygame


class AudioManager:
    SFX_NAMES = (
        "shot",
        "pass",
        "rim",
        "score",
        "dunk",
        "block",
        "rebound",
        "steal",
        "dash",
        "slam",
        "double_jump",
        "clone",
        "bounce",
        "whistle",
    )

    MUSIC_NAMES = (
        "menu",
        "match",
        "win",
    )

    SUPPORTED_EXTENSIONS = (".ogg", ".wav", ".mp3")

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.audio_dir = os.path.join(assets_dir, "audio")
        self.music_dir = os.path.join(self.audio_dir, "music")
        self.sfx_dir = os.path.join(self.audio_dir, "sfx")

        self.enabled = bool(pygame.mixer.get_init())
        self.sounds = {}
        self.music_paths = {}
        self.current_music = None

        self.master_volume = 0.80
        self.music_volume = 1.00
        self.sfx_volume = 1.00
        self.music_scale = 1.00

        if self.enabled:
            self._load_all()

    def _find_audio_file(self, folder: str, name: str):
        for extension in self.SUPPORTED_EXTENSIONS:
            path = os.path.join(folder, name + extension)
            if os.path.isfile(path):
                return path
        return None

    def _load_all(self):
        for name in self.SFX_NAMES:
            path = self._find_audio_file(self.sfx_dir, name)
            if not path:
                continue

            try:
                self.sounds[name] = pygame.mixer.Sound(path)
            except (pygame.error, OSError):
                continue

        for name in self.MUSIC_NAMES:
            path = self._find_audio_file(self.music_dir, name)
            if path:
                self.music_paths[name] = path

        self._refresh_volumes()

    @staticmethod
    def _percent_to_float(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 100.0
        return max(0.0, min(100.0, value)) / 100.0

    def _music_output_volume(self):
        return max(
            0.0,
            min(
                1.0,
                self.master_volume
                * self.music_volume
                * self.music_scale,
            ),
        )

    def _sfx_output_volume(self):
        return max(
            0.0,
            min(
                1.0,
                self.master_volume * self.sfx_volume,
            ),
        )

    def _refresh_volumes(self):
        if not self.enabled:
            return

        try:
            pygame.mixer.music.set_volume(
                self._music_output_volume()
            )
        except pygame.error:
            pass

        # 所有音效使用完全相同的最终音量。
        sfx_output = self._sfx_output_volume()
        for sound in self.sounds.values():
            try:
                sound.set_volume(sfx_output)
            except pygame.error:
                pass

    def set_master_volume(self, value):
        self.master_volume = self._percent_to_float(value)
        self._refresh_volumes()

    def set_music_volume(self, value):
        self.music_volume = self._percent_to_float(value)
        self._refresh_volumes()

    def set_sfx_volume(self, value):
        self.sfx_volume = self._percent_to_float(value)
        self._refresh_volumes()

    def set_music_scale(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 1.0

        self.music_scale = max(0.0, min(1.0, value))
        self._refresh_volumes()

    def play_music(self, name, loops=-1, fade_ms=350):
        if not self.enabled:
            return False

        path = self.music_paths.get(name)
        if not path:
            return False

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(
                self._music_output_volume()
            )
            pygame.mixer.music.play(
                loops=loops,
                fade_ms=max(0, int(fade_ms)),
            )
            self.current_music = name
            return True
        except (pygame.error, OSError, ValueError):
            return False

    def stop_music(self, fade_ms=250):
        if not self.enabled:
            return

        try:
            if fade_ms:
                pygame.mixer.music.fadeout(max(0, int(fade_ms)))
            else:
                pygame.mixer.music.stop()
        except pygame.error:
            pass

        self.current_music = None

    def play_sfx(self, name, volume_scale=1.0):
        if not self.enabled:
            return False

        # 旧的 rim_soft 事件统一映射到 rim。
        if name == "rim_soft":
            name = "rim"

        sound = self.sounds.get(name)
        if sound is None:
            return False

        try:
            # 所有 SFX 每次播放前都使用同一个最终音量。
            sfx_volume = self._sfx_output_volume()

            # 根据动作重要程度做少量听感层次调整。
            if name == "bounce":
                # 运球声更清楚。
                sfx_volume = min(1.0, sfx_volume * 1.35)
            elif name == "rim":
                # 磕篮筐不要压过其他关键音效。
                sfx_volume = min(1.0, sfx_volume * 0.55)
            elif name == "score":
                # 进球声更突出。
                sfx_volume = min(1.0, sfx_volume * 1.25)

            sound.set_volume(sfx_volume)
            sound.play()
            return True
        except pygame.error:
            return False


_AUDIO_MANAGER = None


def init_audio(assets_dir):
    global _AUDIO_MANAGER
    _AUDIO_MANAGER = AudioManager(assets_dir)
    return _AUDIO_MANAGER


def get_audio():
    global _AUDIO_MANAGER

    if _AUDIO_MANAGER is None:
        class _SilentAudio:
            def set_master_volume(self, *args, **kwargs):
                pass

            def set_music_volume(self, *args, **kwargs):
                pass

            def set_sfx_volume(self, *args, **kwargs):
                pass

            def set_music_scale(self, *args, **kwargs):
                pass

            def play_music(self, *args, **kwargs):
                return False

            def stop_music(self, *args, **kwargs):
                pass

            def play_sfx(self, *args, **kwargs):
                return False

        _AUDIO_MANAGER = _SilentAudio()

    return _AUDIO_MANAGER
