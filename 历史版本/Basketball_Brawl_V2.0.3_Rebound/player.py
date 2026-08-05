"""玩家实体、角色技能、投篮与抢断/捡球逻辑。"""

import pygame
import math
import random

from constants import (
    GRAVITY, JUMP_VELOCITY, MOVE_SPEED, GROUND_Y,
    PLAYER_WIDTH, PLAYER_HEIGHT, STEAL_RANGE,
    POSSESSION_COOLDOWN_FRAMES, STEAL_COOLDOWN_FRAMES,
    DASH_SPEED, DASH_DURATION_FRAMES, DASH_COOLDOWN_FRAMES,
    SCREEN_WIDTH,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT,
    COLOR_DASH_TRAIL,
    ANIMATION_SPEED, DEFAULT_FRAME_COUNTS, BALL_SPAWN_X,
    SHOT_CHARGE_MAX_FRAMES, SHOT_PERFECT_MIN, SHOT_PERFECT_MAX,
    SHOT_MAX_HORIZONTAL_ERROR, SHOT_METER_WIDTH, SHOT_METER_HEIGHT,
    SHOT_METER_COLOR, SHOT_METER_PERFECT_COLOR, SHOT_METER_BG_COLOR,
    THREE_POINT_RADIUS,
    AI_SHOT_MISS_OFFSET, AI_DIFFICULTY_PRESETS,
    DASH_HIT_KNOCKBACK, DASH_HIT_VERTICAL, DASH_HIT_COOLDOWN_FRAMES,
    BLOCK_REACH_X, BLOCK_REACH_Y, BLOCK_COOLDOWN_FRAMES,
    BLOCK_HORIZONTAL_FORCE, BLOCK_VERTICAL_FORCE,
    REBOUND_REACH_X, REBOUND_REACH_Y, REBOUND_CATCH_RADIUS,
    REBOUND_COOLDOWN_FRAMES, REBOUND_POSSESSION_IMMUNITY,
    BOX_OUT_RANGE, BOX_OUT_PRIORITY_BONUS,
)
from animation import load_character_animations, draw_procedural_character


class Player:
    def __init__(
        self,
        x,
        y,
        color,
        controls,
        facing_right=True,
        name="P1",
        sprite_folder=None,
        frame_counts=None,
        ai_controlled=False,
        character_config=None,
        arena=None,
    ):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.controls = controls
        self.facing_right = facing_right
        self.name = name
        self.on_ground = False
        self.score = 0
        self.events = []
        self.dash_hit_registered = False
        self.dash_hit_cooldown_timer = 0
        self.block_cooldown_timer = 0
        self.blocks = 0
        self.rebounds = 0
        self.rebound_cooldown_timer = 0
        self.arena = arena or {
            "ground_y": GROUND_Y, "rim_x": HOOP_X + HOOP_WIDTH / 2,
            "rim_y": HOOP_Y + HOOP_HEIGHT / 2, "hoop_width": HOOP_WIDTH,
            "hoop_height": HOOP_HEIGHT, "three_point_distance": THREE_POINT_RADIUS,
            "ball_spawn_x": BALL_SPAWN_X,
        }

        self.character_config = character_config or {}
        self.character_id = self.character_config.get("id", "default")
        self.character_name = self.character_config.get("name", name)
        self.ability_type = self.character_config.get("ability_type", "none")
        self.ability_name = self.character_config.get("ability_name", "No Ability")
        self.ability_description = self.character_config.get("ability_description", "")

        self.base_move_speed = self.character_config.get("move_speed", MOVE_SPEED)
        self.jump_velocity = self.character_config.get("jump_velocity", JUMP_VELOCITY)
        self.base_steal_range = self.character_config.get("steal_range", STEAL_RANGE)
        self.move_speed = self.base_move_speed
        self.steal_range = self.base_steal_range

        self.possession_immune_timer = 0
        self.steal_cooldown_timer = 0

        self.ability_cooldown_max = self.character_config.get("ability_cooldown", 0)
        self.ability_cooldown_timer = 0

        self.dash_speed = self.character_config.get("dash_speed", DASH_SPEED)
        self.dash_duration_max = self.character_config.get("dash_duration", DASH_DURATION_FRAMES)
        self.is_dashing = False
        self.dash_timer = 0

        self.slam_range = self.character_config.get("slam_range", 0)
        self.slam_horizontal_force = self.character_config.get("slam_horizontal_force", 0)
        self.slam_vertical_force = self.character_config.get("slam_vertical_force", 0)
        self.slam_effect_timer = 0

        self.double_jump_velocity = self.character_config.get(
            "double_jump_velocity", JUMP_VELOCITY
        )
        self.double_jump_available = False

        # ---------- 蓄力投篮 ----------
        self.shot_charge_max = self.character_config.get(
            "shot_charge_max", SHOT_CHARGE_MAX_FRAMES
        )
        self.shot_charge_speed = self.character_config.get(
            "shot_charge_speed", 1.0
        )
        self.shot_perfect_min = self.character_config.get(
            "shot_perfect_min", SHOT_PERFECT_MIN
        )
        self.shot_perfect_max = self.character_config.get(
            "shot_perfect_max", SHOT_PERFECT_MAX
        )
        self.shot_error_scale = self.character_config.get(
            "shot_error_scale", SHOT_MAX_HORIZONTAL_ERROR
        )
        self.is_charging_shot = False
        self.shot_charge = 0.0

        self.ai_controlled = ai_controlled
        self.ai_shot_target = None
        normal_preset = AI_DIFFICULTY_PRESETS["normal"]
        self.ai_shot_miss_chance = normal_preset["shot_miss_chance"]
        self.ai_ability_trigger_chance = normal_preset["dash_trigger_chance"]
        self.ai_three_point_shot_chance = normal_preset["three_point_shot_chance"]

        self.frame_counts = frame_counts or DEFAULT_FRAME_COUNTS
        self.animations = load_character_animations(sprite_folder, self.frame_counts)
        self.anim_state = "idle"
        self.anim_frame_index = 0
        self.anim_timer = 0

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), PLAYER_WIDTH, PLAYER_HEIGHT)

    def center(self):
        return self.x + PLAYER_WIDTH / 2, self.y + PLAYER_HEIGHT / 2

    def apply_ai_difficulty(self, difficulty):
        preset = AI_DIFFICULTY_PRESETS.get(difficulty, AI_DIFFICULTY_PRESETS["normal"])
        self.move_speed = self.base_move_speed * preset["move_speed_multiplier"]
        self.steal_range = self.base_steal_range * preset["steal_range_multiplier"]

        if self.ability_type == "dash":
            base_dash_speed = self.character_config.get("dash_speed", DASH_SPEED)
            self.dash_speed = base_dash_speed * preset["dash_speed_multiplier"]
            self.ability_cooldown_max = max(
                1,
                int(
                    self.character_config.get("ability_cooldown", DASH_COOLDOWN_FRAMES)
                    * preset["dash_cooldown_multiplier"]
                ),
            )

        self.ai_shot_miss_chance = preset["shot_miss_chance"]
        self.ai_ability_trigger_chance = preset["dash_trigger_chance"]
        self.ai_three_point_shot_chance = preset["three_point_shot_chance"]

    def _apply_horizontal_move(self, direction):
        if self.is_dashing:
            return
        self.vx = 0
        if direction < 0:
            self.vx = -self.move_speed
            self.facing_right = False
        elif direction > 0:
            self.vx = self.move_speed
            self.facing_right = True

    def _apply_jump(self, want_jump):
        if want_jump and self.on_ground:
            self.vy = self.jump_velocity
            self.on_ground = False
            if self.ability_type == "double_jump":
                self.double_jump_available = True

    def _handle_charge_shot(self, action_pressed, ball):
        """真人玩家蓄力投篮：长按开始蓄力，松开后出手。"""
        has_ball = ball.state == "held" and ball.holder is self

        if not has_ball:
            self.is_charging_shot = False
            self.shot_charge = 0.0
            return

        if action_pressed:
            self.is_charging_shot = True
            self.shot_charge = min(
                float(self.shot_charge_max),
                self.shot_charge + self.shot_charge_speed,
            )

            if self.shot_charge >= self.shot_charge_max:
                self._release_charged_shot(ball)
            return

        if self.is_charging_shot:
            self._release_charged_shot(ball)

    def _release_charged_shot(self, ball):
        if ball.state != "held" or ball.holder is not self:
            self.is_charging_shot = False
            self.shot_charge = 0.0
            return

        hoop_x = self.arena["rim_x"]
        hoop_y = self.arena["rim_y"]
        charge_ratio = max(0.0, min(1.0, self.shot_charge / self.shot_charge_max))

        if self.shot_perfect_min <= charge_ratio <= self.shot_perfect_max:
            horizontal_error = 0.0
        elif charge_ratio < self.shot_perfect_min:
            miss_ratio = (self.shot_perfect_min - charge_ratio) / max(
                0.01, self.shot_perfect_min
            )
            horizontal_error = self.shot_error_scale * miss_ratio
        else:
            miss_ratio = (charge_ratio - self.shot_perfect_max) / max(
                0.01, 1.0 - self.shot_perfect_max
            )
            horizontal_error = -self.shot_error_scale * miss_ratio

        target_x = hoop_x + horizontal_error
        target_y = hoop_y
        shooter_x, shooter_y = self.center()
        shot_distance = (
            (shooter_x - hoop_x) ** 2 + (shooter_y - hoop_y) ** 2
        ) ** 0.5

        ball.shoot_towards(target_x, target_y, self, shot_distance)
        self.is_charging_shot = False
        self.shot_charge = 0.0

    def _apply_steal_or_pickup(self, want_interact, ball):
        """同一个键：无人持球时捡球，对手持球时抢断。"""
        if not want_interact:
            return

        # 只能捡起真正处于 loose 状态的球。
        # flying 状态也满足 holder is None；若不判断 state，AI 投篮后的下一帧
        # 会立刻把刚离手的球重新吸回手中。
        if ball.holder is None and ball.state == "loose":
            my_x, my_y = self.center()
            distance = ((ball.x - my_x) ** 2 + (ball.y - my_y) ** 2) ** 0.5
            pickup_range = max(58, self.steal_range)
            if distance <= pickup_range:
                ball.attach_to(self)
                self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES
            return

        if ball.holder is self:
            return

        # flying 球、被盖后的瞬间以及其他无人持球状态都不能执行抢断。
        # 先保存 holder 并检查 None，避免读取 None.possession_immune_timer。
        holder = ball.holder
        if holder is None:
            return

        if self.steal_cooldown_timer > 0:
            return
        if holder.possession_immune_timer > 0:
            return

        hx, hy = holder.center()
        mx, my = self.center()
        distance = ((hx - mx) ** 2 + (hy - my) ** 2) ** 0.5
        if distance < self.steal_range:
            ball.attach_to(self)
            self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES
            self.steal_cooldown_timer = STEAL_COOLDOWN_FRAMES

    def _apply_ability(self, want_ability, opponent=None, ball=None):
        if not want_ability:
            return
        if self.ability_type == "dash":
            self._use_dash()
        elif self.ability_type == "ground_slam":
            self._use_ground_slam(opponent, ball)
        elif self.ability_type == "double_jump":
            self._use_double_jump()

    def _use_dash(self):
        if self.ability_cooldown_timer > 0 or self.is_dashing:
            return
        self.is_dashing = True
        self.dash_hit_registered = False
        self.dash_timer = self.dash_duration_max
        self.ability_cooldown_timer = self.ability_cooldown_max
        dash_x, dash_y = self.center()
        self.events.append(("dash", dash_x, dash_y))

    def _update_dash(self):
        if not self.is_dashing:
            return
        direction = 1 if self.facing_right else -1
        self.vx = self.dash_speed * direction
        self.dash_timer -= 1
        if self.dash_timer <= 0:
            self.is_dashing = False
            self.dash_hit_registered = False

    def _use_ground_slam(self, opponent, ball):
        if self.ability_cooldown_timer > 0 or opponent is None:
            return

        self.ability_cooldown_timer = self.ability_cooldown_max
        self.slam_effect_timer = 20

        my_x, my_y = self.center()
        self.events.append(("slam", my_x, self.arena["ground_y"] - 6))

        opponent_x, opponent_y = opponent.center()
        distance = ((opponent_x - my_x) ** 2 + (opponent_y - my_y) ** 2) ** 0.5
        if distance > self.slam_range:
            return

        direction = 1 if opponent_x >= my_x else -1
        opponent.vx = self.slam_horizontal_force * direction
        opponent.vy = self.slam_vertical_force
        opponent.on_ground = False

        if ball is not None and ball.state == "held" and ball.holder is opponent:
            ball.state = "loose"
            ball.holder = None
            ball.x = opponent_x
            ball.y = opponent_y
            ball.vx = self.slam_horizontal_force * direction * 0.7
            ball.vy = -7

    def _use_double_jump(self):
        if self.on_ground or not self.double_jump_available:
            return
        self.vy = self.double_jump_velocity
        self.double_jump_available = False
        self.events.append(("double_jump", self.center()[0], self.y + PLAYER_HEIGHT))

    def handle_input(self, keys, ball, opponent=None):
        controls = self.controls
        direction = 0
        if keys[controls["left"]]:
            direction = -1
        if keys[controls["right"]]:
            direction = 1

        self._apply_horizontal_move(direction)
        self._apply_jump(keys[controls["jump"]])
        self._apply_ability(keys[controls["ability"]], opponent, ball)
        self._update_dash()
        self._handle_charge_shot(keys[controls["action"]], ball)
        self._apply_steal_or_pickup(keys[controls["steal"]], ball)

    def handle_ai(self, ball, opponent):
        """AI决策被拆到 ai.py，Player 只负责执行动作。"""
        from ai import update_ai
        update_ai(self, ball, opponent)

    def _apply_shoot_with_ai_accuracy(self, ball):
        """AI 立即投篮；成功时返回 True。"""
        if ball.state != "held" or ball.holder is not self:
            return False

        hoop_center_x = self.arena["rim_x"]
        hoop_center_y = self.arena["rim_y"]
        target_x = hoop_center_x
        target_y = hoop_center_y

        if random.random() < self.ai_shot_miss_chance:
            target_x += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)
            target_y += random.uniform(-AI_SHOT_MISS_OFFSET, AI_SHOT_MISS_OFFSET)

        shooter_x, shooter_y = self.center()
        shot_distance = (
            (shooter_x - hoop_center_x) ** 2
            + (shooter_y - hoop_center_y) ** 2
        ) ** 0.5

        ball.shoot_towards(
            target_x,
            target_y,
            self,
            shot_distance,
        )
        self.ai_shot_target = None
        return True

    def try_dash_hit(self, opponent, ball):
        """DJH 冲刺期间撞到对手时产生击退和掉球效果。"""
        if self.ability_type != "dash" or not self.is_dashing:
            return
        if self.dash_hit_registered or self.dash_hit_cooldown_timer > 0:
            return
        if opponent is None or not self.rect().colliderect(opponent.rect()):
            return

        direction = 1 if self.facing_right else -1
        opponent.vx = DASH_HIT_KNOCKBACK * direction
        opponent.vy = DASH_HIT_VERTICAL
        opponent.on_ground = False

        if ball.state == "held" and ball.holder is opponent:
            ball.state = "loose"
            ball.holder = None
            ball.x, ball.y = opponent.center()
            ball.vx = DASH_HIT_KNOCKBACK * direction * 0.75
            ball.vy = -6

        self.dash_hit_registered = True
        self.dash_hit_cooldown_timer = DASH_HIT_COOLDOWN_FRAMES
        hit_x, hit_y = opponent.center()


    def try_block_ball(self, ball):
        """空中手部碰到对手投出的球时完成盖帽。

        使用篮球上一帧到当前帧的线段做判定，降低高速投篮穿过手部却未触发的问题。
        """
        if self.on_ground or self.block_cooldown_timer > 0:
            return False
        if ball.state != "flying" or ball.last_shooter is self:
            return False

        hand_x = self.x + PLAYER_WIDTH / 2 + (BLOCK_REACH_X if self.facing_right else -BLOCK_REACH_X)
        hand_y = self.y + BLOCK_REACH_Y

        seg_x = ball.x - ball.previous_x
        seg_y = ball.y - ball.previous_y
        seg_len_sq = seg_x * seg_x + seg_y * seg_y
        if seg_len_sq > 0:
            t = ((hand_x - ball.previous_x) * seg_x + (hand_y - ball.previous_y) * seg_y) / seg_len_sq
            t = max(0.0, min(1.0, t))
            closest_x = ball.previous_x + seg_x * t
            closest_y = ball.previous_y + seg_y * t
        else:
            closest_x, closest_y = ball.x, ball.y

        dx = closest_x - hand_x
        dy = closest_y - hand_y
        block_radius = ball.radius + 18
        if dx * dx + dy * dy > block_radius * block_radius:
            return False

        # 把球朝防守者面对方向拍开，并取消本次投篮的得分归属。
        direction = 1 if self.facing_right else -1
        ball.state = "loose"
        ball.holder = None
        ball.last_shooter = None
        ball.shot_distance = 0
        ball.rebound_available = True
        ball.x = hand_x + direction * (ball.radius + 5)
        ball.y = hand_y
        ball.previous_x = ball.x
        ball.previous_y = ball.y
        ball.vx = direction * BLOCK_HORIZONTAL_FORCE + self.vx * 0.35
        ball.vy = BLOCK_VERTICAL_FORCE + min(0.0, self.vy * 0.2)

        self.block_cooldown_timer = BLOCK_COOLDOWN_FRAMES
        self.blocks += 1
        self.events.append(("block", ball.x, ball.y))
        return True


    def rebound_hand_position(self):
        """返回抢篮板时的手部位置。"""
        direction = 1 if self.facing_right else -1
        return (
            self.x + PLAYER_WIDTH / 2 + direction * REBOUND_REACH_X,
            self.y + REBOUND_REACH_Y,
        )

    def rebound_candidate_score(self, ball, opponent=None):
        """返回篮板竞争分数；None 表示当前无法抢到。"""
        if self.on_ground or self.rebound_cooldown_timer > 0:
            return None
        if ball.holder is not None or not getattr(ball, "rebound_available", False):
            return None
        if ball.state not in ("flying", "loose"):
            return None

        hand_x, hand_y = self.rebound_hand_position()
        dx = ball.x - hand_x
        dy = ball.y - hand_y
        distance = (dx * dx + dy * dy) ** 0.5
        catch_range = REBOUND_CATCH_RADIUS + ball.radius
        if distance > catch_range:
            return None

        # 距离越近优先级越高。站在篮筐与对手之间时获得轻微卡位优势。
        score = catch_range - distance
        if opponent is not None:
            rim_x = self.arena["rim_x"]
            my_cx, _ = self.center()
            opp_cx, _ = opponent.center()
            between = min(rim_x, opp_cx) <= my_cx <= max(rim_x, opp_cx)
            close_enough = abs(my_cx - opp_cx) <= BOX_OUT_RANGE
            if between and close_enough:
                score += BOX_OUT_PRIORITY_BONUS
        return score

    def secure_rebound(self, ball):
        """抓下篮板并获得短暂无敌时间。"""
        if ball.holder is not None:
            return False
        ball.attach_to(self)
        self.possession_immune_timer = REBOUND_POSSESSION_IMMUNITY
        self.rebound_cooldown_timer = REBOUND_COOLDOWN_FRAMES
        self.rebounds += 1
        hand_x, hand_y = self.rebound_hand_position()
        self.events.append(("rebound", hand_x, hand_y))
        return True

    def consume_events(self):
        events = self.events[:]
        self.events.clear()
        return events

    def try_pick_up(self, ball, requested=False, force=False):
        """兼容接口：真人需 requested=True，AI可 force=True。"""
        if not (requested or force):
            return False
        before = ball.holder
        self._apply_steal_or_pickup(True, ball)
        return before is not self and ball.holder is self

    def update_animation(self):
        if not self.on_ground:
            new_state = "jump"
        elif self.vx != 0:
            new_state = "run"
        else:
            new_state = "idle"

        if new_state != self.anim_state:
            self.anim_state = new_state
            self.anim_frame_index = 0
            self.anim_timer = 0

        self.anim_timer += 1
        if self.anim_timer >= ANIMATION_SPEED:
            self.anim_timer = 0
            if self.animations:
                frames = self.animations.get(self.anim_state) or self.animations["idle"]
                self.anim_frame_index = (self.anim_frame_index + 1) % len(frames)
            else:
                self.anim_frame_index += 1

    def update_physics(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.y + PLAYER_HEIGHT >= self.arena["ground_y"]:
            self.y = self.arena["ground_y"] - PLAYER_HEIGHT
            self.vy = 0
            self.on_ground = True
            if self.ability_type == "double_jump":
                self.double_jump_available = False
        else:
            self.on_ground = False

        self.x = max(0, min(SCREEN_WIDTH - PLAYER_WIDTH, self.x))

        if self.possession_immune_timer > 0:
            self.possession_immune_timer -= 1
        if self.steal_cooldown_timer > 0:
            self.steal_cooldown_timer -= 1
        if self.ability_cooldown_timer > 0:
            self.ability_cooldown_timer -= 1
        if self.slam_effect_timer > 0:
            self.slam_effect_timer -= 1
        if self.dash_hit_cooldown_timer > 0:
            self.dash_hit_cooldown_timer -= 1
        if self.block_cooldown_timer > 0:
            self.block_cooldown_timer -= 1
        if self.rebound_cooldown_timer > 0:
            self.rebound_cooldown_timer -= 1

        self.update_animation()

    def reset_for_round(self, x):
        self.x = x
        self.y = self.arena["ground_y"] - PLAYER_HEIGHT
        self.vx = 0
        self.vy = 0
        self.facing_right = False
        self.on_ground = True
        self.possession_immune_timer = 0
        self.steal_cooldown_timer = 0
        self.ability_cooldown_timer = 0
        self.is_dashing = False
        self.dash_timer = 0
        self.dash_hit_registered = False
        self.dash_hit_cooldown_timer = 0
        self.block_cooldown_timer = 0
        self.rebound_cooldown_timer = 0
        self.slam_effect_timer = 0
        self.double_jump_available = False
        self.is_charging_shot = False
        self.shot_charge = 0.0
        self.ai_shot_target = None

    def draw(self, screen, font):
        rect = self.rect()

        if self.animations:
            frames = self.animations.get(self.anim_state) or self.animations["idle"]
            frame_img = frames[self.anim_frame_index % len(frames)]
            frame_img = pygame.transform.scale(frame_img, (PLAYER_WIDTH, PLAYER_HEIGHT))
            if not self.facing_right:
                frame_img = pygame.transform.flip(frame_img, True, False)
            screen.blit(frame_img, rect)
        else:
            draw_procedural_character(
                screen,
                rect,
                self.color,
                self.anim_state,
                self.anim_frame_index,
                self.facing_right,
            )

        if self.is_dashing:
            pygame.draw.rect(screen, COLOR_DASH_TRAIL, rect, width=3, border_radius=6)

        if self.slam_effect_timer > 0:
            progress = 1 - self.slam_effect_timer / 20
            effect_radius = max(10, int(self.slam_range * progress))
            pygame.draw.circle(
                screen,
                (255, 180, 80),
                (int(self.x + PLAYER_WIDTH / 2), int(self.arena["ground_y"] - 4)),
                effect_radius,
                width=4,
            )

        bar_w = PLAYER_WIDTH
        pygame.draw.rect(screen, (80, 80, 80), (rect.x, rect.y - 10, bar_w, 4))

        if self.ability_type == "double_jump":
            ratio = 1 if (self.on_ground or self.double_jump_available) else 0
        elif self.ability_cooldown_max > 0:
            ratio = 1 - self.ability_cooldown_timer / self.ability_cooldown_max
        else:
            ratio = 1

        ratio = max(0, min(1, ratio))
        pygame.draw.rect(screen, (90, 220, 90), (rect.x, rect.y - 10, bar_w * ratio, 4))

        if self.is_charging_shot:
            meter_x = rect.centerx - SHOT_METER_WIDTH // 2
            meter_y = rect.y - 19
            pygame.draw.rect(
                screen,
                SHOT_METER_BG_COLOR,
                (meter_x, meter_y, SHOT_METER_WIDTH, SHOT_METER_HEIGHT),
                border_radius=3,
            )

            perfect_x = meter_x + int(SHOT_METER_WIDTH * self.shot_perfect_min)
            perfect_w = max(
                2,
                int(SHOT_METER_WIDTH * (self.shot_perfect_max - self.shot_perfect_min)),
            )
            pygame.draw.rect(
                screen,
                SHOT_METER_PERFECT_COLOR,
                (perfect_x, meter_y, perfect_w, SHOT_METER_HEIGHT),
                border_radius=2,
            )

            charge_ratio = max(0.0, min(1.0, self.shot_charge / self.shot_charge_max))
            marker_x = meter_x + int(SHOT_METER_WIDTH * charge_ratio)
            pygame.draw.line(
                screen,
                SHOT_METER_COLOR,
                (marker_x, meter_y - 2),
                (marker_x, meter_y + SHOT_METER_HEIGHT + 2),
                3,
            )

        label = font.render(self.name, True, (255, 255, 255))
        screen.blit(label, (rect.x, rect.y - 30))
