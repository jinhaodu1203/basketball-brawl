"""Basketball Brawl application entry point."""

import ctypes
import os
import sys

import pygame

from audio import init_audio, get_audio

from constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from game import play_session
from settings import load_settings, save_settings
from localization import create_fonts, set_language
from ui import credits_menu, feedback_menu, how_to_play_menu, main_menu, settings_menu


# ---------------------------------------------------------------------------
# Windows IME guard
# ---------------------------------------------------------------------------
# Player 1 uses Left Shift as the ability key. Some Chinese IMEs use a single
# Shift press to toggle Chinese/English mode. During actual gameplay we detach
# the IME context from the Pygame window, then restore the exact previous
# context as soon as the player returns to the menu.
#
# This is Windows-only. macOS/Linux simply skip these functions.
_saved_ime_context = None
_saved_ime_hwnd = None


def _imm_associate_context(hwnd, context):
    """Call Win32 ImmAssociateContext with 64-bit-safe handle types."""
    imm32 = ctypes.WinDLL("imm32", use_last_error=True)
    func = imm32.ImmAssociateContext
    func.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    func.restype = ctypes.c_void_p

    hwnd_arg = ctypes.c_void_p(int(hwnd))
    context_arg = (
        ctypes.c_void_p(int(context))
        if context
        else ctypes.c_void_p()
    )
    return func(hwnd_arg, context_arg)


def disable_windows_ime_for_gameplay():
    """Disable IME only for the current HOOP HAVOC window while playing."""
    global _saved_ime_context, _saved_ime_hwnd

    if sys.platform != "win32":
        return

    # Avoid stacking multiple detach operations.
    if _saved_ime_hwnd is not None:
        return

    try:
        window_info = pygame.display.get_wm_info()
        hwnd = window_info.get("window")
        if not hwnd:
            return

        previous_context = _imm_associate_context(hwnd, None)

        _saved_ime_hwnd = int(hwnd)
        _saved_ime_context = previous_context

        print("Windows IME disabled for gameplay.")
    except Exception as error:
        # Never prevent the game from launching because of an IME API issue.
        _saved_ime_hwnd = None
        _saved_ime_context = None
        print(f"Windows IME guard could not be enabled: {error}")


def restore_windows_ime_after_gameplay():
    """Restore the window's original IME context after leaving a match."""
    global _saved_ime_context, _saved_ime_hwnd

    if sys.platform != "win32":
        return

    if _saved_ime_hwnd is None:
        return

    try:
        _imm_associate_context(
            _saved_ime_hwnd,
            _saved_ime_context,
        )
        print("Windows IME restored after gameplay.")
    except Exception as error:
        print(f"Windows IME guard could not be restored: {error}")
    finally:
        _saved_ime_context = None
        _saved_ime_hwnd = None


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
    audio = get_audio()
    audio.set_master_volume(settings.master_volume)
    audio.set_music_volume(settings.music_volume)
    audio.set_sfx_volume(settings.sfx_volume)


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

            # Keep Left Shift as the ability key, but stop Windows IME from
            # treating the same key press as a Chinese/English mode toggle.
            disable_windows_ime_for_gameplay()
            try:
                play_session(
                    screen,
                    font,
                    small_font,
                    title_font,
                    assets_dir,
                    show_fps=settings.show_fps,
                )
            finally:
                # Always restore the original IME context, even if the player
                # quits the match through an unusual path or an exception.
                restore_windows_ime_after_gameplay()

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
                screen = create_screen(settings.fullscreen)
                pygame.display.set_caption("HOOP HAVOC")
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

    # Safety restore in case main-loop behavior changes in a future version.
    restore_windows_ime_after_gameplay()
    save_settings(settings)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
