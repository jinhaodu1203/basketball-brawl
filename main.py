"""
2D 篮球大乱斗 - 核心玩法demo
2D Basketball Brawl - core gameplay demo

场地说明 / Court note:
    篮筐挂在场地左侧的墙上，两名玩家都在场地右侧出生，
    一起进攻这一个篮筐——类似真实3v3单筐半场对抗。
    地面画了压扁风格的球场标线(罚球区/罚球圈/两分线/三分线)，
    参考经典街球游戏(如NBA Jam)的画法，纯装饰不影响跳跃物理。

运行方式 / How to run:
    pip install pygame
    python main.py

操作 / Controls:
    玩家1(蓝) / Player 1 (blue): A/D 移动, W 跳跃, Space 投篮/捡球, S 抢断, LShift 冲刺技能
    玩家2(红) / Player 2 (red):  ←/→ 移动, ↑ 跳跃, Enter 投篮/捡球, ↓ 抢断, RCtrl 冲刺技能
"""

import os
import sys
import math
import pygame

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    COLOR_BG, COLOR_GROUND, COLOR_HOOP, COLOR_TEXT,
    COLOR_PLAYER1, COLOR_PLAYER2, COLOR_COURT_LINE, COLOR_PAINT_FILL,
    HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT,
    RIM_X, RIM_Y, BACKBOARD_X, BACKBOARD_TOP_Y, BACKBOARD_HEIGHT,
    PAINT_BAND_HEIGHT, FREE_THROW_LINE_X, FREE_THROW_CIRCLE_RADIUS,
    TWO_POINT_RADIUS, THREE_POINT_RADIUS, COURT_LINE_FLATTEN, COURT_LINE_WIDTH,
    HALF_COURT_X, COURT_BAND_CENTER_Y_OFFSET,
    PLAYER1_SPAWN_X, PLAYER2_SPAWN_X, BALL_SPAWN_X, PLAYER_HEIGHT,
)
from entities import Player, Ball

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


PLAYER1_CONTROLS = {
    "left": pygame.K_a,
    "right": pygame.K_d,
    "jump": pygame.K_w,
    "action": pygame.K_SPACE,
    "steal": pygame.K_s,
    "dash": pygame.K_LSHIFT,
}

PLAYER2_CONTROLS = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "jump": pygame.K_UP,
    "action": pygame.K_RETURN,
    "steal": pygame.K_DOWN,
    "dash": pygame.K_RCTRL,
}


def _draw_flattened_arc(screen, center_x, center_y, radius, color):
    """
    画一条"压扁"的半椭圆弧，只取右半边(开口朝右)，
    模拟侧视角下地面标线应有的透视压缩效果。
    Draw a flattened half-ellipse arc (right half only, opening rightward)
    to simulate the perspective-compressed look of floor markings in a side view.
    """
    a = radius
    b = max(6, int(radius * COURT_LINE_FLATTEN))
    rect = pygame.Rect(center_x - a, center_y - b, a * 2, b * 2)
    pygame.draw.arc(screen, color, rect, -math.pi / 2, math.pi / 2, COURT_LINE_WIDTH)


def draw_court(screen):
    """
    画整个球场：半场线、三分线、两分线、罚球区(禁区)、罚球圈、篮板、篮筐。
    篮筐固定在场地左侧墙上，所有标线以篮筐在地面上的投影点为圆心。
    Draw the whole court: half-court line, three-point arc, two-point arc,
    the paint/key, free-throw circle, backboard, and rim. The hoop is mounted
    on the left wall; all arcs are centered on the rim's ground projection.
    """
    # ---- 半场线(虚线) / half-court dashed line ----
    dash_len = 14
    y = 24
    while y < GROUND_Y:
        pygame.draw.line(screen, COLOR_COURT_LINE,
                          (HALF_COURT_X, y), (HALF_COURT_X, y + dash_len), COURT_LINE_WIDTH)
        y += dash_len * 2

    arc_cx = RIM_X
    arc_cy = GROUND_Y - COURT_BAND_CENTER_Y_OFFSET

    # ---- 三分线 + 两分线 / three-point & two-point arcs ----
    _draw_flattened_arc(screen, arc_cx, arc_cy, THREE_POINT_RADIUS, COLOR_COURT_LINE)
    _draw_flattened_arc(screen, arc_cx, arc_cy, TWO_POINT_RADIUS, COLOR_COURT_LINE)

    # ---- 罚球区/禁区 / the paint (key) ----
    paint_rect = pygame.Rect(0, GROUND_Y - PAINT_BAND_HEIGHT, FREE_THROW_LINE_X, PAINT_BAND_HEIGHT)
    pygame.draw.rect(screen, COLOR_PAINT_FILL, paint_rect)
    pygame.draw.rect(screen, COLOR_COURT_LINE, paint_rect, COURT_LINE_WIDTH)

    # ---- 罚球圈 / free-throw circle ----
    pygame.draw.circle(screen, COLOR_COURT_LINE,
                        (FREE_THROW_LINE_X, GROUND_Y - PAINT_BAND_HEIGHT),
                        FREE_THROW_CIRCLE_RADIUS, COURT_LINE_WIDTH)

    # ---- 篮板 / backboard ----
    pygame.draw.line(screen, COLOR_HOOP,
                      (BACKBOARD_X, BACKBOARD_TOP_Y),
                      (BACKBOARD_X, BACKBOARD_TOP_Y + BACKBOARD_HEIGHT), 5)

    # ---- 篮筐支臂 + 篮筐 / rim arm + rim ----
    pygame.draw.line(screen, COLOR_HOOP, (BACKBOARD_X, RIM_Y), (RIM_X, RIM_Y), 4)
    pygame.draw.rect(screen, COLOR_HOOP, (HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT))


def draw_scoreboard(screen, font, p1, p2):
    text = f"{p1.name}  {p1.score}  :  {p2.score}  {p2.name}"
    surf = font.render(text, True, COLOR_TEXT)
    screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, 20))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Basketball Brawl - Demo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 30)
    small_font = pygame.font.SysFont(None, 20)

    # sprite_folder 指向 assets/<角色名>/ ；文件夹或贴图不存在时会自动
    # 回退成程序化的简笔小人动画，不会报错。等你准备好贴图直接放进去即可。
    player1 = Player(PLAYER1_SPAWN_X, GROUND_Y - PLAYER_HEIGHT, COLOR_PLAYER1, PLAYER1_CONTROLS,
                      facing_right=False, name="P1",
                      sprite_folder=os.path.join(ASSETS_DIR, "player1"))
    player2 = Player(PLAYER2_SPAWN_X, GROUND_Y - PLAYER_HEIGHT, COLOR_PLAYER2, PLAYER2_CONTROLS,
                      facing_right=False, name="P2",
                      sprite_folder=os.path.join(ASSETS_DIR, "player2"))
    ball = Ball(BALL_SPAWN_X, GROUND_Y - 200, sprite_path=os.path.join(ASSETS_DIR, "ball.png"))

    players = [player1, player2]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()

        # ---- 更新逻辑 / update logic ----
        for p in players:
            p.handle_input(keys, ball)
            p.update_physics()
            p.try_pick_up(ball)

        ball.update()
        scorer = ball.check_score()
        if scorer is not None:
            scorer.score += 1

        # ---- 绘制 / draw ----
        screen.fill(COLOR_BG)
        pygame.draw.rect(screen, COLOR_GROUND, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        draw_court(screen)

        for p in players:
            p.draw(screen, small_font)
        ball.draw(screen)

        draw_scoreboard(screen, font, player1, player2)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()