"""菜单、HUD、暂停与结算界面。"""

import os
import math
import sys
import webbrowser
from urllib.parse import quote
import pygame

from audio import get_audio
from display import set_fullscreen

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    COLOR_TEXT,
    SCORE_POPUP_DURATION_FRAMES, SCORE_POPUP_COLOR,
)
from characters import CHARACTER_ORDER, CHARACTERS
from arenas import ARENA_ORDER, ARENAS
from localization import create_fonts, set_language, get_language, tr, tr_list

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")
_IMAGE_CACHE = {}
_BACKDROP_CACHE = {}
_SHOWCASE_FRAME_CACHE = {}


def _remove_connected_dark_background(image, threshold=72):
    """Remove only dark pixels connected to the image border.

    Some portrait PNG files look transparent in image viewers but still contain
    an opaque or semi-opaque near-black matte around the character.  This flood
    fill starts from all four edges, supports diagonal connections, and removes
    only the connected matte.  Dark clothing inside the character silhouette is
    preserved because it is not connected to the outer border.
    """
    surface = image.convert_alpha().copy()
    width, height = surface.get_size()
    if width <= 0 or height <= 0:
        return surface

    pixels = pygame.PixelArray(surface)
    surface.unlock()

    def is_background(x, y):
        r, g, b, a = surface.get_at((x, y))
        # Fully transparent and nearly transparent pixels are always background.
        if a <= 12:
            return True
        # Remove neutral near-black matte pixels, including antialiased edges.
        darkest = max(r, g, b)
        spread = max(r, g, b) - min(r, g, b)
        return darkest <= threshold and spread <= 28

    stack = []
    visited = bytearray(width * height)

    for x in range(width):
        stack.append((x, 0))
        if height > 1:
            stack.append((x, height - 1))
    for y in range(height):
        stack.append((0, y))
        if width > 1:
            stack.append((width - 1, y))

    neighbours = (
        (-1, -1), (0, -1), (1, -1),
        (-1, 0),            (1, 0),
        (-1, 1),  (0, 1),  (1, 1),
    )

    while stack:
        x, y = stack.pop()
        index = y * width + x
        if visited[index]:
            continue
        visited[index] = 1
        if not is_background(x, y):
            continue

        surface.set_at((x, y), (0, 0, 0, 0))
        for dx, dy in neighbours:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                n_index = ny * width + nx
                if not visited[n_index]:
                    stack.append((nx, ny))

    # Clean remaining almost-transparent black pixels that can become visible
    # after smooth scaling and per-surface alpha changes.
    for y in range(height):
        for x in range(width):
            r, g, b, a = surface.get_at((x, y))
            if a <= 18:
                surface.set_at((x, y), (0, 0, 0, 0))

    return surface.convert_alpha()


def _ease_out_cubic(value):
    value = max(0.0, min(1.0, value))
    return 1.0 - (1.0 - value) ** 3


def _lerp(a, b, t):
    return a + (b - a) * t


def _smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _showcase_frames(character_id, action, target_height=250):
    """Load and cache one character action sheet as individual UI frames."""
    config = CHARACTERS.get(character_id, {})
    frame_count = int(config.get("frame_counts", {}).get(action, 0) or 0)
    sprite_folder = config.get("sprite_folder", character_id)
    cache_key = (character_id, sprite_folder, action, frame_count, target_height)

    cached = _SHOWCASE_FRAME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if frame_count <= 0:
        _SHOWCASE_FRAME_CACHE[cache_key] = []
        return []

    path = os.path.join(ASSET_ROOT, "characters", sprite_folder, f"{action}.png")
    if not os.path.isfile(path):
        _SHOWCASE_FRAME_CACHE[cache_key] = []
        return []

    try:
        sheet = pygame.image.load(path).convert_alpha()
        frame_width = sheet.get_width() // frame_count
        frame_height = sheet.get_height()
        if frame_width <= 0 or frame_height <= 0:
            _SHOWCASE_FRAME_CACHE[cache_key] = []
            return []

        scale = target_height / frame_height
        target_width = max(1, int(frame_width * scale))
        frames = []

        for index in range(frame_count):
            source_rect = pygame.Rect(index * frame_width, 0, frame_width, frame_height)
            frame = sheet.subsurface(source_rect).copy().convert_alpha()
            frame = _remove_connected_dark_background(frame)
            frame = _crop_transparent_padding(frame, padding=1)

            if frame.get_height() <= 0:
                continue
            visible_scale = target_height / frame.get_height()
            width = max(1, int(frame.get_width() * visible_scale))
            height = max(1, int(frame.get_height() * visible_scale))
            frame = pygame.transform.scale(frame, (width, height)).convert_alpha()
            frames.append(frame)

        _SHOWCASE_FRAME_CACHE[cache_key] = frames
        return frames
    except (pygame.error, OSError, ValueError):
        _SHOWCASE_FRAME_CACHE[cache_key] = []
        return []



def _showcase_clone_frames(character_id, action="idle", target_height=250):
    """Load DUKE's real Blood Echo sprite frames for the home showcase."""
    config = CHARACTERS.get(character_id, {})
    sprite_folder = config.get("clone_sprite_folder")
    frame_count = int(config.get("clone_frame_counts", {}).get(action, 0) or 0)
    if not sprite_folder or frame_count <= 0:
        return []

    cache_key = ("clone", character_id, sprite_folder, action, frame_count, target_height)
    cached = _SHOWCASE_FRAME_CACHE.get(cache_key)
    if cached is not None:
        return cached

    path = os.path.join(ASSET_ROOT, "characters", sprite_folder, f"{action}.png")
    if not os.path.isfile(path):
        _SHOWCASE_FRAME_CACHE[cache_key] = []
        return []

    try:
        sheet = pygame.image.load(path).convert_alpha()
        frame_width = sheet.get_width() // frame_count
        frame_height = sheet.get_height()
        frames = []

        for index in range(frame_count):
            source_rect = pygame.Rect(index * frame_width, 0, frame_width, frame_height)
            frame = sheet.subsurface(source_rect).copy().convert_alpha()
            frame = _remove_connected_dark_background(frame)
            frame = _crop_transparent_padding(frame, padding=1)
            if frame.get_height() <= 0:
                continue

            visible_scale = target_height / frame.get_height()
            width = max(1, int(frame.get_width() * visible_scale))
            height = max(1, int(frame.get_height() * visible_scale))
            frame = pygame.transform.scale(frame, (width, height)).convert_alpha()
            frames.append(frame)

        _SHOWCASE_FRAME_CACHE[cache_key] = frames
        return frames
    except (pygame.error, OSError, ValueError):
        _SHOWCASE_FRAME_CACHE[cache_key] = []
        return []

def _showcase_routine(character_id):
    """Main-menu personal show: RUN -> REAL SKILL -> RUN.

    Every character enters already running, performs the real gameplay ability,
    then immediately returns to the run animation.  Because the next character
    also starts with run, roster transitions visually connect without an idle
    pose between fighters.

    Tuple:
        (action_name, loops, seconds_per_frame, horizontal_motion, skill_type)
    """
    routines = {
        # DJH: run in -> real Lightning Dash -> keep running.
        "djh": [
            ("run",      2, 0.0722, 36, None),
            ("attack_1", 1, 0.0889, 0, "dash"),
            ("run",      2, 0.0722, 42, None),
        ],

        # BRAX: run in -> real Ground Slam -> immediately run again.
        "gorilla": [
            ("run",      2, 0.0944, 30, None),
            ("attack_3", 1, 0.1111, 0, "slam"),
            ("run",      2, 0.0944, 34, None),
        ],

        # KAGE: run in -> real Double Jump -> land into running.
        "ninja": [
            ("run",  2, 0.0667, 38, None),
            ("jump", 2, 0.0611, 0, "double_jump"),
            ("run",  2, 0.0667, 42, None),
        ],

        # DUKE: run in -> summon Blood Echo -> both continue running.
        "duke": [
            ("run",      2, 0.0778, 34, None),
            ("attack_2", 1, 0.0944, 0, "clone"),
            # Hold the just-summoned Blood Echo on screen a little longer.
            ("idle",     2, 0.1200, 0, "clone_hold"),
            ("run",      2, 0.0778, 40, "clone_run"),
        ],

        # ACE：跑入 -> Deadeye / Shot -> 继续跑动。
        "ace": [
            # 跑入场。
            ("run", 2, 0.0720, 34, None),

            # 举弓并逐渐拉满。
            ("deadeye", 1, 0.0750, 0, "deadeye"),

            # 拉满后真正保持瞄准。
            ("aim", 4, 0.1800, 0, "deadeye_hold"),

            # 技能展示结束后继续跑。
            ("run", 2, 0.0720, 40, None),
        ],
        "ema": [
            # 正常速度入场
            ("walk", 2, 0.0720, 34, None),

            # 短暂停留
            ("idle", 1, 0.0800, 0, None),

            # 正常速度释放石化凝视
            ("special", 2, 0.0750, 0, "petrify"),

            # 技能结束停顿
            ("idle", 1, 0.0800, 0, "petrify_after"),

            # 正常速度离场
            ("walk", 2, 0.0720, 40, None),
        ],
    }
    return routines.get(character_id, [("run", 3, 0.0778, 36, None)])

def _showcase_timeline(character_id):
    """Build a lightweight timeline and return (segments, total_duration)."""
    segments = []
    elapsed = 0.0

    for item in _showcase_routine(character_id):
        action, loops, frame_seconds, motion, skill_type = item

        frames = _showcase_frames(character_id, action)
        if not frames:
            continue

        duration = len(frames) * max(1, loops) * frame_seconds
        segments.append({
            "action": action,
            "frames": frames,
            "loops": max(1, loops),
            "frame_seconds": frame_seconds,
            "motion": motion,
            "skill_type": skill_type,
            "start": elapsed,
            "end": elapsed + duration,
        })
        elapsed += duration

    return segments, max(elapsed + 0.08, 1.0)

def _draw_character_carousel(screen, font, small_font, elapsed):
    """Character personal showcase used by the main menu.

    Only one fighter appears at a time.  The fighter performs a hand-authored
    sequence assembled from the supplied sprite actions; after the sequence
    finishes, the next roster member automatically takes the stage.
    """
    character_order = list(CHARACTER_ORDER)
    if not character_order:
        return

    # Build each routine duration so character switching follows the animation,
    # rather than using an arbitrary fixed carousel timer.
    timelines = []
    cycle_total = 0.0
    for cid in character_order:
        segments, duration = _showcase_timeline(cid)
        timelines.append((cid, segments, duration))
        cycle_total += duration

    if cycle_total <= 0:
        return

    cycle_time = elapsed % cycle_total
    character_id = character_order[0]
    segments = []
    routine_duration = 1.0
    local_time = 0.0

    cursor = 0.0
    for cid, cid_segments, duration in timelines:
        if cycle_time < cursor + duration:
            character_id = cid
            segments = cid_segments
            routine_duration = duration
            local_time = cycle_time - cursor
            break
        cursor += duration

    config = CHARACTERS.get(character_id, {})
    accent = config.get("ui_accent", config.get("color", (255, 132, 55)))

    # Find the action that owns the current moment.
    active = None
    for segment in segments:
        if segment["start"] <= local_time < segment["end"]:
            active = segment
            break
    if active is None and segments:
        active = segments[-1]

    # Stage baseline stays consistent with the old home menu composition.
    stage_left = 66
    stage_right = 492
    baseline_y = 512
    pygame.draw.line(screen, accent, (stage_left, baseline_y), (stage_right, baseline_y), 3)

    if active:
        action_time = max(0.0, local_time - active["start"])
        frames = active["frames"]
        frame_index = int(action_time / active["frame_seconds"]) % len(frames)
        frame = frames[frame_index]

        action_duration = max(0.001, active["end"] - active["start"])
        action_progress = max(0.0, min(1.0, action_time / action_duration))

        # Ordinary showcase movement.
        motion = active["motion"]
        actor_x = 272 + int(motion * (action_progress - 0.5))
        actor_y = baseline_y - 5

        skill_type = active.get("skill_type")

        # --------------------------------------------------------------
        # DJH: reproduce the real Dash.
        # Gameplay uses dash_speed=17 for dash_duration=11 frames, so the
        # showcase covers roughly the same ~187 px burst.
        # --------------------------------------------------------------
        if skill_type == "dash":
            dash_distance = float(config.get("dash_speed", 17.0)) * float(
                config.get("dash_duration", 11)
            )
            dash_t = _ease_out_cubic(action_progress)
            actor_x = int(176 + dash_distance * dash_t)

            # Gameplay feedback-style streak particles behind the dash.
            fx = pygame.Surface((430, 260), pygame.SRCALPHA)
            local_x = actor_x - 60
            for i in range(8):
                trail_x = local_x - i * 18
                alpha = max(20, 185 - i * 20)
                pygame.draw.line(
                    fx,
                    (225, 240, 255, alpha),
                    (trail_x, 140 + (i % 3) * 8),
                    (trail_x - 30, 140 + (i % 3) * 8),
                    3,
                )
            screen.blit(fx, (60, baseline_y - 245))

            # Stronger dash afterimages.
            for offset, alpha in ((34, 90), (64, 58), (94, 30)):
                ghost = frame.copy()
                ghost.set_alpha(alpha)
                screen.blit(
                    ghost,
                    ghost.get_rect(midbottom=(actor_x - offset, actor_y)),
                )

            # Electric speed shards.
            electric = pygame.Surface((430, 250), pygame.SRCALPHA)
            for i in range(14):
                y = 64 + (i * 15) % 145
                x = 38 + (i * 29) % 315
                pygame.draw.line(
                    electric,
                    (170, 225, 255, 180),
                    (x, y),
                    (x + 17, y - 8),
                    3,
                )
                pygame.draw.line(
                    electric,
                    (255, 255, 255, 125),
                    (x + 17, y - 8),
                    (x + 30, y + 2),
                    2,
                )
            screen.blit(electric, (62, baseline_y - 240))



        # --------------------------------------------------------------
        # BRAX: reproduce Ground Slam.
        # Gameplay plays attack_3 and fires orange slam feedback at ground.
        # --------------------------------------------------------------
        elif skill_type == "slam":
            actor_x = 272

            # Main impact timing.  The strongest moment happens just after the
            # attack pose reaches the floor.
            slam_peak = max(
                0.0,
                1.0 - abs(action_progress - 0.52) / 0.20
            )

            if slam_peak > 0:
                # ----------------------------------------------------------
                # 1) Huge layered ground shockwaves
                # ----------------------------------------------------------
                impact = pygame.Surface((520, 220), pygame.SRCALPHA)
                cx, cy = 260, 166

                ring_specs = [
                    (120, 24, 255, 210, 120, 230, 5),
                    (180, 34, 255, 155, 65, 195, 4),
                    (250, 48, 255, 105, 35, 150, 4),
                    (330, 66, 255, 80, 20, 100, 3),
                ]

                for (
                    base_w,
                    base_h,
                    r,
                    g,
                    b,
                    alpha_base,
                    stroke,
                ) in ring_specs:
                    width = int(base_w + 130 * slam_peak)
                    height = int(base_h + 36 * slam_peak)
                    rect = pygame.Rect(0, 0, width, height)
                    rect.center = (cx, cy)

                    pygame.draw.ellipse(
                        impact,
                        (r, g, b, int(alpha_base * slam_peak)),
                        rect,
                        stroke,
                    )

                # Inner molten glow on the ground.
                glow_rect = pygame.Rect(0, 0, 180, 38)
                glow_rect.center = (cx, cy)
                pygame.draw.ellipse(
                    impact,
                    (255, 205, 105, int(150 * slam_peak)),
                    glow_rect,
                )

                screen.blit(
                    impact,
                    impact.get_rect(midbottom=(actor_x, baseline_y + 18)),
                )

                # ----------------------------------------------------------
                # 2) Giant radial ground cracks
                # ----------------------------------------------------------
                cracks = pygame.Surface((520, 230), pygame.SRCALPHA)
                ccx, ccy = 260, 182

                crack_vectors = [
                    (-210, -28),
                    (-175, -55),
                    (-145, -18),
                    (-110, -76),
                    (-72, -28),
                    (-42, -92),
                    (42, -92),
                    (72, -28),
                    (110, -76),
                    (145, -18),
                    (175, -55),
                    (210, -28),
                ]

                crack_alpha = int(245 * slam_peak)

                for i, (vx, vy) in enumerate(crack_vectors):
                    mid_x = ccx + int(vx * 0.48)
                    mid_y = ccy + int(vy * 0.48)

                    # Main crack.
                    pygame.draw.line(
                        cracks,
                        (255, 125, 45, crack_alpha),
                        (ccx, ccy),
                        (mid_x, mid_y),
                        5,
                    )
                    pygame.draw.line(
                        cracks,
                        (255, 210, 125, int(190 * slam_peak)),
                        (mid_x, mid_y),
                        (ccx + vx, ccy + vy),
                        3,
                    )

                    # Branch cracks.
                    branch_dir = -1 if i % 2 == 0 else 1
                    branch_x = mid_x + branch_dir * (18 + (i % 3) * 8)
                    branch_y = mid_y - 10 - (i % 4) * 5
                    pygame.draw.line(
                        cracks,
                        (255, 105, 35, int(175 * slam_peak)),
                        (mid_x, mid_y),
                        (branch_x, branch_y),
                        2,
                    )

                screen.blit(
                    cracks,
                    cracks.get_rect(midbottom=(actor_x, baseline_y + 20)),
                )

                # ----------------------------------------------------------
                # 3) Massive debris eruption
                # ----------------------------------------------------------
                debris = pygame.Surface((520, 300), pygame.SRCALPHA)
                dcx, dcy = 260, 238

                debris_data = [
                    (-210, -58, 7),
                    (-180, -104, 5),
                    (-145, -138, 8),
                    (-112, -74, 6),
                    (-82, -168, 5),
                    (-48, -118, 8),
                    (-24, -188, 6),
                    (24, -180, 7),
                    (52, -122, 5),
                    (86, -164, 8),
                    (116, -78, 6),
                    (148, -134, 7),
                    (182, -98, 5),
                    (216, -60, 8),
                ]

                for i, (dx, dy, radius) in enumerate(debris_data):
                    px = dcx + int(dx * slam_peak)
                    py = dcy + int(dy * slam_peak)

                    # Outer ember.
                    pygame.draw.circle(
                        debris,
                        (255, 120, 40, int(225 * slam_peak)),
                        (px, py),
                        radius + 3,
                    )
                    # Bright stone center.
                    pygame.draw.circle(
                        debris,
                        (255, 215, 145, int(240 * slam_peak)),
                        (px, py),
                        radius,
                    )

                    # Tiny trailing spark.
                    pygame.draw.line(
                        debris,
                        (255, 170, 70, int(180 * slam_peak)),
                        (px, py + 2),
                        (px - int(dx * 0.08), py + 20),
                        2,
                    )

                screen.blit(
                    debris,
                    debris.get_rect(midbottom=(actor_x, baseline_y + 16)),
                )

                # ----------------------------------------------------------
                # 4) Vertical energy eruption / impact pillar
                # ----------------------------------------------------------
                pillar = pygame.Surface((300, 360), pygame.SRCALPHA)
                pcx = 150
                base_y = 325

                pillar_alpha = int(165 * slam_peak)

                # Wide orange cone.
                pygame.draw.polygon(
                    pillar,
                    (
                        255,
                        120,
                        40,
                        int(95 * slam_peak),
                    ),
                    [
                        (pcx - 72, base_y),
                        (pcx - 22, 90),
                        (pcx + 22, 90),
                        (pcx + 72, base_y),
                    ],
                )

                # Bright inner beam.
                pygame.draw.polygon(
                    pillar,
                    (
                        255,
                        225,
                        155,
                        pillar_alpha,
                    ),
                    [
                        (pcx - 28, base_y),
                        (pcx - 8, 54),
                        (pcx + 8, 54),
                        (pcx + 28, base_y),
                    ],
                )

                # White-hot core.
                pygame.draw.line(
                    pillar,
                    (
                        255,
                        250,
                        220,
                        int(210 * slam_peak),
                    ),
                    (pcx, base_y),
                    (pcx, 45),
                    6,
                )

                screen.blit(
                    pillar,
                    pillar.get_rect(midbottom=(actor_x, baseline_y + 8)),
                )

                # ----------------------------------------------------------
                # 5) Starburst explosion at center
                # ----------------------------------------------------------
                burst = pygame.Surface((420, 320), pygame.SRCALPHA)
                bx, by = 210, 238

                rays = [
                    (-170, -24),
                    (-145, -74),
                    (-110, -128),
                    (-52, -168),
                    (0, -190),
                    (52, -168),
                    (110, -128),
                    (145, -74),
                    (170, -24),
                ]

                for vx, vy in rays:
                    pygame.draw.line(
                        burst,
                        (
                            255,
                            220,
                            140,
                            int(220 * slam_peak),
                        ),
                        (bx, by),
                        (bx + vx, by + vy),
                        5,
                    )

                    pygame.draw.line(
                        burst,
                        (
                            255,
                            255,
                            235,
                            int(155 * slam_peak),
                        ),
                        (bx, by),
                        (
                            bx + int(vx * 0.70),
                            by + int(vy * 0.70),
                        ),
                        2,
                    )

                # Huge center flash.
                pygame.draw.circle(
                    burst,
                    (
                        255,
                        245,
                        205,
                        int(205 * slam_peak),
                    ),
                    (bx, by),
                    int(34 + 38 * slam_peak),
                )

                pygame.draw.circle(
                    burst,
                    (
                        255,
                        255,
                        255,
                        int(225 * slam_peak),
                    ),
                    (bx, by),
                    int(12 + 18 * slam_peak),
                )

                screen.blit(
                    burst,
                    burst.get_rect(midbottom=(actor_x, baseline_y + 12)),
                )

                # ----------------------------------------------------------
                # 7) Extra ember particles around BRAX
                # ----------------------------------------------------------
                ember_fx = pygame.Surface((420, 300), pygame.SRCALPHA)
                ecx, ecy = 210, 235

                for i in range(22):
                    side = -1 if i % 2 == 0 else 1
                    spread = 24 + (i % 11) * 16
                    rise = 24 + (i * 17) % 155

                    ex = ecx + side * spread
                    ey = ecy - rise

                    pygame.draw.circle(
                        ember_fx,
                        (
                            255,
                            150 + (i % 3) * 25,
                            55,
                            int(185 * slam_peak),
                        ),
                        (ex, ey),
                        2 + (i % 3),
                    )

                screen.blit(
                    ember_fx,
                    ember_fx.get_rect(midbottom=(actor_x, baseline_y + 10)),
                )

        # --------------------------------------------------------------
        # KAGE: reproduce the real Double Jump.
        # First half = initial jump; second half = vertical velocity resets
        # upward, creating the second boost.
        # --------------------------------------------------------------
        elif skill_type in ("petrify", "petrify_after"):
            # ==========================================================
            # EMA_SHOWCASE_PETRIFY
            # 仅主页角色展示使用。
            # ==========================================================

            fx = pygame.Surface(
                (500, 340),
                pygame.SRCALPHA,
            )

            cx = 145
            cy = 165

            tick = (
                pygame.time.get_ticks()
                * 0.018
            )

            if skill_type == "petrify":
                power = max(
                    0.15,
                    min(
                        1.0,
                        action_progress * 2.4,
                    ),
                )
            else:
                power = 0.42

            pulse = (
                0.85
                + math.sin(tick * 4.0)
                * 0.15
            )

            # ----------------------------------------------------------
            # 1. EMA 身后的美杜莎幽绿色能量环
            # ----------------------------------------------------------

            for radius, alpha, width in (
                (50, 150, 4),
                (72, 95, 3),
                (96, 48, 2),
            ):
                pygame.draw.circle(
                    fx,
                    (
                        85,
                        255,
                        145,
                        int(alpha * power),
                    ),
                    (
                        cx,
                        cy,
                    ),
                    int(
                        radius
                        * pulse
                    ),
                    width,
                )

            # ----------------------------------------------------------
            # 2. 两只眼睛的绿色核心
            # ----------------------------------------------------------

            eye_y = cy - 35

            for eye_offset in (-7, 7):
                pygame.draw.circle(
                    fx,
                    (
                        215,
                        255,
                        220,
                        int(235 * power),
                    ),
                    (
                        cx + eye_offset,
                        eye_y,
                    ),
                    4,
                )

                pygame.draw.circle(
                    fx,
                    (
                        65,
                        255,
                        115,
                        int(130 * power),
                    ),
                    (
                        cx + eye_offset,
                        eye_y,
                    ),
                    10,
                    2,
                )

            # ----------------------------------------------------------
            # 3. 石化凝视锥形光束
            # ----------------------------------------------------------

            beam_start_x = cx + 15
            beam_end_x = 470

            beam_half_height = int(
                64 * power
            )

            pygame.draw.polygon(
                fx,
                (
                    75,
                    255,
                    125,
                    int(36 * power),
                ),
                (
                    (
                        beam_start_x,
                        eye_y,
                    ),
                    (
                        beam_end_x,
                        eye_y - beam_half_height,
                    ),
                    (
                        beam_end_x,
                        eye_y + beam_half_height,
                    ),
                ),
            )

            # 上边缘
            pygame.draw.line(
                fx,
                (
                    125,
                    255,
                    165,
                    int(145 * power),
                ),
                (
                    beam_start_x,
                    eye_y,
                ),
                (
                    beam_end_x,
                    eye_y - beam_half_height,
                ),
                2,
            )

            # 下边缘
            pygame.draw.line(
                fx,
                (
                    125,
                    255,
                    165,
                    int(145 * power),
                ),
                (
                    beam_start_x,
                    eye_y,
                ),
                (
                    beam_end_x,
                    eye_y + beam_half_height,
                ),
                2,
            )

            # ----------------------------------------------------------
            # 4. 光束内部蛇形能量
            # ----------------------------------------------------------

            for i in range(4):
                points = []

                for j in range(10):
                    x = (
                        beam_start_x
                        + j * 30
                    )

                    y = int(
                        eye_y
                        + math.sin(
                            tick * 3
                            + i * 1.7
                            + j * 0.8
                        )
                        * (
                            10
                            + i * 4
                        )
                    )

                    points.append(
                        (
                            x,
                            y,
                        )
                    )

                if len(points) >= 2:
                    pygame.draw.lines(
                        fx,
                        (
                            100,
                            245,
                            140,
                            int(
                                max(
                                    25,
                                    105 * power,
                                )
                            ),
                        ),
                        False,
                        points,
                        2,
                    )

            # ----------------------------------------------------------
            # 5. 光束末端石化碎片
            # ----------------------------------------------------------

            stone_x = 440
            stone_y = eye_y

            for i in range(14):
                angle = (
                    i
                    * math.tau
                    / 14
                    + tick * 0.25
                )

                distance = (
                    18
                    + (i % 4) * 9
                )

                px = int(
                    stone_x
                    + math.cos(angle)
                    * distance
                )

                py = int(
                    stone_y
                    + math.sin(angle)
                    * distance
                )

                size = (
                    2
                    + i % 3
                )

                pygame.draw.rect(
                    fx,
                    (
                        170,
                        190,
                        170,
                        int(195 * power),
                    ),
                    (
                        px,
                        py,
                        size,
                        size,
                    ),
                )

            # ----------------------------------------------------------
            # 6. 石像裂纹核心
            # ----------------------------------------------------------

            pygame.draw.circle(
                fx,
                (
                    145,
                    165,
                    145,
                    int(95 * power),
                ),
                (
                    stone_x,
                    stone_y,
                ),
                int(
                    22 + 8 * power
                ),
                3,
            )

            crack_points = (
                (
                    (stone_x - 11, stone_y - 18),
                    (stone_x - 2, stone_y - 4),
                ),
                (
                    (stone_x - 2, stone_y - 4),
                    (stone_x - 10, stone_y + 11),
                ),
                (
                    (stone_x + 9, stone_y - 16),
                    (stone_x + 1, stone_y - 3),
                ),
                (
                    (stone_x + 1, stone_y - 3),
                    (stone_x + 12, stone_y + 10),
                ),
            )

            for p1, p2 in crack_points:
                pygame.draw.line(
                    fx,
                    (
                        225,
                        235,
                        220,
                        int(180 * power),
                    ),
                    p1,
                    p2,
                    2,
                )

            # ----------------------------------------------------------
            # 整个效果跟随 EMA
            # ----------------------------------------------------------

            screen.blit(
                fx,
                fx.get_rect(
                    center=(
                        actor_x + 145,
                        actor_y - 120,
                    )
                ),
            )

        elif skill_type == "double_jump":
            actor_x = 272

            if action_progress < 0.50:
                p = action_progress / 0.50
                jump_height = 72 * (1.0 - (2.0 * p - 1.0) ** 2)
                actor_y = baseline_y - 5 - int(jump_height)
            else:
                p = (action_progress - 0.50) / 0.50
                # At p=0 KAGE receives the real second upward impulse.
                second_height = 106 * (1.0 - (2.0 * p - 1.0) ** 2)
                actor_y = baseline_y - 54 - int(second_height)

                # Purple burst at the instant of the second jump.
                if p < 0.30:
                    burst_strength = 1.0 - p / 0.30
                    burst = pygame.Surface((220, 120), pygame.SRCALPHA)
                    for i in range(10):
                        angle_x = (i - 4.5) * 15
                        pygame.draw.circle(
                            burst,
                            (180, 145, 255, int(200 * burst_strength)),
                            (110 + int(angle_x), 80 + abs(i - 4) * 3),
                            3 + i % 2,
                        )
                    screen.blit(
                        burst,
                        burst.get_rect(center=(actor_x, actor_y + 95)),
                    )

                    for offset, alpha in ((-42, 75), (42, 48)):
                        ghost = frame.copy()
                        ghost.set_alpha(alpha)
                        screen.blit(
                            ghost,
                            ghost.get_rect(
                                midbottom=(actor_x + offset, actor_y + 18)
                            ),
                        )

                    rise_fx = pygame.Surface((240, 220), pygame.SRCALPHA)
                    for i in range(14):
                        px = 120 + ((i % 5) - 2) * 22
                        py = 192 - (i // 5) * 50 - (i % 3) * 13
                        pygame.draw.line(
                            rise_fx,
                            (195, 155, 255, int(185 * burst_strength)),
                            (px, py + 28),
                            (px, py - 14),
                            3,
                        )
                    screen.blit(
                        rise_fx,
                        rise_fx.get_rect(center=(actor_x, actor_y + 40)),
                    )



        # --------------------------------------------------------------
        # ACE: Deadeye
        # 金色瞄准圈 + 投射强化效果。
        # --------------------------------------------------------------
        if (
            skill_type in ("deadeye", "deadeye_hold")
            and character_id == "ace"
        ):
            actor_x = 272

            deadeye_fx = pygame.Surface(
                (310, 280),
                pygame.SRCALPHA,
            )

            fx_cx = 155
            fx_cy = 155

            pulse = (
                0.72
                + 0.28
                * math.sin(
                    action_progress
                    * math.pi
                    * 4
                )
            )

            # 外层瞄准圈。
            for radius, alpha in (
                (92, 65),
                (72, 105),
                (52, 170),
            ):
                pygame.draw.circle(
                    deadeye_fx,
                    (
                        255,
                        210,
                        72,
                        int(alpha * pulse),
                    ),
                    (fx_cx, fx_cy),
                    radius,
                    2,
                )

            # 十字准星。
            cross_alpha = int(
                210 * pulse
            )

            pygame.draw.line(
                deadeye_fx,
                (
                    255,
                    235,
                    140,
                    cross_alpha,
                ),
                (fx_cx - 112, fx_cy),
                (fx_cx - 48, fx_cy),
                3,
            )

            pygame.draw.line(
                deadeye_fx,
                (
                    255,
                    235,
                    140,
                    cross_alpha,
                ),
                (fx_cx + 48, fx_cy),
                (fx_cx + 112, fx_cy),
                3,
            )

            pygame.draw.line(
                deadeye_fx,
                (
                    255,
                    235,
                    140,
                    cross_alpha,
                ),
                (fx_cx, fx_cy - 112),
                (fx_cx, fx_cy - 48),
                3,
            )

            pygame.draw.line(
                deadeye_fx,
                (
                    255,
                    235,
                    140,
                    cross_alpha,
                ),
                (fx_cx, fx_cy + 48),
                (fx_cx, fx_cy + 112),
                3,
            )

            screen.blit(
                deadeye_fx,
                deadeye_fx.get_rect(
                    center=(
                        actor_x,
                        actor_y - 100,
                    )
                ),
            )

        actor_rect = frame.get_rect(midbottom=(actor_x, actor_y))

        # --------------------------------------------------------------
        # DUKE: reproduce the actual clone spawn.
        # The main body uses attack_2; Blood Echo uses the separate
        # duke_blood_echo model defined by clone_sprite_folder.
        # --------------------------------------------------------------
        if skill_type in ("clone", "clone_hold", "clone_run") and character_id == "duke":
            clone_action = "run" if skill_type == "clone_run" else "idle"
            clone_frames = _showcase_clone_frames("duke", clone_action, 238)

            # Some packs may not contain a usable run sheet; gracefully fall
            # back to idle rather than hiding Blood Echo.
            if not clone_frames and clone_action != "idle":
                clone_frames = _showcase_clone_frames("duke", "idle", 238)

            if clone_frames:
                clone_frame_seconds = 0.0778 if clone_action == "run" else 0.1167
                clone_index = int(action_time / clone_frame_seconds) % len(clone_frames)
                clone_frame = clone_frames[clone_index]

                # Match the actual game clone spacing: approximately 105 px.
                clone_offset = -105

                if skill_type == "clone":
                    # Spawn outward from DUKE during the summon animation.
                    spawn_t = min(1.0, action_progress * 3.2)
                    clone_x = int(
                        actor_x + clone_offset * _ease_out_cubic(spawn_t)
                    )

                    # Red spawn particles.
                    if spawn_t < 1.0:
                        spawn_fx = pygame.Surface((180, 250), pygame.SRCALPHA)
                        alpha = int(230 * (1.0 - spawn_t))
                        for i in range(12):
                            px = 90 + ((i % 4) - 1.5) * 16
                            py = 150 - (i // 4) * 24
                            pygame.draw.circle(
                                spawn_fx,
                                (230, 48, 68, alpha),
                                (int(px), int(py)),
                                4,
                            )
                        screen.blit(
                            spawn_fx,
                            spawn_fx.get_rect(
                                center=(clone_x, actor_y - 95)
                            ),
                        )
                elif skill_type == "clone_hold":
                    # Freeze the composition briefly so the Echo reveal reads clearly.
                    clone_x = actor_x + clone_offset
                else:
                    # After the hold, DUKE and Blood Echo both keep running.
                    clone_x = actor_x + clone_offset

                clone_rect = clone_frame.get_rect(
                    midbottom=(clone_x, actor_y)
                )

                if skill_type == "clone":
                    glow = clone_frame.copy()
                    glow.fill(
                        (150, 20, 36, 0),
                        special_flags=pygame.BLEND_RGBA_ADD,
                    )
                    glow.set_alpha(105)
                    for gx in (-6, 6):
                        for gy in (-4, 4):
                            screen.blit(
                                glow,
                                glow.get_rect(
                                    midbottom=(clone_x + gx, actor_y + gy)
                                ),
                            )

                screen.blit(clone_frame, clone_rect)

                if skill_type == "clone":
                    ability_text = tr("characters.duke.ability")
                    clone_label = small_font.render(
                        ability_text,
                        True,
                        (230, 48, 68),
                    )
                    screen.blit(
                        clone_label,
                        clone_label.get_rect(center=(270, 408)),
                    )
        screen.blit(frame, actor_rect)

    # Character identity plate.
    display_name = tr(f"characters.{character_id}.name")
    name_surface = font.render(display_name, True, COLOR_TEXT)
    name_plate = pygame.Rect(176, 458, 190, 40)
    pygame.draw.rect(screen, (8, 14, 28), name_plate, border_radius=10)
    pygame.draw.rect(screen, accent, name_plate, 2, border_radius=10)
    screen.blit(name_surface, name_surface.get_rect(center=name_plate.center))

    # Ability subtitle gives each solo its own identity without cluttering the menu.
    ability_surface = small_font.render(
        tr(f"characters.{character_id}.ability"),
        True,
        accent,
    )
    ability_rect = ability_surface.get_rect(center=(271, 435))
    screen.blit(ability_surface, ability_rect)

    # Minimal progress markers: one dot per roster member; active one uses the
    # character's accent color.  This makes the automatic order easy to read.
    dot_y = 522
    dot_gap = 20
    total_dot_width = (len(character_order) - 1) * dot_gap
    dot_start_x = 278 - total_dot_width // 2
    for index, cid in enumerate(character_order):
        dot_x = dot_start_x + index * dot_gap
        if cid == character_id:
            dot_color = accent
            radius = 5
        else:
            dot_color = (75, 91, 120)
            radius = 3
        pygame.draw.circle(screen, dot_color, (dot_x, dot_y), radius)

def _crop_transparent_padding(image, alpha_threshold=8, padding=2):
    """Crop fully transparent padding around a portrait.

    Uses only Surface.get_bounding_rect(), which is reliable across the
    macOS/Pygame versions used by this project.
    """
    surface = image.convert_alpha()
    rect = surface.get_bounding_rect(min_alpha=alpha_threshold)
    if rect.width <= 0 or rect.height <= 0:
        return surface

    rect.inflate_ip(padding * 2, padding * 2)
    rect.clamp_ip(surface.get_rect())
    return surface.subsurface(rect).copy().convert_alpha()

def _load_ui_image(relative_path, size=None):
    """Load a UI image with reliable per-pixel transparency.

    Character portraits:
    - convert_alpha()
    - remove only dark background connected to the image edge
    - crop transparent padding
    - nearest-neighbour scale

    Other UI and arena images:
    - convert_alpha()
    - smoothscale
    """
    cache_key = (relative_path, size)
    cached = _IMAGE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    path = os.path.join(ASSET_ROOT, relative_path)
    if not os.path.isfile(path):
        return None

    try:
        image = pygame.image.load(path).convert_alpha()

        is_character = (
            relative_path.startswith("characters/")
            and relative_path.endswith("portrait.png")
        )

        if is_character:
            image = _remove_connected_dark_background(image)
            image = _crop_transparent_padding(image)

        if size:
            if is_character:
                image = pygame.transform.scale(image, size)
            else:
                image = pygame.transform.smoothscale(image, size)

        # Normalize alpha surface so blitting never falls back to colorkey/global alpha.
        normalized = pygame.Surface(image.get_size(), pygame.SRCALPHA, 32)
        normalized.blit(image, (0, 0))
        normalized = normalized.convert_alpha()

        _IMAGE_CACHE[cache_key] = normalized
        return normalized
    except (pygame.error, OSError, ValueError):
        return None

def _load_character_select_art(
    character_id,
    target_height,
    max_width,
):
    """角色选择界面人物图。

    优先使用 portrait.png。
    如果没有 portrait，则自动使用 idle 动画第一帧。
    """

    portrait = _load_ui_image(
        f"characters/{character_id}/portrait.png"
    )

    if portrait is not None:
        width = portrait.get_width()
        height = portrait.get_height()

        if width > 0 and height > 0:
            scale = min(
                target_height / height,
                max_width / width,
            )

            width = max(
                1,
                int(width * scale),
            )

            height = max(
                1,
                int(height * scale),
            )

            return pygame.transform.scale(
                portrait,
                (width, height),
            ).convert_alpha()

    # 没有 portrait.png：
    # 自动使用角色 idle 第一帧。
    frames = _showcase_frames(
        character_id,
        "idle",
        target_height,
    )

    if not frames:
        return None

    art = frames[0].copy()

    if art.get_width() > max_width:
        scale = max_width / art.get_width()

        art = pygame.transform.scale(
            art,
            (
                max_width,
                max(
                    1,
                    int(
                        art.get_height()
                        * scale
                    ),
                ),
            ),
        ).convert_alpha()

    return art


def _draw_backdrop(screen, accent=(255, 116, 54)):
    key = tuple(accent)
    backdrop = _BACKDROP_CACHE.get(key)
    if backdrop is None:
        backdrop = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()
        top, bottom = (6, 10, 24), (20, 28, 48)
        for y in range(SCREEN_HEIGHT):
            t = y / max(1, SCREEN_HEIGHT - 1)
            color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            pygame.draw.line(backdrop, color, (0, y), (SCREEN_WIDTH, y))
        haze = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(haze, (*accent, 42), (130, 110), 220)
        pygame.draw.circle(haze, (38, 124, 255, 30), (850, 420), 260)
        pygame.draw.polygon(haze, (255, 255, 255, 12), [(0, 455), (960, 360), (960, 540), (0, 540)])
        for x in range(-300, 1300, 120):
            pygame.draw.line(haze, (210, 225, 255, 22), (480, 330), (x, 540), 1)
        for y in (390, 430, 478, 530):
            pygame.draw.line(haze, (210, 225, 255, 18), (0, y), (960, y), 1)
        backdrop.blit(haze, (0, 0))
        _BACKDROP_CACHE[key] = backdrop
    screen.blit(backdrop, (0, 0))


def _draw_panel(screen, rect, selected=False, accent=(255, 116, 54), alpha=220, radius=16):
    shadow = pygame.Surface((rect.width + 14, rect.height + 14), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=radius + 3)
    screen.blit(shadow, (rect.x + 3, rect.y + 6))
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 16, 31, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, (*accent, 235 if selected else 105), panel.get_rect(), 3 if selected else 1, border_radius=radius)
    pygame.draw.line(panel, (*accent, 220), (18, 2), (rect.width - 18, 2), 2)
    screen.blit(panel, rect)


def _draw_menu_button(screen, font, text, rect, selected=False):
    accent = (255, 132, 55)
    shadow = rect.move(4, 5)
    pygame.draw.rect(screen, (3, 7, 16), shadow, border_radius=10)
    fill = (29, 44, 72) if selected else (13, 21, 39)
    border = accent if selected else (62, 82, 117)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=10)
    pygame.draw.rect(screen, accent if selected else (45, 62, 88), (rect.x, rect.y, 7, rect.height), border_radius=5)
    label = font.render(text, True, COLOR_TEXT)
    screen.blit(label, label.get_rect(midleft=(rect.x + 28, rect.centery)))
    if selected:
        pygame.draw.polygon(screen, accent, [(rect.right - 24, rect.centery - 6), (rect.right - 14, rect.centery), (rect.right - 24, rect.centery + 6)])

def _mouse_selected(rects):
    mouse_pos = pygame.mouse.get_pos()
    for index, rect in enumerate(rects):
        if rect.collidepoint(mouse_pos):
            return index
    return None


def _clicked_index(event, rects):
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for index, rect in enumerate(rects):
            if rect.collidepoint(event.pos):
                return index
    return None


def _draw_back_button(screen, font):
    """左上角返回按钮；所有选择页面统一使用。"""
    rect = pygame.Rect(18, 18, 150, 38)
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    label = f"Q  {tr('common.back')}"
    _draw_menu_button(screen, font, label, rect, hovered)
    return rect


def main_menu(screen, font, small_font, title_font):
    """正式主菜单。支持键盘与鼠标。"""
    selected = 0
    clock = pygame.time.Clock()
    entrance_started_at = pygame.time.get_ticks()

    while True:
        options = [
            (tr("menu.play"), "play"),
            (tr("menu.how_to_play"), "how_to_play"),
            (tr("menu.settings"), "settings"),
            (tr("menu.credits"), "credits"),
            (tr("menu.feedback"), "feedback"),
            (tr("menu.quit"), "quit"),
        ]
        rects = [pygame.Rect(595, 148 + i * 54, 300, 44) for i in range(len(options))]
        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            clicked = _clicked_index(event, rects)
            if clicked is not None:
                return options[clicked][1]
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return options[selected][1]
                elif event.key == pygame.K_ESCAPE:
                    return "quit"

        _draw_backdrop(screen)
        pygame.draw.rect(screen, (255, 132, 55), (62, 48, 68, 5), border_radius=2)
        kicker = small_font.render("STREET // ARCADE", True, (255, 158, 83))
        screen.blit(kicker, (62, 62))
        title = title_font.render(tr("app.title"), True, COLOR_TEXT)
        subtitle = small_font.render(tr("app.subtitle"), True, (178, 197, 225))
        screen.blit(title, title.get_rect(midleft=(62, 118)))
        screen.blit(subtitle, subtitle.get_rect(midleft=(65, 157)))

        elapsed = (pygame.time.get_ticks() - entrance_started_at) / 1000.0
        _draw_character_carousel(
            screen,
            font,
            small_font,
            elapsed,
        )

        menu_title = small_font.render("SELECT MODE", True, (132, 154, 190))
        screen.blit(menu_title, (595, 116))

        for index, (label, _) in enumerate(options):
            _draw_menu_button(screen, font, label, rects[index], index == selected)

        hint = small_font.render(tr("menu.hint"), True, (142, 158, 184))
        screen.blit(hint, hint.get_rect(midright=(895, 510)))
        pygame.display.flip()
        clock.tick(FPS)


def _wrap_text(font, text, max_width):
    """按像素宽度换行，避免全屏缩放后信息页文字跨列重叠。"""
    text = str(text).strip()
    if not text:
        return [""]

    # 中文通常没有空格，英文则优先按单词换行。
    words = text.split(" ")
    if len(words) == 1:
        units = list(text)
        separator = ""
    else:
        units = words
        separator = " "

    wrapped = []
    current = ""
    for unit in units:
        candidate = unit if not current else current + separator + unit
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue

        if current:
            wrapped.append(current)

        # 单个超长单词继续按字符拆分，确保永远不会越界。
        if font.size(unit)[0] > max_width:
            piece = ""
            for character in unit:
                candidate_piece = piece + character
                if piece and font.size(candidate_piece)[0] > max_width:
                    wrapped.append(piece)
                    piece = character
                else:
                    piece = candidate_piece
            current = piece
        else:
            current = unit

    if current:
        wrapped.append(current)
    return wrapped



def _tracked_text_width(font, text, tracking=1):
    text = str(text)
    if not text:
        return 0
    widths = [font.size(ch)[0] for ch in text]
    return sum(widths) + max(0, len(text) - 1) * tracking


def _render_tracked_text(font, text, color, tracking=1):
    """Render text with explicit character spacing."""
    text = str(text)

    if not text:
        return pygame.Surface(
            (1, max(1, font.get_linesize())),
            pygame.SRCALPHA,
        )

    glyphs = [
        font.render(ch, True, color)
        for ch in text
    ]

    width = sum(
        glyph.get_width()
        for glyph in glyphs
    )
    width += max(0, len(glyphs) - 1) * tracking

    height = max(
        glyph.get_height()
        for glyph in glyphs
    )

    surface = pygame.Surface(
        (max(1, width), max(1, height)),
        pygame.SRCALPHA,
    )

    x = 0

    for glyph in glyphs:
        surface.blit(
            glyph,
            (
                x,
                (height - glyph.get_height()) // 2,
            ),
        )
        x += glyph.get_width() + tracking

    return surface


def _wrap_text_tracked(
    font,
    text,
    max_width,
    tracking=1,
):
    """Wrap Chinese/English using the real tracked width."""
    text = str(text).strip()

    if not text:
        return [""]

    words = text.split(" ")

    if len(words) == 1:
        units = list(text)
        separator = ""
    else:
        units = words
        separator = " "

    wrapped = []
    current = ""

    for unit in units:
        candidate = (
            unit
            if not current
            else current + separator + unit
        )

        if _tracked_text_width(
            font,
            candidate,
            tracking,
        ) <= max_width:
            current = candidate
            continue

        if current:
            wrapped.append(current)

        if _tracked_text_width(
            font,
            unit,
            tracking,
        ) > max_width:
            piece = ""

            for character in unit:
                candidate_piece = (
                    piece + character
                )

                if (
                    piece
                    and _tracked_text_width(
                        font,
                        candidate_piece,
                        tracking,
                    ) > max_width
                ):
                    wrapped.append(piece)
                    piece = character
                else:
                    piece = candidate_piece

            current = piece
        else:
            current = unit

    if current:
        wrapped.append(current)

    return wrapped


def _build_scrollable_info_layout(
    font,
    small_font,
    sections,
    max_width,
    accent,
):
    """Build relaxed reading layout for handbook/credits."""
    tracking = (
        2
        if get_language() == "zh"
        else 1
    )

    # 比原版本明显更宽松的行距。
    line_height = max(
        26,
        small_font.get_linesize() + 7,
    )

    paragraph_gap = 8
    section_gap = 30

    items = []
    y = 0

    for section_index, (
        heading,
        lines,
    ) in enumerate(sections):

        if section_index:
            y += section_gap

        heading_surface = _render_tracked_text(
            font,
            heading,
            accent,
            tracking=1,
        )

        items.append(
            (
                "heading",
                heading_surface,
                y,
            )
        )

        y += (
            heading_surface.get_height()
            + 16
        )

        for raw_line in lines:
            wrapped = _wrap_text_tracked(
                small_font,
                raw_line,
                max_width - 12,
                tracking=tracking,
            )

            for line in wrapped:
                body_surface = (
                    _render_tracked_text(
                        small_font,
                        line,
                        (225, 232, 244),
                        tracking=tracking,
                    )
                )

                items.append(
                    (
                        "body",
                        body_surface,
                        y,
                    )
                )

                y += line_height

            y += paragraph_gap

        y += 4

    return items, max(0, y)


def _scrollable_info_menu(
    screen,
    font,
    small_font,
    title_font,
    title,
    sections,
    accent=(62, 151, 255),
):
    """Unified scrollable reading page."""
    clock = pygame.time.Clock()

    panel = pygame.Rect(
        72,
        98,
        SCREEN_WIDTH - 144,
        SCREEN_HEIGHT - 158,
    )

    viewport = pygame.Rect(
        panel.x + 34,
        panel.y + 26,
        panel.width - 74,
        panel.height - 52,
    )

    back_rect = pygame.Rect(
        18,
        18,
        150,
        38,
    )

    items, content_height = (
        _build_scrollable_info_layout(
            font,
            small_font,
            sections,
            viewport.width,
            accent,
        )
    )

    maximum = max(
        0,
        content_height - viewport.height,
    )

    scroll_y = 0

    def clamp_scroll(value):
        return max(
            0,
            min(
                int(value),
                maximum,
            ),
        )

    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.MOUSEBUTTONDOWN:

                if (
                    event.button == 1
                    and back_rect.collidepoint(
                        event.pos
                    )
                ):
                    return "back"

                # 兼容旧版 Pygame / macOS 滚轮事件。
                if event.button == 4:
                    scroll_y = clamp_scroll(
                        scroll_y - 72
                    )

                elif event.button == 5:
                    scroll_y = clamp_scroll(
                        scroll_y + 72
                    )

            if event.type == pygame.MOUSEWHEEL:
                scroll_y = clamp_scroll(
                    scroll_y
                    - event.y * 72
                )

            if event.type == pygame.KEYDOWN:

                if event.key in (
                    pygame.K_ESCAPE,
                    pygame.K_q,
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    return "back"

                if event.key in (
                    pygame.K_UP,
                    pygame.K_w,
                ):
                    scroll_y = clamp_scroll(
                        scroll_y - 34
                    )

                elif event.key in (
                    pygame.K_DOWN,
                    pygame.K_s,
                ):
                    scroll_y = clamp_scroll(
                        scroll_y + 34
                    )

                elif event.key == pygame.K_PAGEUP:
                    scroll_y = clamp_scroll(
                        scroll_y
                        - max(
                            80,
                            viewport.height - 70,
                        )
                    )

                elif event.key == pygame.K_PAGEDOWN:
                    scroll_y = clamp_scroll(
                        scroll_y
                        + max(
                            80,
                            viewport.height - 70,
                        )
                    )

                elif event.key == pygame.K_HOME:
                    scroll_y = 0

                elif event.key == pygame.K_END:
                    scroll_y = maximum

        _draw_backdrop(
            screen,
            accent,
        )

        title_surface = title_font.render(
            title,
            True,
            COLOR_TEXT,
        )

        screen.blit(
            title_surface,
            title_surface.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    60,
                )
            ),
        )

        _draw_panel(
            screen,
            panel,
            accent=accent,
            alpha=236,
            radius=18,
        )

        old_clip = screen.get_clip()
        screen.set_clip(viewport)

        for (
            kind,
            surface,
            content_y,
        ) in items:

            draw_y = (
                viewport.y
                + content_y
                - scroll_y
            )

            if (
                draw_y
                + surface.get_height()
                < viewport.y
            ):
                continue

            if draw_y > viewport.bottom:
                continue

            if kind == "heading":
                draw_x = viewport.x

                screen.blit(
                    surface,
                    (
                        draw_x,
                        draw_y,
                    ),
                )

                # 标题右侧细分隔线。
                line_x = (
                    draw_x
                    + surface.get_width()
                    + 16
                )

                line_y = (
                    draw_y
                    + surface.get_height() // 2
                )

                if line_x < viewport.right - 8:
                    pygame.draw.line(
                        screen,
                        accent,
                        (
                            line_x,
                            line_y,
                        ),
                        (
                            viewport.right - 8,
                            line_y,
                        ),
                        1,
                    )

            else:
                screen.blit(
                    surface,
                    (
                        viewport.x + 8,
                        draw_y,
                    ),
                )

        screen.set_clip(old_clip)

        # 右侧滚动条。
        if maximum > 0:

            track = pygame.Rect(
                panel.right - 17,
                viewport.y,
                5,
                viewport.height,
            )

            pygame.draw.rect(
                screen,
                (42, 57, 82),
                track,
                border_radius=3,
            )

            total_height = (
                viewport.height
                + maximum
            )

            thumb_height = max(
                34,
                int(
                    viewport.height
                    * viewport.height
                    / total_height
                ),
            )

            travel = max(
                1,
                track.height
                - thumb_height,
            )

            ratio = (
                scroll_y / maximum
                if maximum
                else 0.0
            )

            thumb = pygame.Rect(
                track.x,
                track.y
                + int(
                    travel
                    * ratio
                ),
                track.width,
                thumb_height,
            )

            pygame.draw.rect(
                screen,
                accent,
                thumb,
                border_radius=3,
            )

        _draw_back_button(
            screen,
            small_font,
        )

        if get_language() == "zh":
            hint_text = (
                "滚轮 / W S / ↑↓：上下阅读"
                "    •    "
                "Q / ESC：返回"
            )
        else:
            hint_text = (
                "Wheel / W S / ↑↓: scroll"
                "    •    "
                "Q / ESC: back"
            )

        hint = small_font.render(
            hint_text,
            True,
            (170, 182, 207),
        )

        screen.blit(
            hint,
            hint.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT - 20,
                )
            ),
        )

        pygame.display.flip()
        clock.tick(FPS)


def how_to_play_menu(
    screen,
    font,
    small_font,
    title_font,
):
    """Single-column scrollable handbook."""
    sections = [
        (
            tr("how.p1"),
            tr_list("how.p1_lines"),
        ),
        (
            tr("how.p2"),
            tr_list("how.p2_lines"),
        ),
        (
            tr("how.rules"),
            tr_list("how.rule_lines"),
        ),
        (
            tr("how.general"),
            tr_list("how.general_lines"),
        ),
    ]

    return _scrollable_info_menu(
        screen,
        font,
        small_font,
        title_font,
        tr("how.title"),
        sections,
        accent=(62, 151, 255),
    )


def credits_menu(
    screen,
    font,
    small_font,
    title_font,
):
    """Scrollable credits and thanks page."""
    sections = [
        (
            tr("credits.creator"),
            tr_list(
                "credits.creator_lines"
            ),
        ),
        (
            tr("credits.development"),
            tr_list(
                "credits.development_lines"
            ),
        ),
        (
            tr("credits.thanks"),
            tr_list(
                "credits.thanks_lines"
            ),
        ),
        (
            tr("credits.notice"),
            tr_list(
                "credits.notice_lines"
            ),
        ),
    ]

    return _scrollable_info_menu(
        screen,
        font,
        small_font,
        title_font,
        tr("credits.title"),
        sections,
        accent=(255, 132, 55),
    )


FEEDBACK_ISSUE_URL = "https://github.com/jinhaodu1203/basketball-brawl/issues/new"


def _draw_feedback_input(screen, font, rect, text, placeholder, active=False, multiline=False):
    """Draw one text field in the same neon/arcade style as the rest of the UI."""
    accent = (255, 132, 55) if active else (62, 82, 117)
    fill = (14, 23, 42)
    pygame.draw.rect(screen, fill, rect, border_radius=9)
    pygame.draw.rect(screen, accent, rect, 2 if active else 1, border_radius=9)

    shown = text if text else placeholder
    color = COLOR_TEXT if text else (112, 132, 164)
    padding_x = 14
    padding_y = 9

    if multiline:
        lines = []
        for raw_line in shown.split("\n"):
            lines.extend(_wrap_text(font, raw_line, rect.width - padding_x * 2))
        max_lines = max(1, (rect.height - padding_y * 2) // max(1, font.get_linesize()))
        for index, line in enumerate(lines[:max_lines]):
            surface = font.render(line, True, color)
            screen.blit(surface, (rect.x + padding_x, rect.y + padding_y + index * font.get_linesize()))
    else:
        display_text = shown
        while display_text and font.size(display_text)[0] > rect.width - padding_x * 2:
            display_text = display_text[1:]
        surface = font.render(display_text, True, color)
        screen.blit(surface, surface.get_rect(midleft=(rect.x + padding_x, rect.centery)))


def _feedback_issue_url(feedback_type, content, email):
    """Build a pre-filled bilingual GitHub issue URL from the in-game feedback form."""
    labels = {
        "bug": ("BUG", "游戏问题 / BUG"),
        "balance": ("BALANCE", "平衡建议 / BALANCE"),
        "feature": ("FEATURE", "新功能建议 / FEATURE"),
        "gameplay": ("GAMEPLAY", "游戏体验 / GAMEPLAY"),
        "art_ui": ("ART/UI", "美术 / UI"),
        "audio": ("AUDIO", "音效 / AUDIO"),
        "localization": ("LOCALIZATION", "翻译问题 / LOCALIZATION"),
        "other": ("OTHER", "其他 / OTHER"),
    }
    type_code, type_label = labels.get(feedback_type, labels["other"])
    title = f"[{type_code}] HOOP HAVOC Feedback"
    body = (
        "HOOP HAVOC 玩家反馈 / PLAYER FEEDBACK\n\n"
        f"反馈类型：{type_code}\n"
        f"Feedback Type: {type_code}\n"
        f"类型说明 / Type: {type_label}\n\n"
        "反馈内容 / Feedback:\n"
        f"{content.strip() or '(未填写详细内容 / No details provided)'}\n\n"
        f"邮箱 / Email: {email.strip() or '(未填写 / Not provided)'}\n\n"
        "---\n"
        "通过 HOOP HAVOC 游戏内反馈页面提交 / Submitted from the in-game feedback page."
    )
    return f"{FEEDBACK_ISSUE_URL}?title={quote(title)}&body={quote(body)}"


def feedback_menu(screen, font, small_font, title_font):
    """Bilingual in-game feedback form with a real feedback-type dropdown."""
    clock = pygame.time.Clock()

    zh_font, zh_small, zh_title = create_fonts("zh")
    en_font, en_small, en_title = create_fonts("en")

    type_keys = [
        "bug", "balance", "feature", "gameplay",
        "art_ui", "audio", "localization", "other",
    ]
    type_labels = {
        "bug": "游戏问题 / BUG",
        "balance": "平衡建议 / BALANCE",
        "feature": "新功能建议 / FEATURE",
        "gameplay": "游戏体验 / GAMEPLAY",
        "art_ui": "美术 / UI",
        "audio": "音效 / AUDIO",
        "localization": "翻译问题 / LOCALIZATION",
        "other": "其他 / OTHER",
    }
    type_index = 0
    dropdown_open = False
    dropdown_hover = -1
    content = ""
    email = ""
    active_field = None
    status_until = 0

    back_rect = pygame.Rect(22, 18, 124, 36)
    type_rect = pygame.Rect(430, 130, 455, 42)
    content_rect = pygame.Rect(430, 218, 455, 112)
    email_rect = pygame.Rect(430, 370, 455, 42)
    reset_rect = pygame.Rect(430, 432, 170, 48)
    submit_rect = pygame.Rect(615, 432, 270, 48)

    dropdown_item_h = 34
    dropdown_rects = [
        pygame.Rect(type_rect.x, type_rect.bottom + i * dropdown_item_h,
                    type_rect.width, dropdown_item_h)
        for i in range(len(type_keys))
    ]

    pygame.key.start_text_input()
    try:
        while True:
            mouse_pos = pygame.mouse.get_pos()
            dropdown_hover = -1
            if dropdown_open:
                for i, rect in enumerate(dropdown_rects):
                    if rect.collidepoint(mouse_pos):
                        dropdown_hover = i
                        break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if dropdown_open:
                        picked = None
                        for i, rect in enumerate(dropdown_rects):
                            if rect.collidepoint(event.pos):
                                picked = i
                                break
                        if picked is not None:
                            type_index = picked
                            dropdown_open = False
                            active_field = None
                            continue
                        if type_rect.collidepoint(event.pos):
                            dropdown_open = False
                            continue
                        dropdown_open = False

                    if back_rect.collidepoint(event.pos):
                        return "back"
                    if type_rect.collidepoint(event.pos):
                        dropdown_open = True
                        active_field = None
                    elif content_rect.collidepoint(event.pos):
                        active_field = "content"
                    elif email_rect.collidepoint(event.pos):
                        active_field = "email"
                    elif reset_rect.collidepoint(event.pos):
                        content = ""
                        email = ""
                        type_index = 0
                        dropdown_open = False
                        active_field = None
                    elif submit_rect.collidepoint(event.pos):
                        try:
                            webbrowser.open(
                                _feedback_issue_url(type_keys[type_index], content, email),
                                new=2,
                            )
                        finally:
                            status_until = pygame.time.get_ticks() + 2600
                            active_field = None
                            dropdown_open = False
                    else:
                        active_field = None

                # 中文输入依靠 pygame.TEXTINPUT，不使用 KEYDOWN 拼接字符。
                # 这样可以兼容系统输入法（拼音/日文/韩文等）。
                if event.type == pygame.TEXTINPUT and active_field:
                    if active_field == "content" and len(content) < 900:
                        content += event.text
                    elif active_field == "email" and len(email) < 100:
                        email += event.text

                # 输入法组合阶段不要重复写入。
                if event.type == pygame.TEXTEDITING:
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if dropdown_open:
                            dropdown_open = False
                        elif active_field is not None:
                            active_field = None
                        else:
                            return "back"
                    elif dropdown_open:
                        if event.key in (pygame.K_UP, pygame.K_w):
                            type_index = (type_index - 1) % len(type_keys)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            type_index = (type_index + 1) % len(type_keys)
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            dropdown_open = False
                        continue
                    elif event.key == pygame.K_TAB:
                        active_field = "email" if active_field == "content" else "content"
                    elif event.key == pygame.K_BACKSPACE:
                        if active_field == "content":
                            content = content[:-1]
                        elif active_field == "email":
                            email = email[:-1]
                    elif event.key == pygame.K_RETURN:
                        if active_field == "content" and len(content) < 900:
                            content += "\n"
                        elif active_field == "email":
                            active_field = None
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and active_field is None:
                        dropdown_open = True

            _draw_backdrop(screen, (62, 151, 255))

            back_hovered = back_rect.collidepoint(mouse_pos)
            _draw_menu_button(screen, zh_small, "‹  返回 / BACK", back_rect, back_hovered)

            zh_header = zh_font.render("玩家反馈", True, COLOR_TEXT)
            slash = en_font.render(" / ", True, (255, 132, 55))
            en_header = en_font.render("FEEDBACK", True, (162, 184, 220))
            header_width = zh_header.get_width() + slash.get_width() + en_header.get_width()
            hx = SCREEN_WIDTH // 2 - header_width // 2
            screen.blit(zh_header, (hx, 29))
            screen.blit(slash, (hx + zh_header.get_width(), 29))
            screen.blit(en_header, (hx + zh_header.get_width() + slash.get_width(), 29))

            panel = pygame.Rect(30, 78, 900, 420)
            _draw_panel(screen, panel, accent=(62, 151, 255), alpha=225)
            pygame.draw.line(screen, (52, 76, 112), (382, 100), (382, 473), 1)

            icon_box = pygame.Rect(120, 108, 170, 88)
            pygame.draw.rect(screen, (18, 34, 58), icon_box, border_radius=18)
            pygame.draw.rect(screen, (62, 151, 255), icon_box, 2, border_radius=18)
            pygame.draw.rect(screen, (255, 190, 82), (156, 137, 95, 54), border_radius=7)
            pygame.draw.line(screen, (126, 82, 28), (157, 138), (203, 169), 3)
            pygame.draw.line(screen, (126, 82, 28), (250, 138), (203, 169), 3)
            heart = [(275, 119), (285, 110), (295, 119), (295, 130), (275, 148), (255, 130), (255, 119), (265, 110)]
            pygame.draw.polygon(screen, (255, 112, 62), heart)

            intro_cn = [
                "感谢您对《篮界狂潮》的支持！",
                "如果遇到了问题、有建议或想法，",
                "欢迎告诉我们。",
                "您的反馈会帮助游戏变得更好！",
            ]
            for i, line in enumerate(intro_cn):
                surface = zh_small.render(line, True, (226, 234, 247))
                screen.blit(surface, surface.get_rect(center=(206, 226 + i * 25)))

            pygame.draw.line(screen, (58, 81, 116), (75, 335), (337, 335), 1)
            intro_en = [
                "Thank you for supporting HOOP HAVOC!",
                "Found a bug or have an idea?",
                "We would love to hear from you.",
                "Your feedback makes the game better!",
            ]
            for i, line in enumerate(intro_en):
                surface = en_small.render(line, True, (166, 186, 218))
                screen.blit(surface, surface.get_rect(center=(206, 358 + i * 25)))

            label1 = zh_small.render("问题类型", True, COLOR_TEXT)
            label1_en = en_small.render(" / Type", True, (166, 186, 218))
            screen.blit(label1, (430, 104))
            screen.blit(label1_en, (430 + label1.get_width(), 104))
            _draw_feedback_input(screen, zh_small, type_rect, type_labels[type_keys[type_index]], "", dropdown_open)
            pygame.draw.polygon(
                screen,
                (255, 132, 55) if dropdown_open else (132, 154, 190),
                [(type_rect.right - 24, type_rect.centery - 5),
                 (type_rect.right - 12, type_rect.centery - 5),
                 (type_rect.right - 18, type_rect.centery + 5)],
            )

            label2 = zh_small.render("反馈内容", True, COLOR_TEXT)
            label2_en = en_small.render(" / Content", True, (166, 186, 218))
            screen.blit(label2, (430, 190))
            screen.blit(label2_en, (430 + label2.get_width(), 190))
            _draw_feedback_input(
                screen,
                zh_small if get_language() == "zh" else en_small,
                content_rect,
                content,
                "请详细描述您的问题或建议... / Please describe your issue or suggestion...",
                active_field == "content",
                multiline=True,
            )

            label3 = zh_small.render("您的邮箱（可选）", True, COLOR_TEXT)
            label3_en = en_small.render(" / Email (optional)", True, (166, 186, 218))
            screen.blit(label3, (430, 344))
            screen.blit(label3_en, (430 + label3.get_width(), 344))
            _draw_feedback_input(screen, en_small, email_rect, email, "example@email.com", active_field == "email")

            reset_hover = reset_rect.collidepoint(mouse_pos)
            submit_hover = submit_rect.collidepoint(mouse_pos)
            _draw_menu_button(screen, zh_small, "重置 / RESET", reset_rect, reset_hover)
            _draw_menu_button(screen, zh_small, "提交 / SUBMIT", submit_rect, submit_hover)

            if pygame.time.get_ticks() < status_until:
                status = zh_small.render("已打开 GitHub 提交页面 / GitHub feedback page opened", True, (111, 224, 164))
            else:
                status = zh_small.render("反馈将通过 GitHub Issues 提交给开发者 / Submitted via GitHub Issues", True, (137, 158, 190))
            screen.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2 + 105, 488)))

            # Draw dropdown last so it appears above the rest of the form.
            if dropdown_open:
                for i, key in enumerate(type_keys):
                    rect = dropdown_rects[i]
                    selected = i == type_index
                    hovered = i == dropdown_hover
                    fill = (31, 46, 72) if (selected or hovered) else (14, 23, 42)
                    border = (255, 132, 55) if selected else (62, 82, 117)
                    pygame.draw.rect(screen, fill, rect)
                    pygame.draw.rect(screen, border, rect, 1)
                    label = zh_small.render(type_labels[key], True, COLOR_TEXT if (selected or hovered) else (196, 210, 232))
                    screen.blit(label, label.get_rect(midleft=(rect.x + 14, rect.centery)))
                    if selected:
                        check = en_small.render("✓", True, (255, 132, 55))
                        screen.blit(check, check.get_rect(midright=(rect.right - 14, rect.centery)))

            pygame.display.flip()
            clock.tick(FPS)
    finally:
        pygame.key.stop_text_input()

def settings_menu(screen, font, small_font, title_font, settings):
    get_audio().set_music_scale(1.0)

    items = [
        "language",
        "fullscreen",
        "master_volume",
        "music_volume",
        "sfx_volume",
        "show_fps",
        "back",
    ]
    selected = 0
    clock = pygame.time.Clock()

    def apply_live_audio():
        audio = get_audio()
        audio.set_master_volume(settings.master_volume)
        audio.set_music_volume(settings.music_volume)
        audio.set_sfx_volume(settings.sfx_volume)

    def change_volume(item, delta):
        current = int(getattr(settings, item))
        setattr(settings, item, max(0, min(100, current + delta)))
        apply_live_audio()

    while True:
        rects = [
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 103 + i * 55, 440, 44)
            for i in range(len(items))
        ]
        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return settings, "quit"

            clicked = _clicked_index(event, rects)
            activate = clicked is not None
            if clicked is not None:
                selected = clicked

            if event.type == pygame.MOUSEWHEEL and items[selected] in (
                "master_volume",
                "music_volume",
                "sfx_volume",
            ):
                change_volume(items[selected], event.y * 5)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(items)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(items)
                elif event.key in (
                    pygame.K_LEFT,
                    pygame.K_a,
                    pygame.K_RIGHT,
                    pygame.K_d,
                ):
                    if items[selected] in (
                        "master_volume",
                        "music_volume",
                        "sfx_volume",
                    ):
                        delta = -5 if event.key in (pygame.K_LEFT, pygame.K_a) else 5
                        change_volume(items[selected], delta)
                    elif items[selected] == "language":
                        settings.language = "zh" if settings.language == "en" else "en"
                        set_language(settings.language)
                        font, small_font, title_font = create_fonts(settings.language)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    activate = True
                elif event.key == pygame.K_ESCAPE:
                    return settings, "apply"

            if activate:
                item = items[selected]
                if item == "language":
                    settings.language = "zh" if settings.language == "en" else "en"
                    set_language(settings.language)
                    font, small_font, title_font = create_fonts(settings.language)
                elif item == "fullscreen":
                    settings.fullscreen = not settings.fullscreen
                    # Apply it right away so the player sees the mode change
                    # when they flip the switch, not after leaving this page.
                    # In-place only: a switch that needed the display rebuilt
                    # would invalidate the surface this loop draws into, so
                    # that case is left to main() once we return.
                    set_fullscreen(settings.fullscreen, allow_rebuild=False)
                elif item in (
                    "master_volume",
                    "music_volume",
                    "sfx_volume",
                ):
                    current = int(getattr(settings, item))
                    next_value = (current + 10) % 110
                    change_volume(item, next_value - current)
                elif item == "show_fps":
                    settings.show_fps = not settings.show_fps
                elif item == "back":
                    return settings, "apply"

        _draw_backdrop(screen, (62, 151, 255))
        title = title_font.render(tr("settings.title"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 56)))

        _draw_panel(
            screen,
            pygame.Rect(SCREEN_WIDTH // 2 - 250, 82, 500, 410),
            accent=(62, 151, 255),
            alpha=210,
        )

        on, off = tr("common.on"), tr("common.off")
        lang_value = tr("settings.language_zh") if settings.language == "zh" else tr("settings.language_en")
        values = [
            tr("settings.language", value=lang_value),
            tr("settings.fullscreen", value=on if settings.fullscreen else off),
            tr("settings.master_volume", value=settings.master_volume),
            tr("settings.music_volume", value=settings.music_volume),
            tr("settings.sfx_volume", value=settings.sfx_volume),
            tr("settings.show_fps", value=on if settings.show_fps else off),
            tr("common.back"),
        ]

        for index, label in enumerate(values):
            _draw_menu_button(screen, font, label, rects[index], index == selected)

        help_text = small_font.render(tr("settings.help"), True, (175, 185, 205))
        screen.blit(help_text, help_text.get_rect(center=(SCREEN_WIDTH // 2, 516)))
        pygame.display.flip()
        clock.tick(FPS)

def draw_scoreboard(screen, font, p1, p2):
    panel = pygame.Surface((510, 58), pygame.SRCALPHA)
    pygame.draw.rect(panel, (4, 8, 18, 205), panel.get_rect(), border_radius=15)
    pygame.draw.rect(panel, (255, 255, 255, 42), panel.get_rect(), 1, border_radius=15)
    pygame.draw.polygon(panel, (50, 142, 255, 210), [(0, 0), (172, 0), (150, 58), (0, 58)])
    pygame.draw.polygon(panel, (255, 104, 55, 210), [(338, 0), (510, 0), (510, 58), (360, 58)])
    score = font.render(f"{p1.score}   :   {p2.score}", True, (255, 255, 255))
    p1_label = font.render(p1.character_name.upper(), True, (255, 255, 255))
    p2_label = font.render(p2.character_name.upper(), True, (255, 255, 255))
    panel.blit(score, score.get_rect(center=(255, 29)))
    panel.blit(p1_label, p1_label.get_rect(center=(82, 29)))
    panel.blit(p2_label, p2_label.get_rect(center=(428, 29)))
    screen.blit(panel, panel.get_rect(midtop=(SCREEN_WIDTH // 2, 12)))


def draw_score_popup(screen, title_font, points, timer, arena):
    if timer <= 0 or points <= 0:
        return
    elapsed = SCORE_POPUP_DURATION_FRAMES - timer
    popup_y = arena["rim_y"] - 70 - elapsed * 0.35
    surface = title_font.render(f"+{points}", True, SCORE_POPUP_COLOR)
    screen.blit(surface, (int(arena["rim_x"] + 35 - surface.get_width() / 2), int(popup_y)))


def draw_win_overlay(screen, font, title_font, small_font, winner, single_player, human_player):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    pygame.draw.circle(overlay, (255, 128, 42, 32), (SCREEN_WIDTH // 2, 240), 260)
    screen.blit(overlay, (0, 0))
    _draw_panel(screen, pygame.Rect(205, 125, 550, 265), selected=True, accent=(255, 176, 55), alpha=235, radius=22)

    human_won = winner is human_player
    if single_player and not human_won:
        result_text = tr("result.lose")
        subtitle_text = tr("result.lose_subtitle")
        title_color = (220, 80, 80)
    else:
        result_text = tr("result.win")
        subtitle_text = tr("result.win_subtitle")
        title_color = (255, 215, 0)

    name_surface = font.render(winner.name, True, COLOR_TEXT)
    result_surface = title_font.render(result_text, True, title_color)
    subtitle_surface = font.render(subtitle_text, True, COLOR_TEXT)
    hint_surface = small_font.render(
        tr("result.hint"), True, COLOR_TEXT
    )

    screen.blit(name_surface, (SCREEN_WIDTH // 2 - name_surface.get_width() // 2, 165))
    screen.blit(result_surface, (SCREEN_WIDTH // 2 - result_surface.get_width() // 2, 210))
    screen.blit(subtitle_surface, (SCREEN_WIDTH // 2 - subtitle_surface.get_width() // 2, 275))
    screen.blit(hint_surface, (SCREEN_WIDTH // 2 - hint_surface.get_width() // 2, 345))


def select_mode(screen, font, title_font):
    # 模式选择恢复完整 BGM。
    get_audio().set_music_scale(1.0)

    """开始游戏后的模式选择：1 AI、2 双人、3 训练营。"""
    clock = pygame.time.Clock()
    selected = 0
    modes = ["ai", "local", "training"]

    while True:
        rects = [
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 210, 440, 52),
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 278, 440, 52),
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 346, 440, 52),
        ]
        back_rect = pygame.Rect(18, 18, 150, 38)

        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and back_rect.collidepoint(event.pos)
            ):
                return "back"

            clicked = _clicked_index(event, rects)
            if clicked is not None:
                return modes[clicked]

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(modes)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(modes)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return modes[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    return "ai"
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    return "local"
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    return "training"
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "back"

        _draw_backdrop(screen, (62, 151, 255))
        _draw_back_button(screen, font)

        title = title_font.render(tr("select.mode_title"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))

        _draw_panel(
            screen,
            pygame.Rect(SCREEN_WIDTH // 2 - 250, 178, 500, 250),
            accent=(62, 151, 255),
            alpha=205,
        )

        labels = [
            f"1  {tr('select.ai')}",
            f"2  {tr('select.local')}",
            f"3  {tr('select.training')}",
        ]
        for index, label in enumerate(labels):
            _draw_menu_button(screen, font, label, rects[index], index == selected)

        pygame.display.flip()
        clock.tick(FPS)


def select_character(screen, font, small_font, title_font, player_label):
    # 选人阶段 BGM = 当前音乐音量的 50%。
    get_audio().set_music_scale(0.5)

    """Scalable focus-carousel character select.

    One character is featured in the center with full-size art and complete
    information. Other characters remain as side previews, so the layout keeps
    working even when the roster grows beyond four characters.
    """
    clock = pygame.time.Clock()
    selected = 0
    transition_from = 0
    transition_started = 0
    transition_duration = 220

    def move_selection(delta):
        nonlocal selected, transition_from, transition_started
        if not CHARACTER_ORDER:
            return
        transition_from = selected
        selected = (selected + delta) % len(CHARACTER_ORDER)
        transition_started = pygame.time.get_ticks()

    while True:
        if not CHARACTER_ORDER:
            return "back"

        back_rect = pygame.Rect(18, 18, 150, 38)

        # Side preview hit areas.
        left_preview_rect = pygame.Rect(34, 150, 210, 300)
        right_preview_rect = pygame.Rect(SCREEN_WIDTH - 244, 150, 210, 300)
        center_card = pygame.Rect(250, 118, 460, 366)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if back_rect.collidepoint(event.pos):
                        return "back"
                    if center_card.collidepoint(event.pos):
                        return CHARACTER_ORDER[selected]
                    if left_preview_rect.collidepoint(event.pos):
                        move_selection(-1)
                    elif right_preview_rect.collidepoint(event.pos):
                        move_selection(1)
                elif event.button == 4:
                    move_selection(-1)
                elif event.button == 5:
                    move_selection(1)

            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    move_selection(-1)
                elif event.y < 0:
                    move_selection(1)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "back"
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    move_selection(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    move_selection(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return CHARACTER_ORDER[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1) and len(CHARACTER_ORDER) >= 1:
                    return CHARACTER_ORDER[0]
                elif event.key in (pygame.K_2, pygame.K_KP2) and len(CHARACTER_ORDER) >= 2:
                    return CHARACTER_ORDER[1]
                elif event.key in (pygame.K_3, pygame.K_KP3) and len(CHARACTER_ORDER) >= 3:
                    return CHARACTER_ORDER[2]
                elif event.key in (pygame.K_4, pygame.K_KP4) and len(CHARACTER_ORDER) >= 4:
                    return CHARACTER_ORDER[3]
                elif event.key in (pygame.K_5, pygame.K_KP5) and len(CHARACTER_ORDER) >= 5:
                    return CHARACTER_ORDER[4]
                elif event.key in (pygame.K_6, pygame.K_KP6) and len(CHARACTER_ORDER) >= 6:
                    return CHARACTER_ORDER[5]

        _draw_backdrop(screen, (146, 83, 255))
        _draw_back_button(screen, font)

        title = title_font.render(
            tr("select.character_title", player=player_label),
            True,
            COLOR_TEXT,
        )
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 54)))

        hint_text = (
            "A / D  •  ← / →  •  滚轮切换  •  1-6 快选  •  ENTER 确认"
            if get_language() == "zh"
            else "A / D  •  ← / →  •  Wheel  •  1-6 quick select  •  ENTER confirm"
        )
        hint = small_font.render(hint_text, True, (180, 194, 219))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        now = pygame.time.get_ticks()
        if transition_started:
            t = min(1.0, (now - transition_started) / max(1, transition_duration))
            t = _smoothstep(t)
        else:
            t = 1.0

        current_id = CHARACTER_ORDER[selected]
        current = CHARACTERS[current_id]
        accent = current.get("ui_accent", current["color"])

        # ---- Side previews ----
        roster_count = len(CHARACTER_ORDER)
        left_index = (selected - 1) % roster_count
        right_index = (selected + 1) % roster_count

        for side, index, rect in (
            ("left", left_index, left_preview_rect),
            ("right", right_index, right_preview_rect),
        ):
            cid = CHARACTER_ORDER[index]
            cfg = CHARACTERS[cid]
            side_accent = cfg.get("ui_accent", cfg["color"])

            hovered = rect.collidepoint(pygame.mouse.get_pos())
            preview_panel = rect.inflate(-18, -22)
            _draw_panel(
                screen,
                preview_panel,
                hovered,
                accent=side_accent,
                alpha=150 if not hovered else 190,
                radius=18,
            )

            preview = _load_character_select_art(
                cid,
                target_height=215,
                max_width=155,
            )
            if preview:
                screen.blit(
                    preview,
                    preview.get_rect(midbottom=(preview_panel.centerx, preview_panel.bottom - 42)),
                )

            name = font.render(
                tr(f"characters.{cid}.name"),
                True,
                (205, 215, 235),
            )
            screen.blit(name, name.get_rect(center=(preview_panel.centerx, preview_panel.bottom - 24)))

            arrow_color = side_accent if hovered else (128, 148, 180)
            cy = rect.centery
            if side == "left":
                pygame.draw.polygon(
                    screen,
                    arrow_color,
                    [(rect.x + 4, cy), (rect.x + 18, cy - 14), (rect.x + 18, cy + 14)],
                )
            else:
                pygame.draw.polygon(
                    screen,
                    arrow_color,
                    [(rect.right - 4, cy), (rect.right - 18, cy - 14), (rect.right - 18, cy + 14)],
                )

        # ---- Main featured card ----
        _draw_panel(
            screen,
            center_card,
            True,
            accent=accent,
            alpha=242,
            radius=22,
        )

        # Left half: large portrait, shown cleanly without a glow circle.
        art_rect = pygame.Rect(center_card.x + 18, center_card.y + 18, 205, center_card.height - 36)

        portrait = _load_character_select_art(
            current_id,
            target_height=270,
            max_width=190,
        )
        if portrait:
            screen.blit(
                portrait,
                portrait.get_rect(midbottom=(art_rect.centerx, art_rect.bottom - 22)),
            )

        # Roster counter.
        counter = small_font.render(
            f"{selected + 1:02d} / {roster_count:02d}",
            True,
            accent,
        )
        screen.blit(counter, (center_card.x + 22, center_card.y + 18))

        # Right half: readable full information.
        info_x = center_card.x + 238
        info_width = center_card.width - 258

        name_surface = title_font.render(
            tr(f"characters.{current_id}.name"),
            True,
            COLOR_TEXT,
        )
        screen.blit(name_surface, (info_x, center_card.y + 34))

        ability_label = (
            "专属技能" if get_language() == "zh" else "ABILITY"
        )
        ability_label_surface = small_font.render(
            ability_label,
            True,
            (135, 153, 185),
        )
        screen.blit(ability_label_surface, (info_x, center_card.y + 94))

        ability_lines = _wrap_text(
            font,
            tr(f"characters.{current_id}.ability"),
            info_width,
        )
        y = center_card.y + 118
        for line in ability_lines[:3]:
            surface = font.render(line, True, accent)
            screen.blit(surface, (info_x, y))
            y += font.get_linesize()

        # PROFILE 与普通角色保持统一布局。
        desc_y = max(
            y + 12,
            center_card.y + 186,
        )

        # ---------- PROFILE ----------
        desc_label = (
            "角色介绍"
            if get_language() == "zh"
            else "PROFILE"
        )

        desc_label_surface = small_font.render(
            desc_label,
            True,
            (135, 153, 185),
        )

        screen.blit(
            desc_label_surface,
            (info_x, desc_y),
        )

        desc_y += 25

        description_lines = _wrap_text(
            small_font,
            tr(
                f"characters.{current_id}.description"
            ),
            info_width,
        )

        # 最多只显示两行。
        # 属性条从下方固定区域开始，所以不会再发生重叠。
        for line in description_lines[:2]:
            surface = small_font.render(
                line,
                True,
                (218, 225, 239),
            )

            screen.blit(
                surface,
                (info_x, desc_y),
            )

            desc_y += small_font.get_linesize()

        # Rating bars.
        ratings = current.get("ratings", {})
        # 属性区固定在卡片底部，和角色介绍保持足够间距。
        rating_y = center_card.bottom - 96
        rating_specs = [
            ("SPD", ratings.get("speed", 3)),
            ("3PT", ratings.get("three", 3)),
            ("DNK", ratings.get("dunk", 3)),
            ("DEF", ratings.get("defense", 3)),
        ]

        for idx, (label, value) in enumerate(rating_specs):
            row_y = rating_y + idx * 22
            lab = small_font.render(label, True, (165, 183, 211))
            screen.blit(lab, (info_x, row_y))

            bar_x = info_x + 42
            for pip in range(5):
                pip_rect = pygame.Rect(bar_x + pip * 24, row_y + 4, 18, 8)
                if pip < value:
                    pygame.draw.rect(screen, accent, pip_rect, border_radius=4)
                else:
                    pygame.draw.rect(screen, (47, 61, 88), pip_rect, border_radius=4)

        # Confirm button.
        confirm_rect = pygame.Rect(center_card.centerx - 92, center_card.bottom + 10, 184, 38)
        confirm_hovered = confirm_rect.collidepoint(pygame.mouse.get_pos())
        _draw_menu_button(
            screen,
            small_font,
            tr("common.confirm") if tr("common.confirm") != "common.confirm" else ("确认选择" if get_language() == "zh" else "CONFIRM"),
            confirm_rect,
            confirm_hovered,
        )

        # Mouse click on explicit confirm button.
        if pygame.mouse.get_pressed()[0] and confirm_hovered:
            pygame.time.wait(90)
            return CHARACTER_ORDER[selected]

        pygame.display.flip()
        clock.tick(FPS)

def select_arena(screen, font, small_font, title_font):
    # 球场选择恢复完整 BGM。
    get_audio().set_music_scale(1.0)

    clock = pygame.time.Clock()
    selected = 0
    card_w, card_h, gap = 270, 290, 25
    total = len(ARENA_ORDER) * card_w + (len(ARENA_ORDER) - 1) * gap
    start_x = SCREEN_WIDTH // 2 - total // 2

    while True:
        rects = [
            pygame.Rect(start_x + i * (card_w + gap), 150, card_w, card_h)
            for i in range(len(ARENA_ORDER))
        ]
        back_rect = pygame.Rect(18, 18, 150, 38)

        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and back_rect.collidepoint(event.pos)
            ):
                return "back"

            clicked = _clicked_index(event, rects)
            if clicked is not None:
                return ARENA_ORDER[clicked]

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "back"
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(ARENA_ORDER)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(ARENA_ORDER)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return ARENA_ORDER[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    return ARENA_ORDER[0]
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    return ARENA_ORDER[1]
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    return ARENA_ORDER[2]

        _draw_backdrop(screen, (255, 132, 55))
        _draw_back_button(screen, font)

        title = title_font.render(
            tr("select.arena_title"),
            True,
            COLOR_TEXT,
        )
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))

        for i, arena_id in enumerate(ARENA_ORDER):
            arena = ARENAS[arena_id]
            rect = rects[i]
            x, y = rect.x, rect.y
            _draw_panel(
                screen,
                rect,
                i == selected,
                accent=arena["accent_color"],
                alpha=225,
            )

            preview = _load_ui_image(
                f"arenas/{arena_id}/background.png",
                (card_w - 32, 132),
            )
            if preview:
                if arena.get("flip_background_x", False):
                    preview = pygame.transform.flip(preview, True, False)
                screen.blit(preview, (x + 16, y + 34))
                pygame.draw.rect(
                    screen,
                    arena["accent_color"],
                    (x + 16, y + 34, card_w - 32, 132),
                    2,
                    border_radius=8,
                )

            pygame.draw.circle(screen, arena["accent_color"], (x + 28, y + 24), 14)
            index_surface = small_font.render(str(i + 1), True, COLOR_TEXT)
            screen.blit(index_surface, index_surface.get_rect(center=(x + 28, y + 24)))

            name = font.render(
                tr(f"arenas.{arena_id}.name"),
                True,
                COLOR_TEXT,
            )
            screen.blit(name, name.get_rect(center=(rect.centerx, y + 205)))

            # English arena descriptions can be wider than one card.
            # Wrap them to at most two centered lines so they never overlap
            # neighbouring cards; Chinese descriptions keep working too.
            description = tr(f"arenas.{arena_id}.description")
            description_lines = _wrap_text(
                small_font,
                description,
                card_w - 44,
            )[:2]
            description_y = y + 238
            for line in description_lines:
                desc = small_font.render(line, True, (210, 219, 235))
                screen.blit(
                    desc,
                    desc.get_rect(center=(rect.centerx, description_y)),
                )
                description_y += 22

        hint = small_font.render(tr("common.select_hint"), True, COLOR_TEXT)
        screen.blit(
            hint,
            hint.get_rect(center=(SCREEN_WIDTH // 2, 492)),
        )
        pygame.display.flip()
        clock.tick(FPS)


def select_difficulty(screen, font, title_font):
    # 难度选择恢复完整 BGM。
    get_audio().set_music_scale(1.0)

    clock = pygame.time.Clock()
    selected = 1
    values = ["easy", "normal", "hard"]

    while True:
        rects = [
            pygame.Rect(SCREEN_WIDTH // 2 - 200, 220 + i * 70, 400, 52)
            for i in range(3)
        ]
        back_rect = pygame.Rect(18, 18, 150, 38)

        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and back_rect.collidepoint(event.pos)
            ):
                return "back"

            clicked = _clicked_index(event, rects)
            if clicked is not None:
                return values[clicked]

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "back"
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % 3
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return values[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    return "easy"
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    return "normal"
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    return "hard"

        _draw_backdrop(screen, (255, 76, 88))
        _draw_back_button(screen, font)

        title = title_font.render(
            tr("select.difficulty_title"),
            True,
            COLOR_TEXT,
        )
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 140)))

        _draw_panel(
            screen,
            pygame.Rect(SCREEN_WIDTH // 2 - 235, 190, 470, 250),
            accent=(255, 76, 88),
            alpha=205,
        )

        labels = [
            f"1  {tr('difficulty.easy')}",
            f"2  {tr('difficulty.normal')}",
            f"3  {tr('difficulty.hard')}",
        ]
        for i, label in enumerate(labels):
            _draw_menu_button(screen, font, label, rects[i], i == selected)

        pygame.display.flip()
        clock.tick(FPS)


def pause_menu(screen, font, title_font):
    """ESC 暂停菜单。支持键盘和鼠标。"""
    clock = pygame.time.Clock(); selected = 0
    actions = ["resume", "restart", "menu", "quit"]
    while True:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 205)); screen.blit(overlay, (0, 0))
        _draw_panel(screen, pygame.Rect(SCREEN_WIDTH//2-255, 105, 510, 400), selected=True, accent=(62, 151, 255), alpha=238, radius=22)
        title = title_font.render(tr("pause.title"), True, COLOR_TEXT); screen.blit(title,title.get_rect(center=(SCREEN_WIDTH//2,150)))
        rects=[pygame.Rect(SCREEN_WIDTH//2-210,215+i*62,420,48) for i in range(4)]
        hovered=_mouse_selected(rects)
        if hovered is not None: selected=hovered
        labels=[tr("pause.resume"),tr("pause.restart"),tr("pause.menu"),tr("pause.quit")]
        for i,label in enumerate(labels): _draw_menu_button(screen,font,label,rects[i],i==selected)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "quit"
            clicked=_clicked_index(event,rects)
            if clicked is not None: return actions[clicked]
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP,pygame.K_w): selected=(selected-1)%4
                elif event.key in (pygame.K_DOWN,pygame.K_s): selected=(selected+1)%4
                elif event.key in (pygame.K_RETURN,pygame.K_SPACE): return actions[selected]
                elif event.key in (pygame.K_ESCAPE, pygame.K_p): return "resume"
                elif event.key == pygame.K_r: return "restart"
                elif event.key == pygame.K_m: return "menu"
                elif event.key == pygame.K_q: return "quit"
        clock.tick(FPS)
