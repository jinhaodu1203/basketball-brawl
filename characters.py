"""角色配置数据库。新增角色时优先修改这里。"""

CHARACTERS = {
    "djh": {
        "id": "djh",
        "name": "DJH",
        "description": "Balanced player with an explosive first step.",
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
        "sprite_folder": "djh",
    },
    "gorilla": {
        "id": "gorilla",
        "name": "Gorilla",
        "description": "Powerful, heavy and difficult to stop.",
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
        "sprite_folder": "gorilla",
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
        "sprite_folder": "ninja",
    },
}

CHARACTER_ORDER = ["djh", "gorilla", "ninja"]
DEFAULT_PLAYER1_CHARACTER = "djh"
DEFAULT_PLAYER2_CHARACTER = "gorilla"


def get_character(character_id):
    """返回角色配置；ID 不存在时使用 DJH。"""
    return CHARACTERS.get(character_id, CHARACTERS[DEFAULT_PLAYER1_CHARACTER])
