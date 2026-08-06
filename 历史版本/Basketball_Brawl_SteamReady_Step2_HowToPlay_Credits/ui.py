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


def _draw_menu_button(screen, font, text, rect, selected=False):
    fill = (78, 92, 130) if selected else (48, 52, 70)
    border = (255, 205, 90) if selected else (115, 125, 155)
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, border, rect, width=3, border_radius=12)
    label = font.render(text, True, COLOR_TEXT)
    screen.blit(label, label.get_rect(center=rect.center))


def main_menu(screen, font, small_font, title_font):
    """正式主菜单。返回 play / how_to_play / settings / credits / quit。"""
    options = [
        ("PLAY", "play"),
        ("HOW TO PLAY", "how_to_play"),
        ("SETTINGS", "settings"),
        ("CREDITS", "credits"),
        ("QUIT", "quit"),
    ]
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
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

        title = title_font.render("BASKETBALL BRAWL", True, COLOR_TEXT)
        subtitle = small_font.render("STEAM-READY DEVELOPMENT BUILD", True, (175, 185, 210))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 172)))
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 202)))

        for index, (label, _) in enumerate(options):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 145, 230 + index * 54, 290, 42)
            _draw_menu_button(screen, font, label, rect, index == selected)

        hint = small_font.render("W/S or arrows: select    ENTER: confirm", True, (170, 175, 195))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 516)))
        pygame.display.flip()
        clock.tick(FPS)


def _info_page(screen, title_font, small_font, title, sections, footer="ESC / ENTER: Back"):
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

    footer_surface = small_font.render(footer, True, (170, 180, 205))
    screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, 510)))


def how_to_play_menu(screen, font, small_font, title_font):
    """操作说明页。返回 back / quit。"""
    sections = [
        ("PLAYER 1", [
            "Move: A / D",
            "Jump, block, rebound, dunk: W",
            "Shoot / charge shot: SPACE",
            "Steal / pick up ball: S",
            "Character ability: LEFT SHIFT",
        ]),
        ("PLAYER 2", [
            "Move: LEFT / RIGHT",
            "Jump, block, rebound, dunk: UP",
            "Shoot / charge shot: ENTER",
            "Steal / pick up ball: DOWN",
            "Character ability: RIGHT CTRL",
        ]),
        ("MATCH RULES", [
            "Score from inside the 3PT line: 1 point",
            "Score from outside the 3PT line: 2 points",
            "First player to reach the target score wins",
            "Hold the shoot key, then release in the green zone",
        ]),
        ("GENERAL", [
            "Pause match: ESC",
            "Dunk: carry the ball above the rim, then descend",
            "Blocks and rebounds trigger automatically while jumping",
            "Use each character's ability to create an advantage",
        ]),
    ]
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return "back"
        _info_page(screen, title_font, small_font, "HOW TO PLAY", sections)
        pygame.display.flip()
        clock.tick(FPS)


def credits_menu(screen, font, small_font, title_font):
    """制作组与版本署名页。返回 back / quit。"""
    sections = [
        ("CREATOR", [
            "Created and directed by Jinhao Du (David)",
            "Independent game development project",
            "Original concept: 2D Basketball Brawl",
        ]),
        ("DEVELOPMENT", [
            "Programming: Python + Pygame",
            "Game design, balancing and testing: Jinhao Du",
            "Current build: Steam-ready development version",
        ]),
        ("SPECIAL THANKS", [
            "Pygame community and open-source contributors",
            "Friends and players who test each build",
            "Northeastern University community",
        ]),
        ("NOTICE", [
            "All final commercial art, music and fonts must be licensed",
            "Basketball Brawl is an independent original project",
            "Copyright (c) 2026 Jinhao Du. All rights reserved.",
        ]),
    ]
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                    return "back"
        _info_page(screen, title_font, small_font, "CREDITS", sections)
        pygame.display.flip()
        clock.tick(FPS)

def settings_menu(screen, font, small_font, title_font, settings):
    """设置菜单。直接修改并返回 settings。"""
    items = ["fullscreen", "volume", "show_fps", "back"]
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return settings, "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(items)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(items)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    if items[selected] == "volume":
                        settings.master_volume = max(0, settings.master_volume - 5)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if items[selected] == "volume":
                        settings.master_volume = min(100, settings.master_volume + 5)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if items[selected] == "fullscreen":
                        settings.fullscreen = not settings.fullscreen
                    elif items[selected] == "show_fps":
                        settings.show_fps = not settings.show_fps
                    elif items[selected] == "back":
                        return settings, "apply"
                elif event.key == pygame.K_ESCAPE:
                    return settings, "apply"

        screen.fill((24, 27, 40))
        title = title_font.render("SETTINGS", True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 90)))

        values = [
            f"Fullscreen: {'ON' if settings.fullscreen else 'OFF'}",
            f"Master Volume: {settings.master_volume}%",
            f"Show FPS: {'ON' if settings.show_fps else 'OFF'}",
            "BACK",
        ]
        for index, label in enumerate(values):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 210, 165 + index * 68, 420, 52)
            _draw_menu_button(screen, font, label, rect, index == selected)

        help_text = small_font.render("LEFT/RIGHT adjusts volume. Changes are saved automatically.", True, (175, 185, 205))
        screen.blit(help_text, help_text.get_rect(center=(SCREEN_WIDTH // 2, 470)))
        pygame.display.flip()
        clock.tick(FPS)


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
        result_text = "YOU LOST!"
        subtitle_text = "AI IS THE GOAT!"
        title_color = (220, 80, 80)
    else:
        result_text = "YOU WIN!"
        subtitle_text = "You Are The GOAT!"
        title_color = (255, 215, 0)

    name_surface = font.render(winner.name, True, COLOR_TEXT)
    result_surface = title_font.render(result_text, True, title_color)
    subtitle_surface = font.render(subtitle_text, True, COLOR_TEXT)
    hint_surface = small_font.render(
        "Press ENTER or R to play again, ESC to quit", True, COLOR_TEXT
    )

    screen.blit(name_surface, (SCREEN_WIDTH // 2 - name_surface.get_width() // 2, 165))
    screen.blit(result_surface, (SCREEN_WIDTH // 2 - result_surface.get_width() // 2, 210))
    screen.blit(subtitle_surface, (SCREEN_WIDTH // 2 - subtitle_surface.get_width() // 2, 275))
    screen.blit(hint_surface, (SCREEN_WIDTH // 2 - hint_surface.get_width() // 2, 345))


def select_mode(screen, font, title_font):
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    return True
                if event.key in (pygame.K_2, pygame.K_KP2):
                    return False
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        screen.fill(COLOR_BG)
        title = title_font.render("2D Basketball Brawl", True, COLOR_TEXT)
        option1 = font.render("Press 1  ->  1 Player (vs AI)", True, COLOR_TEXT)
        option2 = font.render("Press 2  ->  2 Player (local)", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))
        screen.blit(option1, (SCREEN_WIDTH // 2 - option1.get_width() // 2, 260))
        screen.blit(option2, (SCREEN_WIDTH // 2 - option2.get_width() // 2, 300))
        pygame.display.flip()
        clock.tick(FPS)


def select_character(screen, font, small_font, title_font, player_label):
    clock = pygame.time.Clock()
    key_to_index = {
        pygame.K_1: 0, pygame.K_KP1: 0,
        pygame.K_2: 1, pygame.K_KP2: 1,
        pygame.K_3: 2, pygame.K_KP3: 2,
    }

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                selected_index = key_to_index.get(event.key)
                if selected_index is not None and selected_index < len(CHARACTER_ORDER):
                    return CHARACTER_ORDER[selected_index]

        screen.fill(COLOR_BG)
        title = title_font.render(f"{player_label}: Choose Your Character", True, COLOR_TEXT)
        hint = small_font.render("Press 1, 2 or 3 to select", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 45))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 100))

        card_width = 250
        card_height = 300
        gap = 25
        total_width = len(CHARACTER_ORDER) * card_width + (len(CHARACTER_ORDER) - 1) * gap
        start_x = SCREEN_WIDTH // 2 - total_width // 2
        card_y = 145

        for index, character_id in enumerate(CHARACTER_ORDER):
            config = CHARACTERS[character_id]
            card_x = start_x + index * (card_width + gap)
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
            pygame.draw.rect(screen, (50, 50, 65), card_rect, border_radius=14)
            pygame.draw.rect(screen, config["color"], card_rect, width=4, border_radius=14)

            number_surface = font.render(str(index + 1), True, COLOR_TEXT)
            screen.blit(number_surface, (card_x + 15, card_y + 12))

            preview_center = (card_x + card_width // 2, card_y + 75)
            pygame.draw.circle(screen, config["color"], preview_center, 45)
            pygame.draw.circle(screen, COLOR_TEXT, preview_center, 45, width=3)

            name_surface = font.render(config["name"], True, COLOR_TEXT)
            ability_surface = small_font.render(config["ability_name"], True, (255, 215, 0))
            description_surface = small_font.render(config["description"], True, COLOR_TEXT)
            stats_surface = small_font.render(
                f"SPD {config['move_speed']:.1f}   JMP {abs(config['jump_velocity']):.1f}",
                True,
                COLOR_TEXT,
            )

            screen.blit(name_surface, (card_x + card_width // 2 - name_surface.get_width() // 2, card_y + 135))
            screen.blit(ability_surface, (card_x + card_width // 2 - ability_surface.get_width() // 2, card_y + 180))
            screen.blit(description_surface, (card_x + card_width // 2 - description_surface.get_width() // 2, card_y + 215))
            screen.blit(stats_surface, (card_x + card_width // 2 - stats_surface.get_width() // 2, card_y + 250))

        pygame.display.flip()
        clock.tick(FPS)


def select_arena(screen, font, small_font, title_font):
    clock = pygame.time.Clock()
    key_to_index = {pygame.K_1: 0, pygame.K_KP1: 0, pygame.K_2: 1, pygame.K_KP2: 1, pygame.K_3: 2, pygame.K_KP3: 2}
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                index = key_to_index.get(event.key)
                if index is not None and index < len(ARENA_ORDER):
                    return ARENA_ORDER[index]

        screen.fill(COLOR_BG)
        title = title_font.render("Choose Your Arena", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH//2-title.get_width()//2, 55))
        card_w, card_h, gap = 270, 290, 25
        total = len(ARENA_ORDER)*card_w + (len(ARENA_ORDER)-1)*gap
        start_x = SCREEN_WIDTH//2-total//2
        for i, arena_id in enumerate(ARENA_ORDER):
            arena = ARENAS[arena_id]
            x, y = start_x+i*(card_w+gap), 150
            rect = pygame.Rect(x,y,card_w,card_h)
            pygame.draw.rect(screen, arena["sky_bottom"], rect, border_radius=16)
            pygame.draw.rect(screen, arena["accent_color"], rect, 4, border_radius=16)
            pygame.draw.rect(screen, arena["court_color"], (x+18,y+38,card_w-36,120), border_radius=10)
            pygame.draw.line(screen, arena["line_color"], (x+145,y+55),(x+145,y+145),5)
            number=font.render(str(i+1),True,COLOR_TEXT)
            name=font.render(arena["name"],True,COLOR_TEXT)
            desc=small_font.render(arena["description"],True,COLOR_TEXT)
            screen.blit(number,(x+14,y+10))
            screen.blit(name,(x+card_w//2-name.get_width()//2,y+185))
            screen.blit(desc,(x+card_w//2-desc.get_width()//2,y+230))
        hint=small_font.render("Press 1, 2 or 3 to select",True,COLOR_TEXT)
        screen.blit(hint,(SCREEN_WIDTH//2-hint.get_width()//2,470))
        pygame.display.flip(); clock.tick(FPS)


def select_difficulty(screen, font, title_font):
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    return "easy"
                if event.key in (pygame.K_2, pygame.K_KP2):
                    return "normal"
                if event.key in (pygame.K_3, pygame.K_KP3):
                    return "hard"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        screen.fill(COLOR_BG)
        title = title_font.render("Choose AI Difficulty", True, COLOR_TEXT)
        option1 = font.render("Press 1  ->  EZ PZ", True, COLOR_TEXT)
        option2 = font.render("Press 2  ->  Normal", True, COLOR_TEXT)
        option3 = font.render("Press 3  ->  Hard as Hell", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 130))
        screen.blit(option1, (SCREEN_WIDTH // 2 - option1.get_width() // 2, 240))
        screen.blit(option2, (SCREEN_WIDTH // 2 - option2.get_width() // 2, 280))
        screen.blit(option3, (SCREEN_WIDTH // 2 - option3.get_width() // 2, 320))
        pygame.display.flip()
        clock.tick(FPS)


def pause_menu(screen, font, title_font):
    """ESC 暂停菜单。返回 resume / restart / menu / quit。"""
    clock = pygame.time.Clock()
    while True:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        screen.blit(overlay, (0, 0))

        title = title_font.render("PAUSED", True, COLOR_TEXT)
        resume = font.render("ESC / P  -  Resume", True, COLOR_TEXT)
        restart = font.render("R  -  Restart Match", True, COLOR_TEXT)
        menu = font.render("M  -  Back to Main Menu", True, COLOR_TEXT)
        quit_text = font.render("Q  -  Quit Game", True, COLOR_TEXT)

        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 135))
        screen.blit(resume, (SCREEN_WIDTH // 2 - resume.get_width() // 2, 235))
        screen.blit(restart, (SCREEN_WIDTH // 2 - restart.get_width() // 2, 275))
        screen.blit(menu, (SCREEN_WIDTH // 2 - menu.get_width() // 2, 315))
        screen.blit(quit_text, (SCREEN_WIDTH // 2 - quit_text.get_width() // 2, 355))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    return "resume"
                if event.key == pygame.K_r:
                    return "restart"
                if event.key == pygame.K_m:
                    return "menu"
                if event.key == pygame.K_q:
                    return "quit"
        clock.tick(FPS)
