"""单人模式 AI 状态机。

每一帧只执行一种明确行为，避免篮下逃离、扣篮、投篮等指令互相覆盖。
"""

import random

from constants import (
    AI_SHOOT_STOP_DISTANCE,
    AI_TWO_POINT_SHOOT_OFFSET,
    AI_THREE_POINT_SHOOT_MARGIN,
    AI_STEAL_APPROACH_DISTANCE,
    AI_REBOUND_JUMP_RANGE,
    AI_SHOT_MISS_OFFSET,
    AI_BLOCK_HORIZONTAL_RANGE,
    AI_BLOCK_VERTICAL_RANGE,
    AI_DUNK_APPROACH_DISTANCE,
    AI_DUNK_TAKEOFF_DISTANCE,
)

# 状态名。使用普通字符串，避免额外依赖。
SEEK_BALL = "seek_ball"
DEFEND = "defend"
BLOCK_SHOT = "block_shot"
OFFENSE_SETUP = "offense_setup"
DRIVE_DUNK = "drive_dunk"
ESCAPE_PAINT = "escape_paint"
SHOT_RECOVER = "shot_recover"

# AI 状态机参数。放在 ai.py 内，避免 constants.py 版本不一致造成导入错误。
UNDER_HOOP_DISTANCE = 42
SAFE_FROM_HOOP_DISTANCE = 105
DUNK_RETRY_COOLDOWN = 80
POST_SHOT_COOLDOWN = 36
MAX_DUNK_COMMIT_FRAMES = 95
MAX_OFFENSE_SETUP_FRAMES = 150
LEFT_WALL_ESCAPE_MARGIN = 18
LEFT_OF_RIM_ESCAPE_MARGIN = 8


def _ensure_ai_state(player):
    if not hasattr(player, "ai_state"):
        player.ai_state = SEEK_BALL
    if not hasattr(player, "ai_state_timer"):
        player.ai_state_timer = 0
    if not hasattr(player, "ai_shot_cooldown"):
        player.ai_shot_cooldown = 0
    if not hasattr(player, "ai_dunk_retry_cooldown"):
        player.ai_dunk_retry_cooldown = 0
    if not hasattr(player, "ai_offense_timer"):
        player.ai_offense_timer = 0
    if not hasattr(player, "ai_rebound_exit_timer"):
        player.ai_rebound_exit_timer = 0


def _set_state(player, state):
    """切换状态；状态持续时间统一在 update_ai 开头递增。"""
    if player.ai_state != state:
        player.ai_state = state
        player.ai_state_timer = 0
        player.ai_shot_target = None


def _tick_cooldowns(player):
    if player.ai_shot_cooldown > 0:
        player.ai_shot_cooldown -= 1
    if player.ai_dunk_retry_cooldown > 0:
        player.ai_dunk_retry_cooldown -= 1


def _shoot(player, ball):
    hoop_x = player.arena["rim_x"]
    hoop_y = player.arena["rim_y"]
    target_x = hoop_x
    target_y = hoop_y

    if random.random() < player.ai_shot_miss_chance:
        target_x += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)
        target_y += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)

    my_cx, my_cy = player.center()
    shot_distance = ((my_cx - hoop_x) ** 2 + (my_cy - hoop_y) ** 2) ** 0.5
    ball.shoot_towards(target_x, target_y, player, shot_distance)
    player.ai_shot_target = None
    player.ai_offense_timer = 0
    player.ai_shot_cooldown = POST_SHOT_COOLDOWN


def update_ai(player, ball, opponent):
    """每帧更新 AI；同一帧只由一个状态决定移动与动作。"""
    _ensure_ai_state(player)
    _tick_cooldowns(player)
    # 状态计时必须每帧递增。旧版本只在部分 _set_state 调用中递增，
    # 导致 DRIVE_DUNK 撞墙后永远无法超时退出。
    player.ai_state_timer += 1

    my_cx, my_cy = player.center()
    hoop_x = player.arena["rim_x"]
    distance_from_rim = my_cx - hoop_x

    direction = 0
    want_jump = False
    want_steal = False
    want_ability = False

    has_ball = ball.state == "held" and ball.holder is player
    opponent_has_ball = ball.state == "held" and ball.holder is opponent
    opponent_shot = ball.state == "flying" and ball.last_shooter is opponent

    # 最高优先级脱困：持球人一旦进入左墙/篮板背后区域，立即终止扣篮，
    # 禁止跳跃和投篮，并持续向右，直到完全回到篮圈右侧。
    trapped_left = (
        has_ball
        and (
            player.x <= LEFT_WALL_ESCAPE_MARGIN
            or my_cx <= hoop_x - LEFT_OF_RIM_ESCAPE_MARGIN
        )
    )
    if trapped_left:
        if player.ai_state != ESCAPE_PAINT:
            player.ai_dunk_retry_cooldown = max(
                player.ai_dunk_retry_cooldown,
                DUNK_RETRY_COOLDOWN,
            )
            player.ai_shot_cooldown = max(
                player.ai_shot_cooldown,
                POST_SHOT_COOLDOWN,
            )
            player.ai_rebound_exit_timer = max(player.ai_rebound_exit_timer, 35)
            _set_state(player, ESCAPE_PAINT)

    # 先根据球权决定允许的状态集合。
    if has_ball:
        # 刚抢到篮板时，优先执行固定撤出阶段。
        if player.ai_rebound_exit_timer > 0:
            _set_state(player, ESCAPE_PAINT)
        elif player.ai_state not in (
            OFFENSE_SETUP,
            DRIVE_DUNK,
            ESCAPE_PAINT,
            SHOT_RECOVER,
        ):
            _set_state(player, OFFENSE_SETUP)
    elif opponent_has_ball:
        _set_state(player, DEFEND)
    elif opponent_shot:
        _set_state(player, BLOCK_SHOT)
    else:
        _set_state(player, SEEK_BALL)

    # ---------- 进攻：整理位置 ----------
    if player.ai_state == OFFENSE_SETUP:
        player.ai_offense_timer += 1

        # 篮板正下方永远先撤出，不允许原地投篮或起跳。
        if distance_from_rim <= UNDER_HOOP_DISTANCE:
            _set_state(player, ESCAPE_PAINT)
            direction = 1

        # 冷却结束且处于合理冲筐区，才进入一次完整扣篮尝试。
        elif (
            player.ai_dunk_retry_cooldown <= 0
            and 0 < distance_from_rim <= AI_DUNK_APPROACH_DISTANCE
        ):
            _set_state(player, DRIVE_DUNK)
            direction = -1

        else:
            if player.ai_shot_target is None:
                if random.random() < player.ai_three_point_shot_chance:
                    shot_distance = (
                        player.arena["three_point_distance"]
                        + AI_THREE_POINT_SHOOT_MARGIN
                    )
                else:
                    shot_distance = AI_TWO_POINT_SHOOT_OFFSET
                player.ai_shot_target = hoop_x + shot_distance

            distance_to_spot = player.ai_shot_target - my_cx
            at_shot_spot = abs(distance_to_spot) <= max(AI_SHOOT_STOP_DISTANCE, 28)
            setup_timed_out = player.ai_offense_timer >= MAX_OFFENSE_SETUP_FRAMES

            # 超时也只能在篮筐安全右侧出手，杜绝篮板底下强投。
            safe_to_shoot = distance_from_rim >= SAFE_FROM_HOOP_DISTANCE
            if (
                player.ai_shot_cooldown <= 0
                and safe_to_shoot
                and (at_shot_spot or setup_timed_out)
            ):
                _shoot(player, ball)
                _set_state(player, SHOT_RECOVER)
            else:
                direction = 1 if distance_to_spot > 0 else -1
                if player.ability_type == "dash":
                    want_ability = (
                        player.ability_cooldown_timer <= 0
                        and random.random() < player.ai_ability_trigger_chance
                    )

    # ---------- 进攻：一次锁定的扣篮尝试 ----------
    elif player.ai_state == DRIVE_DUNK:
        direction = -1
        player.ai_shot_target = None
        player.ai_offense_timer = 0

        # 扣篮过程中越过篮圈进入左侧死角，立即判定本次尝试失败并脱困。
        if player.x <= LEFT_WALL_ESCAPE_MARGIN or my_cx <= hoop_x - LEFT_OF_RIM_ESCAPE_MARGIN:
            player.ai_dunk_retry_cooldown = DUNK_RETRY_COOLDOWN
            player.ai_shot_cooldown = max(player.ai_shot_cooldown, POST_SHOT_COOLDOWN)
            player.ai_rebound_exit_timer = max(player.ai_rebound_exit_timer, 35)
            _set_state(player, ESCAPE_PAINT)
            direction = 1
        else:

            # 只在地面且仍处于起跳区时发出一次跳跃指令。
            if (
                player.on_ground
                and 0 < distance_from_rim <= AI_DUNK_TAKEOFF_DISTANCE
                and player.ai_state_timer <= 12
            ):
                want_jump = True

            # 一旦起跳，直到落地前不允许切换为逃离或投篮。
            airborne = not player.on_ground
            failed_landing = (
                player.ai_state_timer > 12
                and player.on_ground
                and player.vy == 0
            )
            timed_out = player.ai_state_timer >= MAX_DUNK_COMMIT_FRAMES

            if failed_landing or timed_out:
                player.ai_dunk_retry_cooldown = DUNK_RETRY_COOLDOWN
                player.ai_shot_cooldown = max(player.ai_shot_cooldown, POST_SHOT_COOLDOWN)
                _set_state(player, ESCAPE_PAINT)
                direction = 1
            elif airborne:
                # 保持单一方向，让球随持球人真正从篮圈上方向下完成扣篮。
                direction = -1

    # ---------- 进攻：失败后强制离开禁区 ----------
    elif player.ai_state == ESCAPE_PAINT:
        direction = 1
        player.ai_shot_target = None
        player.ai_offense_timer = 0

        # 抢到篮板后至少执行一段撤出时间；同时必须离开安全距离并落地。
        if (
            player.ai_rebound_exit_timer <= 0
            and distance_from_rim >= SAFE_FROM_HOOP_DISTANCE
            and my_cx > hoop_x
            and player.on_ground
        ):
            _set_state(player, OFFENSE_SETUP)

    # ---------- 投篮后的短暂恢复 ----------
    elif player.ai_state == SHOT_RECOVER:
        direction = 1 if distance_from_rim < SAFE_FROM_HOOP_DISTANCE else 0
        if not has_ball:
            _set_state(player, SEEK_BALL)
        elif player.ai_shot_cooldown <= 0:
            _set_state(player, OFFENSE_SETUP)

    # ---------- 防守 ----------
    elif player.ai_state == DEFEND:
        opponent_x, opponent_y = opponent.center()
        horizontal_distance = opponent_x - my_cx
        if abs(horizontal_distance) > AI_STEAL_APPROACH_DISTANCE:
            direction = 1 if horizontal_distance > 0 else -1
        want_steal = True

        if player.ability_type == "dash":
            want_ability = (
                player.ability_cooldown_timer <= 0
                and random.random() < player.ai_ability_trigger_chance
            )
        elif player.ability_type == "ground_slam":
            distance_to_opponent = (
                (opponent_x - my_cx) ** 2 + (opponent_y - my_cy) ** 2
            ) ** 0.5
            want_ability = (
                distance_to_opponent <= player.slam_range
                and player.ability_cooldown_timer <= 0
                and random.random() < 0.08
            )

    # ---------- 追帽 ----------
    elif player.ai_state == BLOCK_SHOT:
        horizontal_distance = ball.x - my_cx
        vertical_distance = my_cy - ball.y
        if abs(horizontal_distance) > 18:
            direction = 1 if horizontal_distance > 0 else -1
        if (
            abs(horizontal_distance) <= AI_BLOCK_HORIZONTAL_RANGE
            and -25 <= vertical_distance <= AI_BLOCK_VERTICAL_RANGE
            and player.on_ground
        ):
            want_jump = True

    # ---------- 追球 / 抢篮板 ----------
    else:  # SEEK_BALL
        horizontal_distance = ball.x - my_cx
        if abs(horizontal_distance) > 12:
            direction = 1 if horizontal_distance > 0 else -1

        distance_to_ball = ((ball.x - my_cx) ** 2 + (ball.y - my_cy) ** 2) ** 0.5
        if ball.state == "loose" and distance_to_ball <= max(62, player.steal_range):
            player.try_pick_up(ball, force=True)

        rebound_available = getattr(ball, "rebound_available", False)
        if (
            ball.holder is None
            and rebound_available
            and ball.y < my_cy + 10
            and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE
        ):
            want_jump = True

        if (
            player.ability_type == "double_jump"
            and ball.holder is None
            and rebound_available
            and not player.on_ground
            and player.double_jump_available
            and ball.y < my_cy
            and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE
        ):
            want_ability = random.random() < 0.08

    player._apply_horizontal_move(direction)
    player._apply_jump(want_jump)
    player._apply_ability(want_ability, opponent, ball)
    player._update_dash()
    player._apply_steal_or_pickup(want_steal, ball)
