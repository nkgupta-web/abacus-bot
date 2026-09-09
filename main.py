import ast
import random
from collections import deque
from typing import Tuple, Optional, Deque, List
from dataclasses import dataclass
from handlers import restore_xp_command

_recent_questions: Deque[str] = deque(maxlen=80)

@dataclass(frozen=True)
class QuestionDifficultyRule:
    max_digits: int
    total_ops: int
    high_ops: int
    max_parens: int

# =========================================================
# EXACT 20 QUESTION LEVELS (Q1 - Q20)
# =========================================================
QUESTION_LEVEL_SPECS = {
    1:  QuestionDifficultyRule(max_digits=1, total_ops=1,  high_ops=0, max_parens=0),
    2:  QuestionDifficultyRule(max_digits=1, total_ops=2,  high_ops=0, max_parens=0),
    3:  QuestionDifficultyRule(max_digits=2, total_ops=2,  high_ops=1, max_parens=0),
    4:  QuestionDifficultyRule(max_digits=2, total_ops=3,  high_ops=1, max_parens=0),
    5:  QuestionDifficultyRule(max_digits=2, total_ops=4,  high_ops=1, max_parens=0),
    6:  QuestionDifficultyRule(max_digits=2, total_ops=4,  high_ops=2, max_parens=0),
    7:  QuestionDifficultyRule(max_digits=3, total_ops=5,  high_ops=2, max_parens=0),
    8:  QuestionDifficultyRule(max_digits=3, total_ops=6,  high_ops=2, max_parens=0),
    9:  QuestionDifficultyRule(max_digits=3, total_ops=6,  high_ops=3, max_parens=0),
    10: QuestionDifficultyRule(max_digits=3, total_ops=7,  high_ops=3, max_parens=1),
    11: QuestionDifficultyRule(max_digits=4, total_ops=7,  high_ops=3, max_parens=1),
    12: QuestionDifficultyRule(max_digits=4, total_ops=8,  high_ops=4, max_parens=1),
    13: QuestionDifficultyRule(max_digits=4, total_ops=8,  high_ops=4, max_parens=1),
    14: QuestionDifficultyRule(max_digits=4, total_ops=9,  high_ops=5, max_parens=2),
    15: QuestionDifficultyRule(max_digits=4, total_ops=9,  high_ops=5, max_parens=2),
    16: QuestionDifficultyRule(max_digits=4, total_ops=10, high_ops=5, max_parens=2),
    17: QuestionDifficultyRule(max_digits=5, total_ops=10, high_ops=5, max_parens=3),
    18: QuestionDifficultyRule(max_digits=5, total_ops=10, high_ops=6, max_parens=3),
    19: QuestionDifficultyRule(max_digits=5, total_ops=10, high_ops=6, max_parens=3),
    20: QuestionDifficultyRule(max_digits=5, total_ops=10, high_ops=6, max_parens=3),
}

def safe_bodmas_eval(expr_str: str) -> Optional[int]:
    clean_expr = (
        expr_str.replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("—", "-")
        .replace("–", "-")
    )
    try:
        node = ast.parse(clean_expr, mode='eval')
        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                return n.value
            elif isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
                return -_eval(n.operand)
            elif isinstance(n, ast.BinOp):
                left = _eval(n.left)
                right = _eval(n.right)
                if isinstance(n.op, ast.Add):
                    return left + right
                elif isinstance(n.op, ast.Sub):
                    return left - right
                elif isinstance(n.op, ast.Mult):
                    return left * right
                elif isinstance(n.op, ast.Div):
                    if right == 0 or left % right != 0:
                        raise ValueError("Non-integer division")
                    return left // right
            raise ValueError("Invalid AST")
        return int(_eval(node))
    except Exception:
        return None

def get_number(level: int, digits_max: int, is_multiplier: bool = False, is_divisor: bool = False) -> int:
    if is_divisor:
        if digits_max <= 2:
            return random.randint(2, 9)
        elif digits_max == 3:
            return random.randint(3, 20)
        elif digits_max == 4:
            return random.randint(5, 50)
        else:
            return random.randint(12, 99)

    if is_multiplier:
        if digits_max == 1:
            return random.randint(2, 9)
        if digits_max <= 3:
            return random.randint(2, 12)
        # Heavy scaling for Q18-Q20
        return random.randint(15, 60) if level >= 18 else random.randint(3, 25)

    if digits_max == 1:
        return random.randint(1, 9)

    low = 10 ** (digits_max - 1)
    high = (10 ** digits_max) - 1

    # Inherent difficulty distinction: Q19 vs Q20
    if level == 19:
        low = max(low, 35000)
    elif level == 20:
        low = max(low, 65000)  # Forces upper tier 5-digit operands for Q20

    return random.randint(low, high)

def pick_operator_slots(total_ops: int, high_count: int, level: int) -> List[str]:
    low_count = total_ops - high_count
    ops = (["HIGH"] * high_count) + (["LOW"] * low_count)
    random.shuffle(ops)

    concrete_ops = []
    for item in ops:
        if item == "HIGH":
            # Q20 has higher multiplication bias over division
            if level == 20:
                concrete_ops.append("×" if random.random() < 0.70 else "÷")
            else:
                concrete_ops.append(random.choice(["×", "÷"]))
        else:
            concrete_ops.append(random.choice(["+", "−"]))
    return concrete_ops

def apply_parentheses(tokens: List[str], max_parens: int) -> List[str]:
    if max_parens <= 0 or len(tokens) < 5:
        return tokens

    result = list(tokens)
    applied = 0
    attempts = 0

    while applied < max_parens and attempts < 15:
        attempts += 1
        start_idx = random.randrange(0, len(result) - 2, 2)
        end_idx = start_idx + 2

        if not result[start_idx].startswith("(") and not result[end_idx].endswith(")"):
            result[start_idx] = "(" + result[start_idx]
            result[end_idx] = result[end_idx] + ")"
            applied += 1

    return result

def generate_question(level: int) -> Tuple[str, int]:
    # Strictly enforce Q1 to Q20 boundaries (Q20 is maximum)
    q_level = max(1, min(20, int(level)))
    rule = QUESTION_LEVEL_SPECS[q_level]

    for _ in range(1200):
        ops = pick_operator_slots(rule.total_ops, rule.high_ops, q_level)
        tokens: List[str] = [str(get_number(q_level, rule.max_digits))]

        for op in ops:
            if op == "÷":
                divisor = get_number(q_level, rule.max_digits, is_divisor=True)
                tokens.append("÷")
                tokens.append(str(divisor))
            elif op == "×":
                multiplier = get_number(q_level, rule.max_digits, is_multiplier=True)
                tokens.append("×")
                tokens.append(str(multiplier))
            else:
                tokens.append(op)
                tokens.append(str(get_number(q_level, rule.max_digits)))

        if rule.max_parens > 0:
            tokens = apply_parentheses(tokens, rule.max_parens)

        raw_expr = " ".join(tokens)
        ans = safe_bodmas_eval(raw_expr)

        # 1. Exact division check & AST validation
        if ans is None:
            continue

        # 2. Level 1-6 non-negative result check
        if q_level <= 6 and ans < 0:
            continue

        # 3. Prevent duplicate questions
        if raw_expr in _recent_questions:
            continue

        _recent_questions.append(raw_expr)
        return f"{raw_expr} = ?", ans

    return "25 + 35 = ?", 60