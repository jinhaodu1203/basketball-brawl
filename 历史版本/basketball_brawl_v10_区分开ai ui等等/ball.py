"""篮球实体与篮筐碰撞逻辑。"""

import pygame

from constants import (
    GRAVITY, GROUND_Y, PLAYER_WIDTH,
    BALL_RADIUS, BALL_BOUNCE_DAMPING, SCREEN_WIDTH,
    RIM_COLLISION_RADIUS, RIM_BOUNCE_DAMPING,
    BACKBOARD_BOUNCE_DAMPING, BACKBOARD_THICKNESS,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT, SHOT_FLIGHT_FRAMES,
    COLOR_BALL, BALL_SPAWN_X,
    BALL_SPRITE_FRAME_COUNT, BALL_STATE_TO_FRAME,
    THREE_POINT_RADIUS, POINTS_OUTSIDE_THREE, POINTS_ON_OR_INSIDE_THREE,
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
        self.frames = load_ball_frames(sprite_path, BALL_SPRITE_FRAME_COUNT)
        self.events = []
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
            self.vx = abs(self.vx) * BACKBOARD_BOUNCE_DAMPING

        # 篮圈左右两端视为两个小圆形碰撞体。
        hit_left = self._resolve_circle_collision(
            rim_x - hoop_half_width,
            rim_y,
            RIM_COLLISION_RADIUS,
        )
        hit_right = self._resolve_circle_collision(
            rim_x + hoop_half_width,
            rim_y,
            RIM_COLLISION_RADIUS,
        )
    def update(self):
        self.previous_x = self.x
        self.previous_y = self.y

        if self.state == "held" and self.holder is not None:
            offset = 26 if self.holder.facing_right else -26
            self.x = self.holder.x + PLAYER_WIDTH / 2 + offset
            self.y = self.holder.y + PLAYER_HEIGHT * 0.4
            self.previous_x = self.x
            self.previous_y = self.y
            return

        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.state == "flying":
            self._handle_hoop_collisions()

        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx *= -BALL_BOUNCE_DAMPING
        if self.x + self.radius > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.vx *= -BALL_BOUNCE_DAMPING

        if self.y + self.radius > self.arena["ground_y"]:
            self.y = self.arena["ground_y"] - self.radius
            self.vy *= -BALL_BOUNCE_DAMPING
            self.vx *= 0.85
            if abs(self.vy) < 2:
                self.state = "loose"

    def check_score(self):
        """篮球从篮圈上方向下穿过时得分，避免高速球漏判。"""
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

        scorer = self.last_shooter
        points = (
            POINTS_OUTSIDE_THREE
            if self.shot_distance > self.arena["three_point_distance"]
            else POINTS_ON_OR_INSIDE_THREE
        )
        self.state = "loose"
        self.vx = 0
        self.vy = 0
        self.x = self.arena["ball_spawn_x"]
        self.y = self.arena["ground_y"] - 200
        self.previous_x = self.x
        self.previous_y = self.y
        self.holder = None
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
