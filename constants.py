"""
全局配置常量
Global configuration constants for the 2D basketball brawl demo.
"""

# ---------- 屏幕 / Screen ----------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

GROUND_Y = 480  # 地面的y坐标 / y-coordinate of the ground

# ---------- 颜色 / Colors ----------
COLOR_BG = (30, 30, 40)
COLOR_GROUND = (60, 60, 70)
COLOR_PLAYER1 = (70, 130, 220)   # 蓝队 / Player 1 (blue)
COLOR_PLAYER2 = (220, 90, 70)    # 红队 / Player 2 (red)
COLOR_BALL = (240, 160, 40)
COLOR_HOOP = (230, 230, 230)
COLOR_TEXT = (255, 255, 255)
COLOR_DASH_TRAIL = (255, 255, 255)

# ---------- 物理 / Physics ----------
GRAVITY = 0.6
JUMP_VELOCITY = -14
MOVE_SPEED = 5
BALL_BOUNCE_DAMPING = 0.6

# ---------- 玩家 / Player ----------
PLAYER_WIDTH = 46
PLAYER_HEIGHT = 68
STEAL_RANGE = 55
POSSESSION_COOLDOWN_FRAMES = 45   # 抢到球后短暂无敌，防止被秒抢回 / brief immunity after gaining ball
STEAL_COOLDOWN_FRAMES = 30

DASH_SPEED = 14
DASH_DURATION_FRAMES = 10
DASH_COOLDOWN_FRAMES = 180  # 3秒 @60fps / 3 seconds at 60fps

# ---------- 篮球 / Ball ----------
BALL_RADIUS = 12
SHOT_FLIGHT_FRAMES = 40  # 投篮抛物线大概飞行帧数，用来反推初速度 / used to back-solve initial velocity

# ---------- 篮筐 / Hoop (现在挂在场景左侧的墙上 / now mounted on the left wall) ----------
BACKBOARD_X = 26                 # 篮板贴墙的x坐标 / backboard x-position against the left wall
RIM_STICK_OUT = 46               # 篮筐从篮板向右探出的距离 / how far the rim sticks out from the backboard
RIM_X = BACKBOARD_X + RIM_STICK_OUT
RIM_Y = GROUND_Y - 210           # 篮筐离地高度 / rim height above the ground
HOOP_WIDTH = 46                  # 篮筐得分判定框宽 / scoring hitbox width
HOOP_HEIGHT = 14                 # 篮筐得分判定框高 / scoring hitbox height
HOOP_X = RIM_X - HOOP_WIDTH // 2
HOOP_Y = RIM_Y - HOOP_HEIGHT // 2
BACKBOARD_HEIGHT = 90
BACKBOARD_TOP_Y = RIM_Y - BACKBOARD_HEIGHT * 0.65

# ---------- 球场标线 / Court markings ----------
# 参照真实半场篮球场(3v3规则)简化画出：罚球区(两分线区域边界)、罚球线、
# 三分线。因为是侧视角游戏，这些标线被"压扁"贴在地面上，
# 类似经典街球游戏(如NBA Jam)的画法，只做视觉参考，不影响跳跃等纵向物理。
COLOR_COURT_LINE = (235, 235, 245)
COLOR_PAINT_FILL = (55, 70, 95)
COURT_LINE_WIDTH = 3

PAINT_WIDTH = 150                # 罚球区(禁区)宽度，从底线(左墙)向右延伸
PAINT_BAND_HEIGHT = 120          # 罚球区画在地面上的"高度"(压扁后的视觉厚度)
FREE_THROW_LINE_X = PAINT_WIDTH  # 罚球线x坐标
FREE_THROW_CIRCLE_RADIUS = 45
COURT_BAND_CENTER_Y_OFFSET = 60  # 三分线/两分线圆心相对地面的向上偏移

TWO_POINT_RADIUS = 210           # 两分线(中距离标线)半径，以篮筐为圆心
THREE_POINT_RADIUS = 340         # 三分线半径，以篮筐为圆心
COURT_LINE_FLATTEN = 0.30        # 压扁比例：纵向半径 = 半径 * 该比例，模拟侧视角透视

HALF_COURT_X = SCREEN_WIDTH // 2  # 半场线(中场线)x坐标

# ---------- 出生位置 / Spawn positions ----------
# 两名玩家都在场地右侧出生，一起进攻左边这个篮筐(类似真实3v3单筐对抗)
PLAYER1_SPAWN_X = 560
PLAYER2_SPAWN_X = 760
BALL_SPAWN_X = 640

# ---------- 动画 / Animation ----------
ANIMATION_SPEED = 8               # 每隔多少个游戏帧切换一次动画帧 / game frames per animation frame
DEFAULT_FRAME_COUNTS = {"idle": 2, "run": 2, "jump": 1}

# 篮球贴图：3帧，顺序固定对应球的三种状态
# ball.png 里从左到右依次是: 手里 / 手和地面中间(空中) / 地面
# Ball sprite sheet: 3 frames, left-to-right = held / mid-air(flying) / on-ground(loose)
BALL_SPRITE_FRAME_COUNT = 3
BALL_STATE_TO_FRAME = {"held": 0, "flying": 1, "loose": 2}

# ---------- 按键 / Controls ----------
# 玩家1 / Player 1: A/D 移动, W 跳跃, Space 投篮/捡球, S 抢断, LShift 冲刺技能
# 玩家2 / Player 2: 方向键左右移动, Up 跳跃, Enter 投篮/捡球, Down 抢断, RCtrl 冲刺技能