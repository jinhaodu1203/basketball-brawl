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
    """Create the game display and retry true scaled fullscreen on macOS.

    pygame.SCALED is required because the whole game uses a logical 960x540
    coordinate system. Plain FULLSCREEN would create a desktop-sized surface
    and leave the game drawing only in the upper-left corner.

    If the current SDL renderer cannot create scaled fullscreen, restart only
    the display module and retry with several renderer backends.
    """
    pygame.event.clear()

    window_flags = pygame.RESIZABLE
    fullscreen_flags = pygame.FULLSCREEN | pygame.SCALED

    if not fullscreen:
        return pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            window_flags,
        )

    # First try the renderer selected by SDL/macOS.
    try:
        screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            fullscreen_flags,
            vsync=0,
        )
        print("Fullscreen enabled with SDL default renderer.")
        return screen
    except pygame.error as first_error:
        print(f"Default fullscreen renderer failed: {first_error}")

    # Reinitialize the display and retry renderer backends commonly available
    # on macOS. The environment variable is read when SDL recreates the
    # renderer, so display.quit()/display.init() is required here.
    renderer_candidates = ("metal", "opengl", "software")

    for renderer in renderer_candidates:
        try:
            pygame.display.quit()
            os.environ["SDL_RENDER_DRIVER"] = renderer
            pygame.display.init()

            screen = pygame.display.set_mode(
                (SCREEN_WIDTH, SCREEN_HEIGHT),
                fullscreen_flags,
                vsync=0,
            )
            pygame.display.set_caption("HOOP HAVOC")
            print(f"Fullscreen enabled with SDL renderer: {renderer}")
            return screen
        except pygame.error as error:
            print(f"Fullscreen renderer '{renderer}' failed: {error}")

    # Clear the renderer override before returning to a window.
    os.environ.pop("SDL_RENDER_DRIVER", None)

    try:
        pygame.display.quit()
        pygame.display.init()
    except pygame.error:
        pass

    print(
        "True scaled fullscreen is unavailable on this SDL/Pygame setup; "
        "returning to windowed mode."
    )
    return pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        window_flags,
    )


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
    pygame.display.set_caption("HOOP HAVOC")

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
                pygame.display.set_caption("HOOP HAVOC")
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
