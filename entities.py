"""
核心实体：Player(玩家角色) 和 Ball(篮球)，包含移动、物理、投篮、
抢断、冲刺技能等逻辑。

美术说明:
    角色支持两种绘制方式，自动二选一：
    1. 如果 assets/<角色名>/ 下放了 idle.png / run.png / jump.png 贴图，
       就播放真正的雪碧图动画(具体规范见 animation.py 顶部注释)。
    2. 如果还没放贴图，自动用程序化绘制的简笔小人代替，保证角色至少
       "能跑能跳"，不会因为没有美术资源就卡在一坨方块上。
    以后贴图准备好了直接放进对应文件夹，代码不用改。

单人模式说明:
    Player 既可以由真人键盘输入驱动(handle_input)，也可以由简单的
    规则AI驱动(handle_ai)。两者最终都是调用同一批 _apply_xxx 辅助方法
    (冲刺/移动/跳跃/投篮/抢断)，保证人类玩家和AI遵守完全相同的规则、
    冷却时间和判定逻辑，只是"决策来源"不同。
"""

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
    PLAYER1_SPAWN_X, PLAYER2_SPAWN_X,
)
from animation import load_character_animations, draw_procedural_character, load_ball_frames


class Ball:
    """
    篮球有三种状态：
        'held'   - 被某个玩家持有
        'loose'  - 在地上自由弹跳，可被捡起
        'flying' - 投篮后飞行中
    """

    def __init__(self, x, y, sprite_path=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = BALL_RADIUS
        self.state = "loose"
        self.holder = None          # 当前持球玩家(Player 或 None)
        self.last_shooter = None    # 最近一次投篮的玩家，用于计分
        self.shot_distance = 0      # 出手时投篮者离篮筐的距离，用于判定1分还是2分

        # ---- 贴图 ----
        # 3帧：手里(held) / 空中(flying) / 地面(loose)，直接按 self.state 选帧，
        # 不需要额外的动画计时器。找不到贴图就回退成程序化画的圆形球。
        self.frames = load_ball_frames(sprite_path, BALL_SPRITE_FRAME_COUNT)

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def attach_to(self, player):
        """球被某玩家控制。"""
        self.state = "held"
        self.holder = player
        self.vx = 0
        self.vy = 0

    def shoot_towards(self, target_x, target_y, shooter, shot_distance=0):
        """
        投篮：根据目标位置反推一个抛物线初速度。
        shot_distance 是出手瞬间投篮者离篮筐的直线距离，
        用于后续判定这一球算1分还是2分。
        """
        self.state = "flying"
        self.holder = None
        self.last_shooter = shooter
        self.shot_distance = shot_distance
        frames = SHOT_FLIGHT_FRAMES
        self.vx = (target_x - self.x) / frames
        # 抛物线公式反推初始垂直速度
        self.vy = (target_y - self.y - 0.5 * GRAVITY * frames ** 2) / frames

    def update(self):
        if self.state == "held" and self.holder is not None:
            # 跟随持球者手部位置
            offset = 26 if self.holder.facing_right else -26
            self.x = self.holder.x + PLAYER_WIDTH / 2 + offset
            self.y = self.holder.y + PLAYER_HEIGHT * 0.4
            return

        # 自由物理：flying 或 loose 都受重力影响
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        # 边界反弹
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -BALL_BOUNCE_DAMPING
        if self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -BALL_BOUNCE_DAMPING

        # 落地 -> 变成自由球
        if self.y + self.radius > GROUND_Y:
            self.y = GROUND_Y - self.radius
            self.vy *= -BALL_BOUNCE_DAMPING
            self.vx *= 0.85
            if abs(self.vy) < 2:
                self.state = "loose"

    def check_score(self):
        """
        检查是否投中篮筐(球在下落过程中经过篮筐区域)。
        返回 (得分玩家, 分值)，没进球则返回 (None, 0)。
        计分规则(本游戏自定义)：出手点在三分线外算2分，
        压线或三分线内算1分。
        """
        if self.state != "flying" or self.vy <= 0:
            return None, 0
        hoop_rect = pygame.Rect(HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT)
        if hoop_rect.collidepoint(self.x, self.y):
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
            return scorer, points
        return None, 0

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
    玩家角色。所有角色共享同一套基础操作，不同角色的差异以后
    通过技能参数/贴图来体现。

    ai_controlled=True 时，这个角色由 handle_ai() 驱动而不是 handle_input()，
    用于单人模式里的AI对手。
    """

    def __init__(self, x, y, color, controls, facing_right=True, name="P1",
                 sprite_folder=None, frame_counts=None, ai_controlled=False):
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

        self.possession_immune_timer = 0  # 拿到球后的短暂保护
        self.steal_cooldown_timer = 0

        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown_timer = 0

        # ---- AI ----
        self.ai_controlled = ai_controlled
        self.ai_shot_target = None  # AI本次持球选定的投篮点(x坐标)，出手/丢球后重置为None

        # 下面这几个是"能力参数"，默认等于普通难度(跟原本的全局常量数值一致)。
        # 真人玩家不会用到 apply_ai_difficulty，所以这几个值对真人玩家没有任何影响；
        # 调用 apply_ai_difficulty 后只会覆盖这一个AI实例自己的数值，
        # 不会碰到 constants.py 里的全局常量，因此不会影响真人玩家的手感。
        normal_preset = AI_DIFFICULTY_PRESETS["normal"]
        self.move_speed = MOVE_SPEED
        self.dash_speed = DASH_SPEED
        self.dash_cooldown_max = DASH_COOLDOWN_FRAMES
        self.steal_range = STEAL_RANGE
        self.ai_shot_miss_chance = normal_preset["shot_miss_chance"]
        self.ai_dash_trigger_chance = normal_preset["dash_trigger_chance"]
        self.ai_three_point_shot_chance = normal_preset["three_point_shot_chance"]

        # ---- 动画 ----
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

    def apply_ai_difficulty(self, difficulty):
        """
        应用AI难度预设("easy" / "normal" / "hard")，调整这个AI实例的
        移动速度、冲刺速度/冷却、抢断判定范围、投篮miss率、选三分概率。
        只修改这一个 Player 实例自己的属性，不动全局常量，
        所以不会影响真人玩家(比如玩家1)的手感。
        """
        preset = AI_DIFFICULTY_PRESETS.get(difficulty, AI_DIFFICULTY_PRESETS["normal"])
        self.move_speed = MOVE_SPEED * preset["move_speed_multiplier"]
        self.dash_speed = DASH_SPEED * preset["dash_speed_multiplier"]
        self.dash_cooldown_max = max(1, int(DASH_COOLDOWN_FRAMES * preset["dash_cooldown_multiplier"]))
        self.steal_range = STEAL_RANGE * preset["steal_range_multiplier"]
        self.ai_shot_miss_chance = preset["shot_miss_chance"]
        self.ai_dash_trigger_chance = preset["dash_trigger_chance"]
        self.ai_three_point_shot_chance = preset["three_point_shot_chance"]

    # ---------------------------------------------------------------
    # 下面这几个 _apply_xxx 方法是"动作执行层"：不管是真人按键还是AI决策，
    # 最终都通过这几个方法真正生效，保证规则、冷却时间完全一致。
    # ---------------------------------------------------------------

    def _apply_horizontal_move(self, direction):
        """direction: -1(左) / 0(不动) / 1(右)。冲刺时忽略，避免打断冲刺方向。"""
        if self.is_dashing:
            return
        self.vx = 0
        if direction < 0:
            self.vx = -self.move_speed
            self.facing_right = False
        elif direction > 0:
            self.vx = self.move_speed
            self.facing_right = True

    def _apply_dash(self, want_dash):
        if want_dash and self.dash_cooldown_timer <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = DASH_DURATION_FRAMES
            self.dash_cooldown_timer = self.dash_cooldown_max

        if self.is_dashing:
            direction = 1 if self.facing_right else -1
            self.vx = self.dash_speed * direction
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False

    def _apply_jump(self, want_jump):
        if want_jump and self.on_ground:
            self.vy = JUMP_VELOCITY
            self.on_ground = False

    def _apply_shoot(self, want_shoot, ball):
        if want_shoot and ball.state == "held" and ball.holder is self:
            target_x = HOOP_X + HOOP_WIDTH / 2
            target_y = HOOP_Y + HOOP_HEIGHT / 2
            shooter_x, shooter_y = self.center()
            shot_distance = ((shooter_x - target_x) ** 2 + (shooter_y - target_y) ** 2) ** 0.5
            ball.shoot_towards(target_x, target_y, self, shot_distance)

    def _apply_steal(self, want_steal, ball):
        if want_steal and self.steal_cooldown_timer <= 0:
            if ball.state == "held" and ball.holder is not self:
                holder = ball.holder
                if holder.possession_immune_timer <= 0:
                    hx, hy = holder.center()
                    mx, my = self.center()
                    dist = ((hx - mx) ** 2 + (hy - my) ** 2) ** 0.5
                    if dist < self.steal_range:
                        ball.attach_to(self)
                        self.possession_immune_timer = POSSESSION_COOLDOWN_FRAMES
                        self.steal_cooldown_timer = STEAL_COOLDOWN_FRAMES

    # ---------------------------------------------------------------
    # 真人输入
    # ---------------------------------------------------------------

    def handle_input(self, keys, ball):
        c = self.controls

        self._apply_dash(keys[c["dash"]])

        direction = 0
        if keys[c["left"]]:
            direction = -1
        if keys[c["right"]]:
            direction = 1
        self._apply_horizontal_move(direction)

        self._apply_jump(keys[c["jump"]])
        self._apply_shoot(keys[c["action"]], ball)
        self._apply_steal(keys[c["steal"]], ball)

    # ---------------------------------------------------------------
    # 简单规则AI(单人模式对手)
    # ---------------------------------------------------------------

    def handle_ai(self, ball, opponent):
        """
        一个轻量级的规则AI，行为逻辑：
        - 自己持球：走到一个选定的投篮点(大概率两分区，小概率三分线外)，
          到位后投篮；为了不让AI百发百中，出手时按概率加一点偏移制造miss。
        - 对手持球：追上去尝试抢断。
        - 球是自由球/飞行中：跑向球落点，球在头顶附近时起跳争抢篮板。
        - 追人/追球过程中，冲刺技能有冷却限制的小概率触发，增加变化。
        """
        my_cx, my_cy = self.center()
        direction = 0
        want_jump = False
        want_shoot = False
        want_steal = False
        want_dash = False

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
                want_dash = random.random() < self.ai_dash_trigger_chance
            else:
                want_shoot = True

        elif ball.state == "held" and ball.holder is opponent:
            self.ai_shot_target = None
            ox, oy = opponent.center()
            if abs(my_cx - ox) > AI_STEAL_APPROACH_DISTANCE:
                direction = 1 if ox > my_cx else -1
                want_dash = random.random() < self.ai_dash_trigger_chance
            want_steal = True

        else:
            self.ai_shot_target = None
            if abs(my_cx - ball.x) > 10:
                direction = 1 if ball.x > my_cx else -1
                want_dash = random.random() < self.ai_dash_trigger_chance
            if ball.y < my_cy - 20 and abs(my_cx - ball.x) < AI_REBOUND_JUMP_RANGE:
                want_jump = True

        self._apply_dash(want_dash)
        self._apply_horizontal_move(direction)
        self._apply_jump(want_jump)
        self._apply_steal(want_steal, ball)

        if want_shoot:
            self._apply_shoot_with_ai_accuracy(ball)

    def _apply_shoot_with_ai_accuracy(self, ball):
        """
        AI专用投篮。

        投篮偏移只影响篮球飞行目标，不影响1分/2分判定。
        计分距离始终按照出手者与真实篮筐中心之间的距离计算。
        """
        if ball.state != "held" or ball.holder is not self:
            return

        # 真实篮筐中心
        hoop_center_x = HOOP_X + HOOP_WIDTH / 2
        hoop_center_y = HOOP_Y + HOOP_HEIGHT / 2

        # 飞行目标默认瞄准篮筐中心
        target_x = hoop_center_x
        target_y = hoop_center_y

        # 根据AI难度制造投篮偏移
        if random.random() < self.ai_shot_miss_chance:
            target_x += random.uniform(
                -AI_SHOT_MISS_OFFSET,
                AI_SHOT_MISS_OFFSET,
            )
            target_y += random.uniform(
                -AI_SHOT_MISS_OFFSET,
                AI_SHOT_MISS_OFFSET,
            )

        shooter_x, shooter_y = self.center()

        # 必须按照真实篮筐位置计算出手距离
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

    def try_pick_up(self, ball):
        """走到松散的球上方即可捡起。"""
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

        # 地面碰撞
        if self.y + PLAYER_HEIGHT >= GROUND_Y:
            self.y = GROUND_Y - PLAYER_HEIGHT
            self.vy = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # 边界限制
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

        # 冲刺时画一点拖影表示技能生效
        if self.is_dashing:
            pygame.draw.rect(screen, COLOR_DASH_TRAIL, rect, width=3, border_radius=6)

        # 冲刺冷却进度条(头顶小条)
        bar_w = PLAYER_WIDTH
        cooldown_ratio = 1 - (self.dash_cooldown_timer / self.dash_cooldown_max)
        pygame.draw.rect(screen, (80, 80, 80), (rect.x, rect.y - 10, bar_w, 4))
        pygame.draw.rect(screen, (90, 220, 90), (rect.x, rect.y - 10, bar_w * cooldown_ratio, 4))

        label = font.render(self.name, True, (255, 255, 255))
        screen.blit(label, (rect.x, rect.y - 26))