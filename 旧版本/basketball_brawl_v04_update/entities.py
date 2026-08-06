"""核心实体：Player 和 Ball。"""

import random
import pygame

from constants import (
    GRAVITY, JUMP_VELOCITY, MOVE_SPEED, GROUND_Y,
    PLAYER_WIDTH, PLAYER_HEIGHT, STEAL_RANGE,
    POSSESSION_COOLDOWN_FRAMES, STEAL_COOLDOWN_FRAMES,
    DASH_SPEED, DASH_DURATION_FRAMES, DASH_COOLDOWN_FRAMES,
    BALL_RADIUS, BALL_BOUNCE_DAMPING, SCREEN_WIDTH,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT, SHOT_FLIGHT_FRAMES,
    COLOR_BALL, COLOR_DASH_TRAIL,
    ANIMATION_SPEED, DEFAULT_FRAME_COUNTS, BALL_SPAWN_X,
    BALL_SPRITE_FRAME_COUNT, BALL_STATE_TO_FRAME,
    THREE_POINT_RADIUS, POINTS_OUTSIDE_THREE, POINTS_ON_OR_INSIDE_THREE,
    AI_SHOOT_STOP_DISTANCE, AI_TWO_POINT_SHOOT_OFFSET, AI_THREE_POINT_SHOOT_MARGIN,
    AI_SHOT_MISS_OFFSET, AI_STEAL_APPROACH_DISTANCE, AI_REBOUND_JUMP_RANGE,
    AI_DIFFICULTY_PRESETS,
)
from animation import load_character_animations, draw_procedural_character, load_ball_frames


class Ball:
    def __init__(self, x, y, sprite_path=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = BALL_RADIUS
        self.state = "loose"
        self.holder = None
        self.last_shooter = None
        self.shot_distance = 0
        self.frames = load_ball_frames(sprite_path, BALL_SPRITE_FRAME_COUNT)

    def rect(self):
        return pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            self.radius * 2,
            self.radius * 2,
        )

    def attach_to(self, player):
        self.state = "held"
        self.holder = player
        self.vx = 0
        self.vy = 0

    def shoot_towards(self, target_x, target_y, shooter, shot_distance=0):
        self.state = "flying"
        self.holder = None
        self.last_shooter = shooter
        self.shot_distance = shot_distance
        frames = SHOT_FLIGHT_FRAMES
        self.vx = (target_x - self.x) / frames
        self.vy = (target_y - self.y - 0.5 * GRAVITY * frames ** 2) / frames

    def update(self):
        if self.state == "held" and self.holder is not None:
            offset = 26 if self.holder.facing_right else -26
            self.x = self.holder.x + PLAYER_WIDTH / 2 + offset
            self.y = self.holder.y + PLAYER_HEIGHT * 0.4
            return

        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -BALL_BOUNCE_DAMPING
        if self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -BALL_BOUNCE_DAMPING

        if self.y + self.radius > GROUND_Y:
            self.y = GROUND_Y - self.radius
            self.vy *= -BALL_BOUNCE_DAMPING
            self.vx *= 0.85
            if abs(self.vy) < 2:
                self.state = "loose"

    def check_score(self):
        if self.state != "flying" or self.vy <= 0:
            return None, 0

        hoop_rect = pygame.Rect(HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT)
        if not hoop_rect.collidepoint(self.x, self.y):
            return None, 0

        scorer = self.last_shooter
        points = (
            POINTS_OUTSIDE_THREE
            if self.shot_distance > THREE_POINT_RADIUS
            else POINTS_ON_OR_INSIDE_THREE
        )
        self.state = "loose"
        self.vx = 0
        self.vy = 0
        self.x = BALL_SPAWN_X
        self.y = GROUND_Y - 200
        self.holder = None
        return scorer, points

    def draw(self, screen):
        if self.frames:
            frame_index = BALL_STATE_TO_FRAME.get(self.state, 0)
            frame_img = self.frames[frame_index % len(self.frames)]
            frame_img = pygame.transform.scale(frame_img, (self.radius * 2, self.radius * 2))
            screen.blit(frame_img, frame_img.get_rect(center=(int(self.x), int(self.y))))
        else:
            pygame.draw.circle(screen, COLOR_BALL, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 1)


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

    def _apply_shoot(self, want_shoot, ball):
        if want_shoot and ball.state == "held" and ball.holder is self:
            target_x = HOOP_X + HOOP_WIDTH / 2
            target_y = HOOP_Y + HOOP_HEIGHT / 2
            shooter_x, shooter_y = self.center()
            shot_distance = (
                (shooter_x - target_x) ** 2 + (shooter_y - target_y) ** 2
            ) ** 0.5
            ball.shoot_towards(target_x, target_y, self, shot_distance)

    def _apply_steal(self, want_steal, ball):
        if not want_steal or self.steal_cooldown_timer > 0:
            return
        if ball.state != "held" or ball.holder is self:
            return

        holder = ball.holder
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
        self.dash_timer = self.dash_duration_max
        self.ability_cooldown_timer = self.ability_cooldown_max

    def _update_dash(self):
        if not self.is_dashing:
            return
        direction = 1 if self.facing_right else -1
        self.vx = self.dash_speed * direction
        self.dash_timer -= 1
        if self.dash_timer <= 0:
            self.is_dashing = False

    def _use_ground_slam(self, opponent, ball):
        if self.ability_cooldown_timer > 0 or opponent is None:
            return

        self.ability_cooldown_timer = self.ability_cooldown_max
        self.slam_effect_timer = 20

        my_x, my_y = self.center()
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
        self._apply_shoot(keys[controls["action"]], ball)
        self._apply_steal(keys[controls["steal"]], ball)

    def handle_ai(self, ball, opponent):
        my_cx, my_cy = self.center()
        direction = 0
        want_jump = False
        want_shoot = False
        want_steal = False
        want_ability = False

        if ball.state == "held" and ball.holder is self:
            if self.ai_shot_target is None:
                hoop_cx = HOOP_X + HOOP_WIDTH / 2
                if random.random() < self.ai_three_point_shot_chance:
                    self.ai_shot_target = hoop_cx + THREE_POINT_RADIUS + AI_THREE_POINT_SHOOT_MARGIN
                else:
                    self.ai_shot_target = hoop_cx + AI_TWO_POINT_SHOOT_OFFSET

            distance_to_spot = self.ai_shot_target - my_cx
            if abs(distance_to_spot) > AI_SHOOT_STOP_DISTANCE:
                direction = 1 if distance_to_spot > 0 else -1
                if self.ability_type == "dash":
                    want_ability = random.random() < self.ai_ability_trigger_chance
            else:
                want_shoot = True

        elif ball.state == "held" and ball.holder is opponent:
            self.ai_shot_target = None
            opponent_x, _ = opponent.center()
            if abs(my_cx - opponent_x) > AI_STEAL_APPROACH_DISTANCE:
                direction = 1 if opponent_x > my_cx else -1
                if self.ability_type == "dash":
                    want_ability = random.random() < self.ai_ability_trigger_chance
            want_steal = True

        else:
            self.ai_shot_target = None
            if abs(my_cx - ball.x) > 10:
                direction = 1 if ball.x > my_cx else -1
                if self.ability_type == "dash":
                    want_ability = random.random() < self.ai_ability_trigger_chance
            if ball.y < my_cy - 20 and abs(my_cx - ball.x) < AI_REBOUND_JUMP_RANGE:
                want_jump = True

        if self.ability_type == "ground_slam":
            opponent_x, opponent_y = opponent.center()
            distance = ((opponent_x - my_cx) ** 2 + (opponent_y - my_cy) ** 2) ** 0.5
            want_ability = distance <= self.slam_range and random.random() < 0.08
        elif self.ability_type == "double_jump":
            want_ability = (
                not self.on_ground
                and self.double_jump_available
                and ball.y < my_cy
                and random.random() < 0.08
            )

        self._apply_horizontal_move(direction)
        self._apply_jump(want_jump)
        self._apply_ability(want_ability, opponent, ball)
        self._update_dash()
        self._apply_steal(want_steal, ball)

        if want_shoot:
            self._apply_shoot_with_ai_accuracy(ball)

    def _apply_shoot_with_ai_accuracy(self, ball):
        if ball.state != "held" or ball.holder is not self:
            return

        hoop_center_x = HOOP_X + HOOP_WIDTH / 2
        hoop_center_y = HOOP_Y + HOOP_HEIGHT / 2
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
        ball.shoot_towards(target_x, target_y, self, shot_distance)
        self.ai_shot_target = None

    def try_pick_up(self, ball):
        if ball.state == "loose" and self.rect().colliderect(ball.rect()):
            ball.attach_to(self)
            self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES

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

        if self.y + PLAYER_HEIGHT >= GROUND_Y:
            self.y = GROUND_Y - PLAYER_HEIGHT
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

        self.update_animation()

    def reset_for_round(self, x):
        self.x = x
        self.y = GROUND_Y - PLAYER_HEIGHT
        self.vx = 0
        self.vy = 0
        self.facing_right = False
        self.on_ground = True
        self.possession_immune_timer = 0
        self.steal_cooldown_timer = 0
        self.ability_cooldown_timer = 0
        self.is_dashing = False
        self.dash_timer = 0
        self.slam_effect_timer = 0
        self.double_jump_available = False
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
                (int(self.x + PLAYER_WIDTH / 2), int(GROUND_Y - 4)),
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

        label = font.render(self.name, True, (255, 255, 255))
        screen.blit(label, (rect.x, rect.y - 26))
