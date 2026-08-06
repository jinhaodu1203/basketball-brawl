"""Basketball Brawl application entry point."""

import os
import sys

import pygame

from constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from game import play_session
from settings import load_settings, save_settings
from ui import main_menu, settings_menu


def create_screen(fullscreen: bool):
    flags = pygame.FULLSCREEN if fullscreen else 0
    return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)


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

    font = pygame.font.SysFont(None, 30)
    small_font = pygame.font.SysFont(None, 20)
    title_font = pygame.font.SysFont(None, 48)
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
        elif action == "settings":
            old_fullscreen = settings.fullscreen
            settings, result = settings_menu(
                screen, font, small_font, title_font, settings
            )
            save_settings(settings)
            apply_audio_settings(settings)
            if settings.fullscreen != old_fullscreen:
                screen = create_screen(settings.fullscreen)
            if result == "quit":
                running = False
        else:
            running = False

        clock.tick(FPS)

    save_settings(settings)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
