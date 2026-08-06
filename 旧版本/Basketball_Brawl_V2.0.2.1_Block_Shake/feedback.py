
"""比赛反馈系统：震屏、顿帧、中央提示文字和简单粒子。"""

import math
import random
import pygame

from constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FEEDBACK_TEXT_FRAMES,
    SCREEN_SHAKE_SCORE,
    SCREEN_SHAKE_STEAL,
    SCREEN_SHAKE_SLAM,
    SCREEN_SHAKE_DASH,
    HIT_STOP_STEAL_FRAMES,
    HIT_STOP_SLAM_FRAMES,
    HIT_STOP_DASH_FRAMES,
    SCREEN_SHAKE_BLOCK, HIT_STOP_BLOCK_FRAMES,
)


EVENT_STYLE = {
    # 只保留“角色技能”和“进球”反馈。所有震屏都控制在轻微范围内。
    "score": {
        "text": "BUCKET!",
        "color": (255, 215, 70),
        "shake": SCREEN_SHAKE_SCORE,
        "shake_frames": 4,
        "freeze": 1,
        "flash": (255, 220, 120),
        "particle_count": 10,
    },
    "dash": {
        "text": "DASH!",
        "color": (225, 240, 255),
        "shake": SCREEN_SHAKE_DASH,
        "shake_frames": 3,
        "freeze": HIT_STOP_DASH_FRAMES,
        "flash": (220, 240, 255),
        "particle_count": 8,
    },
    "slam": {
        "text": "SLAM!",
        "color": (255, 150, 70),
        "shake": SCREEN_SHAKE_SLAM,
        "shake_frames": 4,
        "freeze": HIT_STOP_SLAM_FRAMES,
        "flash": (255, 145, 70),
        "particle_count": 12,
    },
    "block": {
        "text": "BLOCK!",
        "color": (105, 215, 255),
        "shake": SCREEN_SHAKE_BLOCK,
        "shake_frames": 8,
        "freeze": HIT_STOP_BLOCK_FRAMES,
        "flash": (150, 225, 255),
        "particle_count": 12,
    },
    "double_jump": {
        "text": "SHADOW JUMP!",
        "color": (180, 145, 255),
        "shake": 1,
        "shake_frames": 2,
        "freeze": 0,
        "flash": None,
        "particle_count": 6,
    },
}



class FeedbackManager:
    def __init__(self):
        self.shake_timer = 0
        self.shake_intensity = 0
        self.freeze_timer = 0
        self.flash_timer = 0
        self.flash_color = (255, 255, 255)
        self.messages = []
        self.particles = []

    def trigger(self, event_type, x=None, y=None, text=None):
        style = EVENT_STYLE.get(event_type)
        if style is None:
            return

        self.shake_timer = max(self.shake_timer, style["shake_frames"])
        self.shake_intensity = max(self.shake_intensity, style["shake"])
        self.freeze_timer = max(self.freeze_timer, style["freeze"])

        if style["flash"] is not None:
            self.flash_timer = max(self.flash_timer, 4)
            self.flash_color = style["flash"]

        message = style["text"] if text is None else text
        if message:
            self.messages.append({
                "text": message,
                "color": style["color"],
                "timer": FEEDBACK_TEXT_FRAMES,
            })

        if x is not None and y is not None:
            count = style["particle_count"]
            for _ in range(count):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(1.5, 5.5)
                self.particles.append({
                    "x": float(x),
                    "y": float(y),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - 1.5,
                    "timer": random.randint(18, 34),
                    "color": style["color"],
                    "size": random.randint(2, 5),
                })

    @property
    def gameplay_frozen(self):
        return self.freeze_timer > 0

    def update(self):
        if self.freeze_timer > 0:
            self.freeze_timer -= 1

        if self.shake_timer > 0:
            self.shake_timer -= 1
            if self.shake_timer == 0:
                self.shake_intensity = 0

        if self.flash_timer > 0:
            self.flash_timer -= 1

        for message in self.messages:
            message["timer"] -= 1
        self.messages = [m for m in self.messages if m["timer"] > 0]

        for particle in self.particles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += 0.16
            particle["vx"] *= 0.98
            particle["timer"] -= 1
        self.particles = [p for p in self.particles if p["timer"] > 0]

    def present_world(self, world_surface, screen):
        if self.shake_timer > 0 and self.shake_intensity > 0:
            offset_x = random.randint(-self.shake_intensity, self.shake_intensity)
            offset_y = random.randint(-self.shake_intensity, self.shake_intensity)
        else:
            offset_x = 0
            offset_y = 0

        screen.fill((0, 0, 0))
        screen.blit(world_surface, (offset_x, offset_y))

    def draw_overlay(self, screen, title_font):
        for particle in self.particles:
            pygame.draw.circle(
                screen,
                particle["color"],
                (int(particle["x"]), int(particle["y"])),
                particle["size"],
            )

        if self.messages:
            message = self.messages[-1]
            progress = message["timer"] / FEEDBACK_TEXT_FRAMES
            scale = 1.0 + max(0.0, progress - 0.7) * 0.8
            surface = title_font.render(message["text"], True, message["color"])
            if scale != 1.0:
                surface = pygame.transform.smoothscale(
                    surface,
                    (
                        max(1, int(surface.get_width() * scale)),
                        max(1, int(surface.get_height() * scale)),
                    ),
                )
            y = 115 - int((1 - progress) * 18)
            screen.blit(
                surface,
                (
                    SCREEN_WIDTH // 2 - surface.get_width() // 2,
                    y,
                ),
            )

        if self.flash_timer > 0:
            alpha = int(52 * self.flash_timer / 4)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((*self.flash_color, alpha))
            screen.blit(overlay, (0, 0))
