from typing import Tuple, Dict

# Progression Table — Level 1 to 100 (10M Total XP Cap)
LEVEL_PROGRESSION: Dict[int, Tuple[int, str]] = {
    # 🥉 NOVICE TIER
    1:  (0, "🥉 Novice I"),
    2:  (1020, "🥉 Novice II"),
    3:  (4081, "🥉 Novice III"),
    4:  (9183, "🥉 Novice IV"),
    5:  (16325, "🥉 Novice V"),

    # 🥈 ROOKIE TIER
    6:  (25508, "🥈 Rookie I"),
    7:  (36731, "🥈 Rookie II"),
    8:  (49995, "🥈 Rookie III"),
    9:  (65299, "🥈 Rookie IV"),
    10: (82645, "🥈 Rookie V"),

    # 🎖️ SOLVER TIER
    11: (102030, "🎖️ Solver I"),
    12: (123457, "🎖️ Solver II"),
    13: (146924, "🎖️ Solver III"),
    14: (172431, "🎖️ Solver IV"),
    15: (199980, "🎖️ Solver V"),

    # 🏅 PRO TIER
    16: (229568, "🏅 Pro I"),
    17: (261198, "🏅 Pro II"),
    18: (294867, "🏅 Pro III"),
    19: (330578, "🏅 Pro IV"),
    20: (368329, "🏅 Pro V"),

    # 💠 PRIME TIER
    21: (408120, "💠 Prime I"),
    22: (449953, "💠 Prime II"),
    23: (493825, "💠 Prime III"),
    24: (539739, "💠 Prime IV"),
    25: (587693, "💠 Prime V"),

    # ⚔️ ACE TIER
    26: (637687, "⚔️ Ace I"),
    27: (689722, "⚔️ Ace II"),
    28: (743798, "⚔️ Ace III"),
    29: (799914, "⚔️ Ace IV"),
    30: (858071, "⚔️ Ace V"),

    # 💎 ELITE TIER
    31: (918269, "💎 Elite I"),
    32: (980507, "💎 Elite II"),
    33: (1044786, "💎 Elite III"),
    34: (1111105, "💎 Elite IV"),
    35: (1179466, "💎 Elite V"),

    # 🔮 MASTER TIER
    36: (1249866, "🔮 Master I"),
    37: (1322308, "🔮 Master II"),
    38: (1396790, "🔮 Master III"),
    39: (1473313, "🔮 Master IV"),
    40: (1551876, "🔮 Master V"),

    # 👑 GRAND MASTER TIER
    41: (1632480, "👑 Grand Master I"),
    42: (1715125, "👑 Grand Master II"),
    43: (1799810, "👑 Grand Master III"),
    44: (1886536, "👑 Grand Master IV"),
    45: (1975303, "👑 Grand Master V"),

    # ⚡ LEGEND TIER
    46: (2066110, "⚡ Legend I"),
    47: (2158957, "⚡ Legend II"),
    48: (2253846, "⚡ Legend III"),
    49: (2350774, "⚡ Legend IV"),
    50: (2449744, "⚡ Legend V"),

    # 🌠 MYTHIC TIER
    51: (2550754, "🌠 Mythic I"),
    52: (2653805, "🌠 Mythic II"),
    53: (2758896, "🌠 Mythic III"),
    54: (2866028, "🌠 Mythic IV"),
    55: (2975200, "🌠 Mythic V"),

    # 🔱 SOVEREIGN TIER
    56: (3086413, "🔱 Sovereign I"),
    57: (3199667, "🔱 Sovereign II"),
    58: (3314961, "🔱 Sovereign III"),
    59: (3432296, "🔱 Sovereign IV"),
    60: (3551672, "🔱 Sovereign V"),

    # 🌀 TRANSCENDENT TIER
    61: (3673088, "🌀 Transcendent I"),
    62: (3796545, "🌀 Transcendent II"),
    63: (3922043, "🌀 Transcendent III"),
    64: (4049581, "🌀 Transcendent IV"),
    65: (4179160, "🌀 Transcendent V"),

    # 🛡️ IMMORTAL TIER
    66: (4310780, "🛡️ Immortal I"),
    67: (4444440, "🛡️ Immortal II"),
    68: (4580141, "🛡️ Immortal III"),
    69: (4717882, "🛡️ Immortal IV"),
    70: (4857665, "🛡️ Immortal V"),

    # ✨ CELESTIAL TIER
    71: (4999487, "✨ Celestial I"),
    72: (5143351, "✨ Celestial II"),
    73: (5289255, "✨ Celestial III"),
    74: (5437199, "✨ Celestial IV"),
    75: (5587185, "✨ Celestial V"),

    # ⏳ ETERNAL TIER
    76: (5739211, "⏳ Eternal I"),
    77: (5893278, "⏳ Eternal II"),
    78: (6049385, "⏳ Eternal III"),
    79: (6207533, "⏳ Eternal IV"),
    80: (6367722, "⏳ Eternal V"),

    # 🔥 APEX TIER
    81: (6529951, "🔥 Apex I"),
    82: (6694222, "🔥 Apex II"),
    83: (6860533, "🔥 Apex III"),
    84: (7028884, "🔥 Apex IV"),
    85: (7199277, "🔥 Apex V"),

    # 🌌 SUPREME TIER
    86: (7371710, "🌌 Supreme I"),
    87: (7546183, "🌌 Supreme II"),
    88: (7722698, "🌌 Supreme III"),
    89: (7901253, "🌌 Supreme IV"),
    90: (8081849, "🌌 Supreme V"),

    # 💫 ULTIMATE TIER
    91: (8264485, "💫 Ultimate I"),
    92: (8449163, "💫 Ultimate II"),
    93: (8635881, "💫 Ultimate III"),
    94: (8824639, "💫 Ultimate IV"),
    95: (9015438, "💫 Ultimate V"),

    # 🚀 COSMIC ASCENSION
    96: (9208277, "🚀 Cosmic"),
    97: (9403157, "🪐 Hyper Cosmic"),
    98: (9600077, "☄️ Infinite Cosmic"),
    99: (9799037, "🌠 Beyond Cosmic"),

    # 🐐 THE G.O.A.T
    100: (10000000, "🐐 The G.O.A.T"),
}

MAX_LEVEL = 100


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