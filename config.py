from dataclasses import dataclass
from typing import Dict
import os

# Keep bot token in environment variables for deployment safety
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "8705986554:AAHy3PhzeTIxHzU7gm3x1PVAPY2mAOejkQI")
DB_PATH: str = "abacus_game.db"
OWNER_ID = 8810769292

# Maximum limits matching Q20 ABSOLUTE MAX
MAX_DIGITS: int = 5
MAX_OPERATIONS: int = 10


@dataclass(frozen=True)
class LevelRule:
    digits_max: int
    total_ops: int
    high_ops: int       # Maximum count of × / ÷
    parens_pairs: int   # Number of parentheses pairs
    time_limit: int     # Seconds
    base_xp: int
    difficulty_name: str


# -------------------------------------------------------------
# Q1–Q20 EXACT DIFFICULTY MATRIX
# (digits_max, total_ops, high_ops, parens, time_limit, base_xp, name)
# -------------------------------------------------------------
LEVEL_DATA = {
    1:  (1, 1,  0, 0, 15, 10,  "Starter"),
    2:  (1, 2,  0, 0, 15, 14,  "Starter+"),
    3:  (2, 2,  1, 0, 14, 18,  "Basic"),
    4:  (2, 3,  1, 0, 14, 24,  "Basic+"),
    5:  (2, 3,  2, 0, 13, 30,  "Easy"),
    6:  (2, 4,  2, 0, 13, 38,  "Easy+"),
    7:  (3, 4,  2, 0, 12, 48,  "Intermediate"),
    8:  (3, 4,  3, 0, 12, 60,  "Intermediate+"),
    9:  (3, 5,  2, 1, 12, 75,  "Medium"),
    10: (3, 5,  3, 1, 11, 92,  "Medium+"),
    11: (3, 6,  3, 1, 11, 110, "Hard"),
    12: (4, 6,  3, 2, 10, 130, "Hard+"),
    13: (4, 7,  3, 2, 10, 155, "Advanced"),
    14: (4, 7,  4, 2, 10, 180, "Advanced+"),
    15: (4, 8,  4, 3, 9,  210, "Expert"),
    16: (5, 8,  4, 3, 9,  245, "Expert+"),
    17: (5, 8,  5, 3, 8,  285, "Master"),
    18: (5, 9,  5, 4, 8,  330, "Master+"),
    19: (5, 9,  6, 4, 7,  380, "Extreme"),
    20: (5, 10, 6, 5, 7,  450, "ABSOLUTE MAX"),
}


def _build_level_rule(level: int) -> LevelRule:
    """Returns exact specifications for Q1-Q20 or scaled ceiling values for L21+."""
    if level in LEVEL_DATA:
        d_max, t_ops, h_ops, parens, t_limit, xp, name = LEVEL_DATA[level]
        return LevelRule(
            digits_max=d_max,
            total_ops=t_ops,
            high_ops=h_ops,
            parens_pairs=parens,
            time_limit=t_limit,
            base_xp=xp,
            difficulty_name=name,
        )

    # Beyond Level 20 (Cap to Q20 ceiling with scaling XP)
    return LevelRule(
        digits_max=5,
        total_ops=10,
        high_ops=6,
        parens_pairs=5,
        time_limit=7,
        base_xp=450 + (level - 20) * 30,
        difficulty_name="Overdrive",
    )


# Level map building up to 100 for global progress tracking
MAX_LEVEL: int = 100

LEVEL_SPECS: Dict[int, LevelRule] = {
    level: _build_level_rule(level)
    for level in range(1, MAX_LEVEL + 1)
}