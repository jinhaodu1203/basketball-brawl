"""角色配置数据库。新增角色时优先修改这里。"""

CHARACTERS = {
    "djh": {
        "id": "djh",
        "name": "DJH",
        "description": "The fastest player on the court.",
        "ratings": {"speed": 5, "three": 3, "dunk": 2, "defense": 3},
        "color": (70, 130, 220),
        "move_speed": 5.3,
        "jump_velocity": -14.0,
        "steal_range": 55,
        "ability_type": "dash",
        "ability_name": "Lightning Dash",
        "ability_description": "Rush forward at extreme speed.",
        "ability_cooldown": 180,
        "dash_speed": 17.0,
        "dash_duration": 11,
        "shot_charge_speed": 1.0,
        "shot_perfect_min": 0.42,
        "shot_perfect_max": 0.68,
        "shot_error_scale": 88,
        "sprite_folder": "djh",
        "frame_counts": {'idle': 6, 'run': 8, 'jump': 10, 'walk': 8, 'attack_1': 4, 'attack_2': 3, 'attack_3': 4, 'hurt': 3, 'shield': 2},
        "render_height": 132,
        "ui_accent": (53, 156, 255),
    },
    "gorilla": {
        "id": "gorilla",
        "name": "BRAX",
        "description": "A dominant force in the paint.",
        "ratings": {"speed": 2, "three": 2, "dunk": 5, "defense": 5},
        "color": (125, 90, 75),
        "move_speed": 4.2,
        "jump_velocity": -12.5,
        "steal_range": 68,
        "ability_type": "ground_slam",
        "ability_name": "Ground Slam",
        "ability_description": "Knocks nearby opponents away.",
        "ability_cooldown": 300,
        "slam_range": 115,
        "slam_horizontal_force": 13,
        "slam_vertical_force": -8,
        "shot_charge_speed": 0.85,
        "shot_perfect_min": 0.50,
        "shot_perfect_max": 0.60,
        "shot_error_scale": 118,
        "sprite_folder": "gorilla",
        "frame_counts": {'idle': 6, 'run': 8, 'jump': 12, 'walk': 8, 'attack_1': 6, 'attack_2': 4, 'attack_3': 3, 'hurt': 2, 'shield': 2},
        "render_height": 140,
        "ui_accent": (255, 128, 55),
    },
    "ninja": {
        "id": "ninja",
        "name": "KAGE",
        "description": "Move like a shadow.",
        "ratings": {"speed": 4, "three": 4, "dunk": 3, "defense": 4},
        "color": (100, 90, 180),
        "move_speed": 5.8,
        "jump_velocity": -15.0,
        "steal_range": 50,
        "ability_type": "double_jump",
        "ability_name": "Shadow Jump",
        "ability_description": "Jump one more time in mid-air.",
        "ability_cooldown": 0,
        "double_jump_velocity": -13.5,
        "shot_charge_speed": 1.25,
        "shot_perfect_min": 0.44,
        "shot_perfect_max": 0.62,
        "shot_error_scale": 100,
        "sprite_folder": "ninja",
        "frame_counts": {'idle': 6, 'run': 8, 'jump': 12, 'walk': 8, 'attack_1': 5, 'attack_2': 3, 'attack_3': 4, 'hurt': 2, 'shield': 4},
        "render_height": 136,
        "ui_accent": (167, 92, 255),
    },
    "ace": {
        "id": "ace",
        "name": "ACE",
        "description": "A cold-blooded perimeter scorer.",
        "ratings": {
            "speed": 3,
            "three": 5,
            "dunk": 2,
            "defense": 2,
        },
        "color": (235, 190, 55),

        "move_speed": 4.9,
        "jump_velocity": -13.8,
        "steal_range": 50,

        "ability_type": "deadeye",
        "ability_name": "Deadeye",
        "ability_description": "Expand the perfect shooting window for a short time.",

        "ability_cooldown": 720,
        "deadeye_duration": 300,

        "shot_charge_speed": 1.15,
        "shot_perfect_min": 0.36,
        "shot_perfect_max": 0.70,
        "shot_error_scale": 72,

        # 暂时没有专属贴图时会使用程序绘制角色。
        # 后续直接把 ACE 素材放进 assets/characters/ace 即可。
        "sprite_folder": "ace",

        "frame_counts": {
            "idle": 9,
            "run": 8,
            "jump": 9,
            "walk": 8,
            "attack_1": 5,
            "attack_2": 5,
            "attack_3": 6,
            "hurt": 3,
            "deadeye": 8,
            "aim": 1,
        },

        "render_height": 134,
        "ui_accent": (245, 196, 70),
    },

    "duke": {
        "id": "duke",
        "name": "DUKE",
        "description": "Turn one playmaker into two.",
        "ratings": {"speed": 4, "three": 4, "dunk": 2, "defense": 3},
        "color": (196, 42, 58),
        "move_speed": 5.2,
        "jump_velocity": -14.2,
        "steal_range": 54,
        "ability_type": "clone",
        "ability_name": "Mirror Clone",
        "ability_description": "Create a temporary clone and pass between both bodies.",
        "ability_cooldown": 780,
        "clone_duration": 420,
        "clone_support_distance": 165,
        "shot_charge_speed": 1.08,
        "shot_perfect_min": 0.43,
        "shot_perfect_max": 0.64,
        "shot_error_scale": 94,
        # Duke 本体使用 Converted Vampire；分身使用独立的 Blood Echo 形态。
        "sprite_folder": "duke",
        "frame_counts": {'idle': 5, 'run': 8, 'jump': 7, 'walk': 8, 'attack_1': 5, 'attack_2': 3, 'attack_3': 4, 'hurt': 1, 'shield': 2},
        "clone_sprite_folder": "duke_blood_echo",
        "clone_frame_counts": {'idle': 5, 'run': 6, 'jump': 6, 'walk': 6, 'attack_1': 5, 'attack_2': 4, 'attack_3': 2, 'hurt': 2},
        "render_height": 136,
        "ui_accent": (230, 48, 68),
    },

    "ema": {
        "id": "ema",
        "name": "EMA",
        "description": "A defensive controller with a petrifying gaze.",

        "ratings": {
            "speed": 3,
            "three": 3,
            "dunk": 2,
            "defense": 5,
        },

        # 美杜莎主题：蛇绿色 + 紫色
        "color": (78, 168, 105),
        "ui_accent": (105, 235, 145),

        "move_speed": 4.8,
        "movement_animation_speed_multiplier": 1.35,
        "dribble_speed_multiplier": 0.46,
        "jump_velocity": -13.6,
        "steal_range": 64,

        # ---------- 石化凝视 ----------
        "ability_type": "petrify",
        "ability_name": "Petrifying Gaze",
        "ability_description": "Petrify an opponent caught in her gaze.",
        "ability_cooldown": 720,

        # 210px 射程
        "petrify_range": 210,

        # 70度正面锥形区域
        "petrify_angle": 70,

        # 48帧 ≈ 0.8秒
        "petrify_duration": 48,

        # ---------- 投篮 ----------
        "shot_charge_speed": 1.0,
        "shot_perfect_min": 0.46,
        "shot_perfect_max": 0.62,
        "shot_error_scale": 96,

        # 等真正的美杜莎素材放进来后直接自动读取。
        "sprite_folder": "ema",

        "frame_counts": {
            "idle": 7,
            "run": 7,
            "walk": 13,
            "jump": 1,
            "attack_1": 16,
            "attack_2": 7,
            "attack_3": 10,
            "hurt": 3,
            "shield": 5,
            "special": 5,
            "dead": 3,
        },

        "render_height": 148,
    },

}

CHARACTER_ORDER = ["djh", "gorilla", "ninja", "duke", "ace", "ema"]
DEFAULT_PLAYER1_CHARACTER = "djh"
DEFAULT_PLAYER2_CHARACTER = "gorilla"


def get_character(character_id):
    """返回角色配置；ID 不存在时使用 DJH。"""
    return CHARACTERS.get(character_id, CHARACTERS[DEFAULT_PLAYER1_CHARACTER])
