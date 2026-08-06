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
from localization import tr
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
    ball.rebound_available = False



def resolve_rebound(player1, player2, ball):
    """同时比较两名球员的篮板位置，避免固定更新顺序偏向 P1。"""
    if ball.holder is not None or not getattr(ball, "rebound_available", False):
        return None

    p1_score = player1.rebound_candidate_score(ball, player2)
    p2_score = player2.rebound_candidate_score(ball, player1)
    candidates = []
    if p1_score is not None:
        candidates.append((p1_score, player1))
    if p2_score is not None:
        candidates.append((p2_score, player2))
    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    winner = candidates[0][1]
    return winner if winner.secure_rebound(ball) else None


def _create_match(screen, font, small_font, title_font, assets_dir, mode):
    """创建比赛；Q/左上返回按钮会回到真正的上一个选择页面。"""
    single_player = mode == "ai"
    stage = "p1"

    p1_config = None
    p2_config = None
    difficulty = "normal"
    arena = None

    while True:
        if stage == "p1":
            p1_id = select_character(
                screen,
                font,
                small_font,
                title_font,
                tr("common.player1"),
            )
            if p1_id == "back":
                return None
            p1_config = get_character(p1_id)
            stage = "p2"
            continue

        if stage == "p2":
            p2_label = tr("common.ai") if single_player else tr("common.player2")
            p2_id = select_character(
                screen,
                font,
                small_font,
                title_font,
                p2_label,
            )
            if p2_id == "back":
                stage = "p1"
                continue
            p2_config = get_character(p2_id)
            stage = "difficulty" if single_player else "arena"
            continue

        if stage == "difficulty":
            difficulty_result = select_difficulty(screen, font, title_font)
            if difficulty_result == "back":
                stage = "p2"
                continue
            difficulty = difficulty_result
            stage = "arena"
            continue

        if stage == "arena":
            arena_id = select_arena(screen, font, small_font, title_font)
            if arena_id == "back":
                stage = "difficulty" if single_player else "p2"
                continue
            arena = get_arena(arena_id)
            break

    screen.fill((30, 30, 40))
    loading = title_font.render(tr("select.loading"), True, (255, 255, 255))
    screen.blit(
        loading,
        (
            SCREEN_WIDTH // 2 - loading.get_width() // 2,
            SCREEN_HEIGHT // 2 - loading.get_height() // 2,
        ),
    )
    pygame.display.flip()
    pygame.event.pump()

    player1 = Player(
        arena["player1_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        p1_config["color"],
        PLAYER1_CONTROLS,
        facing_right=False,
        name=f"{tr('common.player1')} - {tr('characters.' + p1_config['id'] + '.name')}",
        sprite_folder=os.path.join(
            assets_dir,
            "characters",
            p1_config["sprite_folder"],
        ),
        character_config=p1_config,
        arena=arena,
    )

    p2_name = (
        f"{tr('common.ai')} {tr('characters.' + p2_config['id'] + '.name')} "
        f"({tr('difficulty.' + difficulty)})"
        if single_player
        else f"{tr('common.player2')} - "
        f"{tr('characters.' + p2_config['id'] + '.name')}"
    )

    player2 = Player(
        arena["player2_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        p2_config["color"],
        PLAYER2_CONTROLS,
        facing_right=False,
        name=p2_name,
        sprite_folder=os.path.join(
            assets_dir,
            "characters",
            p2_config["sprite_folder"],
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


def _create_training(screen, font, small_font, title_font, assets_dir):
    """训练营选择流程：角色 -> 地图；Q 返回上一步。"""
    stage = "character"
    player_config = None

    while True:
        if stage == "character":
            player_id = select_character(
                screen,
                font,
                small_font,
                title_font,
                tr("training.player_label"),
            )
            if player_id == "back":
                return None
            player_config = get_character(player_id)
            stage = "arena"
            continue

        arena_id = select_arena(screen, font, small_font, title_font)
        if arena_id == "back":
            stage = "character"
            continue

        arena = get_arena(arena_id)
        break

    player = Player(
        arena["player1_spawn_x"],
        arena["ground_y"] - PLAYER_HEIGHT,
        player_config["color"],
        PLAYER1_CONTROLS,
        facing_right=False,
        name=tr("characters." + player_config["id"] + ".name"),
        sprite_folder=os.path.join(
            assets_dir,
            "characters",
            player_config["sprite_folder"],
        ),
        character_config=player_config,
        arena=arena,
    )

    ball = Ball(
        arena["ball_spawn_x"],
        arena["ground_y"] - 200,
        sprite_path=os.path.join(assets_dir, "ball.png"),
        arena=arena,
    )
    ball.attach_to(player)
    return arena, player, ball


def _reset_training_ball(player, ball, arena, attach=False):
    """重置训练营篮球。TAB 回手，R 回到场上。"""
    ball.vx = 0
    ball.vy = 0
    ball.last_shooter = None
    ball.shot_distance = 0
    ball.rebound_available = False
    ball.previous_x = ball.x
    ball.previous_y = ball.y

    if attach:
        ball.attach_to(player)
        return

    ball.state = "loose"
    ball.holder = None
    ball.x = arena["ball_spawn_x"]
    ball.y = arena["ground_y"] - 150
    ball.previous_x = ball.x
    ball.previous_y = ball.y


def play_training(
    screen,
    font,
    small_font,
    title_font,
    assets_dir,
    show_fps=False,
):
    """训练营：单人自由练习，无 AI、无比赛结束。"""
    training_setup = _create_training(
        screen,
        font,
        small_font,
        title_font,
        assets_dir,
    )
    if training_setup is None:
        return "back"

    arena, player, ball = training_setup

    feedback = FeedbackManager()
    world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    made = 0
    points = 0
    dunks = 0
    previous_dunks = getattr(player, "dunks", 0)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_TAB:
                    _reset_training_ball(player, ball, arena, attach=True)
                elif event.key == pygame.K_r:
                    _reset_training_ball(player, ball, arena, attach=False)

        if not feedback.gameplay_frozen:
            keys = pygame.key.get_pressed()
            player.handle_input(keys, ball, None)
            player.update_physics()

            player.try_dunk(ball)
            ball.update()

            scorer, scored_points = ball.check_score()
            if scorer is player:
                made += 1
                points += scored_points

            current_dunks = getattr(player, "dunks", 0)
            if current_dunks > previous_dunks:
                dunks += current_dunks - previous_dunks
                previous_dunks = current_dunks

            # 防止球长时间卡在场外或静止在左侧死角。
            if (
                ball.y > SCREEN_HEIGHT + 80
                or ball.x < -80
                or ball.x > SCREEN_WIDTH + 80
            ):
                _reset_training_ball(player, ball, arena, attach=False)

        for event_type, event_x, event_y in player.consume_events():
            feedback.trigger(event_type, event_x, event_y)
        for event_type, event_x, event_y in ball.consume_events():
            feedback.trigger(event_type, event_x, event_y)

        feedback.update()

        draw_arena(world_surface, arena, assets_dir)
        player.draw(world_surface, small_font)
        ball.draw(world_surface)

        panel = pygame.Surface((250, 132), pygame.SRCALPHA)
        pygame.draw.rect(panel, (5, 10, 22, 205), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (255, 255, 255, 45), panel.get_rect(), 1, border_radius=14)

        title_surface = font.render(tr("training.title"), True, (255, 215, 90))
        made_surface = small_font.render(
            tr("training.made", value=made), True, (235, 240, 250)
        )
        points_surface = small_font.render(
            tr("training.points", value=points), True, (235, 240, 250)
        )
        dunk_surface = small_font.render(
            tr("training.dunks", value=dunks), True, (235, 240, 250)
        )
        hint_surface = small_font.render(
            tr("training.hint"), True, (175, 190, 215)
        )

        panel.blit(title_surface, (16, 12))
        panel.blit(made_surface, (16, 48))
        panel.blit(points_surface, (16, 70))
        panel.blit(dunk_surface, (16, 92))
        world_surface.blit(panel, (SCREEN_WIDTH - 266, 18))
        world_surface.blit(
            hint_surface,
            hint_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18)),
        )

        feedback.present_world(world_surface, screen)
        feedback.draw_overlay(screen, title_font)

        if show_fps:
            fps_surface = small_font.render(
                f"FPS: {clock.get_fps():.0f}", True, (255, 255, 255)
            )
            screen.blit(fps_surface, (12, 10))

        pygame.display.flip()
        clock.tick(FPS)


def play_session(screen, font, small_font, title_font, assets_dir, show_fps=False):
    while True:
        mode = select_mode(screen, font, title_font)
        if mode == "back":
            return

        if mode == "training":
            training_result = play_training(
                screen,
                font,
                small_font,
                title_font,
                assets_dir,
                show_fps=show_fps,
            )
            if training_result == "back":
                continue
            return

        match_setup = _create_match(
            screen,
            font,
            small_font,
            title_font,
            assets_dir,
            mode,
        )
        if match_setup is None:
            continue

        single_player, arena, player1, player2, ball = match_setup
        break

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

                # 玩家或 AI 持球冲到篮下并处于上升阶段时自动扣篮。
                dunked = player1.try_dunk(ball)
                if not dunked:
                    player2.try_dunk(ball)

                ball.update()

                # 盖帽必须在篮球移动后、得分判定前处理。
                # 任意一名空中防守者成功碰球后，本帧不再继续判定另一人。
                blocked = player1.try_block_ball(ball)
                if not blocked:
                    player2.try_block_ball(ball)

                scorer, points = ball.check_score()
                if scorer is None:
                    resolve_rebound(player1, player2, ball)
                else:
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

        if show_fps:
            fps_surface = small_font.render(f"FPS: {clock.get_fps():.0f}", True, (255, 255, 255))
            screen.blit(fps_surface, (SCREEN_WIDTH - fps_surface.get_width() - 12, 10))

        pygame.display.flip()
        clock.tick(FPS)