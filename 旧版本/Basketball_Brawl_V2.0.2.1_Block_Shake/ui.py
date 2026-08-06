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
