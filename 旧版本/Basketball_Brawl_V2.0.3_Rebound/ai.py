"""单人模式 AI 决策逻辑。"""

import random

from constants import (
    AI_SHOOT_STOP_DISTANCE,
    AI_TWO_POINT_SHOOT_OFFSET,
    AI_THREE_POINT_SHOOT_MARGIN,
    AI_STEAL_APPROACH_DISTANCE,
    AI_REBOUND_JUMP_RANGE,
    AI_SHOT_MISS_OFFSET,
    AI_BLOCK_HORIZONTAL_RANGE, AI_BLOCK_VERTICAL_RANGE,
)


def update_ai(player, ball, opponent):
    """每帧更新 AI 行为。"""
    my_cx, my_cy = player.center()

    direction = 0
    want_jump = False
    want_steal = False
    want_ability = False

    # 用于防止 AI 因碰撞或位置误差一直卡在投篮点附近。
    if not hasattr(player, "ai_offense_timer"):
        player.ai_offense_timer = 0

    # 1. AI 持球：移动到投篮点并直接出手。
    if ball.holder is player and ball.state == "held":
        player.ai_offense_timer += 1
        hoop_x = player.arena["rim_x"]
        hoop_y = player.arena["rim_y"]

        if player.ai_shot_target is None:
            if random.random() < player.ai_three_point_shot_chance:
                shot_distance = (
                    player.arena["three_point_distance"]
                    + AI_THREE_POINT_SHOOT_MARGIN
                )
            else:
                shot_distance = AI_TWO_POINT_SHOOT_OFFSET

            # 当前篮筐在左侧，投篮点位于篮筐右侧。
            player.ai_shot_target = hoop_x + shot_distance

        distance_to_spot = player.ai_shot_target - my_cx

        # 到达投篮点，或者持球超过 120 帧，直接投篮。
        should_shoot = (
            abs(distance_to_spot) <= max(AI_SHOOT_STOP_DISTANCE, 28)
            or player.ai_offense_timer >= 120
        )

        if should_shoot:
            target_x = hoop_x
            target_y = hoop_y

            if random.random() < player.ai_shot_miss_chance:
                target_x += random.uniform(
                    -AI_SHOT_MISS_OFFSET,
                    AI_SHOT_MISS_OFFSET,
                )
                target_y += random.uniform(
                    -AI_SHOT_MISS_OFFSET,
                    AI_SHOT_MISS_OFFSET,
                )

            shot_distance = (
                (my_cx - hoop_x) ** 2
                + (my_cy - hoop_y) ** 2
            ) ** 0.5

            # 直接让篮球离手，绕过 Player 的辅助投篮函数。
            ball.shoot_towards(
                target_x,
                target_y,
                player,
                shot_distance,
            )

            player.ai_shot_target = None
            player.ai_offense_timer = 0
            direction = 0

        else:
            direction = 1 if distance_to_spot > 0 else -1

            if player.ability_type == "dash":
                want_ability = (
                    player.ability_cooldown_timer <= 0
                    and random.random()
                    < player.ai_ability_trigger_chance
                )

    # 2. 对手持球：追防、抢断。
    elif ball.holder is opponent:
        player.ai_shot_target = None
        player.ai_offense_timer = 0

        opponent_x, opponent_y = opponent.center()
        horizontal_distance = opponent_x - my_cx

        if abs(horizontal_distance) > AI_STEAL_APPROACH_DISTANCE:
            direction = 1 if horizontal_distance > 0 else -1

        want_steal = True

        if player.ability_type == "dash":
            want_ability = (
                player.ability_cooldown_timer <= 0
                and random.random()
                < player.ai_ability_trigger_chance
            )

        elif player.ability_type == "ground_slam":
            distance_to_opponent = (
                (opponent_x - my_cx) ** 2
                + (opponent_y - my_cy) ** 2
            ) ** 0.5

            want_ability = (
                distance_to_opponent <= player.slam_range
                and player.ability_cooldown_timer <= 0
                and random.random() < 0.08
            )

    # 3. 对手投篮后：优先判断是否需要追帽。
    elif ball.state == "flying" and ball.last_shooter is opponent:
        player.ai_shot_target = None
        player.ai_offense_timer = 0
        horizontal_distance = ball.x - my_cx
        vertical_distance = my_cy - ball.y

        if abs(horizontal_distance) > 18:
            direction = 1 if horizontal_distance > 0 else -1

        # 球在头顶附近且仍处于可触及高度时起跳封盖。
        if (
            abs(horizontal_distance) <= AI_BLOCK_HORIZONTAL_RANGE
            and -25 <= vertical_distance <= AI_BLOCK_VERTICAL_RANGE
            and player.on_ground
        ):
            want_jump = True

    # 4. 无人持球：追球、捡球、抢篮板。
    else:
        player.ai_shot_target = None
        player.ai_offense_timer = 0

        horizontal_distance = ball.x - my_cx

        if abs(horizontal_distance) > 12:
            direction = 1 if horizontal_distance > 0 else -1

        distance_to_ball = (
            (ball.x - my_cx) ** 2
            + (ball.y - my_cy) ** 2
        ) ** 0.5

        # 只追捡 loose 球，绝不能把 flying 的投篮球重新吸回手中。
        if (
            ball.state == "loose"
            and distance_to_ball <= max(62, player.steal_range)
        ):
            player.try_pick_up(ball, force=True)

        if (
            ball.holder is None
            and getattr(ball, "rebound_available", False)
            and ball.y < my_cy + 10
            and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE
        ):
            want_jump = True

        if (
            player.ability_type == "double_jump"
            and ball.holder is None
            and getattr(ball, "rebound_available", False)
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