"""场景数据库与绘制逻辑。

每个场景既可以使用程序化背景，也可以放入 background.png。
图片路径：assets/arenas/<场景ID>/background.png
"""

import os
import math
import pygame

from constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT

ARENAS = {
    "street": {
        "id": "street",
        "name": "Sunset Street",
        "description": "A warm street court at sunset.",
        "sky_top": (245, 120, 85),
        "sky_bottom": (95, 75, 130),
        "ground_color": (68, 63, 72),
        "court_color": (93, 82, 92),
        "line_color": (245, 225, 190),
        "accent_color": (255, 190, 90),
        "flip_background_x": True,
        "ground_y": 480,
        "backboard_x": 28,
        "rim_x": 76,
        "rim_y": 305,
        "hoop_width": 46,
        "hoop_height": 14,
        "three_point_distance": 340,
        "player1_spawn_x": 560,
        "player2_spawn_x": 760,
        "ball_spawn_x": 640,
    },
    "gym": {
        "id": "gym",
        "name": "Neon Gym",
        "description": "An indoor court with bright arena lights.",
        "sky_top": (22, 32, 58),
        "sky_bottom": (48, 58, 86),
        "ground_color": (47, 39, 51),
        "court_color": (82, 66, 78),
        "line_color": (120, 235, 255),
        "accent_color": (255, 95, 185),
        "flip_background_x": True,
        "ground_y": 470,
        "backboard_x": 34,
        "rim_x": 84,
        "rim_y": 300,
        "hoop_width": 48,
        "hoop_height": 14,
        "three_point_distance": 355,
        "player1_spawn_x": 555,
        "player2_spawn_x": 755,
        "ball_spawn_x": 635,
    },
    "rooftop": {
        "id": "rooftop",
        "name": "Moon Rooftop",
        "description": "A windy rooftop above the city.",
        "sky_top": (12, 20, 44),
        "sky_bottom": (52, 66, 105),
        "ground_color": (54, 59, 69),
        "court_color": (72, 78, 88),
        "line_color": (220, 235, 255),
        "accent_color": (145, 185, 255),
        "flip_background_x": True,
        "ground_y": 475,
        "backboard_x": 30,
        "rim_x": 78,
        "rim_y": 303,
        "hoop_width": 46,
        "hoop_height": 14,
        "three_point_distance": 345,
        "player1_spawn_x": 565,
        "player2_spawn_x": 765,
        "ball_spawn_x": 645,
    },
}

ARENA_ORDER = ["street", "gym", "rooftop"]
DEFAULT_ARENA = "street"


def get_arena(arena_id):
    return dict(ARENAS.get(arena_id, ARENAS[DEFAULT_ARENA]))


def _gradient(screen, top, bottom):
    for y in range(SCREEN_HEIGHT):
        t = y / max(1, SCREEN_HEIGHT - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))


def _load_background(arena, assets_dir):
    path = os.path.join(assets_dir, "arenas", arena["id"], "background.png")
    if not os.path.exists(path):
        return None
    try:
        image = pygame.image.load(path).convert()
        if arena.get("flip_background_x", False):
            image = pygame.transform.flip(image, True, False)
        return pygame.transform.smoothscale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error:
        return None


def _load_hoop(arena, assets_dir):
    if "_hoop" in arena:
        return arena["_hoop"]
    path = os.path.join(assets_dir, "props", "hoop.png")
    try:
        image = pygame.image.load(path).convert_alpha() if os.path.exists(path) else None
    except pygame.error:
        image = None
    arena["_hoop"] = image
    return image


def draw_arena(screen, arena, assets_dir):
    """绘制场景，并缓存静态画面以减少每帧重复绘制造成的卡顿。"""
    cached = arena.get("_rendered_surface")
    if cached is not None:
        screen.blit(cached, (0, 0))
        return

    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)).convert()

    background = arena.get("_background")
    if "_background" not in arena:
        background = _load_background(arena, assets_dir)
        arena["_background"] = background

    if background is not None:
        canvas.blit(background, (0, 0))
    else:
        _gradient(canvas, arena["sky_top"], arena["sky_bottom"])
        _draw_theme_details(canvas, arena)

    ground_y = arena["ground_y"]
    three_x = arena["rim_x"] + arena["three_point_distance"]

    guide = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(guide, (*arena["line_color"], 115), (0, ground_y), (SCREEN_WIDTH, ground_y), 2)
    pygame.draw.line(guide, (*arena["accent_color"], 205), (three_x, ground_y - 19), (three_x, ground_y + 2), 4)
    pygame.draw.circle(guide, (*arena["accent_color"], 80), (three_x, ground_y - 8), 13, 2)
    canvas.blit(guide, (0, 0))

    bx, rx, ry = arena["backboard_x"], arena["rim_x"], arena["rim_y"]
    hoop_asset = _load_hoop(arena, assets_dir)
    if hoop_asset is not None:
        hoop_h = 310
        hoop_w = int(hoop_asset.get_width() * hoop_h / hoop_asset.get_height())
        hoop = pygame.transform.scale(hoop_asset, (hoop_w, hoop_h))
        hoop_pos = (int(rx - hoop_w * 0.82), int(ry - hoop_h * 0.358))
        canvas.blit(hoop, hoop_pos)
    else:
        pygame.draw.line(canvas, (238, 238, 245), (bx, ry - 62), (bx, ry + 28), 6)
        pygame.draw.line(canvas, (238, 238, 245), (bx, ry), (rx, ry), 4)
        pygame.draw.rect(
            canvas,
            arena["accent_color"],
            (rx - arena["hoop_width"] // 2, ry - arena["hoop_height"] // 2,
             arena["hoop_width"], arena["hoop_height"]),
            3,
        )

    label_font = pygame.font.Font(None, 18)
    label_font.set_bold(True)
    label = label_font.render("3PT", True, arena["line_color"])
    badge = pygame.Surface((label.get_width() + 12, label.get_height() + 5), pygame.SRCALPHA)
    pygame.draw.rect(badge, (5, 10, 22, 165), badge.get_rect(), border_radius=7)
    badge.blit(label, (6, 2))
    canvas.blit(badge, badge.get_rect(midbottom=(three_x, ground_y - 24)))

    arena["_rendered_surface"] = canvas
    screen.blit(canvas, (0, 0))


def trigger_hoop_net(arena, strength=1.0):
    """进球后触发篮网摆动。"""
    strength = max(
        0.5,
        min(1.6, float(strength)),
    )

    duration = (
        54
        if strength >= 1.25
        else 44
    )

    arena["_net_timer"] = duration
    arena["_net_duration"] = duration
    arena["_net_strength"] = strength


def update_hoop_net(arena):
    """更新篮网摆动时间。"""
    timer = int(
        arena.get(
            "_net_timer",
            0,
        )
    )

    if timer > 0:
        timer -= 1
        arena["_net_timer"] = timer

    if timer <= 0:
        arena["_net_timer"] = 0
        arena["_net_strength"] = 0.0


def draw_dynamic_hoop_net(screen, arena):
    """只在进球/扣篮后叠加动态篮网。"""

    timer = int(
        arena.get(
            "_net_timer",
            0,
        )
    )

    if timer <= 0:
        return

    duration = max(
        1,
        int(
            arena.get(
                "_net_duration",
                44,
            )
        ),
    )

    strength = float(
        arena.get(
            "_net_strength",
            1.0,
        )
    )

    age = duration - timer
    decay = timer / duration

    rim_x = float(
        arena["rim_x"]
    )

    rim_y = float(
        arena["rim_y"]
    )

    top_width = float(
        arena["hoop_width"]
    )

    bottom_width = (
        top_width * 0.50
    )

    # 左右摆动逐渐减弱。
    sway = (
        math.sin(age * 0.72)
        * 12.0
        * decay
        * strength
    )

    # 进球后篮网先被向下拉长再回弹。
    stretch = (
        abs(
            math.sin(
                age * 0.32
            )
        )
        * 9.0
        * decay
        * strength
    )

    net_height = (
        40.0 + stretch
    )

    fx_width = 132
    fx_height = 96

    fx = pygame.Surface(
        (
            fx_width,
            fx_height,
        ),
        pygame.SRCALPHA,
    )

    cx = fx_width / 2
    top_y = 7.0

    alpha = max(
        35,
        int(
            205
            * decay
        ),
    )

    main_color = (
        240,
        245,
        255,
        alpha,
    )

    soft_color = (
        210,
        225,
        245,
        max(
            20,
            int(alpha * 0.66),
        ),
    )

    # --------------------------------------------------------
    # 纵向篮网线
    # --------------------------------------------------------
    line_count = 8

    for i in range(line_count):
        t = (
            i
            / (line_count - 1)
        )

        top_x = (
            cx
            - top_width / 2
            + top_width * t
        )

        bottom_x = (
            cx
            - bottom_width / 2
            + bottom_width * t
            + sway
        )

        middle_x_1 = (
            top_x * 0.67
            + bottom_x * 0.33
            + sway * 0.08
        )

        middle_x_2 = (
            top_x * 0.34
            + bottom_x * 0.66
            + sway * 0.16
        )

        points = [
            (
                int(top_x),
                int(top_y),
            ),
            (
                int(middle_x_1),
                int(
                    top_y
                    + net_height * 0.34
                ),
            ),
            (
                int(middle_x_2),
                int(
                    top_y
                    + net_height * 0.67
                ),
            ),
            (
                int(bottom_x),
                int(
                    top_y
                    + net_height
                ),
            ),
        ]

        pygame.draw.lines(
            fx,
            main_color,
            False,
            points,
            2,
        )

    # --------------------------------------------------------
    # 横向篮网线
    # --------------------------------------------------------
    for row in range(1, 5):
        t = row / 5.0

        width_here = (
            top_width * (1.0 - t)
            + bottom_width * t
        )

        center_shift = (
            sway * (t ** 1.55)
        )

        wave = (
            math.sin(
                age * 0.55
                + row * 1.15
            )
            * 2.5
            * decay
            * strength
        )

        y = (
            top_y
            + net_height * t
            + wave
        )

        left_x = (
            cx
            - width_here / 2
            + center_shift
        )

        right_x = (
            cx
            + width_here / 2
            + center_shift
        )

        pygame.draw.line(
            fx,
            soft_color,
            (
                int(left_x),
                int(y),
            ),
            (
                int(right_x),
                int(y),
            ),
            2,
        )

    screen.blit(
        fx,
        (
            int(
                rim_x
                - fx_width / 2
            ),
            int(
                rim_y
                - top_y
            ),
        ),
    )


def _draw_theme_details(screen, arena):
    if arena["id"] == "street":
        pygame.draw.circle(screen, (255,205,125), (760,115), 58)
        for x,h in [(80,95),(150,130),(230,78),(810,120),(885,88)]:
            pygame.draw.rect(screen, (42,42,58), (x, 480-h, 64, h))
    elif arena["id"] == "gym":
        for x in range(90, SCREEN_WIDTH, 190):
            pygame.draw.ellipse(screen, (190,245,255), (x,42,90,20))
        pygame.draw.rect(screen, (18,24,42), (270,110,420,120), border_radius=12)
        pygame.draw.rect(screen, arena["accent_color"], (285,125,390,90), 4, border_radius=10)
    else:
        pygame.draw.circle(screen, (225,235,255), (760,105), 50)
        for x,h in [(70,115),(145,75),(220,145),(310,92),(785,100),(865,145)]:
            pygame.draw.rect(screen, (25,31,49), (x, 475-h, 58, h))
            for wy in range(475-h+14, 465, 22):
                pygame.draw.rect(screen, (245,210,105), (x+12,wy,8,8))
