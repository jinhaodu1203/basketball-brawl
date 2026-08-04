"""
角色配置数据库。

以后新增角色时，主要在这里添加配置，
不需要为每个角色重新写一个 Player 类。

贴图默认放在：
assets/characters/<角色ID>/
"""

CHARACTERS = {
    "cheetah": {
        "id": "cheetah",
        "name": "Cheetah",
        "description": "Fast and aggressive.",
        "color": (235, 180, 45),

        # 基础能力
        "move_speed": 6.5,
        "jump_velocity": -14.0,
        "dash_speed": 18.0,
        "dash_duration": 12,
        "dash_cooldown": 160,
        "steal_range": 50,

        # 技能信息
        "skill_type": "speed_dash",
        "skill_name": "Lightning Dash",
        "skill_description": "A longer and faster dash.",

        # 对应 assets/characters/cheetah/
        "sprite_folder": "cheetah",
    },

    "gorilla": {
        "id": "gorilla",
        "name": "Gorilla",
        "description": "Strong but slower.",
        "color": (125, 90, 75),

        "move_speed": 4.2,
        "jump_velocity": -12.5,
        "dash_speed": 12.0,
        "dash_duration": 9,
        "dash_cooldown": 210,
        "steal_range": 68,

        "skill_type": "ground_slam",
        "skill_name": "Ground Slam",
        "skill_description": "Knocks nearby opponents away.",

        "sprite_folder": "gorilla",
    },

    "ninja": {
        "id": "ninja",
        "name": "Ninja",
        "description": "Agile and difficult to guard.",
        "color": (100, 90, 180),

        "move_speed": 5.7,
        "jump_velocity": -15.5,
        "dash_speed": 15.0,
        "dash_duration": 9,
        "dash_cooldown": 180,
        "steal_range": 52,

        "skill_type": "double_jump",
        "skill_name": "Shadow Jump",
        "skill_description": "Can jump a second time in the air.",

        "sprite_folder": "ninja",
    },
}


CHARACTER_ORDER = [
    "cheetah",
    "gorilla",
    "ninja",
]


DEFAULT_PLAYER1_CHARACTER = "cheetah"
DEFAULT_PLAYER2_CHARACTER = "gorilla"


def get_character(character_id):
    """
    根据角色ID返回角色配置。

    如果ID不存在，自动返回默认角色，防止游戏直接报错。
    """
    return CHARACTERS.get(
        character_id,
        CHARACTERS[DEFAULT_PLAYER1_CHARACTER],
    )