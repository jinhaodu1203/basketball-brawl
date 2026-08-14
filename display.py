"""Window, scaling and fullscreen management for HOOP HAVOC.

The entire game draws into a fixed 960x540 logical coordinate system
(``constants.SCREEN_WIDTH`` / ``SCREEN_HEIGHT``).  Every drawing call, hit box
and mouse test assumes that size.  This module's whole job is to keep that
promise no matter what the player does to the window.

``pygame.SCALED`` is what makes it work: SDL hands the game a surface that is
always 960x540, stretches it to whatever the real window is, letterboxes it to
preserve the aspect ratio, and translates incoming mouse coordinates back into
logical space.  Without it a resized window leaves the game drawing in the
upper-left corner of a much larger surface.

Two SDL details make the difference between "works" and "looks broken", and
both are handled here:

* pygame enables *integer* scaling under SCALED unless
  ``SDL_HINT_RENDER_SCALE_QUALITY`` is set.  With integer scaling a 1440x810
  window shows the game at 1:1 in the middle with a thick black border instead
  of filling the window.  :func:`prepare` sets the hint before the display is
  created.
* pygame also enlarges a new SCALED window to the largest whole multiple of the
  logical size that fits the desktop, which on a 1080p screen means the game
  opens at 1920x1080 - taller than the usable work area.  The window is pulled
  back to its intended size after creation.

That correction has to be made through the Win32 API rather than through
``pygame._sdl2``.  Setting ``Window.size`` that soon after ``set_mode``
corrupts SDL's window state and kills the process with an access violation a
few seconds later - reproduced 5 times out of 5 on pygame 2.6.1 / SDL 2.28.4,
against 0 out of 5 when driving the HWND directly.

On Windows the process is also made DPI aware.  SDL 2.28 leaves it unaware, so
on a 125%/150% display Windows renders the game into a smaller buffer and
bitmap-stretches the result, blurring the art.
"""

import os
import sys

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH

LOGICAL_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

WINDOW_TITLE = "HOOP HAVOC"

# Setting this hint to any value disables pygame's integer scaling, which is
# what lets the picture fill the window at fractional scales.  "linear" suits
# the game's hand-drawn art; "nearest" keeps edges crisp at the cost of uneven
# pixel sizes at fractional scales.  Players can override it from the
# environment.
SCALE_QUALITY = "linear"

# SDL render backends worth trying, per platform.  The first entry that works
# is remembered for the rest of the session.  "metal" is macOS only and always
# fails on Windows, so probing it there just wastes a display teardown.
_RENDERER_CANDIDATES = {
    "darwin": ("metal", "opengl", "software"),
    "win32": ("direct3d11", "direct3d", "opengl", "software"),
}
_FALLBACK_RENDERER_CANDIDATES = ("opengl", "software")

# True once a display has been created with SCALED.  Fullscreen toggling is
# only reliable in that case; without it we have to rebuild the display.
_scaled_active = False

# Renderer override already proven to work on this machine, so later display
# rebuilds don't have to probe again.
_proven_renderer = None

# The window size the player last had, in physical pixels, restored when
# leaving fullscreen.  None until the first window is created, because the
# default depends on the monitor's DPI scaling.
_windowed_size = None


def _log(message):
    """Print diagnostics without ever taking the game down with it.

    Packaged as a windowed (``console=False``) executable there is no console:
    ``sys.stdout`` is ``None`` or a stub that raises.  Diagnostics are never
    important enough to crash the game over.
    """
    try:
        print(message)
    except Exception:
        pass


def renderer_candidates():
    """SDL render backends to probe on this platform, in preference order."""
    return _RENDERER_CANDIDATES.get(sys.platform, _FALLBACK_RENDERER_CANDIDATES)


def prepare_display():
    """Configure SDL before the display exists.

    Must run before ``pygame.init()``; SDL reads these hints when it sets up
    the video subsystem and builds the renderer.  Both are ``setdefault`` so a
    player can still override them from the environment.
    """
    os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", SCALE_QUALITY)
    if sys.platform == "win32":
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")


def _default_window_size():
    """Window size to open at, in physical pixels.

    A DPI-aware process is sized in real pixels, so a 960x540 window would look
    two thirds of its intended size on a 150% display.  Scaling by the monitor
    factor keeps the apparent size right while still rendering at full
    resolution.
    """
    if sys.platform != "win32":
        return LOGICAL_SIZE
    try:
        import ctypes
        import ctypes.wintypes as wt

        hwnd = pygame.display.get_wm_info()["window"]
        dpi = ctypes.windll.user32.GetDpiForWindow(wt.HWND(hwnd))
        if dpi > 0 and dpi != 96:
            return (round(SCREEN_WIDTH * dpi / 96), round(SCREEN_HEIGHT * dpi / 96))
    except Exception as error:  # pre-Win10 user32, no window yet, no wm_info
        _log(f"Could not read the window DPI: {error}")
    return LOGICAL_SIZE


def _apply_renderer(renderer):
    """Force an SDL render backend, or clear the override when ``None``."""
    if renderer is None:
        os.environ.pop("SDL_RENDER_DRIVER", None)
    else:
        os.environ["SDL_RENDER_DRIVER"] = renderer


def _restart_display():
    """Tear the display module down and back up.

    SDL only reads ``SDL_RENDER_DRIVER`` when it creates a renderer, so a
    restart is the only way to make a different backend take effect.
    """
    try:
        pygame.display.quit()
    except pygame.error:
        pass
    pygame.display.init()


def _set_mode(flags):
    """One ``set_mode`` attempt.  Returns the surface, or ``None`` on failure."""
    try:
        screen = pygame.display.set_mode(LOGICAL_SIZE, flags, vsync=0)
    except pygame.error as error:
        _log(f"set_mode(flags={flags:#x}) failed: {error}")
        return None
    pygame.display.set_caption(WINDOW_TITLE)
    return screen


def _resize_window_win32(size):
    """Resize via the Win32 API, keeping the client area exactly ``size``.

    Preferred over pygame._sdl2 on Windows: going through SDL's own window
    object right after ``set_mode`` corrupts its state and crashes the process
    a few seconds later, while driving the HWND directly is stable.
    """
    import ctypes
    import ctypes.wintypes as wt

    try:
        hwnd = pygame.display.get_wm_info()["window"]
    except (KeyError, pygame.error) as error:
        _log(f"No window handle available: {error}")
        return False

    user32 = ctypes.windll.user32
    style = user32.GetWindowLongW(wt.HWND(hwnd), -16)      # GWL_STYLE
    exstyle = user32.GetWindowLongW(wt.HWND(hwnd), -20)    # GWL_EXSTYLE
    rect = wt.RECT(0, 0, size[0], size[1])
    user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, exstyle)
    ok = user32.SetWindowPos(
        wt.HWND(hwnd), None, 0, 0,
        rect.right - rect.left, rect.bottom - rect.top,
        0x0002 | 0x0004,                                   # NOMOVE | NOZORDER
    )
    if not ok:
        _log(f"SetWindowPos to {size} failed: {ctypes.get_last_error()}")
    return bool(ok)


def _resize_window(size):
    """Resize the OS window without touching the logical surface.

    Used to undo pygame's automatic enlargement of SCALED windows and to
    restore the player's window size when leaving fullscreen.
    """
    if sys.platform == "win32" and _resize_window_win32(size):
        return True
    try:
        from pygame._sdl2 import video as sdl2_video

        sdl2_video.Window.from_display_module().size = size
        return True
    except Exception as error:  # ImportError, pygame.error, AttributeError...
        _log(f"Could not resize the window to {size}: {error}")
        return False


def _create_scaled(flags):
    """Create a SCALED display, probing render backends if the default fails."""
    scaled_flags = flags | pygame.SCALED

    # A backend we already proved works this session, else SDL's own choice.
    _apply_renderer(_proven_renderer)
    screen = _set_mode(scaled_flags)
    if screen is not None:
        return screen, _proven_renderer

    for renderer in renderer_candidates():
        _restart_display()
        _apply_renderer(renderer)
        screen = _set_mode(scaled_flags)
        if screen is not None:
            _log(f"Scaled display enabled with SDL renderer: {renderer}")
            return screen, renderer
        _log(f"SDL renderer '{renderer}' cannot drive a scaled display.")

    return None, None


def create_screen(fullscreen):
    """Create (or rebuild) the display and return the 960x540 game surface.

    Falls back through progressively less capable modes rather than failing:
    scaled fullscreen -> scaled window -> plain fixed-size window.
    """
    global _scaled_active, _proven_renderer, _windowed_size

    pygame.event.clear()

    mode_flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
    screen, renderer = _create_scaled(mode_flags)

    if screen is None and fullscreen:
        # Scaled fullscreen is impossible here; a plain FULLSCREEN surface
        # would be desktop-sized and leave the game drawing in one corner, so
        # go back to a window instead.
        _log("Scaled fullscreen is unavailable; falling back to a window.")
        screen, renderer = _create_scaled(pygame.RESIZABLE)
        fullscreen = False

    if screen is not None:
        _proven_renderer = renderer
        _scaled_active = True
        if not fullscreen:
            # pygame enlarges new SCALED windows to the biggest whole multiple
            # of 960x540 that fits the desktop; put it back.
            if _windowed_size is None:
                _windowed_size = _default_window_size()
            _resize_window(_windowed_size)
        pygame.event.clear()
        return screen

    # No SCALED anywhere.  Deliberately drop RESIZABLE too: a resizable window
    # without SCALED is exactly the combination that strands the game in the
    # upper-left corner.  A fixed window always looks right.
    _apply_renderer(None)
    _restart_display()
    _scaled_active = False
    _proven_renderer = None
    _log("Scaled display unavailable; using a fixed-size 960x540 window.")

    screen = _set_mode(0)
    if screen is None:
        # Last resort - let the error escape rather than return None and fail
        # somewhere far away with a confusing traceback.
        screen = pygame.display.set_mode(LOGICAL_SIZE)
        pygame.display.set_caption(WINDOW_TITLE)
    pygame.event.clear()
    return screen


def is_fullscreen():
    """Whether the display is currently a fullscreen one."""
    screen = pygame.display.get_surface()
    if screen is None:
        return False
    return bool(screen.get_flags() & pygame.FULLSCREEN)


def set_fullscreen(fullscreen, allow_rebuild=True):
    """Switch between fullscreen and windowed, returning the game surface.

    Prefers :func:`pygame.display.toggle_fullscreen`, which keeps the existing
    window, renderer *and surface object* alive.  Rebuilding the display with
    ``set_mode`` instead fails outright once a SCALED renderer exists ("failed
    to create renderer"), so the rebuild is only a fallback.

    With ``allow_rebuild=False`` the switch is attempted in place or not at
    all, and ``None`` is returned if it could not be done.  Callers use that
    when something else is still holding the current surface and a rebuild
    would pull it out from under them.
    """
    global _windowed_size

    def give_up(reason):
        if not allow_rebuild:
            _log(f"In-place fullscreen switch unavailable: {reason}")
            return None
        return create_screen(fullscreen)

    screen = pygame.display.get_surface()

    if screen is None or not _scaled_active:
        return give_up("no scaled display")

    if is_fullscreen() == bool(fullscreen):
        return screen

    if fullscreen:
        _windowed_size = pygame.display.get_window_size()

    try:
        pygame.display.toggle_fullscreen()
    except pygame.error as error:
        return give_up(f"toggle_fullscreen failed ({error})")

    # Let SDL finish the mode change before anyone draws again.
    pygame.event.pump()

    screen = pygame.display.get_surface()
    if screen is None or screen.get_size() != LOGICAL_SIZE:
        _log("Display was lost while toggling fullscreen; rebuilding.")
        return create_screen(fullscreen)

    if not fullscreen:
        # SDL leaves the window at the desktop size after a fullscreen exit, so
        # put the player's own window size back.
        _resize_window(_windowed_size or _default_window_size())

    pygame.event.clear()
    return screen
