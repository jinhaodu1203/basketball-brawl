"""场景数据库与绘制逻辑。

每个场景既可以使用程序化背景，也可以放入 background.png。
图片路径：assets/arenas/<场景ID>/background.png
"""

import os
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
        "ground_y": 480,
        "backboard_x": 28,
        "rim_x": 76,
        "rim_y": 270,
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
        "ground_y": 470,
        "backboard_x": 34,
        "rim_x": 84,
        "rim_y": 255,
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
        "ground_y": 475,
        "backboard_x": 30,
        "rim_x": 78,
        "rim_y": 265,
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
        return pygame.transform.smoothscale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except pygame.error:
        return None


def draw_arena(screen, arena, assets_dir):
    background = arena.get("_background")
    if "_background" not in arena:
        background = _load_background(arena, assets_dir)
        arena["_background"] = background

    if background is not None:
        screen.blit(background, (0, 0))
    else:
        _gradient(screen, arena["sky_top"], arena["sky_bottom"])
        _draw_theme_details(screen, arena)

    ground_y = arena["ground_y"]
    pygame.draw.rect(screen, arena["ground_color"], (0, ground_y, SCREEN_WIDTH, SCREEN_HEIGHT-ground_y))
    pygame.draw.rect(screen, arena["court_color"], (0, ground_y-54, SCREEN_WIDTH, 54))

    # 侧视角不再画压扁圆弧。三分线用明确的地板竖线表示出手边界。
    three_x = arena["rim_x"] + arena["three_point_distance"]
    pygame.draw.line(screen, arena["line_color"], (three_x, ground_y-54), (three_x, ground_y), 5)
    pygame.draw.line(screen, arena["line_color"], (0, ground_y-54), (SCREEN_WIDTH, ground_y-54), 2)

    # 罚球区视觉块
    pygame.draw.rect(screen, arena["accent_color"], (0, ground_y-54, 155, 54), 3)
    pygame.draw.line(screen, arena["line_color"], (155, ground_y-54), (155, ground_y), 3)

    # 篮板与篮筐
    bx, rx, ry = arena["backboard_x"], arena["rim_x"], arena["rim_y"]
    pygame.draw.line(screen, (238,238,245), (bx, ry-62), (bx, ry+28), 6)
    pygame.draw.line(screen, (238,238,245), (bx, ry), (rx, ry), 4)
    hoop_x = rx-arena["hoop_width"]//2
    hoop_y = ry-arena["hoop_height"]//2
    pygame.draw.rect(screen, arena["accent_color"], (hoop_x, hoop_y, arena["hoop_width"], arena["hoop_height"]), 3)

    # 简单篮网：只负责视觉，不参与碰撞。
    net_top_y = ry + arena["hoop_height"] // 2
    net_bottom_y = net_top_y + 34
    net_left = hoop_x + 6
    net_right = hoop_x + arena["hoop_width"] - 6
    pygame.draw.line(screen, (225, 225, 235), (net_left, net_top_y), (net_left + 7, net_bottom_y), 2)
    pygame.draw.line(screen, (225, 225, 235), (net_right, net_top_y), (net_right - 7, net_bottom_y), 2)
    pygame.draw.line(screen, (225, 225, 235), (net_left + 7, net_bottom_y), (net_right - 7, net_bottom_y), 2)
    pygame.draw.line(screen, (225, 225, 235), (rx, net_top_y), (rx, net_bottom_y), 1)

    label_font = pygame.font.SysFont(None, 18)
    label = label_font.render("3PT", True, arena["line_color"])
    screen.blit(label, (three_x-label.get_width()//2, ground_y-78))


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
