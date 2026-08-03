"""
角色动画系统
Character animation system.

设计思路 / Design:
    - 如果 assets/<角色名>/ 文件夹下能找到 idle.png / run.png / jump.png
      三张"雪碧图"(横向排列的连续帧图片)，就自动切片播放真正的贴图动画。
    - 如果找不到(比如你还没来得及找/画贴图)，自动退化成程序化绘制的
      简笔小人动画——保证"角色能动"这件事不依赖美术资源，先把手感跑起来，
      之后随时把贴图丢进对应文件夹，代码不用改一行就会自动切换成贴图动画。

贴图规范 / Sprite sheet convention:
    assets/<角色名>/idle.png   -> 一张图，横向排N帧，比如站立呼吸的2帧循环
    assets/<角色名>/run.png    -> 一张图，横向排N帧，跑步循环(常见4~6帧)
    assets/<角色名>/jump.png   -> 一张图，横向排N帧，起跳/滞空/下落(1帧也可以)
    每张图内的所有帧必须等宽等高，代码会按 图片宽度 / 帧数 自动切割。
    具体帧数在 constants.DEFAULT_FRAME_COUNTS 里配置，也可以针对某个角色单独传。
"""

import os
import math
import pygame


def _slice_sprite_sheet(path, frame_count):
    """
    把一张横向排列的雪碧图切成 frame_count 等份。
    Slice a horizontal sprite sheet into frame_count equal-width frames.
    """
    sheet = pygame.image.load(path).convert_alpha()
    sheet_w, sheet_h = sheet.get_size()
    frame_w = max(1, sheet_w // frame_count)
    frames = []
    for i in range(frame_count):
        frame = sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, sheet_h)).copy()
        frames.append(frame)
    return frames


def load_character_animations(folder, frame_counts):
    """
    尝试加载并切片某个角色的三套动画贴图。

    返回 dict: {"idle": [Surface, ...], "run": [...], "jump": [...]}
    如果文件夹不存在，或任意一个状态的图片缺失，返回 None
    (上层会据此自动回退到程序化动画，不会崩溃)。
    """
    if not folder or not os.path.isdir(folder):
        return None

    animations = {}
    for state, count in frame_counts.items():
        path = os.path.join(folder, f"{state}.png")
        if not os.path.isfile(path):
            return None
        animations[state] = _slice_sprite_sheet(path, count)

    return animations


def load_ball_frames(path, frame_count):
    """
    加载篮球的雪碧图，切成 frame_count 帧(默认3帧：手里/空中/地面)。
    Load the basketball's sprite sheet, sliced into frame_count frames
    (default 3: held / mid-air / on-ground).
    找不到文件就返回 None，上层会回退成程序化画的圆形球。
    """
    if not path or not os.path.isfile(path):
        return None
    return _slice_sprite_sheet(path, frame_count)


def draw_procedural_character(screen, rect, color, state, anim_frame, facing_right):
    """
    没有贴图时的占位动画：圆头 + 主干 + 会摆动的四肢。
    根据 state("idle"/"run"/"jump") 和 anim_frame(持续递增的帧计数)
    计算摆动幅度，让角色在没有美术资源时也能看出"正在跑"/"正在跳"。
    """
    cx = rect.centerx
    top = rect.top
    bottom = rect.bottom
    width = rect.width
    height = rect.height

    head_r = width * 0.28
    head_center = (cx, top + head_r)
    body_top = (cx, top + head_r * 2)

    direction = 1 if facing_right else -1

    if state == "run":
        swing = math.sin(anim_frame * 0.9) * (width * 0.34)
        knee_bend = 0
        hip_y = bottom - height * 0.16
    elif state == "jump":
        swing = width * 0.06 * direction
        knee_bend = height * 0.14
        hip_y = bottom - height * 0.22
    else:  # idle
        swing = math.sin(anim_frame * 0.3) * (width * 0.05)
        knee_bend = 0
        hip_y = bottom - height * 0.16

    body_bottom = (cx, hip_y)

    pygame.draw.circle(screen, color, head_center, max(1, int(head_r)))
    pygame.draw.line(screen, color, body_top, body_bottom, 6)

    left_leg_end = (cx - width * 0.22 + swing, bottom - knee_bend)
    right_leg_end = (cx + width * 0.22 - swing, bottom - knee_bend)
    pygame.draw.line(screen, color, body_bottom, left_leg_end, 5)
    pygame.draw.line(screen, color, body_bottom, right_leg_end, 5)

    arm_y = top + head_r * 2.5
    left_arm_end = (cx - width * 0.32 - swing * 0.5, arm_y + height * 0.16)
    right_arm_end = (cx + width * 0.32 + swing * 0.5, arm_y + height * 0.16)
    pygame.draw.line(screen, color, (cx, arm_y), left_arm_end, 5)
    pygame.draw.line(screen, color, (cx, arm_y), right_arm_end, 5)