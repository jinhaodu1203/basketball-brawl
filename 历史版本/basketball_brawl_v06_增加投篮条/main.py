"""2D 篮球大乱斗主程序。"""

import os
import sys

import pygame

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    COLOR_BG, COLOR_GROUND, COLOR_HOOP, COLOR_TEXT,
    COLOR_COURT_LINE, COLOR_PAINT_FILL,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT,
    RIM_X, RIM_Y, BACKBOARD_X, BACKBOARD_TOP_Y, BACKBOARD_HEIGHT,
    PAINT_BAND_HEIGHT, FREE_THROW_LINE_X, FREE_THROW_CIRCLE_RADIUS,
    TWO_POINT_RADIUS, THREE_POINT_RADIUS, COURT_LINE_FLATTEN, COURT_LINE_WIDTH,
    HALF_COURT_X, COURT_BAND_CENTER_Y_OFFSET,
    PLAYER1_SPAWN_X, PLAYER2_SPAWN_X, BALL_SPAWN_X, PLAYER_HEIGHT,
    AI_DIFFICULTY_LABELS, WINNING_SCORE,
    SCORE_POPUP_DURATION_FRAMES, ROUND_RESET_DELAY_FRAMES, SCORE_POPUP_COLOR,
)
from entities import Player, Ball
from characters import CHARACTER_ORDER, CHARACTERS, get_character
from arenas import ARENA_ORDER, ARENAS, get_arena, draw_arena

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

PLAYER1_CONTROLS = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "action": pygame.K_SPACE,
    "steal": pygame.K_s,
    "ability": pygame.K_LSHIFT,
}

PLAYER2_CONTROLS = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "action": pygame.K_RETURN,
    "steal": pygame.K_DOWN,
    "ability": pygame.K_RCTRL,
}


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


def reset_round(player1, player2, ball, arena):
    player1.reset_for_round(arena["player1_spawn_x"])
    player2.reset_for_round(arena["player2_spawn_x"])
    ball.x = arena["ball_spawn_x"]
    ball.y = arena["ground_y"] - 200
    ball.vx = 0
    ball.vy = 0
    ball.state = "loose"
    ball.holder = None
    ball.last_shooter = None
    ball.shot_distance = 0


def play_session(screen, font, small_font, title_font):
    single_player = select_mode(screen, font, title_font)

    player1_character = get_character(
        select_character(screen, font, small_font, title_font, "Player 1")
    )
    player2_label = "AI" if single_player else "Player 2"
    player2_character = get_character(
        select_character(screen, font, small_font, title_font, player2_label)
    )

    ai_difficulty = (
        select_difficulty(screen, font, title_font) if single_player else "normal"
    )

    arena = get_arena(select_arena(screen, font, small_font, title_font))

    player1 = Player(
        arena["player1_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        player1_character["color"],
        PLAYER1_CONTROLS,
        facing_right=False,
        name=f"P1 - {player1_character['name']}",
        sprite_folder=os.path.join(
            ASSETS_DIR, "characters", player1_character["sprite_folder"]
        ),
        character_config=player1_character,
        arena=arena,
    )

    player2_name = (
        f"AI {player2_character['name']} ({AI_DIFFICULTY_LABELS[ai_difficulty]})"
        if single_player
        else f"P2 - {player2_character['name']}"
    )
    player2 = Player(
        arena["player2_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        player2_character["color"],
        PLAYER2_CONTROLS,
        facing_right=False,
        name=player2_name,
        sprite_folder=os.path.join(
            ASSETS_DIR, "characters", player2_character["sprite_folder"]
        ),
        ai_controlled=single_player,
        character_config=player2_character,
        arena=arena,
    )

    if single_player:
        player2.apply_ai_difficulty(ai_difficulty)

    ball = Ball(
        arena["ball_spawn_x"],
        arena["ground_y"] - 200,
        sprite_path=os.path.join(ASSETS_DIR, "ball.png"),
        arena=arena,
    )

    players = [player1, player2]
    clock = pygame.time.Clock()
    game_over = False
    winner = None
    round_reset_timer = 0
    score_popup_timer = 0
    score_popup_points = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if game_over and event.key in (pygame.K_RETURN, pygame.K_r):
                    return

        if not game_over:
            if round_reset_timer > 0:
                round_reset_timer -= 1
                if round_reset_timer == 0:
                    reset_round(player1, player2, ball, arena)
            else:
                keys = pygame.key.get_pressed()
                for player in players:
                    opponent = player2 if player is player1 else player1
                    if player.ai_controlled:
                        player.handle_ai(ball, opponent)
                    else:
                        player.handle_input(keys, ball, opponent)
                    player.update_physics()
                    player.try_pick_up(ball)

                ball.update()
                scorer, points = ball.check_score()
                if scorer is not None:
                    scorer.score += points
                    score_popup_points = points
                    score_popup_timer = SCORE_POPUP_DURATION_FRAMES
                    if scorer.score >= WINNING_SCORE:
                        game_over = True
                        winner = scorer
                    else:
                        round_reset_timer = ROUND_RESET_DELAY_FRAMES

        if score_popup_timer > 0:
            score_popup_timer -= 1

        draw_arena(screen, arena, ASSETS_DIR)

        for player in players:
            player.draw(screen, small_font)
        ball.draw(screen)
        draw_scoreboard(screen, font, player1, player2)
        draw_score_popup(screen, title_font, score_popup_points, score_popup_timer, arena)

        if game_over:
            draw_win_overlay(
                screen,
                font,
                title_font,
                small_font,
                winner,
                single_player,
                player1,
            )

        pygame.display.flip()
        clock.tick(FPS)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Basketball Brawl - Demo")
    font = pygame.font.SysFont(None, 30)
    small_font = pygame.font.SysFont(None, 20)
    title_font = pygame.font.SysFont(None, 48)

    while True:
        play_session(screen, font, small_font, title_font)


if __name__ == "__main__":
    main()
