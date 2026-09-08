from dataclasses import dataclass
from typing import Dict
import os

# Keep your bot token in an environment variable.
BOT_TOKEN: str = "8705986554:AAHy3PhzeTIxHzU7gm3x1PVAPY2mAOejkQI"
DB_PATH: str = "abacus_game.db"

# Maximum number of digits allowed in a single number.
MAX_DIGITS: int = 4

# Maximum number of operators in one question.
MAX_OPERATIONS: int = 8


@dataclass(frozen=True)
class LevelRule:
    digits_max: int
    total_ops: int
    high_ops: int       # Exact count of × / ÷
    time_limit: int     # Seconds
    base_xp: int
    allow_low: bool = True
    allow_high: bool = True


def _build_level_rule(level: int) -> LevelRule:
    """
    Build difficulty rules dynamically for player/question levels.

    Difficulty increases through:
    - Larger numbers
    - More operations
    - More × / ÷ operations
    - More time for genuinely harder questions
    """

    # ---------------------------------------------------------
    # DIGIT PROGRESSION
    # ---------------------------------------------------------
    if level <= 5:
        digits_max = 2
    elif level <= 15:
        digits_max = 3
    else:
        digits_max = 4

    # ---------------------------------------------------------
    # OPERATION PROGRESSION
    #
    # L1-L3   -> 1 op
    # L4-L6   -> 2 ops
    # L7-L9   -> 3 ops
    # L10-L12 -> 4 ops
    # L13-L15 -> 5 ops
    # L16-L18 -> 6 ops
    # L19-L21 -> 7 ops
    # L22+    -> 8 ops (maximum)
    # ---------------------------------------------------------
    total_ops = min(8, 1 + (level - 1) // 3)

    # ---------------------------------------------------------
    # HIGH OPERATION PROGRESSION
    # Controlled instead of relying on rounding.
    # ---------------------------------------------------------
    if level <= 2:
        high_ops = 0
        allow_high = False

    elif level <= 6:
        high_ops = 1
        allow_high = True

    elif level <= 12:
        high_ops = 2
        allow_high = True

    elif level <= 18:
        high_ops = 3
        allow_high = True

    else:
        # Maximum 50% of operators can be × / ÷.
        high_ops = min(4, total_ops // 2)
        allow_high = True

    # Never allow more high operations than total operations.
    high_ops = min(high_ops, total_ops)

    # Low operations exist only when there are remaining operators.
    allow_low = high_ops < total_ops

    # ---------------------------------------------------------
    # TIME
    #
    # More operations  -> more time
    # More × / ÷       -> more time
    # More digits      -> more time
    #
    # Time NEVER decreases just because the level increases.
    # ---------------------------------------------------------
    time_limit = (
        12
        + total_ops * 4
        + high_ops * 3
        + (digits_max - 2) * 5
    )

    # ---------------------------------------------------------
    # XP
    # Gradually increasing reward.
    # ---------------------------------------------------------
    base_xp = round(8 + (level ** 1.6) * 1.6)

    return LevelRule(
        digits_max=digits_max,
        total_ops=total_ops,
        high_ops=high_ops,
        time_limit=time_limit,
        base_xp=base_xp,
        allow_low=allow_low,
        allow_high=allow_high,
    )


# -------------------------------------------------------------
# BUILD LEVEL TABLE
# -------------------------------------------------------------
MAX_LEVEL = 50

LEVEL_SPECS: Dict[int, LevelRule] = {
    level: _build_level_rule(level)
    for level in range(1, MAX_LEVEL + 1)
}