from typing import Tuple, Dict

# Smooth quadratic XP progression — Level 1 to 50
LEVEL_PROGRESSION: Dict[int, Tuple[int, str]] = {
    # 🥉 NOVICE TIER
    1:  (0, "🥉 Novice Ⅰ"),
    2:  (104, "🥉 Novice Ⅱ"),
    3:  (416, "🥉 Novice Ⅲ"),
    4:  (937, "🥉 Novice Ⅳ"),
    5:  (1666, "🥉 Novice Ⅴ"),

    # 🥈 ROOKIE TIER
    6:  (2603, "🥈 Rookie Ⅰ"),
    7:  (3748, "🥈 Rookie Ⅱ"),
    8:  (5102, "🥈 Rookie Ⅲ"),
    9:  (6664, "🥈 Rookie Ⅳ"),
    10: (8434, "🥈 Rookie Ⅴ"),

    # 🎖️ SOLVER TIER
    11: (10412, "🎖️ Solver Ⅰ"),
    12: (12599, "🎖️ Solver Ⅱ"),
    13: (14994, "🎖️ Solver Ⅲ"),
    14: (17597, "🎖️ Solver Ⅳ"),
    15: (20408, "🎖️ Solver Ⅴ"),

    # 🏅 PRO TIER
    16: (23428, "🏅 Pro Ⅰ"),
    17: (26656, "🏅 Pro Ⅱ"),
    18: (30090, "🏅 Pro Ⅲ"),
    19: (33740, "🏅 Pro Ⅳ"),
    20: (37590, "🏅 Pro Ⅴ"),

    # ⚔️ ACE TIER
    21: (41650, "⚔️ Ace Ⅰ"),
    22: (45920, "⚔️ Ace Ⅱ"),
    23: (50400, "⚔️ Ace Ⅲ"),
    24: (55080, "⚔️ Ace Ⅳ"),
    25: (59980, "⚔️ Ace Ⅴ"),

    # 💎 ELITE TIER
    26: (65080, "💎 Elite Ⅰ"),
    27: (70390, "💎 Elite Ⅱ"),
    28: (75910, "💎 Elite Ⅲ"),
    29: (81630, "💎 Elite Ⅳ"),
    30: (87570, "💎 Elite Ⅴ"),

    # 🔮 MASTER TIER
    31: (93710, "🔮 Master Ⅰ"),
    32: (100060, "🔮 Master Ⅱ"),
    33: (106620, "🔮 Master Ⅲ"),
    34: (113390, "🔮 Master Ⅳ"),
    35: (120370, "🔮 Master Ⅴ"),

    # 👑 GRAND MASTER TIER
    36: (127550, "👑 Grand Master Ⅰ"),
    37: (134940, "👑 Grand Master Ⅱ"),
    38: (142550, "👑 Grand Master Ⅲ"),
    39: (150350, "👑 Grand Master Ⅳ"),
    40: (158370, "👑 Grand Master Ⅴ"),

    # 🌌 ABACUS MASTER TIER
    41: (166600, "🌌 Abacus Master Ⅰ"),
    42: (175030, "🌌 Abacus Master Ⅱ"),
    43: (183670, "🌌 Abacus Master Ⅲ"),
    44: (192520, "🌌 Abacus Master Ⅳ"),
    45: (201580, "🌌 Abacus Master Ⅴ"),

    # ⚡ LEGENDARY TIER
    46: (210850, "⚡ Legend"),
    47: (220330, "🌠 Mythic Legend"),
    48: (230010, "🔥 Apex Legend"),
    49: (239900, "🔱 Sovereign Legend"),

    # 🐐 ENDGAME
    50: (250000, "🐐 G.O.A.T ✨"),
}

MAX_LEVEL = 50


def calculate_player_level(total_xp: int) -> int:
    current_level = 1

    for lvl in range(1, MAX_LEVEL + 1):
        req_xp, _ = LEVEL_PROGRESSION[lvl]

        if total_xp >= req_xp:
            current_level = lvl
        else:
            break

    return current_level


def get_level_badge(level: int) -> str:
    level = max(1, min(MAX_LEVEL, level))
    _, badge = LEVEL_PROGRESSION[level]
    return badge


def get_level_progress(total_xp: int) -> Tuple[int, str, int, int]:
    level = calculate_player_level(total_xp)
    badge = get_level_badge(level)

    if level >= MAX_LEVEL:
        next_level_xp = LEVEL_PROGRESSION[MAX_LEVEL][0]
        xp_needed = 0
    else:
        next_level_xp = LEVEL_PROGRESSION[level + 1][0]
        xp_needed = max(0, next_level_xp - total_xp)

    return level, badge, next_level_xp, xp_needed