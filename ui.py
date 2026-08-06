"""菜单、HUD、暂停与结算界面。"""

import sys
import pygame

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    COLOR_BG, COLOR_TEXT,
    SCORE_POPUP_DURATION_FRAMES, SCORE_POPUP_COLOR,
)
from characters import CHARACTER_ORDER, CHARACTERS
from arenas import ARENA_ORDER, ARENAS
from localization import create_fonts, set_language, tr, tr_list


def _draw_menu_button(screen, font, text, rect, selected=False):
    fill = (78, 92, 130) if selected else (48, 52, 70)
    border = (255, 205, 90) if selected else (115, 125, 155)
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, border, rect, width=3, border_radius=12)
    label = font.render(text, True, COLOR_TEXT)
    screen.blit(label, label.get_rect(center=rect.center))

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
    rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, SCREEN_HEIGHT - 48, 180, 34)
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    _draw_menu_button(screen, font, tr("common.back"), rect, hovered)
    return rect


def main_menu(screen, font, small_font, title_font):
    """正式主菜单。支持键盘与鼠标。"""
    selected = 0
    clock = pygame.time.Clock()

    while True:
        options = [
            (tr("menu.play"), "play"),
            (tr("menu.how_to_play"), "how_to_play"),
            (tr("menu.settings"), "settings"),
            (tr("menu.credits"), "credits"),
            (tr("menu.quit"), "quit"),
        ]
        rects = [pygame.Rect(SCREEN_WIDTH // 2 - 145, 230 + i * 54, 290, 42) for i in range(len(options))]
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

        screen.fill((22, 24, 36))
        pygame.draw.circle(screen, (60, 75, 120), (SCREEN_WIDTH // 2, 92), 68)
        pygame.draw.circle(screen, (255, 170, 55), (SCREEN_WIDTH // 2, 92), 45)
        pygame.draw.line(screen, (40, 35, 30), (SCREEN_WIDTH // 2 - 45, 92), (SCREEN_WIDTH // 2 + 45, 92), 4)
        pygame.draw.arc(screen, (40, 35, 30), (SCREEN_WIDTH // 2 - 45, 47, 90, 90), 1.0, 2.15, 4)
        pygame.draw.arc(screen, (40, 35, 30), (SCREEN_WIDTH // 2 - 45, 47, 90, 90), 4.15, 5.28, 4)

        title = title_font.render(tr("app.title"), True, COLOR_TEXT)
        subtitle = small_font.render(tr("app.subtitle"), True, (175, 185, 210))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 172)))
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 202)))

        for index, (label, _) in enumerate(options):
            _draw_menu_button(screen, font, label, rects[index], index == selected)

        hint = small_font.render(tr("menu.hint"), True, (170, 175, 195))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 516)))
        pygame.display.flip()
        clock.tick(FPS)


def _info_page(screen, title_font, small_font, title, sections, footer=None):
    """绘制可复用的信息页；sections 为 (heading, lines) 列表。"""
    screen.fill((22, 24, 36))
    title_surface = title_font.render(title, True, COLOR_TEXT)
    screen.blit(title_surface, title_surface.get_rect(center=(SCREEN_WIDTH // 2, 54)))

    panel = pygame.Rect(74, 95, SCREEN_WIDTH - 148, SCREEN_HEIGHT - 150)
    pygame.draw.rect(screen, (35, 39, 56), panel, border_radius=16)
    pygame.draw.rect(screen, (105, 120, 165), panel, width=2, border_radius=16)

    columns = 2 if len(sections) > 2 else 1
    column_width = panel.width // columns
    for index, (heading, lines) in enumerate(sections):
        column = index % columns
        row = index // columns
        x = panel.x + 30 + column * column_width
        y = panel.y + 26 + row * 178
        heading_surface = small_font.render(heading, True, (255, 205, 90))
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

        screen.fill((24, 27, 40))
        title = title_font.render(tr("settings.title"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))
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
    text = f"{p1.name}  {p1.score}  :  {p2.score}  {p2.name}"
    surface = font.render(text, True, COLOR_TEXT)
    screen.blit(surface, (SCREEN_WIDTH // 2 - surface.get_width() // 2, 20))


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
    screen.blit(overlay, (0, 0))

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
    clock = pygame.time.Clock()
    selected = 0
    while True:
        rects = [
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 235, 440, 52),
            pygame.Rect(SCREEN_WIDTH // 2 - 220, 305, 440, 52),
        ]
        hovered = _mouse_selected(rects)
        if hovered is not None:
            selected = hovered
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            clicked = _clicked_index(event, rects)
            if clicked is not None:
                return clicked == 0
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s): selected = 1 - selected
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE): return selected == 0
                elif event.key in (pygame.K_1, pygame.K_KP1): return True
                elif event.key in (pygame.K_2, pygame.K_KP2): return False
                elif event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
        screen.fill(COLOR_BG)
        title = title_font.render(tr("select.mode_title"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150)))
        labels = [tr("select.single"), tr("select.local")]
        for i, label in enumerate(labels): _draw_menu_button(screen, font, label, rects[i], i == selected)
        pygame.display.flip(); clock.tick(FPS)


def select_character(screen, font, small_font, title_font, player_label):
    clock = pygame.time.Clock()
    selected = 0
    card_width, card_height, gap = 250, 300, 25
    total_width = len(CHARACTER_ORDER) * card_width + (len(CHARACTER_ORDER) - 1) * gap
    start_x = SCREEN_WIDTH // 2 - total_width // 2
    card_y = 145
    while True:
        rects = [pygame.Rect(start_x + i * (card_width + gap), card_y, card_width, card_height) for i in range(len(CHARACTER_ORDER))]
        hovered = _mouse_selected(rects)
        if hovered is not None: selected = hovered
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            clicked = _clicked_index(event, rects)
            if clicked is not None: return CHARACTER_ORDER[clicked]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.key in (pygame.K_LEFT, pygame.K_a): selected = (selected - 1) % len(CHARACTER_ORDER)
                elif event.key in (pygame.K_RIGHT, pygame.K_d): selected = (selected + 1) % len(CHARACTER_ORDER)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE): return CHARACTER_ORDER[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1): return CHARACTER_ORDER[0]
                elif event.key in (pygame.K_2, pygame.K_KP2): return CHARACTER_ORDER[1]
                elif event.key in (pygame.K_3, pygame.K_KP3): return CHARACTER_ORDER[2]
        screen.fill(COLOR_BG)
        title = title_font.render(tr("select.character_title", player=player_label), True, COLOR_TEXT)
        hint = small_font.render(tr("common.select_hint"), True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 62)))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 105)))
        for index, character_id in enumerate(CHARACTER_ORDER):
            config = CHARACTERS[character_id]; card_rect = rects[index]; card_x, card_y = card_rect.x, card_rect.y
            fill = (64, 66, 86) if index == selected else (50, 50, 65)
            pygame.draw.rect(screen, fill, card_rect, border_radius=14)
            pygame.draw.rect(screen, (255, 215, 0) if index == selected else config["color"], card_rect, width=5 if index == selected else 4, border_radius=14)
            screen.blit(font.render(str(index + 1), True, COLOR_TEXT), (card_x + 15, card_y + 12))
            preview_center = (card_x + card_width // 2, card_y + 75)
            pygame.draw.circle(screen, config["color"], preview_center, 45); pygame.draw.circle(screen, COLOR_TEXT, preview_center, 45, width=3)
            name_surface = font.render(tr(f"characters.{character_id}.name"), True, COLOR_TEXT)
            ability_surface = small_font.render(tr(f"characters.{character_id}.ability"), True, (255, 215, 0))
            description_surface = small_font.render(tr(f"characters.{character_id}.description"), True, COLOR_TEXT)
            stats_surface = small_font.render(tr("select.speed_jump", speed=config["move_speed"], jump=abs(config["jump_velocity"])), True, COLOR_TEXT)
            screen.blit(name_surface, name_surface.get_rect(center=(card_rect.centerx, card_y + 148)))
            screen.blit(ability_surface, ability_surface.get_rect(center=(card_rect.centerx, card_y + 185)))
            screen.blit(description_surface, description_surface.get_rect(center=(card_rect.centerx, card_y + 220)))
            screen.blit(stats_surface, stats_surface.get_rect(center=(card_rect.centerx, card_y + 258)))
        pygame.display.flip(); clock.tick(FPS)


def select_arena(screen, font, small_font, title_font):
    clock = pygame.time.Clock(); selected = 0
    card_w, card_h, gap = 270, 290, 25
    total = len(ARENA_ORDER) * card_w + (len(ARENA_ORDER) - 1) * gap
    start_x = SCREEN_WIDTH // 2 - total // 2
    while True:
        rects = [pygame.Rect(start_x + i * (card_w + gap), 150, card_w, card_h) for i in range(len(ARENA_ORDER))]
        hovered = _mouse_selected(rects)
        if hovered is not None: selected = hovered
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            clicked = _clicked_index(event, rects)
            if clicked is not None: return ARENA_ORDER[clicked]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.key in (pygame.K_LEFT, pygame.K_a): selected = (selected - 1) % len(ARENA_ORDER)
                elif event.key in (pygame.K_RIGHT, pygame.K_d): selected = (selected + 1) % len(ARENA_ORDER)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE): return ARENA_ORDER[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1): return ARENA_ORDER[0]
                elif event.key in (pygame.K_2, pygame.K_KP2): return ARENA_ORDER[1]
                elif event.key in (pygame.K_3, pygame.K_KP3): return ARENA_ORDER[2]
        screen.fill(COLOR_BG)
        title = title_font.render(tr("select.arena_title"), True, COLOR_TEXT); screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 70)))
        for i, arena_id in enumerate(ARENA_ORDER):
            arena = ARENAS[arena_id]; rect = rects[i]; x,y=rect.x,rect.y
            pygame.draw.rect(screen, arena["sky_bottom"], rect, border_radius=16)
            pygame.draw.rect(screen, (255,215,0) if i == selected else arena["accent_color"], rect, 6 if i == selected else 4, border_radius=16)
            pygame.draw.rect(screen, arena["court_color"], (x+18,y+38,card_w-36,120), border_radius=10)
            pygame.draw.line(screen, arena["line_color"], (x+145,y+55),(x+145,y+145),5)
            screen.blit(font.render(str(i+1),True,COLOR_TEXT),(x+14,y+10))
            name=font.render(tr(f"arenas.{arena_id}.name"),True,COLOR_TEXT); desc=small_font.render(tr(f"arenas.{arena_id}.description"),True,COLOR_TEXT)
            screen.blit(name,name.get_rect(center=(rect.centerx,y+200))); screen.blit(desc,desc.get_rect(center=(rect.centerx,y+245)))
        hint=small_font.render(tr("common.select_hint"),True,COLOR_TEXT); screen.blit(hint,hint.get_rect(center=(SCREEN_WIDTH//2,480)))
        pygame.display.flip(); clock.tick(FPS)


def select_difficulty(screen, font, title_font):
    clock = pygame.time.Clock(); selected = 1
    values = ["easy", "normal", "hard"]
    while True:
        rects = [pygame.Rect(SCREEN_WIDTH // 2 - 200, 220 + i * 70, 400, 52) for i in range(3)]
        hovered = _mouse_selected(rects)
        if hovered is not None: selected = hovered
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            clicked = _clicked_index(event, rects)
            if clicked is not None: return values[clicked]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                if event.key in (pygame.K_UP, pygame.K_w): selected = (selected - 1) % 3
                elif event.key in (pygame.K_DOWN, pygame.K_s): selected = (selected + 1) % 3
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE): return values[selected]
                elif event.key in (pygame.K_1, pygame.K_KP1): return "easy"
                elif event.key in (pygame.K_2, pygame.K_KP2): return "normal"
                elif event.key in (pygame.K_3, pygame.K_KP3): return "hard"
        screen.fill(COLOR_BG)
        title = title_font.render(tr("select.difficulty_title"), True, COLOR_TEXT); screen.blit(title,title.get_rect(center=(SCREEN_WIDTH//2,140)))
        labels=[tr("select.easy"),tr("select.normal"),tr("select.hard")]
        for i,label in enumerate(labels): _draw_menu_button(screen,font,label,rects[i],i==selected)
        pygame.display.flip(); clock.tick(FPS)


def pause_menu(screen, font, title_font):
    """ESC 暂停菜单。支持键盘和鼠标。"""
    clock = pygame.time.Clock(); selected = 0
    actions = ["resume", "restart", "menu", "quit"]
    while True:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 205)); screen.blit(overlay, (0, 0))
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