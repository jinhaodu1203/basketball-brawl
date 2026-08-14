"""Basketball Brawl application entry point."""

import os
import sys

import pygame

from audio import init_audio, get_audio

from constants import FPS
from display import create_screen, prepare_display, set_fullscreen
from game import play_session
from settings import load_settings, save_settings
from localization import create_fonts, set_language
from ui import credits_menu, feedback_menu, how_to_play_menu, main_menu, settings_menu


def apply_audio_settings(settings) -> None:
    audio = get_audio()
    audio.set_master_volume(settings.master_volume)
    audio.set_music_volume(settings.music_volume)
    audio.set_sfx_volume(settings.sfx_volume)


def main():
    # SDL reads its scaling and DPI hints while the video subsystem starts up,
    # so this has to happen before pygame.init().
    prepare_display()

    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        # The game remains playable on machines without an audio device.
        pass

    settings = load_settings()
    screen = create_screen(settings.fullscreen)

    set_language(settings.language)
    font, small_font, title_font = create_fonts(settings.language)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    clock = pygame.time.Clock()

    # 初始化 HOOP HAVOC 音频系统。
    audio = init_audio(assets_dir)
    apply_audio_settings(settings)
    audio.play_music("menu")

    running = True
    while running:
        action = main_menu(screen, font, small_font, title_font)

        if action == "play":
            # 从主菜单音乐切换到比赛音乐。
            audio.play_music(
                "match",
                fade_ms=450,
            )

            play_session(
                screen,
                font,
                small_font,
                title_font,
                assets_dir,
                show_fps=settings.show_fps,
            )

            # 比赛结束 / 返回菜单。
            audio.play_music(
                "menu",
                fade_ms=450,
            )
        elif action == "how_to_play":
            if how_to_play_menu(screen, font, small_font, title_font) == "quit":
                running = False
        elif action == "settings":
            old_fullscreen = settings.fullscreen
            settings, result = settings_menu(
                screen, font, small_font, title_font, settings
            )
            set_language(settings.language)
            font, small_font, title_font = create_fonts(settings.language)
            save_settings(settings)
            apply_audio_settings(settings)
            if settings.fullscreen != old_fullscreen:
                # settings_menu already switched in place; this reapplies it for
                # the case where that needed a display rebuild.  Keep the old
                # surface if nothing was handed back.
                screen = set_fullscreen(settings.fullscreen) or screen
            if result == "quit":
                running = False
        elif action == "credits":
            if credits_menu(screen, font, small_font, title_font) == "quit":
                running = False
        elif action == "feedback":
            if feedback_menu(screen, font, small_font, title_font) == "quit":
                running = False
        else:
            running = False

        clock.tick(FPS)

    save_settings(settings)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
