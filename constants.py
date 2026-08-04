"""
2D篮球大乱斗demo的全局配置常量。
"""

# ---------- 屏幕 ----------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
FPS = 60

GROUND_Y = 480  # 地面的y坐标

# ---------- 颜色 ----------
COLOR_BG = (30, 30, 40)
COLOR_GROUND = (60, 60, 70)
COLOR_PLAYER1 = (70, 130, 220)   # 玩家1(蓝)
COLOR_PLAYER2 = (220, 90, 70)    # 玩家2(红)
COLOR_BALL = (240, 160, 40)
COLOR_HOOP = (230, 230, 230)
COLOR_TEXT = (255, 255, 255)
COLOR_DASH_TRAIL = (255, 255, 255)

# ---------- 物理 ----------
GRAVITY = 0.6
JUMP_VELOCITY = -14
MOVE_SPEED = 5
BALL_BOUNCE_DAMPING = 0.6

# ---------- 玩家 ----------
PLAYER_WIDTH = 46
PLAYER_HEIGHT = 68
STEAL_RANGE = 55
POSSESSION_COOLDOWN_FRAMES = 45   # 拿到球后的短暂无敌，防止被秒抢回
STEAL_COOLDOWN_FRAMES = 30

DASH_SPEED = 14
DASH_DURATION_FRAMES = 10
DASH_COOLDOWN_FRAMES = 180  # 3秒 @60fps

# ---------- 篮球 ----------
BALL_RADIUS = 12
SHOT_FLIGHT_FRAMES = 40  # 投篮抛物线大概飞行帧数，用来反推初速度

# ---------- 篮筐(现在挂在场地左侧墙上) ----------
BACKBOARD_X = 26                 # 篮板贴墙的x坐标
RIM_STICK_OUT = 46               # 篮筐从篮板向右探出的距离
RIM_X = BACKBOARD_X + RIM_STICK_OUT
RIM_Y = GROUND_Y - 210           # 篮筐离地高度
HOOP_WIDTH = 46                  # 篮筐得分判定框宽
HOOP_HEIGHT = 14                 # 篮筐得分判定框高
HOOP_X = RIM_X - HOOP_WIDTH // 2
HOOP_Y = RIM_Y - HOOP_HEIGHT // 2
BACKBOARD_HEIGHT = 90
BACKBOARD_TOP_Y = RIM_Y - BACKBOARD_HEIGHT * 0.65

# ---------- 球场标线 ----------
# 简化版真实半场布局(3v3规则)：罚球区/禁区、罚球线、三分线。
# 因为这是侧视角游戏，这些标线被"压扁"贴在地面上，
# 类似经典街球游戏(如NBA Jam)的画法，纯视觉效果，不影响纵向跳跃物理。
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

# ---------- 出生位置 ----------
# 两名玩家都在场地右侧出生，一起进攻左边这个篮筐(类似真实3v3单筐对抗)
PLAYER1_SPAWN_X = 560
PLAYER2_SPAWN_X = 760
BALL_SPAWN_X = 640

# ---------- 动画 ----------
ANIMATION_SPEED = 8               # 每隔多少个游戏帧切换一次动画帧
DEFAULT_FRAME_COUNTS = {"idle": 2, "run": 2, "jump": 1}

# 篮球贴图：3帧，顺序固定对应球的三种状态
# ball.png 里从左到右依次是: 手里 / 手和地面中间(空中) / 地面
BALL_SPRITE_FRAME_COUNT = 3
BALL_STATE_TO_FRAME = {"held": 0, "flying": 1, "loose": 2}

# ---------- 计分规则 ----------
# 本游戏的自定义计分规则(不是真实篮球规则)：
#   投篮出手点在三分线外 -> 2分
#   投篮出手点压线或在三分线内 -> 1分
POINTS_OUTSIDE_THREE = 2
POINTS_ON_OR_INSIDE_THREE = 1

# ---------- 得分反馈 / 回合重置 ----------
SCORE_POPUP_DURATION_FRAMES = 90   # +1/+2 显示约1.5秒
ROUND_RESET_DELAY_FRAMES = 75      # 进球后暂停约1.25秒

SCORE_POPUP_COLOR = (255, 215, 0)

# ---------- 胜负 ----------
WINNING_SCORE = 12  # 谁先拿到这个分数就获胜，游戏立刻结束

# ---------- AI(单人模式对手) ----------
AI_SHOOT_STOP_DISTANCE = 20        # 移动到选定投篮点后，允许的水平误差
AI_TWO_POINT_SHOOT_OFFSET = 130    # AI靠近篮筐后选的"两分区"投篮点，相对篮筐的水平距离
AI_THREE_POINT_SHOOT_MARGIN = 40   # 三分投篮点：在三分线基础上再往外一点
AI_THREE_POINT_SHOT_CHANCE = 0.25  # AI选择走三分投篮点的概率(其余走两分区)
AI_SHOT_MISS_CHANCE = 0.3          # AI投篮时故意加偏移(制造不命中)的概率，避免AI百发百中
AI_SHOT_MISS_OFFSET = 30           # 偏移的像素范围
AI_STEAL_APPROACH_DISTANCE = 30    # AI追人抢断时，允许的水平距离误差
AI_REBOUND_JUMP_RANGE = 60         # 球在头顶附近时，起跳去争抢篮板的水平距离阈值
AI_DASH_TRIGGER_CHANCE = 0.02      # 追球/追人时，每帧触发冲刺技能的概率(有冷却限制，不会连发)

# AI难度预设：每一档在"普通"基础上做倍率/数值调整。
# 这些参数只会应用到AI控制的那个Player实例身上(见 Player.apply_ai_difficulty)，
# 不会改动上面这些全局常量本身，所以不会影响真人玩家的手感。
# "normal"档直接复用上面已经调好的默认值，即"现在的AI难度"。
AI_DIFFICULTY_PRESETS = {
    "easy": {
        "move_speed_multiplier": 0.75,     # 移动变慢
        "dash_speed_multiplier": 0.75,     # 冲刺变弱
        "dash_cooldown_multiplier": 1.6,   # 冲刺冷却变长，用得更少
        "steal_range_multiplier": 0.75,    # 抢断判定范围变小
        "shot_miss_chance": 0.6,           # 投篮很容易不进
        "dash_trigger_chance": 0.01,       # 更少主动冲刺
        "three_point_shot_chance": 0.10,   # 很少尝试三分
    },
    "normal": {
        "move_speed_multiplier": 1.0,
        "dash_speed_multiplier": 1.0,
        "dash_cooldown_multiplier": 1.0,
        "steal_range_multiplier": 1.0,
        "shot_miss_chance": AI_SHOT_MISS_CHANCE,
        "dash_trigger_chance": AI_DASH_TRIGGER_CHANCE,
        "three_point_shot_chance": AI_THREE_POINT_SHOT_CHANCE,
    },
    "hard": {
        "move_speed_multiplier": 1.3,      # 移动更快
        "dash_speed_multiplier": 1.25,     # 冲刺更猛
        "dash_cooldown_multiplier": 0.55,  # 冲刺冷却大幅缩短，用得更频繁
        "steal_range_multiplier": 1.3,     # 抢断判定范围变大
        "shot_miss_chance": 0.08,          # 几乎百发百中
        "dash_trigger_chance": 0.06,       # 更爱主动冲刺
        "three_point_shot_chance": 0.35,   # 更爱尝试三分
    },
}

# 菜单上显示的难度标签
AI_DIFFICULTY_LABELS = {
    "easy": "EZ PZ",
    "normal": "Normal",
    "hard": "Hard as Hell",
}

# ---------- 按键 ----------
# 玩家1: A/D 移动, W 跳跃, Space 投篮/捡球, S 抢断, LShift 冲刺技能
# 玩家2: 方向键左右移动, Up 跳跃, Enter 投篮/捡球, Down 抢断, RCtrl 冲刺技能