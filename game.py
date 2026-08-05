"""一场比赛的创建、更新、绘制和状态切换。"""

import os
import sys

import pygame

from constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    PLAYER_HEIGHT,
    AI_DIFFICULTY_LABELS,
    WINNING_SCORE,
    SCORE_POPUP_DURATION_FRAMES,
    ROUND_RESET_DELAY_FRAMES,
)
from player import Player
from ball import Ball
from characters import get_character
from arenas import get_arena, draw_arena
from feedback import FeedbackManager
from ui import (
    select_mode,
    select_character,
    select_difficulty,
    select_arena,
    pause_menu,
    draw_scoreboard,
    draw_score_popup,
    draw_win_overlay,
)

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


def reset_round(player1, player2, ball, arena):
    player1.reset_for_round(arena["player1_spawn_x"])
    player2.reset_for_round(arena["player2_spawn_x"])
    ball.x = arena["ball_spawn_x"]
    ball.y = arena["ground_y"] - 200
    ball.previous_x = ball.x
    ball.previous_y = ball.y
    ball.vx = 0
    ball.vy = 0
    ball.state = "loose"
    ball.holder = None
    ball.last_shooter = None
    ball.shot_distance = 0


def _create_match(screen, font, small_font, title_font, assets_dir):
    single_player = select_mode(screen, font, title_font)

    p1_config = get_character(
        select_character(screen, font, small_font, title_font, "Player 1")
    )
    p2_label = "AI" if single_player else "Player 2"
    p2_config = get_character(
        select_character(screen, font, small_font, title_font, p2_label)
    )

    difficulty = (
        select_difficulty(screen, font, title_font)
        if single_player
        else "normal"
    )
    arena = get_arena(select_arena(screen, font, small_font, title_font))

    # 立即显示加载反馈，避免选择场景后看起来没有响应。
    screen.fill((30, 30, 40))
    loading = title_font.render("Loading Match...", True, (255, 255, 255))
    screen.blit(
        loading,
        (SCREEN_WIDTH // 2 - loading.get_width() // 2,
         SCREEN_HEIGHT // 2 - loading.get_height() // 2),
    )
    pygame.display.flip()
    pygame.event.pump()

    player1 = Player(
        arena["player1_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        p1_config["color"],
        PLAYER1_CONTROLS,
        facing_right=False,
        name=f"P1 - {p1_config['name']}",
        sprite_folder=os.path.join(
            assets_dir, "characters", p1_config["sprite_folder"]
        ),
        character_config=p1_config,
        arena=arena,
    )

    p2_name = (
        f"AI {p2_config['name']} ({AI_DIFFICULTY_LABELS[difficulty]})"
        if single_player
        else f"P2 - {p2_config['name']}"
    )
    player2 = Player(
        arena["player2_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        p2_config["color"],
        PLAYER2_CONTROLS,
        facing_right=False,
        name=p2_name,
        sprite_folder=os.path.join(
            assets_dir, "characters", p2_config["sprite_folder"]
        ),
        ai_controlled=single_player,
        character_config=p2_config,
        arena=arena,
    )
    if single_player:
        player2.apply_ai_difficulty(difficulty)

    ball = Ball(
        arena["ball_spawn_x"],
        arena["ground_y"] - 200,
        sprite_path=os.path.join(assets_dir, "ball.png"),
        arena=arena,
    )
    return single_player, arena, player1, player2, ball


def play_session(screen, font, small_font, title_font, assets_dir):
    single_player, arena, player1, player2, ball = _create_match(
        screen, font, small_font, title_font, assets_dir
    )

    players = [player1, player2]
    feedback = FeedbackManager()
    world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
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
                if event.key == pygame.K_ESCAPE and not game_over:
                    result = pause_menu(screen, font, title_font)
                    if result == "quit":
                        pygame.quit()
                        sys.exit()
                    if result == "menu":
                        return
                    if result == "restart":
                        player1.score = 0
                        player2.score = 0
                        reset_round(player1, player2, ball, arena)
                        game_over = False
                        winner = None
                        round_reset_timer = 0
                        score_popup_timer = 0
                        score_popup_points = 0
                        feedback = FeedbackManager()

                elif event.key == pygame.K_ESCAPE and game_over:
                    return

                elif game_over and event.key in (pygame.K_RETURN, pygame.K_r):
                    return

        if not game_over and not feedback.gameplay_frozen:
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

                player1.try_dash_hit(player2, ball)
                player2.try_dash_hit(player1, ball)

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

        for player in players:
            for event_type, event_x, event_y in player.consume_events():
                feedback.trigger(event_type, event_x, event_y)
        for event_type, event_x, event_y in ball.consume_events():
            feedback.trigger(event_type, event_x, event_y)

        if score_popup_timer > 0:
            score_popup_timer -= 1
        feedback.update()

        draw_arena(world_surface, arena, assets_dir)
        for player in players:
            player.draw(world_surface, small_font)
        ball.draw(world_surface)
        draw_scoreboard(world_surface, font, player1, player2)
        draw_score_popup(
            world_surface,
            title_font,
            score_popup_points,
            score_popup_timer,
            arena,
        )

        feedback.present_world(world_surface, screen)
        feedback.draw_overlay(screen, title_font)

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
