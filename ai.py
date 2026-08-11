"""单人模式 AI 状态机。

V3.x 进攻决策：AI 每次获得球权时锁定一次进攻选择（中投 / 三分 / 扣篮），
避免旧逻辑因为接近篮筐就强制切成冲筐，导致几乎不投篮。
"""

import math
import random

from constants import (
    AI_SHOOT_STOP_DISTANCE,
    AI_THREE_POINT_SHOOT_MARGIN,
    AI_STEAL_APPROACH_DISTANCE,
    AI_REBOUND_JUMP_RANGE,
    AI_SHOT_MISS_OFFSET,
    AI_BLOCK_HORIZONTAL_RANGE,
    AI_BLOCK_VERTICAL_RANGE,
    GRAVITY,
    PLAYER_HEIGHT,
    DRIBBLE_HAND_OFFSET_Y,
)

# ---------- 状态 ----------
SEEK_BALL = "seek_ball"
DEFEND = "defend"
BLOCK_SHOT = "block_shot"
OFFENSE_SETUP = "offense_setup"
DRIVE_DUNK = "drive_dunk"
ESCAPE_PAINT = "escape_paint"
SHOT_RECOVER = "shot_recover"

# ---------- 进攻选择 ----------
ATTACK_MID = "mid"
ATTACK_THREE = "three"
ATTACK_DUNK = "dunk"

UNDER_HOOP_DISTANCE = 42
SAFE_FROM_HOOP_DISTANCE = 112
POST_SHOT_COOLDOWN = 34
DUNK_RETRY_COOLDOWN = 85
MAX_DUNK_COMMIT_FRAMES = 105
MAX_OFFENSE_SETUP_FRAMES = 175
LEFT_WALL_ESCAPE_MARGIN = 18
LEFT_OF_RIM_ESCAPE_MARGIN = 8

# 中投点不再使用旧版 130px。130px 会刚好落入旧扣篮触发区，
# 是 AI “只会冲篮下”的主要原因之一。
MID_SHOT_MIN_DISTANCE = 170
MID_SHOT_MAX_DISTANCE = 235


def _ensure_ai_state(player):
    defaults = {
        "ai_state": SEEK_BALL,
        "ai_state_timer": 0,
        "ai_shot_cooldown": 0,
        "ai_dunk_retry_cooldown": 0,
        "ai_offense_timer": 0,
        "ai_rebound_exit_timer": 0,
        "ai_attack_choice": None,
        "ai_had_ball_last_frame": False,
        "ai_dunk_jump_started": False,
    }
    for key, value in defaults.items():
        if not hasattr(player, key):
            setattr(player, key, value)


def _set_state(player, state):
    if player.ai_state != state:
        player.ai_state = state
        player.ai_state_timer = 0
        player.ai_shot_target = None
        if state != DRIVE_DUNK:
            player.ai_dunk_jump_started = False


def _tick_cooldowns(player):
    if player.ai_shot_cooldown > 0:
        player.ai_shot_cooldown -= 1
    if player.ai_dunk_retry_cooldown > 0:
        player.ai_dunk_retry_cooldown -= 1
    if player.ai_rebound_exit_timer > 0:
        player.ai_rebound_exit_timer -= 1


def _character_rating(player, key, fallback=3):
    ratings = getattr(player, "character_config", {}).get("ratings", {})
    try:
        return max(1, min(5, int(ratings.get(key, fallback))))
    except (TypeError, ValueError):
        return fallback


def _choose_attack(player, opponent):
    """一次球权只决定一次主要进攻方式。

    角色属性存在时会参与权重：BRAX 更爱扣、KAGE 更爱三分；
    旧角色配置没有 ratings 时仍可正常运行。
    """
    my_x, _ = player.center()
    opp_x, _ = opponent.center()
    rim_x = player.arena["rim_x"]
    rim_distance = max(0.0, my_x - rim_x)
    defender_gap = abs(opp_x - my_x)

    three_rating = _character_rating(player, "three")
    dunk_rating = _character_rating(player, "dunk")

    # 难度设置中的三分倾向仍然有效。
    three_weight = 0.12 + player.ai_three_point_shot_chance * 0.75
    three_weight += (three_rating - 3) * 0.055

    dunk_weight = 0.24 + (dunk_rating - 3) * 0.075

    # 空位时更多跳投；防守贴身时更愿意突破。
    if defender_gap >= 150:
        three_weight += 0.10
        dunk_weight -= 0.04
    elif defender_gap <= 70:
        dunk_weight += 0.10
        three_weight -= 0.05

    # 已经在很深的位置时适当增加扣篮，但不是 100% 强制扣篮。
    if rim_distance <= 150:
        dunk_weight += 0.14
        three_weight -= 0.05

    # 扣篮处于失败冷却时，彻底移除本回合扣篮选项。
    if player.ai_dunk_retry_cooldown > 0:
        dunk_weight = 0.0

    three_weight = max(0.08, min(0.48, three_weight))
    dunk_weight = max(0.0, min(0.55, dunk_weight))
    mid_weight = max(0.22, 1.0 - three_weight - dunk_weight)

    total = three_weight + dunk_weight + mid_weight
    roll = random.random() * total
    if roll < dunk_weight:
        return ATTACK_DUNK
    if roll < dunk_weight + three_weight:
        return ATTACK_THREE
    return ATTACK_MID


def _new_shot_spot(player):
    rim_x = player.arena["rim_x"]
    if player.ai_attack_choice == ATTACK_THREE:
        distance = (
            player.arena["three_point_distance"]
            + AI_THREE_POINT_SHOOT_MARGIN
            + random.uniform(0, 24)
        )
    else:
        distance = random.uniform(MID_SHOT_MIN_DISTANCE, MID_SHOT_MAX_DISTANCE)
    player.ai_shot_target = rim_x + distance


def _get_difficulty_accuracy(player):
    """根据游戏难度返回 AI 基础命中率。"""
    difficulty = str(
        getattr(player, "ai_difficulty",
                getattr(player, "difficulty", "normal"))
    ).lower()

    return {
        "easy": {
            "three": 0.25,
            "mid": 0.40,
            "layup": 0.65,
            "dunk": 0.95,
        },
        "hard": {
            "three": 0.80,
            "mid": 0.80,
            "layup": 1.00,
            "dunk": 1.00,
        },
        "normal": {
            "three": 0.38,
            "mid": 0.55,
            "layup": 0.75,
            "dunk": 0.98,
        },
    }.get(difficulty, {
        "three": 0.38,
        "mid": 0.55,
        "layup": 0.75,
        "dunk": 0.98,
    })


def _shoot(player, ball):
    hoop_x = player.arena["rim_x"]
    hoop_y = player.arena["rim_y"]
    target_x = hoop_x
    target_y = hoop_y

    accuracy = _get_difficulty_accuracy(player)

    difficulty = str(
        getattr(
            player,
            "ai_difficulty",
            getattr(player, "difficulty", "normal"),
        )
    ).lower()

    if difficulty == "hard":
        # 困难模式：
        # 三分和中投最终命中率固定为 80%。
        hit_chance = 0.80
    else:
        if player.ai_attack_choice == ATTACK_THREE:
            hit_chance = accuracy["three"]
            three_rating = _character_rating(player, "three")
            hit_chance += (three_rating - 3) * 0.035
        else:
            hit_chance = accuracy["mid"]

        # Easy / Normal 仍然受防守压力影响。
        opponent = getattr(player, "opponent", None)
        if opponent:
            distance = math.hypot(
                opponent.center()[0] - player.center()[0],
                opponent.center()[1] - player.center()[1],
            )
            if distance < 70:
                hit_chance -= 0.15
            elif distance > 160:
                hit_chance += 0.05

        hit_chance = max(0.05, min(0.95, hit_chance))

    if random.random() > hit_chance:
        target_x += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)
        target_y += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)

    my_cx, my_cy = player.center()
    shot_distance = math.hypot(my_cx - hoop_x, my_cy - hoop_y)
    ball.shoot_towards(target_x, target_y, player, shot_distance)

    player.ai_shot_target = None
    player.ai_attack_choice = None
    player.ai_offense_timer = 0
    player.ai_shot_cooldown = POST_SHOT_COOLDOWN


def _dunk_takeoff_distance(player):
    """按角色速度/弹跳估算正确扣篮起跳距离。

    旧版统一在距离篮筐约 105px 才起跳。高速角色会在仍处于上升阶段时
    越过篮筐，落下时已经飞到篮板后面，因此几乎无法触发“从上往下扣入”。
    这里估算篮球手部下降到 rim_y 所需时间，再换算水平距离。
    """
    ground_y = player.arena["ground_y"]
    rim_y = player.arena["rim_y"]
    hand_y_ground = ground_y - PLAYER_HEIGHT + DRIBBLE_HAND_OFFSET_Y
    c = hand_y_ground - rim_y
    v0 = float(player.jump_velocity)

    discriminant = v0 * v0 - 2.0 * GRAVITY * c
    if discriminant <= 0:
        # 极端自定义角色兜底。
        return 145.0

    descending_time = (-v0 + math.sqrt(discriminant)) / GRAVITY
    distance = player.move_speed * descending_time
    return max(112.0, min(245.0, distance))


def _fail_dunk_and_escape(player):
    player.ai_dunk_retry_cooldown = DUNK_RETRY_COOLDOWN
    player.ai_shot_cooldown = max(player.ai_shot_cooldown, 18)
    # 扣篮失败后下一次固定改打中投，避免连续重复同一种失败动作。
    player.ai_attack_choice = ATTACK_MID
    player.ai_rebound_exit_timer = max(player.ai_rebound_exit_timer, 24)
    _set_state(player, ESCAPE_PAINT)



def _consider_character_ability(
    player,
    ball,
    opponent,
    *,
    state,
    direction,
    has_ball,
    opponent_has_ball,
    existing_request=False,
):
    """Let every AI character actively use its real gameplay ability.

    This supplements the state machine instead of replacing it:
    - DJH: dash when there is meaningful space to cover.
    - BRAX: ground slam when the opponent is inside slam range.
    - KAGE: use the second jump while airborne during a drive/block/rebound.
    - DUKE: summon Blood Echo during live possessions when no clone exists.

    Player ability cooldowns remain the final limiter, so the AI cannot spam.
    """
    if existing_request:
        return True

    ability_type = getattr(player, "ability_type", "none")
    if ability_type in (None, "none"):
        return False

    if getattr(player, "ability_cooldown_timer", 0) > 0:
        return False

    my_x, my_y = player.center()
    opp_x, opp_y = opponent.center()
    opponent_distance = math.hypot(opp_x - my_x, opp_y - my_y)

    # Reuse the difficulty's existing ability tendency.
    trigger = float(getattr(player, "ai_ability_trigger_chance", 0.02))

    # DJH — Lightning Dash.
    if ability_type == "dash":
        if getattr(player, "is_dashing", False):
            return False

        # Offensive dash: cover real distance, including committed dunk drives.
        if has_ball and direction != 0:
            if state == DRIVE_DUNK:
                return random.random() < max(0.055, trigger * 2.2)

            target = getattr(player, "ai_shot_target", None)
            if target is not None:
                distance_to_target = abs(target - my_x)
                if distance_to_target >= 105:
                    return random.random() < max(0.035, trigger * 1.7)

            if state == ESCAPE_PAINT:
                return random.random() < max(0.030, trigger * 1.5)

        # Defensive chase dash.
        if opponent_has_ball and direction != 0 and opponent_distance >= 95:
            return random.random() < max(0.030, trigger * 1.5)

        return False

    # BRAX — Ground Slam.
    if ability_type == "ground_slam":
        slam_range = float(getattr(player, "slam_range", 115))

        if opponent_distance <= slam_range:
            # Higher priority if the slam can knock the ball out of the opponent.
            chance = 0.18 if opponent_has_ball else 0.11
            if has_ball:
                chance = max(chance, 0.12)
            return random.random() < chance

        return False

    # KAGE — Shadow / Double Jump.
    if ability_type == "double_jump":
        if getattr(player, "on_ground", True):
            return False
        if not getattr(player, "double_jump_available", False):
            return False

        vy = float(getattr(player, "vy", 0.0))
        rim_x = player.arena["rim_x"]
        distance_from_rim = my_x - rim_x

        # During a dunk drive, save the second jump for around the first apex.
        if has_ball and state == DRIVE_DUNK:
            if distance_from_rim <= 175 and vy >= -3.0:
                return True

        # Chase a shot/block higher in the air.
        if state == BLOCK_SHOT and ball.state == "flying":
            horizontal = abs(ball.x - my_x)
            if horizontal <= AI_BLOCK_HORIZONTAL_RANGE + 20 and ball.y < my_y:
                if vy >= -4.0:
                    return True

        # Rebound second jump.
        if (
            state == SEEK_BALL
            and getattr(ball, "rebound_available", False)
            and ball.holder is None
            and ball.y < my_y
            and abs(ball.x - my_x) <= AI_REBOUND_JUMP_RANGE
            and vy >= -3.0
        ):
            return True

        return False

    # DUKE — Blood Echo.
    if ability_type == "clone":
        if getattr(player, "is_clone", False):
            return False

        # game.py links pass_target to the live Blood Echo.  None therefore
        # doubles as a reliable "no clone currently active" signal.
        if getattr(player, "pass_target", None) is not None:
            return False
        if getattr(player, "clone_request_pending", False):
            return False

        # Summon during an actual possession, not while idling after loose balls.
        if has_ball:
            return random.random() < max(0.055, trigger * 2.5)

        if opponent_has_ball:
            return random.random() < max(0.030, trigger * 1.5)

        return False

    return False

def update_ai(player, ball, opponent):
    """每帧更新 AI；同一帧只由一个状态决定移动与动作。"""
    _ensure_ai_state(player)
    _tick_cooldowns(player)
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

    # ========================================================
    # 困难 AI：Shot Clock 最后 3 秒紧急进攻
    # ========================================================
    shot_clock_frames = getattr(
        player,
        "ai_shot_clock_frames",
        None,
    )

    difficulty = str(
        getattr(
            player,
            "ai_difficulty",
            "normal",
        )
    ).lower()

    urgent_offense = (
        has_ball
        and difficulty == "hard"
        and shot_clock_frames is not None
        and shot_clock_frames <= 3 * 60
        and not getattr(
            player,
            "must_clear_three",
            False,
        )
    )

    if urgent_offense:
        rim_distance = max(
            0.0,
            distance_from_rim,
        )

        # 根据当前位置决定按中投还是三分结算。
        if (
            rim_distance
            >= player.arena["three_point_distance"]
        ):
            player.ai_attack_choice = ATTACK_THREE
        else:
            player.ai_attack_choice = ATTACK_MID

        player.ai_shot_target = None

        opponent_distance = math.hypot(
            opponent.center()[0] - my_cx,
            opponent.center()[1] - my_cy,
        )

        # 3 秒内：
        # 空位或正常空间直接出手。
        #
        # 1.5 秒内：
        # 无论防守多近都必须强投，避免进攻超时。
        force_shot = shot_clock_frames <= 90
        reasonable_window = opponent_distance >= 70

        if (
            player.ai_shot_cooldown <= 0
            and (
                force_shot
                or reasonable_window
            )
        ):
            _shoot(
                player,
                ball,
            )

            _set_state(
                player,
                SHOT_RECOVER,
            )

            player.ai_had_ball_last_frame = False
            return

    # 新球权：只在这里抽一次进攻选择，之后一直锁定到出手/扣篮结束。
    if has_ball and not player.ai_had_ball_last_frame:
        player.ai_attack_choice = _choose_attack(player, opponent)
        player.ai_shot_target = None
        player.ai_offense_timer = 0

    if not has_ball:
        player.ai_attack_choice = None
        player.ai_shot_target = None

    # 左墙/篮板背后脱困优先级最高。
    trapped_left = has_ball and (
        player.x <= LEFT_WALL_ESCAPE_MARGIN
        or my_cx <= hoop_x - LEFT_OF_RIM_ESCAPE_MARGIN
    )
    if trapped_left:
        player.ai_dunk_retry_cooldown = max(
            player.ai_dunk_retry_cooldown, DUNK_RETRY_COOLDOWN
        )
        player.ai_attack_choice = ATTACK_MID
        player.ai_rebound_exit_timer = max(player.ai_rebound_exit_timer, 30)
        _set_state(player, ESCAPE_PAINT)

    # ---------- 根据球权限制状态 ----------
    if has_ball:
        if player.ai_rebound_exit_timer > 0 or trapped_left:
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

    # ---------- 进攻：根据锁定选择执行 ----------
    if player.ai_state == OFFENSE_SETUP:
        player.ai_offense_timer += 1

        if player.ai_attack_choice is None:
            player.ai_attack_choice = _choose_attack(player, opponent)

        # 在篮板正下方，任何战术都先撤出。
        if distance_from_rim <= UNDER_HOOP_DISTANCE:
            _set_state(player, ESCAPE_PAINT)
            direction = 1

        elif player.ai_attack_choice == ATTACK_DUNK:
            if player.ai_dunk_retry_cooldown > 0:
                player.ai_attack_choice = ATTACK_MID
            else:
                _set_state(player, DRIVE_DUNK)
                direction = -1

        if player.ai_state == OFFENSE_SETUP:
            if player.ai_shot_target is None:
                _new_shot_spot(player)

            distance_to_spot = player.ai_shot_target - my_cx
            at_shot_spot = abs(distance_to_spot) <= max(AI_SHOOT_STOP_DISTANCE, 24)
            setup_timed_out = player.ai_offense_timer >= MAX_OFFENSE_SETUP_FRAMES
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
                    # 只有去投篮点的路较长时才可能用冲刺，避免在投篮点附近乱冲。
                    want_ability = (
                        abs(distance_to_spot) > 120
                        and player.ability_cooldown_timer <= 0
                        and random.random() < player.ai_ability_trigger_chance
                    )

    # ---------- 进攻：扣篮 ----------
    elif player.ai_state == DRIVE_DUNK:
        player.ai_shot_target = None
        player.ai_offense_timer = 0
        takeoff_distance = _dunk_takeoff_distance(player)

        # 还没到起跳点：带球直线冲向篮筐。
        if not player.ai_dunk_jump_started and player.on_ground:
            if distance_from_rim > takeoff_distance + 8:
                direction = -1
            elif distance_from_rim > 0:
                direction = -1
                want_jump = True
                player.ai_dunk_jump_started = True
            else:
                _fail_dunk_and_escape(player)
                direction = 1
        else:
            # 起跳后保持向篮筐方向移动。正确起跳距离会让下降过筐时恰好在篮圈上方。
            direction = -1

            # 一旦已经越过篮圈太多，立即结束失败尝试。
            if my_cx <= hoop_x - LEFT_OF_RIM_ESCAPE_MARGIN:
                _fail_dunk_and_escape(player)
                direction = 1
            else:
                landed_after_jump = (
                    player.ai_dunk_jump_started
                    and player.ai_state_timer > 10
                    and player.on_ground
                    and player.vy == 0
                )
                timed_out = player.ai_state_timer >= MAX_DUNK_COMMIT_FRAMES
                if landed_after_jump or timed_out:
                    _fail_dunk_and_escape(player)
                    direction = 1

    # ---------- 禁区撤出 ----------
    elif player.ai_state == ESCAPE_PAINT:
        direction = 1
        player.ai_shot_target = None
        player.ai_offense_timer = 0

        if (
            player.ai_rebound_exit_timer <= 0
            and distance_from_rim >= SAFE_FROM_HOOP_DISTANCE
            and my_cx > hoop_x
            and player.on_ground
        ):
            if player.ai_attack_choice is None:
                player.ai_attack_choice = _choose_attack(player, opponent)
            _set_state(player, OFFENSE_SETUP)

    # ---------- 出手后恢复 ----------
    elif player.ai_state == SHOT_RECOVER:
        direction = 1 if distance_from_rim < SAFE_FROM_HOOP_DISTANCE else 0
        if not has_ball:
            _set_state(player, SEEK_BALL)
        elif player.ai_shot_cooldown <= 0:
            if player.ai_attack_choice is None:
                player.ai_attack_choice = _choose_attack(player, opponent)
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
            distance_to_opponent = math.hypot(opponent_x - my_cx, opponent_y - my_cy)
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

        distance_to_ball = math.hypot(ball.x - my_cx, ball.y - my_cy)
        if ball.state == "loose" and distance_to_ball <= max(62, player.steal_range):
            player.try_pick_up(ball, force=True)

        rebound_available = getattr(ball, "rebound_available", False)
        rebound_ready = (
            rebound_available
            and getattr(ball, "rebound_grace_timer", 0) <= 0
        )

        if (
            ball.holder is None
            and rebound_ready
            and ball.y < my_cy + 10
            and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE
        ):
            want_jump = True

        if (
            player.ability_type == "double_jump"
            and ball.holder is None
            and rebound_ready
            and not player.on_ground
            and player.double_jump_available
            and ball.y < my_cy
            and abs(horizontal_distance) < AI_REBOUND_JUMP_RANGE
        ):
            want_ability = random.random() < 0.08

    # Final character-skill decision. Existing state-specific requests remain
    # valid, while this fills the gaps for BRAX, KAGE and especially DUKE.
    want_ability = _consider_character_ability(
        player,
        ball,
        opponent,
        state=player.ai_state,
        direction=direction,
        has_ball=has_ball,
        opponent_has_ball=opponent_has_ball,
        existing_request=want_ability,
    )

    player._apply_horizontal_move(direction)
    player._apply_jump(want_jump)
    player._apply_ability(want_ability, opponent, ball)
    player._update_dash()
    player._apply_steal_or_pickup(want_steal, ball)

    # try_pick_up 可能在本帧末尾刚刚拿到球，因此使用最终球权记录。
    player.ai_had_ball_last_frame = ball.state == "held" and ball.holder is player
