"""
2D 篮球大乱斗 - 核心玩法demo

场地说明:
    篮筐挂在场地左侧墙上，两名玩家都在场地右侧出生，一起进攻这一个
    篮筐——类似真实3v3单筐半场对抗。地面画了压扁风格的球场标线
    (罚球区/禁区、罚球圈、两分线、三分线)，参考经典街球游戏
    (如NBA Jam)的画法，纯装饰不影响跳跃物理。

运行方式:
    pip install pygame
    python main.py
    启动后先选模式：按 1 单人模式(对战AI)，按 2 双人模式(本地对战)。
    选了单人模式后，再选AI难度：按 1 EZ PZ，按 2 Normal，按 3 Hard as Hell。

操作:
    玩家1(蓝): A/D 移动, W 跳跃, Space 投篮/捡球, S 抢断, LShift 冲刺技能
    玩家2(红，双人模式下由真人操作): 方向键左右移动, Up 跳跃, Enter 投篮/捡球,
        Down 抢断, RCtrl 冲刺技能
    单人模式下，玩家2由AI自动操作，不需要手动输入。
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
    AI_DIFFICULTY_LABELS, WINNING_SCORE,
    SCORE_POPUP_DURATION_FRAMES, ROUND_RESET_DELAY_FRAMES,
    SCORE_POPUP_COLOR,
)
from entities import Player, Ball

from characters import (
    CHARACTER_ORDER,
    CHARACTERS,
    get_character,
)

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
    """
    a = radius
    b = max(6, int(radius * COURT_LINE_FLATTEN))
    rect = pygame.Rect(center_x - a, center_y - b, a * 2, b * 2)
    pygame.draw.arc(screen, color, rect, -math.pi / 2, math.pi / 2, COURT_LINE_WIDTH)


def draw_court(screen):
    """
    画整个球场：半场线、三分线、两分线、罚球区(禁区)、罚球圈、篮板、篮筐。
    篮筐固定在场地左侧墙上，所有标线以篮筐在地面上的投影点为圆心。
    """
    # ---- 半场线(虚线) ----
    dash_len = 14
    y = 24
    while y < GROUND_Y:
        pygame.draw.line(screen, COLOR_COURT_LINE,
                          (HALF_COURT_X, y), (HALF_COURT_X, y + dash_len), COURT_LINE_WIDTH)
        y += dash_len * 2

    arc_cx = RIM_X
    arc_cy = GROUND_Y - COURT_BAND_CENTER_Y_OFFSET

    # ---- 三分线 + 两分线 ----
    _draw_flattened_arc(screen, arc_cx, arc_cy, THREE_POINT_RADIUS, COLOR_COURT_LINE)
    _draw_flattened_arc(screen, arc_cx, arc_cy, TWO_POINT_RADIUS, COLOR_COURT_LINE)

    # ---- 罚球区/禁区 ----
    paint_rect = pygame.Rect(0, GROUND_Y - PAINT_BAND_HEIGHT, FREE_THROW_LINE_X, PAINT_BAND_HEIGHT)
    pygame.draw.rect(screen, COLOR_PAINT_FILL, paint_rect)
    pygame.draw.rect(screen, COLOR_COURT_LINE, paint_rect, COURT_LINE_WIDTH)

    # ---- 罚球圈 ----
    pygame.draw.circle(screen, COLOR_COURT_LINE,
                        (FREE_THROW_LINE_X, GROUND_Y - PAINT_BAND_HEIGHT),
                        FREE_THROW_CIRCLE_RADIUS, COURT_LINE_WIDTH)

    # ---- 篮板 ----
    pygame.draw.line(screen, COLOR_HOOP,
                      (BACKBOARD_X, BACKBOARD_TOP_Y),
                      (BACKBOARD_X, BACKBOARD_TOP_Y + BACKBOARD_HEIGHT), 5)

    # ---- 篮筐支臂 + 篮筐 ----
    pygame.draw.line(screen, COLOR_HOOP, (BACKBOARD_X, RIM_Y), (RIM_X, RIM_Y), 4)
    pygame.draw.rect(screen, COLOR_HOOP, (HOOP_X, HOOP_Y, HOOP_WIDTH, HOOP_HEIGHT))


def draw_scoreboard(screen, font, p1, p2):
    text = f"{p1.name}  {p1.score}  :  {p2.score}  {p2.name}"
    surf = font.render(text, True, COLOR_TEXT)
    screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, 20))

def reset_round(player1, player2, ball):
    """
    进球后重置双方位置和篮球状态，开始一个新回合。
    分数不会被清零。
    """

    # ---- 玩家1重置 ----
    player1.x = PLAYER1_SPAWN_X
    player1.y = GROUND_Y - PLAYER_HEIGHT
    player1.vx = 0
    player1.vy = 0
    player1.facing_right = False
    player1.on_ground = True

    player1.possession_immune_timer = 0
    player1.steal_cooldown_timer = 0
    player1.is_dashing = False
    player1.dash_timer = 0
    player1.dash_cooldown_timer = 0
    player1.ai_shot_target = None

    # ---- 玩家2重置 ----
    player2.x = PLAYER2_SPAWN_X
    player2.y = GROUND_Y - PLAYER_HEIGHT
    player2.vx = 0
    player2.vy = 0
    player2.facing_right = False
    player2.on_ground = True

    player2.possession_immune_timer = 0
    player2.steal_cooldown_timer = 0
    player2.is_dashing = False
    player2.dash_timer = 0
    player2.dash_cooldown_timer = 0
    player2.ai_shot_target = None

    # ---- 篮球重置 ----
    ball.x = BALL_SPAWN_X
    ball.y = GROUND_Y - 200
    ball.vx = 0
    ball.vy = 0
    ball.state = "loose"
    ball.holder = None
    ball.last_shooter = None
    ball.shot_distance = 0


def draw_win_overlay(
    screen,
    font,
    title_font,
    small_font,
    winner,
    single_player,
    human_player,
):
    """
    根据胜利者显示不同结算画面：

    玩家获胜：
        YOU WIN!
        You Are The GOAT!

    AI获胜：
        YOU LOST!
        AI IS THE GOAT!
    """
    overlay = pygame.Surface(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.SRCALPHA,
    )
    overlay.fill((0, 0, 0, 185))
    screen.blit(overlay, (0, 0))

    human_won = winner is human_player

    if single_player and not human_won:
        result_text = "YOU LOST!"
        subtitle_text = "AI IS THE GOAT!"
        title_color = (220, 80, 80)
    else:
        result_text = "YOU WIN!"
        subtitle_text = "You Are The GOAT!"
        title_color = (255, 215, 0)

    name_surf = font.render(
        winner.name,
        True,
        COLOR_TEXT,
    )

    result_surf = title_font.render(
        result_text,
        True,
        title_color,
    )

    subtitle_surf = font.render(
        subtitle_text,
        True,
        COLOR_TEXT,
    )

    hint_surf = small_font.render(
        "Press ENTER or R to play again, ESC to quit",
        True,
        COLOR_TEXT,
    )

    screen.blit(
        name_surf,
        (
            SCREEN_WIDTH // 2 - name_surf.get_width() // 2,
            165,
        ),
    )

    screen.blit(
        result_surf,
        (
            SCREEN_WIDTH // 2 - result_surf.get_width() // 2,
            210,
        ),
    )

    screen.blit(
        subtitle_surf,
        (
            SCREEN_WIDTH // 2 - subtitle_surf.get_width() // 2,
            275,
        ),
    )

    screen.blit(
        hint_surf,
        (
            SCREEN_WIDTH // 2 - hint_surf.get_width() // 2,
            345,
        ),
    )


def select_mode(screen, font, title_font):
    """
    开局模式选择菜单：按 1 选单人模式(对战AI)，按 2 选双人模式(本地对战)。
    返回 True 表示单人模式，False 表示双人模式。
    菜单上显示给玩家看的文字用英文，方便直接截图/录屏分享。
    """
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    return True
                if event.key in (pygame.K_2, pygame.K_KP2):
                    return False
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        screen.fill(COLOR_BG)
        title = title_font.render("2D Basketball Brawl", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 160))

        option1 = font.render("Press 1  ->  1 Player (vs AI)", True, COLOR_TEXT)
        option2 = font.render("Press 2  ->  2 Player (local)", True, COLOR_TEXT)
        screen.blit(option1, (SCREEN_WIDTH // 2 - option1.get_width() // 2, 260))
        screen.blit(option2, (SCREEN_WIDTH // 2 - option2.get_width() // 2, 300))

        pygame.display.flip()
        clock.tick(FPS)

def select_character(
    screen,
    font,
    small_font,
    title_font,
    player_label,
):
    """
    基础角色选择界面。

    数字键：
        1 = Cheetah
        2 = Gorilla
        3 = Ninja

    返回角色ID。
    """
    clock = pygame.time.Clock()

    key_to_index = {
        pygame.K_1: 0,
        pygame.K_KP1: 0,
        pygame.K_2: 1,
        pygame.K_KP2: 1,
        pygame.K_3: 2,
        pygame.K_KP3: 2,
    }

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                selected_index = key_to_index.get(event.key)

                if (
                    selected_index is not None
                    and selected_index < len(CHARACTER_ORDER)
                ):
                    return CHARACTER_ORDER[selected_index]

        screen.fill(COLOR_BG)

        title = title_font.render(
            f"{player_label}: Choose Your Character",
            True,
            COLOR_TEXT,
        )

        screen.blit(
            title,
            (
                SCREEN_WIDTH // 2 - title.get_width() // 2,
                45,
            ),
        )

        hint = small_font.render(
            "Press 1, 2 or 3 to select",
            True,
            COLOR_TEXT,
        )

        screen.blit(
            hint,
            (
                SCREEN_WIDTH // 2 - hint.get_width() // 2,
                100,
            ),
        )

        card_width = 250
        card_height = 300
        gap = 25

        total_width = (
            len(CHARACTER_ORDER) * card_width
            + (len(CHARACTER_ORDER) - 1) * gap
        )

        start_x = SCREEN_WIDTH // 2 - total_width // 2
        card_y = 145

        for index, character_id in enumerate(CHARACTER_ORDER):
            config = CHARACTERS[character_id]

            card_x = start_x + index * (card_width + gap)

            card_rect = pygame.Rect(
                card_x,
                card_y,
                card_width,
                card_height,
            )

            pygame.draw.rect(
                screen,
                (50, 50, 65),
                card_rect,
                border_radius=14,
            )

            pygame.draw.rect(
                screen,
                config["color"],
                card_rect,
                width=4,
                border_radius=14,
            )

            # 角色编号
            number_surface = font.render(
                str(index + 1),
                True,
                COLOR_TEXT,
            )

            screen.blit(
                number_surface,
                (
                    card_x + 15,
                    card_y + 12,
                ),
            )

            # 临时角色预览
            # 以后这里替换成 portrait.png
            preview_center = (
                card_x + card_width // 2,
                card_y + 75,
            )

            pygame.draw.circle(
                screen,
                config["color"],
                preview_center,
                45,
            )

            pygame.draw.circle(
                screen,
                COLOR_TEXT,
                preview_center,
                45,
                width=3,
            )

            # 角色名字
            name_surface = font.render(
                config["name"],
                True,
                COLOR_TEXT,
            )

            screen.blit(
                name_surface,
                (
                    card_x
                    + card_width // 2
                    - name_surface.get_width() // 2,
                    card_y + 135,
                ),
            )

            # 技能名称
            skill_surface = small_font.render(
                config["skill_name"],
                True,
                (255, 215, 0),
            )

            screen.blit(
                skill_surface,
                (
                    card_x
                    + card_width // 2
                    - skill_surface.get_width() // 2,
                    card_y + 180,
                ),
            )

            # 简介
            description_surface = small_font.render(
                config["description"],
                True,
                COLOR_TEXT,
            )

            screen.blit(
                description_surface,
                (
                    card_x
                    + card_width // 2
                    - description_surface.get_width() // 2,
                    card_y + 215,
                ),
            )

            # 基础属性
            stats_text = (
                f"SPD {config['move_speed']:.1f}   "
                f"JMP {abs(config['jump_velocity']):.1f}"
            )

            stats_surface = small_font.render(
                stats_text,
                True,
                COLOR_TEXT,
            )

            screen.blit(
                stats_surface,
                (
                    card_x
                    + card_width // 2
                    - stats_surface.get_width() // 2,
                    card_y + 250,
                ),
            )

        pygame.display.flip()
        clock.tick(FPS)

def select_difficulty(screen, font, title_font):
    """
    选AI难度：EZ PZ(简单) / Normal(普通) / Hard as Hell(超级难)。
    返回 "easy" / "normal" / "hard" 三者之一，对应
    constants.py 里 AI_DIFFICULTY_PRESETS 的key。
    只有选了单人模式才会进这个菜单。
    """
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_KP1):
                    return "easy"
                if event.key in (pygame.K_2, pygame.K_KP2):
                    return "normal"
                if event.key in (pygame.K_3, pygame.K_KP3):
                    return "hard"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        screen.fill(COLOR_BG)
        title = title_font.render("Choose AI Difficulty", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 130))

        option1 = font.render("Press 1  ->  EZ PZ", True, COLOR_TEXT)
        option2 = font.render("Press 2  ->  Normal", True, COLOR_TEXT)
        option3 = font.render("Press 3  ->  Hard as Hell", True, COLOR_TEXT)
        screen.blit(option1, (SCREEN_WIDTH // 2 - option1.get_width() // 2, 240))
        screen.blit(option2, (SCREEN_WIDTH // 2 - option2.get_width() // 2, 280))
        screen.blit(option3, (SCREEN_WIDTH // 2 - option3.get_width() // 2, 320))

        pygame.display.flip()
        clock.tick(FPS)


def play_session(screen, font, small_font, title_font):
    """
    跑完完整的一局：

    选择模式
    -> 选择AI难度
    -> 开始对局
    -> 进球反馈
    -> 重置新回合
    -> 任意玩家达到12分
    -> 显示结算画面
    """
    single_player = select_mode(
        screen,
        font,
        title_font,
    )

    player1_character_id = select_character(
        screen,
        font,
        small_font,
        title_font,
        "Player 1",
    )

    player2_label = "AI" if single_player else "Player 2"

    player2_character_id = select_character(
        screen,
        font,
        small_font,
        title_font,
        player2_label,
    )

    ai_difficulty = (
        select_difficulty(
            screen,
            font,
            title_font,
        )
        if single_player
        else "normal"
    )

    player1_character = get_character(
        player1_character_id,
    )

    player2_character = get_character(
        player2_character_id,
    )

    player1 = Player(
        PLAYER1_SPAWN_X,
        GROUND_Y - PLAYER_HEIGHT,
        player1_character["color"],
        PLAYER1_CONTROLS,
        facing_right=False,
        name=f"P1 - {player1_character['name']}",
        sprite_folder=os.path.join(
            ASSETS_DIR,
            "characters",
            player1_character["sprite_folder"],
        ),
        character_config=player1_character,
    )

    if single_player:
        player2_name = (
            f"AI {player2_character['name']} "
            f"({AI_DIFFICULTY_LABELS[ai_difficulty]})"
        )
    else:
        player2_name = (
            f"P2 - {player2_character['name']}"
        )

    player2 = Player(
        PLAYER2_SPAWN_X,
        GROUND_Y - PLAYER_HEIGHT,
        player2_character["color"],
        PLAYER2_CONTROLS,
        facing_right=False,
        name=player2_name,
        sprite_folder=os.path.join(
            ASSETS_DIR,
            "characters",
            player2_character["sprite_folder"],
        ),
        ai_controlled=single_player,
        character_config=player2_character,
    )

    if single_player:
        player2.apply_ai_difficulty(ai_difficulty)

    ball = Ball(
        BALL_SPAWN_X,
        GROUND_Y - 200,
        sprite_path=os.path.join(
            ASSETS_DIR,
            "ball.png",
        ),
    )

    players = [player1, player2]
    clock = pygame.time.Clock()

    game_over = False
    winner = None

    # 进球后的短暂停顿
    round_reset_timer = 0

    # +1 / +2 浮字
    score_popup_timer = 0
    score_popup_points = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if (
                    game_over
                    and event.key in (
                        pygame.K_RETURN,
                        pygame.K_r,
                    )
                ):
                    return

        # --------------------------------------------------
        # 游戏更新
        # --------------------------------------------------
        if not game_over:
            # 进球后的暂停阶段
            if round_reset_timer > 0:
                round_reset_timer -= 1

                if round_reset_timer == 0:
                    reset_round(
                        player1,
                        player2,
                        ball,
                    )

            else:
                keys = pygame.key.get_pressed()

                for player in players:
                    if player.ai_controlled:
                        opponent = (
                            player1
                            if player is player2
                            else player2
                        )

                        player.handle_ai(
                            ball,
                            opponent,
                        )
                    else:
                        player.handle_input(
                            keys,
                            ball,
                        )

                    player.update_physics()
                    player.try_pick_up(ball)

                ball.update()

                scorer, points = ball.check_score()

                if scorer is not None:
                    scorer.score += points

                    score_popup_points = points
                    score_popup_timer = (
                        SCORE_POPUP_DURATION_FRAMES
                    )

                    if scorer.score >= WINNING_SCORE:
                        game_over = True
                        winner = scorer
                    else:
                        # 暂停一会儿再重置新回合
                        round_reset_timer = (
                            ROUND_RESET_DELAY_FRAMES
                        )

        if score_popup_timer > 0:
            score_popup_timer -= 1

        # --------------------------------------------------
        # 绘制
        # --------------------------------------------------
        screen.fill(COLOR_BG)

        pygame.draw.rect(
            screen,
            COLOR_GROUND,
            (
                0,
                GROUND_Y,
                SCREEN_WIDTH,
                SCREEN_HEIGHT - GROUND_Y,
            ),
        )

        draw_court(screen)

        for player in players:
            player.draw(
                screen,
                small_font,
            )

        ball.draw(screen)

        draw_scoreboard(
            screen,
            font,
            player1,
            player2,
        )

        draw_score_popup(
            screen,
            title_font,
            score_popup_points,
            score_popup_timer,
        )

        if game_over:
            draw_win_overlay(
                screen,
                font,
                title_font,
                small_font,
                winner,
                single_player,
                player1,
            )

        pygame.display.flip()
        clock.tick(FPS)


def draw_score_popup(screen, title_font, points, timer):
    """
    在篮筐附近显示短暂的 +1 或 +2 得分提示。
    timer 越小，文字越往上漂。
    """
    if timer <= 0 or points <= 0:
        return

    elapsed = SCORE_POPUP_DURATION_FRAMES - timer

    # 文字逐渐向上移动
    popup_y = RIM_Y - 70 - elapsed * 0.35

    text = f"+{points}"
    surf = title_font.render(text, True, SCORE_POPUP_COLOR)

    popup_x = RIM_X + 35

    screen.blit(
        surf,
        (
            int(popup_x - surf.get_width() / 2),
            int(popup_y),
        ),
    )


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Basketball Brawl - Demo")
    font = pygame.font.SysFont(None, 30)
    small_font = pygame.font.SysFont(None, 20)
    title_font = pygame.font.SysFont(None, 48)

    while True:
        play_session(screen, font, small_font, title_font)


if __name__ == "__main__":
    main()