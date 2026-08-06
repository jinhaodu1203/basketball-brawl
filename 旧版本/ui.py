"""菜单、HUD、暂停与结算界面。"""

import os
import sys
import pygame

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


def _draw_character_carousel(screen, characters, elapsed_ms):
    """
    主菜单人物轮盘：左后方 -> 中间前景 -> 右后方。

    每隔一段时间轮换一次，中间人物最大、最亮并绘制在最上层，
    另外两个人物缩小、变暗，形成类似角色选秀轮盘的纵深效果。
    """
    if not characters:
        return

    # 每个停留阶段 1.55 秒，其中最后 0.48 秒进行滑动切换。
    hold_ms = 1070
    move_ms = 480
    cycle_ms = hold_ms + move_ms
    phase_index = elapsed_ms // cycle_ms
    phase_time = elapsed_ms % cycle_ms

    if phase_time < hold_ms:
        transition = 0.0
    else:
        transition = _smoothstep((phase_time - hold_ms) / move_ms)

    # 槽位顺序：左后方、中间前景、右后方。
    slots = [
        {"center": (122, 338), "scale": 0.80, "alpha": 255, "y_offset": 6},
        {"center": (275, 312), "scale": 1.22, "alpha": 255, "y_offset": 0},
        {"center": (428, 338), "scale": 0.80, "alpha": 255, "y_offset": 6},
    ]

    # 角色按 Ninja -> DJH -> Gorilla 的顺序从左向右通过中央。
    count = len(characters)
    draw_items = []
    for character_index, (name, image) in enumerate(characters):
        if image is None:
            continue

        current_slot = (character_index + phase_index) % count
        next_slot = (current_slot + 1) % count
        current = slots[current_slot]
        target = slots[next_slot]

        # 右侧人物回到左侧时从屏幕边缘绕回，避免横穿中央。
        if current_slot == 2 and next_slot == 0:
            if transition < 0.5:
                local_t = transition * 2.0
                center_x = _lerp(current["center"][0], 520, local_t)
                center_y = _lerp(current["center"][1], 350, local_t)
                scale = _lerp(current["scale"], 0.55, local_t)
                alpha = 255
            else:
                local_t = (transition - 0.5) * 2.0
                center_x = _lerp(30, target["center"][0], local_t)
                center_y = _lerp(350, target["center"][1], local_t)
                scale = _lerp(0.55, target["scale"], local_t)
                alpha = 255
        else:
            center_x = _lerp(current["center"][0], target["center"][0], transition)
            center_y = _lerp(current["center"][1], target["center"][1], transition)
            scale = _lerp(current["scale"], target["scale"], transition)
            alpha = 255

        transformed = pygame.transform.scale(
            image,
            (
                max(1, int(image.get_width() * scale)),
                max(1, int(image.get_height() * scale)),
            ),
        )
        # 主页面人物保持逐像素透明，不再对整张 Surface 做透明度乘法。
        # 后排人物只通过缩放和位置制造层次，避免透明区域变成黑色方框。

        # 越接近中央越后绘制，确保中央角色盖在另外两个角色前面。
        depth = scale
        draw_items.append((depth, name, transformed, (int(center_x), int(center_y))))

    draw_items.sort(key=lambda item: item[0])
    for _, name, transformed, center in draw_items:
        # 后排角色加轻微暗色遮罩，中央人物保持正常亮度。
        screen.blit(transformed, transformed.get_rect(center=center))

    # 中央角色姓名牌随轮盘同步切换。
    center_character_index = (1 - phase_index) % count
    if transition >= 0.5:
        center_character_index = (center_character_index - 1) % count
    center_name = characters[center_character_index][0]

    plate = pygame.Rect(202, 426, 146, 28)
    panel = pygame.Surface(plate.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (7, 12, 25, 205), panel.get_rect(), border_radius=8)
    pygame.draw.rect(panel, (255, 132, 55, 225), panel.get_rect(), 2, border_radius=8)
    screen.blit(panel, plate)
    return center_name


def _crop_transparent_padding(image, alpha_threshold=12, padding=3):
    """Crop empty transparent padding around a portrait.

    This makes the visible character occupy more of the same UI rectangle,
    so the dark/empty box behind the carousel appears smaller without
    changing the rest of the main-menu layout.
    """
    surface = image.convert_alpha()
    width, height = surface.get_size()

    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            if surface.get_at((x, y)).a > alpha_threshold:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return surface

    min_x = max(0, min_x - padding)
    min_y = max(0, min_y - padding)
    max_x = min(width - 1, max_x + padding)
    max_y = min(height - 1, max_y + padding)

    rect = pygame.Rect(
        min_x,
        min_y,
        max_x - min_x + 1,
        max_y - min_y + 1,
    )
    return surface.subsurface(rect).copy().convert_alpha()

def _load_ui_image(relative_path, size=None):
    key = (relative_path, size)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    path = os.path.join(ASSET_ROOT, *relative_path.split("/"))
    try:
        image = pygame.image.load(path).convert_alpha()
        if relative_path.startswith("characters/") and relative_path.endswith("portrait.png"):
            image = _remove_connected_dark_background(image)
            image = _crop_transparent_padding(image)
        if size:
            if relative_path.startswith("characters/"):
                image = pygame.transform.scale(image, size)
            else:
                image = pygame.transform.smoothscale(image, size)
    except (pygame.error, FileNotFoundError):
        image = None
    _IMAGE_CACHE[key] = image
    return image


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
            (tr("menu.quit"), "quit"),
        ]
        rects = [pygame.Rect(595, 175 + i * 57, 300, 44) for i in range(len(options))]
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

        gorilla = _load_ui_image("characters/gorilla/portrait.png", (310, 430))
        djh = _load_ui_image("characters/djh/portrait.png", (294, 418))
        ninja = _load_ui_image("characters/ninja/portrait.png", (292, 414))

        elapsed = pygame.time.get_ticks() - entrance_started_at
        center_name = _draw_character_carousel(
            screen,
            [
                (tr("characters.ninja.name"), ninja),
                (tr("characters.djh.name"), djh),
                (tr("characters.gorilla.name"), gorilla),
            ],
            elapsed,
        )
        pygame.draw.line(screen, (255, 132, 55), (62, 460), (480, 460), 3)
        if center_name:
            roster = small_font.render(center_name, True, (245, 248, 255))
            screen.blit(roster, roster.get_rect(center=(275, 440)))

        menu_title = small_font.render("SELECT MODE", True, (132, 154, 190))
        screen.blit(menu_title, (595, 140))

        for index, (label, _) in enumerate(options):
            _draw_menu_button(screen, font, label, rects[index], index == selected)

        hint = small_font.render(tr("menu.hint"), True, (142, 158, 184))
        screen.blit(hint, hint.get_rect(midright=(895, 510)))
        pygame.display.flip()
        clock.tick(FPS)


def _info_page(screen, title_font, small_font, title, sections, footer=None):
    """绘制可复用的信息页；sections 为 (heading, lines) 列表。"""
    _draw_backdrop(screen, (62, 151, 255))
    title_surface = title_font.render(title, True, COLOR_TEXT)
    screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_WIDTH // 2, 54)))

    panel = pygame.Rect(74, 95, SCREEN_WIDTH - 148, SCREEN_HEIGHT - 150)
    _draw_panel(screen, panel, accent=(62, 151, 255), alpha=232)

    columns = 2 if len(sections) > 2 else 1
    column_width = panel.width // columns
    for index, (heading, lines) in enumerate(sections):
        column = index % columns
        row = index // columns
        x = panel.x + 30 + column * column_width
        y = panel.y + 26 + row * 178
        heading_surface = small_font.render(heading, True, (88, 181, 255))
        screen.blit(heading_surface, (x, y))
        for line_index, line in enumerate(lines):
            line_surface = small_font.render(line, True, (225, 230, 242))
            screen.blit(line_surface, (x, y + 29 + line_index * 24))

    footer_surface = small_font.render(footer or tr("common.footer_back"), True, (170, 180, 205))
    screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, 510)))


def how_to_play_menu(screen, font, small_font, title_font):
    sections = [
        (tr("how.p1"), tr_list("how.p1_lines")),
        (tr("how.p2"), tr_list("how.p2_lines")),
        (tr("how.rules"), tr_list("how.rule_lines")),
        (tr("how.general"), tr_list("how.general_lines")),
    ]
    clock = pygame.time.Clock()
    while True:
        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT - 48, 180, 34)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                return "back"
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                return "back"
        _info_page(screen, title_font, small_font, tr("how.title"), sections, footer="")
        _draw_back_button(screen, font)
        pygame.display.flip()
        clock.tick(FPS)

def credits_menu(screen, font, small_font, title_font):
    sections = [
        (tr("credits.creator"), tr_list("credits.creator_lines")),
        (tr("credits.development"), tr_list("credits.development_lines")),
        (tr("credits.thanks"), tr_list("credits.thanks_lines")),
        (tr("credits.notice"), tr_list("credits.notice_lines")),
    ]
    clock = pygame.time.Clock()
    while True:
        back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT - 48, 180, 34)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and back_rect.collidepoint(event.pos):
                return "back"
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                return "back"
        _info_page(screen, title_font, small_font, tr("credits.title"), sections, footer="")
        _draw_back_button(screen, font)
        pygame.display.flip()
        clock.tick(FPS)

def settings_menu(screen, font, small_font, title_font, settings):
    items = ["language", "fullscreen", "volume", "show_fps", "back"]
    selected = 0
    clock = pygame.time.Clock()
    while True:
        rects = [pygame.Rect(SCREEN_WIDTH // 2 - 220, 125 + i * 66, 440, 50) for i in range(len(items))]
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
            if event.type == pygame.MOUSEWHEEL and items[selected] == "volume":
                settings.master_volume = max(0, min(100, settings.master_volume + event.y * 5))
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w): selected = (selected - 1) % len(items)
                elif event.key in (pygame.K_DOWN, pygame.K_s): selected = (selected + 1) % len(items)
                elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    if items[selected] == "volume":
                        delta = -5 if event.key in (pygame.K_LEFT, pygame.K_a) else 5
                        settings.master_volume = max(0, min(100, settings.master_volume + delta))
                    elif items[selected] == "language":
                        settings.language = "zh" if settings.language == "en" else "en"
                        set_language(settings.language)
                        font, small_font, title_font = create_fonts(settings.language)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE): activate = True
                elif event.key == pygame.K_ESCAPE: return settings, "apply"
            if activate:
                if items[selected] == "language":
                    settings.language = "zh" if settings.language == "en" else "en"
                    set_language(settings.language)
                    font, small_font, title_font = create_fonts(settings.language)
                elif items[selected] == "fullscreen": settings.fullscreen = not settings.fullscreen
                elif items[selected] == "volume": settings.master_volume = (settings.master_volume + 10) % 110
                elif items[selected] == "show_fps": settings.show_fps = not settings.show_fps
                elif items[selected] == "back": return settings, "apply"

        _draw_backdrop(screen, (62, 151, 255))
        title = title_font.render(tr("settings.title"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))
        _draw_panel(screen, pygame.Rect(SCREEN_WIDTH // 2 - 250, 105, 500, 350), accent=(62, 151, 255), alpha=210)
        on, off = tr("common.on"), tr("common.off")
        lang_value = tr("settings.language_zh") if settings.language == "zh" else tr("settings.language_en")
        values = [
            tr("settings.language", value=lang_value),
            tr("settings.fullscreen", value=on if settings.fullscreen else off),
            tr("settings.volume", value=settings.master_volume),
            tr("settings.show_fps", value=on if settings.show_fps else off),
            tr("common.back"),
        ]
        for index, label in enumerate(values):
            _draw_menu_button(screen, font, label, rects[index], index == selected)
        help_text = small_font.render(tr("settings.help"), True, (175, 185, 205))
        screen.blit(help_text, help_text.get_rect(center=(SCREEN_WIDTH // 2, 485)))
        pygame.display.flip(); clock.tick(FPS)


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
    clock = pygame.time.Clock()
    selected = 0
    card_width, card_height, gap = 250, 340, 25
    total_width = len(CHARACTER_ORDER) * card_width + (len(CHARACTER_ORDER) - 1) * gap
    start_x = SCREEN_WIDTH // 2 - total_width // 2
    card_y = 128

    while True:
        rects = [
            pygame.Rect(
                start_x + i * (card_width + gap),
                card_y,
                card_width,
                card_height,
            )
            for i in range(len(CHARACTER_ORDER))
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
                return CHARACTER_ORDER[clicked]

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return "back"
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected = (selected - 1) % len(CHARACTER_ORDER)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected = (selected + 1) % len(CHARACTER_ORDER)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return CHARACTER_ORDER[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    return CHARACTER_ORDER[0]
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    return CHARACTER_ORDER[1]
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    return CHARACTER_ORDER[2]

        _draw_backdrop(screen, (146, 83, 255))
        _draw_back_button(screen, font)

        title = title_font.render(
            tr("select.character_title", player=player_label),
            True,
            COLOR_TEXT,
        )
        hint = small_font.render(tr("common.select_hint"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 62)))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 105)))

        for index, character_id in enumerate(CHARACTER_ORDER):
            config = CHARACTERS[character_id]
            card_rect = rects[index]
            card_x, local_card_y = card_rect.x, card_rect.y
            accent = config.get("ui_accent", config["color"])
            _draw_panel(
                screen,
                card_rect,
                index == selected,
                accent=accent,
                alpha=230 if index == selected else 205,
            )

            pygame.draw.circle(screen, accent, (card_x + 25, local_card_y + 25), 15)
            number = small_font.render(str(index + 1), True, (255, 255, 255))
            screen.blit(number, number.get_rect(center=(card_x + 25, local_card_y + 25)))

            preview = _load_ui_image(
                f"characters/{character_id}/portrait.png",
                (184, 252),
            )
            if preview:
                screen.blit(
                    preview,
                    preview.get_rect(midtop=(card_rect.centerx, local_card_y + 12)),
                )
            else:
                pygame.draw.circle(
                    screen,
                    accent,
                    (card_rect.centerx, local_card_y + 80),
                    45,
                )

            name_surface = font.render(
                tr(f"characters.{character_id}.name"),
                True,
                COLOR_TEXT,
            )
            ability_surface = small_font.render(
                tr(f"characters.{character_id}.ability"),
                True,
                accent,
            )
            description_surface = small_font.render(
                tr(f"characters.{character_id}.description"),
                True,
                (210, 219, 235),
            )
            stats_surface = small_font.render(
                tr(
                    "select.speed_jump",
                    speed=config["move_speed"],
                    jump=abs(config["jump_velocity"]),
                ),
                True,
                (158, 177, 207),
            )

            screen.blit(
                name_surface,
                name_surface.get_rect(center=(card_rect.centerx, local_card_y + 206)),
            )
            screen.blit(
                ability_surface,
                ability_surface.get_rect(center=(card_rect.centerx, local_card_y + 242)),
            )
            screen.blit(
                description_surface,
                description_surface.get_rect(center=(card_rect.centerx, local_card_y + 278)),
            )
            pygame.draw.line(
                screen,
                accent,
                (card_x + 25, local_card_y + 305),
                (card_x + card_width - 25, local_card_y + 305),
                1,
            )
            screen.blit(
                stats_surface,
                stats_surface.get_rect(center=(card_rect.centerx, local_card_y + 321)),
            )

        pygame.display.flip()
        clock.tick(FPS)


def select_arena(screen, font, small_font, title_font):
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
            desc = small_font.render(
                tr(f"arenas.{arena_id}.description"),
                True,
                COLOR_TEXT,
            )
            screen.blit(name, name.get_rect(center=(rect.centerx, y + 205)))
            screen.blit(desc, desc.get_rect(center=(rect.centerx, y + 245)))

        hint = small_font.render(tr("common.select_hint"), True, COLOR_TEXT)
        screen.blit(
            hint,
            hint.get_rect(center=(SCREEN_WIDTH // 2, 480)),
        )
        pygame.display.flip()
        clock.tick(FPS)


def select_difficulty(screen, font, title_font):
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
