"""单人模式 AI 决策。

这里仅决定“想做什么”，实际移动、技能、抢断和投篮仍由 Player 执行。
"""

import random

from constants import (
    AI_SHOOT_STOP_DISTANCE,
    AI_TWO_POINT_SHOOT_OFFSET,
    AI_THREE_POINT_SHOOT_MARGIN,
    AI_STEAL_APPROACH_DISTANCE,
    AI_REBOUND_JUMP_RANGE,
)


def update_ai(player, ball, opponent):
    my_cx, my_cy = player.center()
    direction = 0
    want_jump = False
    want_shoot = False
    want_steal = False
    want_ability = False

    # 1. 自己持球：跑到投篮点后出手。
    if ball.holder is player:
        if player.ai_shot_target is None:
            hoop_x = player.arena["rim_x"]
            if random.random() < player.ai_three_point_shot_chance:
                player.ai_shot_target = (
                    hoop_x
                    + player.arena["three_point_distance"]
                    + AI_THREE_POINT_SHOOT_MARGIN
                )
            else:
                player.ai_shot_target = hoop_x + AI_TWO_POINT_SHOOT_OFFSET

        distance_to_spot = player.ai_shot_target - my_cx
        if abs(distance_to_spot) > AI_SHOOT_STOP_DISTANCE:
            direction = 1 if distance_to_spot > 0 else -1
            if player.ability_type == "dash":
                want_ability = random.random() < player.ai_ability_trigger_chance
        else:
            want_shoot = True

    # 2. 对手持球：追人、抢断，特定技能只在这个阶段考虑。
    elif ball.holder is opponent:
        player.ai_shot_target = None
        opponent_x, opponent_y = opponent.center()
        horizontal_distance = opponent_x - my_cx
        if abs(horizontal_distance) > AI_STEAL_APPROACH_DISTANCE:
            direction = 1 if horizontal_distance > 0 else -1

        want_steal = True

        if player.ability_type == "dash":
            want_ability = random.random() < player.ai_ability_trigger_chance
        elif player.ability_type == "ground_slam":
            distance = ((opponent_x - my_cx) ** 2 + (opponent_y - my_cy) ** 2) ** 0.5
            want_ability = (
                distance <= player.slam_range
                and player.ability_cooldown_timer <= 0
                and random.random() < 0.08
            )

    # 3. 无人持球：只追球、跳篮板和捡球，不释放攻击技能。
    else:
        player.ai_shot_target = None
        horizontal_distance = ball.x - my_cx
        if abs(horizontal_distance) > 12:
            direction = 1 if horizontal_distance > 0 else -1

        distance_to_ball = ((ball.x - my_cx) ** 2 + (ball.y - my_cy) ** 2) ** 0.5
        if distance_to_ball <= max(62, player.steal_range):
            player.try_pick_up(ball, force=True)

        if ball.y < my_cy - 20 and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE:
            want_jump = True

        # Ninja 可以为了空中篮板二段跳；不会在地面球旁乱放技能。
        if (
            player.ability_type == "double_jump"
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

    if want_shoot:
        player._apply_shoot_with_ai_accuracy(ball)
