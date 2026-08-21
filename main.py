"""Basketball Brawl application entry point."""

import ctypes
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

    # Safety restore in case main-loop behavior changes in a future version.
    restore_windows_ime_after_gameplay()
    save_settings(settings)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
