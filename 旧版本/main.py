"""Basketball Brawl application entry point."""

import os
import sys

import pygame

from constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from game import play_session
from settings import load_settings, save_settings
from localization import create_fonts, set_language
from ui import credits_menu, how_to_play_menu, main_menu, settings_menu


def create_screen(fullscreen: bool):
    """Create the game window.

    In fullscreen mode use pygame.SCALED so the game keeps its logical
    960x540 coordinate system while SDL scales it to the Mac's real display
    size. This avoids the unused black strip caused by requesting a literal
    960x540 fullscreen display mode.
    """
    if fullscreen:
        flags = pygame.FULLSCREEN | pygame.SCALED
        return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))


def apply_audio_settings(settings) -> None:
    if pygame.mixer.get_init():
        pygame.mixer.music.set_volume(settings.master_volume / 100.0)


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        # The game remains playable on machines without an audio device.
        pass

    settings = load_settings()
    screen = create_screen(settings.fullscreen)
    pygame.display.set_caption("Basketball Brawl")

    set_language(settings.language)
    font, small_font, title_font = create_fonts(settings.language)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    clock = pygame.time.Clock()
    apply_audio_settings(settings)

    running = True
    while running:
        action = main_menu(screen, font, small_font, title_font)

        if action == "play":
            play_session(
                screen,
                font,
                small_font,
                title_font,
                assets_dir,
                show_fps=settings.show_fps,
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
                screen = create_screen(settings.fullscreen)
            if result == "quit":
                running = False
        elif action == "credits":
            if credits_menu(screen, font, small_font, title_font) == "quit":
                running = False
        else:
            running = False

        clock.tick(FPS)

    save_settings(settings)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
