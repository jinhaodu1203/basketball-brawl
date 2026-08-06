"""角色配置数据库。新增角色时优先修改这里。"""

CHARACTERS = {
    "djh": {
        "id": "djh",
        "name": "DJH",
        "description": "Player with an explosive first step.",
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
        "name": "Gorilla",
        "description": "Powerful and heavy.",
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
        "name": "Ninja",
        "description": "Fast, agile and difficult to defend.",
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
}

CHARACTER_ORDER = ["djh", "gorilla", "ninja"]
DEFAULT_PLAYER1_CHARACTER = "djh"
DEFAULT_PLAYER2_CHARACTER = "gorilla"


def get_character(character_id):
    """返回角色配置；ID 不存在时使用 DJH。"""
    return CHARACTERS.get(character_id, CHARACTERS[DEFAULT_PLAYER1_CHARACTER])
