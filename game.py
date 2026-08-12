"""一场比赛的创建、更新、绘制和状态切换。"""

import os
import sys
import math
import random

import pygame

from audio import get_audio

from constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    PLAYER_WIDTH,
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
from localization import tr, get_language
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
    "pass": pygame.K_f,
}

PLAYER2_CONTROLS = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "action": pygame.K_RETURN,
    "steal": pygame.K_DOWN,
    "ability": pygame.K_RCTRL,
    "pass": pygame.K_RSHIFT,
}


# ---------- 半场进攻计时器 ----------
SHOT_CLOCK_FULL_FRAMES = 14 * FPS
SHOT_CLOCK_OFFENSIVE_REBOUND_FRAMES = 10 * FPS
SHOT_CLOCK_WARNING_FRAMES = 5 * FPS
SHOT_CLOCK_VIOLATION_NOTICE_FRAMES = 60


def reset_round(player1, player2, ball, arena):
    player1.reset_for_round(arena["player1_spawn_x"])
    player2.reset_for_round(arena["player2_spawn_x"])

    # 新回合重新拥有正常进攻资格。
    player1.must_clear_three = False
    player2.must_clear_three = False

    # 清除三分线 clear 提示。
    player1.clear_feedback_state = None
    player2.clear_feedback_state = None
    player1.clear_feedback_timer = 0
    player2.clear_feedback_timer = 0

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
    ball.clear_pass()



def _create_duke_clone(owner, assets_dir):
    """Create Duke's temporary teammate. The clone is a real Player so it can receive, hold and shoot the ball."""
    config = dict(owner.character_config)
    offset = -105 if owner.facing_right else 105
    clone_x = max(0, min(SCREEN_WIDTH - PLAYER_WIDTH, owner.x + offset))
    clone_config = dict(config)
    clone_config["frame_counts"] = config.get("clone_frame_counts", config.get("frame_counts"))
    clone = Player(
        clone_x,
        owner.arena["ground_y"] - PLAYER_HEIGHT,
        config.get("color", owner.color),
        owner.controls,
        facing_right=owner.facing_right,
        name=f"{owner.character_name} BLOOD ECHO",
        sprite_folder=os.path.join(
            assets_dir,
            "characters",
            config.get("clone_sprite_folder", config.get("sprite_folder", "duke")),
        ),
        frame_counts=clone_config.get("frame_counts"),
        character_config=clone_config,
        arena=owner.arena,
    )
    clone.is_clone = True
    clone.clone_owner = owner
    clone.clone_lifetime = int(config.get("clone_duration", 420))
    clone.ability_type = "none"
    clone.ability_cooldown_max = 0
    clone.ability_cooldown_timer = 0
    clone.pass_target = owner
    owner.pass_target = clone

    # DUKE 与 Blood Echo 属于同一支球队，
    # 防守篮板后的 clear 状态必须共享。
    clone.must_clear_three = getattr(
        owner,
        "must_clear_three",
        False,
    )

    if owner.ai_controlled:
        difficulty = str(getattr(owner, "ai_difficulty", "normal")).lower()
        clone.ai_controlled = True
        clone.ai_difficulty = difficulty
        clone.apply_ai_difficulty(difficulty)

        # Give the summon animation a moment before the first tactical pass.
        owner.ai_duke_pass_cooldown = 18 if difficulty == "hard" else 28
        owner.ai_duke_pass_decision_timer = 10

    return clone


def _support_clone(clone, active, opponent):
    """Very small off-ball brain: create a passing lane without independently shooting or stealing."""
    if clone is None or active is clone:
        return
    spacing = float(clone.character_config.get("clone_support_distance", 165))
    rim_x = clone.arena["rim_x"]
    # Prefer the opposite side of the ball handler relative to the hoop.
    side = -1 if active.x < rim_x else 1
    desired_x = active.x + side * spacing
    desired_x = max(28, min(SCREEN_WIDTH - PLAYER_WIDTH - 28, desired_x))
    delta = desired_x - clone.x
    direction = 0 if abs(delta) < 18 else (1 if delta > 0 else -1)
    clone._apply_horizontal_move(direction)

    # Blood Echo 移动时必须朝移动方向看，
    # 否则会出现身体朝持球人、却反方向倒着跑的视觉 Bug。
    if direction > 0:
        clone.facing_right = True
    elif direction < 0:
        clone.facing_right = False
    else:
        # 只有站着不动时才面向持球人。
        clone.facing_right = active.center()[0] >= clone.center()[0]



def _distance_to_pass_lane(point, start, end):
    """Return the shortest distance from point to the pass segment."""
    px, py = point
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0001:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    closest_x = ax + dx * t
    closest_y = ay + dy * t
    return math.hypot(px - closest_x, py - closest_y)


def _ai_duke_try_tactical_pass(owner, active, teammate, opponent, ball):
    """Harder DUKE AI: use Blood Echo as a real passing partner.

    The decision is intentionally throttled so DUKE does not ping-pong the
    ball every frame. Hard AI reads pressure, teammate openness, progress
    toward the rim, and interception-lane safety before passing.
    """
    if teammate is None or active is None:
        return False
    if ball.state != "held" or ball.holder is not active:
        return False
    if active not in (owner, owner.pass_target) and not getattr(active, "is_clone", False):
        return False

    difficulty = str(getattr(owner, "ai_difficulty", "normal")).lower()

    # 困难 AI 最后 3 秒进入紧急进攻。
    # 此时不再让 DUKE / Blood Echo 来回传球浪费进攻时间。
    shot_clock_frames = getattr(
        active,
        "ai_shot_clock_frames",
        None,
    )

    if (
        difficulty == "hard"
        and shot_clock_frames is not None
        and shot_clock_frames <= 3 * FPS
    ):
        return False

    # Persistent team-level timers live on the real DUKE body.
    cooldown = int(getattr(owner, "ai_duke_pass_cooldown", 0))
    decision_timer = int(getattr(owner, "ai_duke_pass_decision_timer", 0))

    if cooldown > 0:
        owner.ai_duke_pass_cooldown = cooldown - 1
        return False

    if decision_timer > 0:
        owner.ai_duke_pass_decision_timer = decision_timer - 1
        return False

    # Re-evaluate only every few tenths of a second.
    if difficulty == "hard":
        owner.ai_duke_pass_decision_timer = random.randint(14, 24)
    elif difficulty == "normal":
        owner.ai_duke_pass_decision_timer = random.randint(25, 38)
    else:
        owner.ai_duke_pass_decision_timer = random.randint(38, 55)

    active_pos = active.center()
    teammate_pos = teammate.center()
    opponent_pos = opponent.center()

    pass_distance = math.hypot(
        teammate_pos[0] - active_pos[0],
        teammate_pos[1] - active_pos[1],
    )

    # Very short passes look silly; very long ones are easy interceptions.
    if pass_distance < 72 or pass_distance > 330:
        return False

    holder_pressure = math.hypot(
        opponent_pos[0] - active_pos[0],
        opponent_pos[1] - active_pos[1],
    )
    teammate_pressure = math.hypot(
        opponent_pos[0] - teammate_pos[0],
        opponent_pos[1] - teammate_pos[1],
    )
    lane_clearance = _distance_to_pass_lane(
        opponent_pos,
        active_pos,
        teammate_pos,
    )

    rim_x = active.arena["rim_x"]

    # This game attacks the left-side rim: smaller x is generally more advanced.
    teammate_progress = active_pos[0] - teammate_pos[0]

    pressured = holder_pressure <= 82
    heavily_pressured = holder_pressure <= 58
    teammate_more_open = teammate_pressure >= holder_pressure + 34
    teammate_wide_open = teammate_pressure >= 135
    teammate_ahead = teammate_progress >= 38
    trapped_near_rim = active_pos[0] <= rim_x + 78
    safe_lane = lane_clearance >= 62
    very_safe_lane = lane_clearance >= 92

    # Hard AI avoids throwing directly through the defender.
    if difficulty == "hard" and not safe_lane and not heavily_pressured:
        return False

    score = 0.0
    if pressured:
        score += 2.3
    if heavily_pressured:
        score += 1.1
    if teammate_more_open:
        score += 2.0
    if teammate_wide_open:
        score += 0.8
    if teammate_ahead:
        score += 1.2
    if trapped_near_rim:
        score += 1.0
    if safe_lane:
        score += 0.7
    if very_safe_lane:
        score += 0.5

    if difficulty == "hard":
        # Hard DUKE actively uses give-and-go passes and punishes double teams.
        if score >= 4.0:
            chance = 0.92
        elif score >= 3.0:
            chance = 0.72
        elif score >= 2.2 and very_safe_lane:
            chance = 0.42
        else:
            chance = 0.08 if very_safe_lane and teammate_ahead else 0.0

        cooldown_after_pass = random.randint(42, 62)

    elif difficulty == "normal":
        if score >= 4.0:
            chance = 0.58
        elif score >= 3.2:
            chance = 0.32
        else:
            chance = 0.0

        cooldown_after_pass = random.randint(72, 100)

    else:
        # Easy DUKE only passes out of obvious pressure.
        chance = 0.20 if heavily_pressured and teammate_more_open and safe_lane else 0.0
        cooldown_after_pass = random.randint(105, 145)

    if random.random() >= chance:
        return False

    if not ball.pass_to(teammate, active):
        return False

    owner.ai_duke_pass_cooldown = cooldown_after_pass
    owner.ai_duke_pass_decision_timer = max(
        owner.ai_duke_pass_decision_timer,
        10,
    )

    # Receiver is the next offensive body. Once the pass is caught, the regular
    # AI state machine immediately chooses its own shot / drive / dunk plan.
    return True



def _tick_duke_clone(owner, clone, ball):
    """Return None when a clone expires. If it still has the ball, send a final pass home first."""
    if clone is None:
        owner.pass_target = None
        return None
    clone.clone_lifetime -= 1
    if clone.clone_lifetime > 0:
        return clone

    if ball.state == "held" and ball.holder is clone:
        if ball.pass_to(owner, clone):
            clone.clone_lifetime = 45
            return clone
    if ball.state == "passing" and ball.pass_receiver is clone:
        clone.clone_lifetime = 30
        return clone

    owner.pass_target = None
    if ball.pass_passer is clone or ball.pass_receiver is clone:
        ball.clear_pass()
    return None


def _team_score_owner(player):
    return getattr(player, "clone_owner", None) or player


def _set_team_clear_required(owner, clone=None, required=True):
    """设置整支球队是否需要先退出三分线，并管理屏幕提示。"""
    was_required = getattr(owner, "must_clear_three", False)

    owner.must_clear_three = bool(required)

    if clone is not None:
        clone.must_clear_three = bool(required)

    if required:
        # 防守篮板后持续显示，直到真正退出三分线。
        owner.clear_feedback_state = "required"
        owner.clear_feedback_timer = -1

        if clone is not None:
            clone.clear_feedback_state = "required"
            clone.clear_feedback_timer = -1

    elif was_required:
        # 成功退出三分线后短暂显示 CLEARED。
        owner.clear_feedback_state = "cleared"
        owner.clear_feedback_timer = 45

        if clone is not None:
            clone.clear_feedback_state = "cleared"
            clone.clear_feedback_timer = 45


def _draw_clear_notice(surface, title_font, small_font, player1, player2):
    """绘制防守篮板后三分线清球提示。"""
    required_owner = None

    for owner in (player1, player2):
        if getattr(owner, "must_clear_three", False):
            required_owner = owner
            break

    if required_owner is not None:
        main_text = tr("gameplay.clear_ball")
        sub_text = tr("gameplay.clear_ball_hint")
        main_color = (255, 190, 65)
    else:
        cleared_owner = None

        for owner in (player1, player2):
            if (
                getattr(owner, "clear_feedback_state", None) == "cleared"
                and getattr(owner, "clear_feedback_timer", 0) > 0
            ):
                cleared_owner = owner
                break

        if cleared_owner is None:
            return

        main_text = tr("gameplay.cleared")
        sub_text = tr("gameplay.cleared_hint")
        main_color = (100, 255, 145)

    main_surface = title_font.render(
        main_text,
        True,
        main_color,
    )

    sub_surface = small_font.render(
        sub_text,
        True,
        (235, 240, 250),
    )

    panel_width = max(
        360,
        main_surface.get_width() + 60,
        sub_surface.get_width() + 60,
    )
    panel_height = 92

    panel = pygame.Surface(
        (panel_width, panel_height),
        pygame.SRCALPHA,
    )

    pygame.draw.rect(
        panel,
        (5, 10, 22, 215),
        panel.get_rect(),
        border_radius=16,
    )

    pygame.draw.rect(
        panel,
        (*main_color, 210),
        panel.get_rect(),
        width=2,
        border_radius=16,
    )

    panel.blit(
        main_surface,
        main_surface.get_rect(
            center=(panel_width // 2, 32)
        ),
    )

    panel.blit(
        sub_surface,
        sub_surface.get_rect(
            center=(panel_width // 2, 68)
        ),
    )

    surface.blit(
        panel,
        (
            SCREEN_WIDTH // 2 - panel_width // 2,
            58,
        ),
    )


def _update_team_clear_status(owner, clone, ball):
    """持球队员真正越过三分线后，解除球队 clear 限制。"""
    if not getattr(owner, "must_clear_three", False):
        return

    if ball.state != "held" or ball.holder is None:
        return

    team_bodies = (owner, clone) if clone is not None else (owner,)
    if ball.holder not in team_bodies:
        return

    holder = ball.holder
    holder_x, _ = holder.center()

    rim_x = owner.arena["rim_x"]
    three_distance = owner.arena["three_point_distance"]

    # 当前比赛只使用左侧篮筐，因此三分线外在篮筐右侧。
    clear_line_x = rim_x + three_distance

    if holder_x >= clear_line_x:
        _set_team_clear_required(
            owner,
            clone,
            False,
        )


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
        player2.ai_difficulty = difficulty
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
    ball.clear_pass()
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
    duke_clone = None
    active_player = player

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

            # Duke: whoever currently possesses the ball becomes the controlled body.
            if duke_clone is not None and ball.state == "held" and ball.holder in (player, duke_clone):
                active_player = ball.holder
            if active_player is duke_clone and duke_clone is None:
                active_player = player

            active_player.handle_input(keys, ball, None)
            if duke_clone is not None:
                support = player if active_player is duke_clone else duke_clone
                _support_clone(support, active_player, None)

            player.update_physics()
            if duke_clone is not None:
                duke_clone.update_physics()

            if player.consume_clone_request() and duke_clone is None:
                duke_clone = _create_duke_clone(player, assets_dir)
            old_clone = duke_clone
            duke_clone = _tick_duke_clone(player, duke_clone, ball)
            if old_clone is not None and duke_clone is None and active_player is old_clone:
                active_player = player

            dunked = active_player.try_dunk(ball)
            ball.update()

            scorer, scored_points = ball.check_score()
            if scorer is not None and _team_score_owner(scorer) is player:
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
        if duke_clone is not None:
            for event_type, event_x, event_y in duke_clone.consume_events():
                feedback.trigger(event_type, event_x, event_y)
        for event_type, event_x, event_y in ball.consume_events():
            feedback.trigger(event_type, event_x, event_y)

        feedback.update()

        draw_arena(world_surface, arena, assets_dir)
        player.draw(world_surface, small_font)
        if duke_clone is not None:
            duke_clone.draw(world_surface, small_font)
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



def _draw_shot_clock(
    surface,
    font,
    small_font,
    frames_left,
    active,
    violation_timer,
):
    """绘制 14 秒进攻计时器。"""
    if active:
        seconds_left = max(
            0,
            math.ceil(frames_left / FPS),
        )
    else:
        seconds_left = 14

    warning = (
        active
        and frames_left <= SHOT_CLOCK_WARNING_FRAMES
    )

    if warning:
        accent = (255, 80, 72)
        number_color = (255, 95, 80)
    else:
        accent = (255, 184, 70)
        number_color = (255, 225, 145)

    panel = pygame.Surface(
        (142, 66),
        pygame.SRCALPHA,
    )

    pygame.draw.rect(
        panel,
        (5, 10, 22, 220),
        panel.get_rect(),
        border_radius=13,
    )

    pygame.draw.rect(
        panel,
        (*accent, 220),
        panel.get_rect(),
        width=2,
        border_radius=13,
    )

    label = small_font.render(
        tr("gameplay.shot_clock"),
        True,
        (220, 228, 242),
    )

    number = font.render(
        str(seconds_left),
        True,
        number_color,
    )

    panel.blit(
        label,
        label.get_rect(
            center=(71, 17),
        ),
    )

    panel.blit(
        number,
        number.get_rect(
            center=(71, 45),
        ),
    )

    surface.blit(
        panel,
        (
            SCREEN_WIDTH - 158,
            14,
        ),
    )

    if violation_timer > 0:
        notice = font.render(
            tr("gameplay.shot_clock_violation"),
            True,
            (255, 88, 72),
        )

        bg = pygame.Surface(
            (
                notice.get_width() + 40,
                notice.get_height() + 22,
            ),
            pygame.SRCALPHA,
        )

        pygame.draw.rect(
            bg,
            (5, 10, 22, 225),
            bg.get_rect(),
            border_radius=12,
        )

        pygame.draw.rect(
            bg,
            (255, 75, 65, 220),
            bg.get_rect(),
            width=2,
            border_radius=12,
        )

        bg.blit(
            notice,
            notice.get_rect(
                center=bg.get_rect().center,
            ),
        )

        surface.blit(
            bg,
            bg.get_rect(
                center=(
                    SCREEN_WIDTH // 2,
                    155,
                )
            ),
        )


def _shot_clock_turnover(
    violator,
    receiver,
    ball,
    arena,
    receiver_clone=None,
):
    """进攻时间到：球权直接交给对方，并从三分线外重新进攻。"""

    # 两队都清除旧的 CLEAR 状态。
    violator.must_clear_three = False
    receiver.must_clear_three = False

    violator.clear_feedback_state = None
    receiver.clear_feedback_state = None

    violator.clear_feedback_timer = 0
    receiver.clear_feedback_timer = 0

    if receiver_clone is not None:
        receiver_clone.must_clear_three = False
        receiver_clone.clear_feedback_state = None
        receiver_clone.clear_feedback_timer = 0

    # 把新持球队员放到三分线外侧。
    clear_x = (
        arena["rim_x"]
        + arena["three_point_distance"]
        + 36
    )

    receiver.x = max(
        0,
        min(
            SCREEN_WIDTH - PLAYER_WIDTH,
            clear_x - PLAYER_WIDTH / 2,
        ),
    )

    receiver.y = (
        arena["ground_y"]
        - PLAYER_HEIGHT
    )

    receiver.vx = 0
    receiver.vy = 0
    receiver.on_ground = True
    receiver.facing_right = False

    # 清除上一回合投篮数据。
    ball.last_shooter = None
    ball.shot_distance = 0
    ball.rebound_available = False

    if hasattr(ball, "rebound_grace_timer"):
        ball.rebound_grace_timer = 0

    ball.attach_to(receiver)

    # AI 立即进入新的进攻回合。
    receiver.ai_state = "offense_setup"
    receiver.ai_state_timer = 0
    receiver.ai_offense_timer = 0
    receiver.ai_shot_target = None
    receiver.ai_attack_choice = None
    receiver.ai_shot_cooldown = 0
    receiver.ai_rebound_exit_timer = 0



def _draw_controls_hud(surface, small_font, single_player):
    # 左右分组式操作 HUD。
    is_zh = get_language() == "zh"

    if is_zh:
        p1_left = [
            ("A/D", "移动"),
            ("W", "跳跃"),
        ]
        p1_right = [
            ("SPACE", "投篮"),
            ("S", "抢断"),
            ("SHIFT", "技能"),
            ("F", "传球"),
        ]

        p2_left = [
            ("←/→", "移动"),
            ("↑", "跳跃"),
        ]
        p2_right = [
            ("ENTER", "投篮"),
            ("↓", "抢断"),
            ("RCTRL", "技能"),
            ("RSHIFT", "传球"),
        ]

        hide_hint = "H  隐藏"
    else:
        p1_left = [
            ("A/D", "Move"),
            ("W", "Jump"),
        ]
        p1_right = [
            ("SPACE", "Shoot"),
            ("S", "Steal"),
            ("SHIFT", "Ability"),
            ("F", "Pass"),
        ]

        p2_left = [
            ("←/→", "Move"),
            ("↑", "Jump"),
        ]
        p2_right = [
            ("ENTER", "Shoot"),
            ("↓", "Steal"),
            ("RCTRL", "Ability"),
            ("RSHIFT", "Pass"),
        ]

        hide_hint = "H  Hide"

    rows = [
        ("P1", p1_left, p1_right)
    ]

    if not single_player:
        rows.append(
            ("P2", p2_left, p2_right)
        )

    width = 930
    row_height = 38
    height = 14 + row_height * len(rows)

    panel = pygame.Surface(
        (width, height),
        pygame.SRCALPHA,
    )

    pygame.draw.rect(
        panel,
        (5, 10, 20, 160),
        panel.get_rect(),
        border_radius=12,
    )

    pygame.draw.rect(
        panel,
        (255, 255, 255, 30),
        panel.get_rect(),
        width=1,
        border_radius=12,
    )

    def draw_item(x, y, key_name, action_name):
        key_surface = small_font.render(
            key_name,
            True,
            (248, 250, 255),
        )

        key_rect = pygame.Rect(
            x,
            y,
            key_surface.get_width() + 16,
            25,
        )

        pygame.draw.rect(
            panel,
            (255, 255, 255, 25),
            key_rect,
            border_radius=6,
        )

        pygame.draw.rect(
            panel,
            (255, 255, 255, 52),
            key_rect,
            width=1,
            border_radius=6,
        )

        panel.blit(
            key_surface,
            key_surface.get_rect(
                center=key_rect.center
            ),
        )

        action_surface = small_font.render(
            action_name,
            True,
            (208, 219, 235),
        )

        action_x = key_rect.right + 7

        panel.blit(
            action_surface,
            (
                action_x,
                y + 4,
            ),
        )

        return (
            action_x
            + action_surface.get_width()
            + 20
        )

    y = 7

    for title, left_items, right_items in rows:
        # P1 / P2 标签
        title_box = pygame.Rect(
            12,
            y,
            38,
            26,
        )

        pygame.draw.rect(
            panel,
            (255, 145, 55, 48),
            title_box,
            border_radius=7,
        )

        title_surface = small_font.render(
            title,
            True,
            (255, 195, 95),
        )

        panel.blit(
            title_surface,
            title_surface.get_rect(
                center=title_box.center
            ),
        )

        # 左组：移动 / 跳跃
        x = 62

        for key_name, action_name in left_items:
            x = draw_item(
                x,
                y,
                key_name,
                action_name,
            )

        # 中间分隔线
        divider_x = 330

        pygame.draw.line(
            panel,
            (255, 255, 255, 38),
            (divider_x, y + 3),
            (divider_x, y + 23),
            1,
        )

        # 右组：投篮 / 抢断 / 技能 / 传球
        x = divider_x + 20

        for key_name, action_name in right_items:
            x = draw_item(
                x,
                y,
                key_name,
                action_name,
            )

        y += row_height

    hint_surface = small_font.render(
        hide_hint,
        True,
        (125, 142, 168),
    )

    panel.blit(
        hint_surface,
        (
            width - hint_surface.get_width() - 12,
            height - hint_surface.get_height() - 6,
        ),
    )

    surface.blit(
        panel,
        (
            SCREEN_WIDTH // 2 - width // 2,
            SCREEN_HEIGHT - height - 8,
        ),
    )


def _draw_match_stats_overlay(
    surface,
    font,
    small_font,
    title_font,
    player1,
    player2,
    winner,
):
    """V3.5 比赛结束统计面板。"""

    overlay = pygame.Surface(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.SRCALPHA,
    )
    overlay.fill((2, 6, 15, 205))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(135, 70, 690, 405)

    pygame.draw.rect(
        surface,
        (8, 15, 30),
        panel,
        border_radius=22,
    )

    pygame.draw.rect(
        surface,
        (255, 142, 55),
        panel,
        width=2,
        border_radius=22,
    )

    win_text = (
        "比赛结束"
        if get_language() == "zh"
        else "FINAL"
    )

    title = title_font.render(
        win_text,
        True,
        (255, 205, 90),
    )

    surface.blit(
        title,
        title.get_rect(
            center=(SCREEN_WIDTH // 2, 105)
        ),
    )

    winner_text = (
        "获胜"
        if get_language() == "zh"
        else "WINNER"
    )

    winner_name = winner.character_name

    winner_surface = font.render(
        f"{winner_text}  •  {winner_name}",
        True,
        (110, 255, 160),
    )

    surface.blit(
        winner_surface,
        winner_surface.get_rect(
            center=(SCREEN_WIDTH // 2, 145)
        ),
    )

    left_name = small_font.render(
        player1.character_name,
        True,
        (255, 170, 80),
    )

    right_name = small_font.render(
        player2.character_name,
        True,
        (100, 190, 255),
    )

    surface.blit(
        left_name,
        left_name.get_rect(center=(280, 187)),
    )

    surface.blit(
        right_name,
        right_name.get_rect(center=(680, 187)),
    )

    labels = (
        [
            "得分",
            "投篮",
            "三分",
            "篮板",
            "抢断",
            "盖帽",
            "扣篮",
        ]
        if get_language() == "zh"
        else [
            "SCORE",
            "FG",
            "3PT",
            "REB",
            "STL",
            "BLK",
            "DUNK",
        ]
    )

    p1_values = [
        str(player1.score),
        f"{getattr(player1, 'fg_made', 0)}/{getattr(player1, 'fg_attempts', 0)}",
        f"{getattr(player1, 'three_made', 0)}/{getattr(player1, 'three_attempts', 0)}",
        str(getattr(player1, "rebounds", 0)),
        str(getattr(player1, "steals", 0)),
        str(getattr(player1, "blocks", 0)),
        str(getattr(player1, "dunks", 0)),
    ]

    p2_values = [
        str(player2.score),
        f"{getattr(player2, 'fg_made', 0)}/{getattr(player2, 'fg_attempts', 0)}",
        f"{getattr(player2, 'three_made', 0)}/{getattr(player2, 'three_attempts', 0)}",
        str(getattr(player2, "rebounds", 0)),
        str(getattr(player2, "steals", 0)),
        str(getattr(player2, "blocks", 0)),
        str(getattr(player2, "dunks", 0)),
    ]

    y = 222

    for label, left, right in zip(
        labels,
        p1_values,
        p2_values,
    ):
        left_surface = font.render(
            left,
            True,
            (240, 245, 255),
        )

        label_surface = small_font.render(
            label,
            True,
            (145, 165, 195),
        )

        right_surface = font.render(
            right,
            True,
            (240, 245, 255),
        )

        surface.blit(
            left_surface,
            left_surface.get_rect(
                center=(280, y)
            ),
        )

        surface.blit(
            label_surface,
            label_surface.get_rect(
                center=(480, y)
            ),
        )

        surface.blit(
            right_surface,
            right_surface.get_rect(
                center=(680, y)
            ),
        )

        y += 34

    hint_text = (
        "ENTER / R  返回菜单    ESC  返回菜单"
        if get_language() == "zh"
        else "ENTER / R  RETURN TO MENU    ESC  RETURN"
    )

    hint = small_font.render(
        hint_text,
        True,
        (150, 165, 190),
    )

    surface.blit(
        hint,
        hint.get_rect(
            center=(SCREEN_WIDTH // 2, 455)
        ),
    )


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
    duke_clones = {player1: None, player2: None}
    active_bodies = {player1: player1, player2: player2}
    feedback = FeedbackManager()
    world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    game_over = False
    winner = None
    round_reset_timer = 0
    score_popup_timer = 0
    score_popup_points = 0

    # ---------- 对局按键 HUD ----------
    # 默认显示；玩家可随时按 H 开关。
    show_controls_hud = True

    # ---------- Shot Clock ----------
    # 第一次有人真正获得球权后才开始倒计时。
    shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
    shot_clock_team = None
    shot_clock_active = False
    shot_clock_violation_timer = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h and not game_over:
                    show_controls_hud = not show_controls_hud

                elif event.key == pygame.K_ESCAPE and not game_over:
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
                        duke_clones = {player1: None, player2: None}
                        active_bodies = {player1: player1, player2: player2}
                        players = [player1, player2]
                        game_over = False
                        winner = None
                        round_reset_timer = 0
                        score_popup_timer = 0
                        score_popup_points = 0

                        shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                        shot_clock_team = None
                        shot_clock_active = False
                        shot_clock_violation_timer = 0

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
                    duke_clones = {player1: None, player2: None}
                    active_bodies = {player1: player1, player2: player2}
                    players = [player1, player2]

                    shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                    shot_clock_team = None
                    shot_clock_active = False

            else:
                keys = pygame.key.get_pressed()

                # Update each team. Duke can switch control between body and clone by passing.
                for owner, opponent in ((player1, player2), (player2, player1)):
                    clone = duke_clones[owner]
                    team_bodies = (owner, clone) if clone is not None else (owner,)
                    if ball.state == "held" and ball.holder in team_bodies:
                        active_bodies[owner] = ball.holder
                    active = active_bodies[owner]
                    if active is None or (active is not owner and active is not clone):
                        active = owner
                        active_bodies[owner] = owner

                    if owner.ai_controlled:
                        # 把当前进攻时间传给正在控制的 AI 身体。
                        # DUKE 与 Blood Echo 谁持球，谁就读取同一个球队计时器。
                        active.ai_shot_clock_frames = (
                            shot_clock_frames
                            if (
                                shot_clock_active
                                and shot_clock_team is owner
                            )
                            else None
                        )

                        # DUKE AI controls whichever body currently owns the ball.
                        # This lets Blood Echo become a real secondary ball handler
                        # instead of freezing whenever it receives a pass.
                        if (
                            clone is not None
                            and ball.state == "held"
                            and ball.holder in (owner, clone)
                        ):
                            active = ball.holder
                            active_bodies[owner] = active
                        elif (
                            clone is not None
                            and ball.state == "passing"
                            and ball.pass_receiver in (owner, clone)
                        ):
                            # During the pass, let the intended receiver move toward
                            # the ball so catches stay reliable.
                            active = ball.pass_receiver
                            active_bodies[owner] = active
                        else:
                            active = active_bodies[owner]
                            if active not in (owner, clone):
                                active = owner
                                active_bodies[owner] = owner

                        # 防守篮板后，AI 的第一优先级是把球带出三分线。
                        # clear 完成以前不投篮、不扣篮，也不进行 DUKE 战术传球。
                        force_clear = (
                            getattr(owner, "must_clear_three", False)
                            and ball.state == "held"
                            and ball.holder is active
                        )

                        if force_clear:
                            clear_line_x = (
                                active.arena["rim_x"]
                                + active.arena["three_point_distance"]
                            )

                            if active.center()[0] < clear_line_x:
                                # 本游戏进攻篮筐位于左侧，
                                # 所以退出三分线就是向右运球。
                                active._apply_horizontal_move(1)
                                active._update_dash()
                            else:
                                _set_team_clear_required(
                                    owner,
                                    clone,
                                    False,
                                )
                                active.handle_ai(ball, opponent)

                        else:
                            teammate = None
                            if clone is not None:
                                teammate = clone if active is owner else owner

                            passed = False
                            if teammate is not None:
                                passed = _ai_duke_try_tactical_pass(
                                    owner,
                                    active,
                                    teammate,
                                    opponent,
                                    ball,
                                )

                            if not passed:
                                active.handle_ai(ball, opponent)
                    else:
                        active.handle_input(keys, ball, opponent)

                    if clone is not None:
                        support = owner if active is clone else clone
                        _support_clone(support, active, opponent)

                    owner.update_physics()
                    if clone is not None:
                        clone.update_physics()

                    # 真人和 AI 都使用同一套三分线 clear 判定。
                    _update_team_clear_status(
                        owner,
                        clone,
                        ball,
                    )

                    if owner.consume_clone_request() and clone is None:
                        clone = _create_duke_clone(owner, assets_dir)
                        duke_clones[owner] = clone
                        players.append(clone)

                    new_clone = _tick_duke_clone(owner, clone, ball)
                    if new_clone is None and clone is not None:
                        if clone in players:
                            players.remove(clone)
                        if active_bodies[owner] is clone:
                            active_bodies[owner] = owner
                        duke_clones[owner] = None

                player1.try_dash_hit(player2, ball)
                player2.try_dash_hit(player1, ball)

                # The currently controlled Duke body can dunk just like the original.
                dunk_candidates = [active_bodies[player1], active_bodies[player2]]
                dunked = False
                for dunker in dunk_candidates:
                    if dunker is not None and dunker.try_dunk(ball):
                        dunked = True
                        break

                ball.update()

                # 盖帽必须在篮球移动后、得分判定前处理。
                # 任意一名空中防守者成功碰球后，本帧不再继续判定另一人。
                blocked = active_bodies[player1].try_block_ball(ball)
                if not blocked:
                    active_bodies[player2].try_block_ball(ball)

                scorer, points = ball.check_score()
                if scorer is None:
                    rebounder = resolve_rebound(
                        player1,
                        player2,
                        ball,
                    )

                    if rebounder is not None:
                        rebound_owner = _team_score_owner(
                            rebounder
                        )

                        previous_shooter = ball.last_shooter

                        if previous_shooter is not None:
                            shooter_owner = _team_score_owner(
                                previous_shooter
                            )

                            # 只有“对方投丢后抢到的防守篮板”
                            # 才需要退出三分线。
                            #
                            # 自己投丢后自己抢到：
                            # 属于进攻篮板，可以直接二次进攻。
                            if shooter_owner is not rebound_owner:
                                # 防守篮板：
                                # 新球权 14 秒，并且必须先 CLEAR。
                                _set_team_clear_required(
                                    rebound_owner,
                                    duke_clones.get(
                                        rebound_owner
                                    ),
                                    True,
                                )

                                shot_clock_team = rebound_owner
                                shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                                shot_clock_active = True

                            else:
                                # 进攻篮板：
                                # 同一支球队继续进攻，但重置为 10 秒。
                                shot_clock_team = rebound_owner
                                shot_clock_frames = (
                                    SHOT_CLOCK_OFFENSIVE_REBOUND_FRAMES
                                )
                                shot_clock_active = True
                else:
                    scorer = _team_score_owner(scorer)

                    # 得分后当前进攻回合结束。
                    shot_clock_active = False
                    shot_clock_team = None

                    scorer.score += points
                    score_popup_points = points
                    score_popup_timer = SCORE_POPUP_DURATION_FRAMES
                    if scorer.score >= WINNING_SCORE:
                        game_over = True
                        winner = scorer

                        # 比赛结束：停止比赛 BGM，播放一次胜利音乐。
                        get_audio().play_music(
                            "win",
                            loops=0,
                            fade_ms=250,
                        )
                    else:
                        round_reset_timer = ROUND_RESET_DELAY_FRAMES

        # ==================================================
        # Shot Clock 更新
        # ==================================================
        if (
            not game_over
            and round_reset_timer <= 0
            and not feedback.gameplay_frozen
        ):
            current_possession_team = None

            if (
                ball.state == "held"
                and ball.holder is not None
            ):
                current_possession_team = _team_score_owner(
                    ball.holder
                )

            # 第一次持球，或者抢断/截断导致球权真正改变。
            if current_possession_team is not None:
                if shot_clock_team is None:
                    shot_clock_team = current_possession_team
                    shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                    shot_clock_active = True

                elif current_possession_team is not shot_clock_team:
                    shot_clock_team = current_possession_team
                    shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                    shot_clock_active = True

            # 持球和队内传球期间继续走表。
            # 投篮已经离手进入 flying 后停止倒计时，
            # 因此压哨出手仍允许篮球完成本次飞行。
            clock_running = (
                shot_clock_active
                and shot_clock_team is not None
                and ball.state in ("held", "passing")
            )

            if clock_running:
                shot_clock_frames -= 1

                if shot_clock_frames <= 0:
                    violator = shot_clock_team

                    receiver = (
                        player2
                        if violator is player1
                        else player1
                    )

                    _shot_clock_turnover(
                        violator,
                        receiver,
                        ball,
                        arena,
                        duke_clones.get(receiver),
                    )

                    active_bodies[receiver] = receiver

                    shot_clock_team = receiver
                    shot_clock_frames = SHOT_CLOCK_FULL_FRAMES
                    shot_clock_active = True
                    shot_clock_violation_timer = (
                        SHOT_CLOCK_VIOLATION_NOTICE_FRAMES
                    )

                    # 进攻时间到，播放裁判哨声。
                    get_audio().play_sfx("whistle")

        if shot_clock_violation_timer > 0:
            shot_clock_violation_timer -= 1

        for player in players:
            for event_type, event_x, event_y in player.consume_events():
                feedback.trigger(event_type, event_x, event_y)
        for event_type, event_x, event_y in ball.consume_events():
            feedback.trigger(event_type, event_x, event_y)

        if score_popup_timer > 0:
            score_popup_timer -= 1

        # CLEARED 提示显示约 0.75 秒后自动消失。
        for clear_owner in (player1, player2):
            timer = getattr(
                clear_owner,
                "clear_feedback_timer",
                0,
            )

            if timer > 0:
                clear_owner.clear_feedback_timer -= 1

                if clear_owner.clear_feedback_timer <= 0:
                    clear_owner.clear_feedback_state = None

        feedback.update()

        draw_arena(world_surface, arena, assets_dir)
        for player in players:
            player.draw(world_surface, small_font)
        ball.draw(world_surface)
        draw_scoreboard(world_surface, font, player1, player2)

        if show_controls_hud:
            _draw_controls_hud(
                world_surface,
                small_font,
                single_player,
            )

        _draw_shot_clock(
            world_surface,
            font,
            small_font,
            shot_clock_frames,
            shot_clock_active,
            shot_clock_violation_timer,
        )
        draw_score_popup(
            world_surface,
            title_font,
            score_popup_points,
            score_popup_timer,
            arena,
        )

        # 防守篮板后三分线 clear 状态提示。
        _draw_clear_notice(
            world_surface,
            title_font,
            small_font,
            player1,
            player2,
        )

        feedback.present_world(world_surface, screen)
        feedback.draw_overlay(screen, title_font)

        if game_over:
            _draw_match_stats_overlay(
                screen,
                font,
                small_font,
                title_font,
                player1,
                player2,
                winner,
            )

        if show_fps:
            fps_surface = small_font.render(f"FPS: {clock.get_fps():.0f}", True, (255, 255, 255))
            screen.blit(fps_surface, (SCREEN_WIDTH - fps_surface.get_width() - 12, 10))

        pygame.display.flip()
        clock.tick(FPS)