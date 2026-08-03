"""
核心实体：Player（玩家角色）与 Ball（篮球）
Core entities: Player and Ball, including movement, physics, shooting,
stealing, and the dash skill.

美术说明 / Art note:
    角色现在支持两种绘制方式，自动二选一：
    1. 如果 assets/<角色名>/ 下放了 idle.png / run.png / jump.png 贴图，
       就播放真正的雪碧图动画(具体规范见 animation.py 顶部注释)。
    2. 如果还没放贴图，自动用程序化绘制的简笔小人代替，
       保证角色至少"能跑能跳"，不会因为没有美术资源就卡在一坨方块上。
    以后贴图准备好了直接放进对应文件夹，代码不用改。
"""

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
)
from animation import load_character_animations, draw_procedural_character, load_ball_frames


class Ball:
    """
    篮球对象，有三种状态 / The ball has three states:
        'held'   - 被某个玩家持有 / carried by a player
        'loose'  - 在地上自由弹跳，可被捡起 / bouncing freely, can be picked up
        'flying' - 投篮后飞行中 / in the air after a shot
    """

    def __init__(self, x, y, sprite_path=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = BALL_RADIUS
        self.state = "loose"
        self.holder = None          # 当前持球玩家 / current holder (Player or None)
        self.last_shooter = None    # 最近一次投篮的玩家，用于计分 / who took the last shot

        # ---- 贴图 / Sprite ----
        # 3帧：手里(held) / 空中(flying) / 地面(loose)，直接按 self.state 选帧，
        # 不需要额外的动画计时器。找不到贴图就回退成程序化画的圆形球。
        self.frames = load_ball_frames(sprite_path, BALL_SPRITE_FRAME_COUNT)

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def attach_to(self, player):
        """球被某玩家控制 / ball becomes held by a player."""
        self.state = "held"
        self.holder = player
        self.vx = 0
        self.vy = 0

    def shoot_towards(self, target_x, target_y, shooter):
        """
        投篮：根据目标位置反推一个抛物线初速度。
        Shoot: back-solve an initial velocity for a parabolic arc toward the target.
        """
        self.state = "flying"
        self.holder = None
        self.last_shooter = shooter
        frames = SHOT_FLIGHT_FRAMES
        self.vx = (target_x - self.x) / frames
        # 抛物线公式反推初始垂直速度 / solve initial vertical velocity for the arc
        self.vy = (target_y - self.y - 0.5 * GRAVITY * frames ** 2) / frames

    def update(self):
        if self.state == "held" and self.holder is not None:
            # 跟随持球者手部位置 / follow the holder's hand position
            offset = 26 if self.holder.facing_right else -26
            self.x = self.holder.x + PLAYER_WIDTH / 2 + offset
            self.y = self.holder.y + PLAYER_HEIGHT * 0.4
            return

        # 自由物理：flying 或 loose 都受重力影响 / free physics under gravity
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        # 边界反弹 / bounce off left/right walls
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -BALL_BOUNCE_DAMPING
        if self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -BALL_BOUNCE_DAMPING

        # 落地 / hits the ground -> becomes a loose ball
        if self.y + self.radius > GROUND_Y:
            self.y = GROUND_Y - self.radius
            self.vy *= -BALL_BOUNCE_DAMPING
            self.vx *= 0.85
            if abs(self.vy) < 2:
                self.state = "loose"

    def check_score(self):
        """
        检查是否投中篮筐（球在下落过程中经过篮筐区域）。
        Check whether the ball scores (passes through the hoop while descending).
        返回得分玩家或 None / returns the scoring player, or None.
        """
        if self.state != "flying" or self.vy <= 0:
            return None
        hoop_rect = pygame.Rect(HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT)
        if hoop_rect.collidepoint(self.x, self.y):
            scorer = self.last_shooter
            self.state = "loose"
            self.vx = 0
            self.vy = 0
            self.x = BALL_SPAWN_X
            self.y = GROUND_Y - 200
            return scorer
        return None

    def draw(self, screen):
        if self.frames:
            frame_index = BALL_STATE_TO_FRAME.get(self.state, 0)
            frame_img = self.frames[frame_index % len(self.frames)]
            frame_img = pygame.transform.scale(frame_img, (self.radius * 2, self.radius * 2))
            rect = frame_img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(frame_img, rect)
        else:
            pygame.draw.circle(screen, COLOR_BALL, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 1)


class Player:
    """
    玩家角色。所有角色共享同一套基础操作，
    不同角色的差异以后通过技能参数/贴图来体现。
    All players share the same base moveset; character differences
    should later come from skill parameters and sprite art.
    """

    def __init__(self, x, y, color, controls, facing_right=True, name="P1",
                 sprite_folder=None, frame_counts=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.color = color
        self.controls = controls  # dict: left/right/jump/action/steal/dash
        self.facing_right = facing_right
        self.name = name
        self.on_ground = False
        self.score = 0

        self.possession_immune_timer = 0  # 拿到球后的短暂保护 / brief protection after gaining ball
        self.steal_cooldown_timer = 0

        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown_timer = 0

        # ---- 动画 / Animation ----
        # sprite_folder 指向 assets/<角色名>/ ；找不到贴图会自动返回 None，
        # 上层 draw() 会据此自动切换成程序化动画兜底。
        self.frame_counts = frame_counts or DEFAULT_FRAME_COUNTS
        self.animations = load_character_animations(sprite_folder, self.frame_counts)
        self.anim_state = "idle"
        self.anim_frame_index = 0
        self.anim_timer = 0

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), PLAYER_WIDTH, PLAYER_HEIGHT)

    def center(self):
        return self.x + PLAYER_WIDTH / 2, self.y + PLAYER_HEIGHT / 2

    def handle_input(self, keys, ball):
        c = self.controls

        # ---- 冲刺技能 / Dash skill ----
        if keys[c["dash"]] and self.dash_cooldown_timer <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = DASH_DURATION_FRAMES
            self.dash_cooldown_timer = DASH_COOLDOWN_FRAMES

        if self.is_dashing:
            direction = 1 if self.facing_right else -1
            self.vx = DASH_SPEED * direction
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            # ---- 左右移动 / left-right movement ----
            self.vx = 0
            if keys[c["left"]]:
                self.vx = -MOVE_SPEED
                self.facing_right = False
            if keys[c["right"]]:
                self.vx = MOVE_SPEED
                self.facing_right = True

        # ---- 跳跃 / jump ----
        if keys[c["jump"]] and self.on_ground:
            self.vy = JUMP_VELOCITY
            self.on_ground = False

        # ---- 投篮 / shoot (只有持球时才有效 / only works while holding the ball) ----
        if keys[c["action"]] and ball.state == "held" and ball.holder is self:
            target_x = HOOP_X + HOOP_WIDTH / 2
            target_y = HOOP_Y + HOOP_HEIGHT / 2
            ball.shoot_towards(target_x, target_y, self)

        # ---- 抢断 / steal ----
        if keys[c["steal"]] and self.steal_cooldown_timer <= 0:
            if ball.state == "held" and ball.holder is not self:
                holder = ball.holder
                if holder.possession_immune_timer <= 0:
                    hx, hy = holder.center()
                    mx, my = self.center()
                    dist = ((hx - mx) ** 2 + (hy - my) ** 2) ** 0.5
                    if dist < STEAL_RANGE:
                        ball.attach_to(self)
                        self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES
                        self.steal_cooldown_timer = STEAL_COOLDOWN_FRAMES

    def try_pick_up(self, ball):
        """走到松散的球上方即可捡起 / walking over a loose ball picks it up."""
        if ball.state == "loose" and self.rect().colliderect(ball.rect()):
            ball.attach_to(self)
            self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES

    def update_animation(self):
        """
        根据当前物理状态(在不在地上、有没有横向速度)判断该播放
        idle / run / jump 哪一套动画，并按固定间隔推进到下一帧。
        """
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
                # 程序化动画不需要严格循环，持续递增当相位用即可
                self.anim_frame_index += 1

    def update_physics(self):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        # 地面碰撞 / ground collision
        if self.y + PLAYER_HEIGHT >= GROUND_Y:
            self.y = GROUND_Y - PLAYER_HEIGHT
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # 边界限制 / keep inside screen bounds
        self.x = max(0, min(SCREEN_WIDTH - PLAYER_WIDTH, self.x))

        if self.possession_immune_timer > 0:
            self.possession_immune_timer -= 1
        if self.steal_cooldown_timer > 0:
            self.steal_cooldown_timer -= 1
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1

        self.update_animation()

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
                screen, rect, self.color, self.anim_state,
                self.anim_frame_index, self.facing_right,
            )

        # 冲刺时画一点拖影表示技能生效 / a simple trail while dashing
        if self.is_dashing:
            pygame.draw.rect(screen, COLOR_DASH_TRAIL, rect, width=3, border_radius=6)

        # 冲刺冷却进度条（头顶小条）/ dash cooldown bar above the head
        bar_w = PLAYER_WIDTH
        cooldown_ratio = 1 - (self.dash_cooldown_timer / DASH_COOLDOWN_FRAMES)
        pygame.draw.rect(screen, (80, 80, 80), (rect.x, rect.y - 10, bar_w, 4))
        pygame.draw.rect(screen, (90, 220, 90), (rect.x, rect.y - 10, bar_w * cooldown_ratio, 4))

        label = font.render(self.name, True, (255, 255, 255))
        screen.blit(label, (rect.x, rect.y - 26))