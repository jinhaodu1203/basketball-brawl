"""篮球实体与篮筐碰撞逻辑。"""

import pygame

from constants import (
    GRAVITY, GROUND_Y, PLAYER_WIDTH, PLAYER_HEIGHT,
    BALL_RADIUS, BALL_BOUNCE_DAMPING, SCREEN_WIDTH,
    RIM_COLLISION_RADIUS, RIM_BOUNCE_DAMPING,
    BACKBOARD_BOUNCE_DAMPING, BACKBOARD_THICKNESS,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT, SHOT_FLIGHT_FRAMES,
    COLOR_BALL, BALL_SPAWN_X,
    BALL_SPRITE_FRAME_COUNT, BALL_STATE_TO_FRAME,
    THREE_POINT_RADIUS, POINTS_OUTSIDE_THREE, POINTS_ON_OR_INSIDE_THREE,
    DRIBBLE_SPEED_IDLE, DRIBBLE_SPEED_MOVING,
    DRIBBLE_HAND_OFFSET_X, DRIBBLE_HAND_OFFSET_Y,
    DRIBBLE_GROUND_CLEARANCE, DRIBBLE_MOVING_SWAY,
    PASS_MIN_FRAMES, PASS_MAX_FRAMES, PASS_PIXELS_PER_FRAME,
    PASS_CATCH_RADIUS, PASS_RECEIVE_IMMUNITY_FRAMES,
)
from animation import load_ball_frames


class Ball:
    def __init__(self, x, y, sprite_path=None, arena=None):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.previous_x = x
        self.previous_y = y
        self.radius = BALL_RADIUS
        self.state = "loose"
        self.holder = None
        self.last_shooter = None
        self.shot_distance = 0
        self.rebound_available = False

        # V3.6 打板上篮。
        self.bank_layup_active = False

        # 记录当前投篮的碰框次数。
        self.rim_contact_count = 0
        self.rim_sound_cooldown = 0

        # AI 篮板保护时间。
        # 球刚碰到篮圈/篮板时先让篮球自然颠动，
        # 避免 AI 在球还可能滚进篮筐时提前把球摘走。
        self.rebound_grace_timer = 0

        self.pending_score = None
        self.frames = load_ball_frames(sprite_path, BALL_SPRITE_FRAME_COUNT)
        self.events = []

        # 传球元数据。Duke 的分身会直接作为 pass_receiver 使用。
        self.pass_passer = None
        self.pass_receiver = None
        self.pass_catch_delay = 0

        # V2.0：持球时篮球不再固定粘在手上，而是在手和地面之间循环运球。
        self.dribble_phase = 0.0
        self.dribble_side = 1

        self.arena = arena or {
            "ground_y": GROUND_Y, "rim_x": HOOP_X + HOOP_WIDTH / 2,
            "rim_y": HOOP_Y + HOOP_HEIGHT / 2, "hoop_width": HOOP_WIDTH,
            "hoop_height": HOOP_HEIGHT, "three_point_distance": THREE_POINT_RADIUS,
            "ball_spawn_x": BALL_SPAWN_X,
        }

    def rect(self):
        return pygame.Rect(
            self.x - self.radius,
            self.y - self.radius,
            self.radius * 2,
            self.radius * 2,
        )

    def clear_pass(self):
        self.pass_passer = None
        self.pass_receiver = None
        self.pass_catch_delay = 0

    def attach_to(self, player):
        self.rebound_available = False
        self.bank_layup_active = False
        self.rebound_grace_timer = 0
        self.clear_pass()
        self.state = "held"
        self.holder = player
        self.vx = 0
        self.vy = 0
        self.dribble_phase = 0.0
        self.dribble_side = 1 if player.facing_right else -1

    def pass_to(self, receiver, passer):
        """把球以真实抛物线传向接球队友。返回是否成功发起传球。"""
        if receiver is None or passer is None:
            return False
        if self.state != "held" or self.holder is not passer:
            return False

        target_x, target_y = receiver.center()
        dx = target_x - self.x
        dy = target_y - self.y
        distance = max(1.0, (dx * dx + dy * dy) ** 0.5)
        frames = int(round(distance / max(1, PASS_PIXELS_PER_FRAME)))
        frames = max(PASS_MIN_FRAMES, min(PASS_MAX_FRAMES, frames))

        self.rebound_available = False
        self.state = "passing"
        self.holder = None
        self.last_shooter = None
        self.shot_distance = 0
        self.pass_passer = passer
        self.pass_receiver = receiver
        self.pass_catch_delay = 4
        self.vx = dx / frames
        self.vy = (dy - 0.5 * GRAVITY * frames ** 2) / frames

        self.events.append(
            ("pass", self.x, self.y)
        )

        return True

    def shoot_towards(self, target_x, target_y, shooter, shot_distance=0):
        self.rebound_available = False
        self.bank_layup_active = False

        # 新投篮重新计算碰框次数。
        self.rim_contact_count = 0
        self.rim_sound_cooldown = 0
        self.rebound_grace_timer = 0
        self.clear_pass()
        self.state = "flying"
        self.holder = None
        self.last_shooter = shooter
        self.shot_distance = shot_distance

        # ---------- V3.5 投篮统计 ----------
        shooter.fg_attempts = getattr(shooter, "fg_attempts", 0) + 1
        if shot_distance > self.arena["three_point_distance"]:
            shooter.three_attempts = getattr(
                shooter,
                "three_attempts",
                0,
            ) + 1

        # 半场规则：
        # 防守篮板后必须先退出三分线。
        # 出手瞬间还没有完成 clear，则这一球即使进框也不计分。
        self.shot_score_allowed = not getattr(
            shooter,
            "must_clear_three",
            False,
        )

        frames = SHOT_FLIGHT_FRAMES
        self.vx = (target_x - self.x) / frames
        self.vy = (target_y - self.y - 0.5 * GRAVITY * frames ** 2) / frames

        self.events.append(
            ("shot", self.x, self.y)
        )

    def shoot_bank_layup(self, shooter, shot_distance=0):
        """让上篮球先命中篮板，再反弹向篮筐。"""
        self.rebound_available = False
        self.bank_layup_active = True

        self.rim_contact_count = 0
        self.rim_sound_cooldown = 0
        self.rebound_grace_timer = 0
        self.clear_pass()

        self.state = "flying"
        self.holder = None
        self.last_shooter = shooter
        self.shot_distance = shot_distance

        shooter.fg_attempts = getattr(
            shooter,
            "fg_attempts",
            0,
        ) + 1

        self.shot_score_allowed = not getattr(
            shooter,
            "must_clear_three",
            False,
        )

        rim_x = self.arena["rim_x"]
        rim_y = self.arena["rim_y"]
        backboard_x = self.arena.get(
            "backboard_x",
            rim_x - 48,
        )

        # 第一阶段：瞄准篮板上方甜点区。
        target_x = backboard_x + self.radius + 2
        target_y = rim_y - 24

        frames = 17

        self.vx = (target_x - self.x) / frames
        self.vy = (
            target_y
            - self.y
            - 0.5 * GRAVITY * frames ** 2
        ) / frames

        self.events.append(
            ("shot", self.x, self.y)
        )


    def _resolve_circle_collision(self, collider_x, collider_y, collider_radius):
        """让篮球与圆形篮筐边缘发生反弹。"""
        dx = self.x - collider_x
        dy = self.y - collider_y
        distance_sq = dx * dx + dy * dy
        minimum_distance = self.radius + collider_radius

        if distance_sq >= minimum_distance * minimum_distance:
            return False

        distance = max(0.001, distance_sq ** 0.5)
        normal_x = dx / distance
        normal_y = dy / distance

        # 把篮球推出碰撞体，防止连续卡住。
        overlap = minimum_distance - distance
        self.x += normal_x * overlap
        self.y += normal_y * overlap

        velocity_along_normal = self.vx * normal_x + self.vy * normal_y
        if velocity_along_normal >= 0:
            return False

        impulse = -(1 + RIM_BOUNCE_DAMPING) * velocity_along_normal
        self.vx += impulse * normal_x
        self.vy += impulse * normal_y
        return True

    def _handle_hoop_collisions(self):
        """处理篮板和篮圈两端的物理碰撞。"""
        rim_x = self.arena["rim_x"]
        rim_y = self.arena["rim_y"]
        hoop_half_width = self.arena["hoop_width"] / 2

        # 篮板是一条竖直的薄墙。
        backboard_x = self.arena.get("backboard_x", rim_x - 48)
        board_top = rim_y - 62
        board_bottom = rim_y + 28
        touching_board_height = (
            self.y + self.radius >= board_top
            and self.y - self.radius <= board_bottom
        )
        crossed_board = (
        self.x - self.radius <= backboard_x + BACKBOARD_THICKNESS / 2
        and self.previous_x - self.radius > backboard_x + BACKBOARD_THICKNESS / 2
        )
        if touching_board_height and crossed_board and self.vx < 0:
            self.x = backboard_x + BACKBOARD_THICKNESS / 2 + self.radius

            if self.bank_layup_active:
                # 打板后把球柔和送向篮筐。
                # 让球在约 12 帧后回到篮圈高度附近。
                self.vx = 2.8
                self.vy = -3.2
                self.bank_layup_active = False
            else:
                self.vx = abs(self.vx) * BACKBOARD_BOUNCE_DAMPING

            self.rebound_available = True

            # 约 0.4 秒内 AI 不允许抢篮板。
            # 再次碰板会重新开始计时。
            self.rebound_grace_timer = 24

        hit_left_rim = self._resolve_circle_collision(
            rim_x - hoop_half_width,
            rim_y,
            RIM_COLLISION_RADIUS,
        )

        hit_right_rim = self._resolve_circle_collision(
            rim_x + hoop_half_width,
            rim_y,
            RIM_COLLISION_RADIUS,
        )
        if hit_left_rim or hit_right_rim:
            self.rebound_available = True

            # 第一次砸框正常音量。
            # 后续每次真实颠框都播放更轻的 DUANG。
            #
            # cooldown 防止同一个物理碰撞连续几帧产生声音。
            if self.rim_sound_cooldown <= 0:
                if self.rim_contact_count == 0:
                    self.events.append(
                        ("rim", rim_x, rim_y)
                    )
                else:
                    self.events.append(
                        ("rim_soft", rim_x, rim_y)
                    )

                self.rim_contact_count += 1
                self.rim_sound_cooldown = 4

            # 球在篮圈上颠动期间不要让 AI 立即摘板。
            # 每一次重新碰框都会刷新保护时间。
            self.rebound_grace_timer = 24

    def update(self):
        self.previous_x = self.x
        self.previous_y = self.y

        if self.rim_sound_cooldown > 0:
            self.rim_sound_cooldown -= 1

        if self.rebound_grace_timer > 0:
            self.rebound_grace_timer -= 1

        if self.state == "held" and self.holder is not None:
            holder = self.holder
            moving = abs(holder.vx) > 0.1
            charging = getattr(holder, "is_charging_shot", False)
            airborne = not holder.on_ground

            hand_side = 1 if holder.facing_right else -1
            hand_x = holder.x + PLAYER_WIDTH / 2 + hand_side * DRIBBLE_HAND_OFFSET_X
            hand_y = holder.y + DRIBBLE_HAND_OFFSET_Y

            # 投篮蓄力或滞空时把球收回手中，避免投篮起手阶段篮球还在地面。
            if charging or airborne:
                self.x = hand_x
                self.y = hand_y
            else:
                speed = DRIBBLE_SPEED_MOVING if moving else DRIBBLE_SPEED_IDLE
                self.dribble_phase = (self.dribble_phase + speed) % 2.0

                # 三角波：0 -> 1 -> 0。比正弦波更像篮球快速下落、回弹。
                bounce = self.dribble_phase if self.dribble_phase <= 1.0 else 2.0 - self.dribble_phase
                bounce = bounce * bounce * (3.0 - 2.0 * bounce)

                ground_ball_y = self.arena["ground_y"] - self.radius - DRIBBLE_GROUND_CLEARANCE
                self.y = hand_y + (ground_ball_y - hand_y) * bounce

                sway = DRIBBLE_MOVING_SWAY * bounce if moving else 0
                self.x = hand_x + hand_side * sway

            self.vx = 0
            self.vy = 0

            # 不要在这里再次把 previous_x / previous_y 覆盖成当前坐标。
            # update() 开头已经保存了上一帧位置；扣篮判定需要依赖
            # “上一帧在篮筐上方，本帧向下穿过篮筐高度”。
            return

        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.state == "passing":
            if self.pass_catch_delay > 0:
                self.pass_catch_delay -= 1
            receiver = self.pass_receiver
            if receiver is not None and self.pass_catch_delay <= 0:
                rx, ry = receiver.center()
                dx = self.x - rx
                dy = self.y - ry
                if dx * dx + dy * dy <= (PASS_CATCH_RADIUS + self.radius) ** 2:
                    self.attach_to(receiver)
                    receiver.possession_immune_timer = max(
                        receiver.possession_immune_timer,
                        PASS_RECEIVE_IMMUNITY_FRAMES,
                    )
                    receiver.play_action_animation("shield", 10)
                    return

        if self.state == "flying":
            self._handle_hoop_collisions()

        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -BALL_BOUNCE_DAMPING
        if self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -BALL_BOUNCE_DAMPING

        if self.y + self.radius > self.arena["ground_y"]:
            impact_speed = abs(self.vy)

            self.y = self.arena["ground_y"] - self.radius
            self.vy *= -BALL_BOUNCE_DAMPING
            self.vx *= 0.85

            if impact_speed >= 4.0:
                self.events.append(
                    ("bounce", self.x, self.y)
                )
            if abs(self.vy) < 2:
                self.state = "loose"
                self.rebound_available = False
                self.clear_pass()

    def complete_dunk(self, player, points=1):
        """完成扣篮并缓存得分，让主循环沿用统一的计分流程。"""
        rim_x = self.arena["rim_x"]
        rim_y = self.arena["rim_y"]
        self.pending_score = (player, points)

        # 扣篮也属于一次两分球出手并命中。
        player.fg_attempts = getattr(player, "fg_attempts", 0) + 1
        player.fg_made = getattr(player, "fg_made", 0) + 1

        self.clear_pass()
        self.last_shooter = player
        self.state = "loose"
        self.holder = None
        self.vx = 0
        self.vy = 0
        self.x = self.arena["ball_spawn_x"]
        self.y = self.arena["ground_y"] - 200
        self.previous_x = self.x
        self.previous_y = self.y
        self.rebound_available = False
        self.events.append(("dunk", rim_x, rim_y))

    def check_score(self):
        """篮球从篮圈上方向下穿过时得分，避免高速球漏判。"""
        if self.pending_score is not None:
            scorer, points = self.pending_score
            self.pending_score = None
            return scorer, points
        if self.state != "flying" or self.vy <= 0:
            return None, 0

        rim_x = self.arena["rim_x"]
        rim_y = self.arena["rim_y"]
        scoring_half_width = max(
            4,
            self.arena["hoop_width"] / 2 - self.radius * 0.35,
        )

        crossed_rim_height = self.previous_y < rim_y <= self.y
        inside_rim = abs(self.x - rim_x) <= scoring_half_width
        if not (crossed_rim_height and inside_rim):
            return None, 0

        # 防守篮板后没有先退出三分线：
        # 篮球可以正常穿框，但不计任何分数，也不重置回合。
        if not getattr(self, "shot_score_allowed", True):
            return None, 0

        scorer = self.last_shooter
        points = (
            POINTS_OUTSIDE_THREE
            if self.shot_distance > self.arena["three_point_distance"]
            else POINTS_ON_OR_INSIDE_THREE
        )

        if scorer is not None:
            scorer.fg_made = getattr(scorer, "fg_made", 0) + 1
            if self.shot_distance > self.arena["three_point_distance"]:
                scorer.three_made = getattr(
                    scorer,
                    "three_made",
                    0,
                ) + 1

        self.state = "loose"
        self.clear_pass()
        self.vx = 0
        self.vy = 0
        self.x = self.arena["ball_spawn_x"]
        self.y = self.arena["ground_y"] - 200
        self.previous_x = self.x
        self.previous_y = self.y
        self.holder = None
        self.rebound_available = False
        self.events.append(("score", rim_x, rim_y))
        return scorer, points

    def consume_events(self):
        events = self.events[:]
        self.events.clear()
        return events

    def draw(self, screen):
        if self.frames:
            frame_index = BALL_STATE_TO_FRAME.get(self.state, 0)
            frame_img = self.frames[frame_index % len(self.frames)]
            frame_img = pygame.transform.scale(frame_img, (self.radius * 2, self.radius * 2))
            screen.blit(frame_img, frame_img.get_rect(center=(int(self.x), int(self.y))))
        else:
            pygame.draw.circle(screen, COLOR_BALL, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(screen, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 1)
