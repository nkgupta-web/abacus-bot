import ast
import random
from collections import deque
from typing import Tuple, Optional, Deque, List

from config import LEVEL_SPECS

_recent_questions: Deque[str] = deque(maxlen=80)

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

def get_number(digits_max: int, is_multiplier: bool = False, is_divisor: bool = False) -> int:
    if is_divisor:
        return random.randint(2, 9) if digits_max <= 2 else random.randint(2, 15)

    if is_multiplier:
        if digits_max == 1:
            return random.randint(2, 9)
        elif digits_max <= 3:
            return random.randint(2, 12)
        return random.randint(3, 20)

    if digits_max == 1:
        return random.randint(1, 9)

    low = 10 ** (digits_max - 1)
    high = (10 ** digits_max) - 1
    return random.randint(low, high)

def apply_parentheses(tokens: List[str], max_parens: int) -> List[str]:
    if max_parens <= 0 or len(tokens) < 5:
        return tokens

    result = list(tokens)
    applied = 0
    attempts = 0

    while applied < max_parens and attempts < 20:
        attempts += 1
        # Random pair around 2 adjacent numbers with their operator
        start_idx = random.randrange(0, len(result) - 2, 2)
        end_idx = start_idx + 2

        # Overlapping check
        if not result[start_idx].startswith("(") and not result[end_idx].endswith(")"):
            # Avoid placing parens that cause clean division to break
            if end_idx + 1 < len(result) and result[end_idx + 1] == "÷":
                continue
            result[start_idx] = "(" + result[start_idx]
            result[end_idx] = result[end_idx] + ")"
            applied += 1

    return result

def generate_question(level: int) -> Tuple[str, int]:
    q_level = max(1, min(20, int(level)))
    spec = LEVEL_SPECS.get(q_level, LEVEL_SPECS[20])

    digits_max = spec.digits_max
    total_ops = spec.total_ops
    high_ops = spec.high_ops
    parens_pairs = spec.parens_pairs

    # Handcrafted early levels for speed & zero-wait latency
    if q_level == 1:
        a, b = random.randint(1, 9), random.randint(1, 9)
        return f"{a} + {b} = ?", a + b

    if q_level == 2:
        a, b, c = random.randint(2, 9), random.randint(1, 9), random.randint(1, 9)
        if a + b - c > 0 and random.random() > 0.5:
            return f"{a} + {b} − {c} = ?", a + b - c
        return f"{a} + {b} + {c} = ?", a + b + c

    for _ in range(300):
        # Operators distribution
        low_count = total_ops - high_ops
        slot_types = (["HIGH"] * high_ops) + (["LOW"] * low_count)
        random.shuffle(slot_types)

        tokens: List[str] = [str(get_number(digits_max))]

        for slot in slot_types:
            if slot == "HIGH":
                op = "×" if random.random() < 0.65 else "÷"
                if op == "÷":
                    divisor = get_number(digits_max, is_divisor=True)
                    # Guaranteed integer division: multiply previous token
                    prev_val = int(tokens[-1].strip("()")) if tokens[-1].strip("()").isdigit() else random.randint(2, 20)
                    tokens[-1] = str(prev_val * divisor)
                    tokens.append("÷")
                    tokens.append(str(divisor))
                else:
                    mult = get_number(digits_max, is_multiplier=True)
                    tokens.append("×")
                    tokens.append(str(mult))
            else:
                op = random.choice(["+", "−"])
                tokens.append(op)
                tokens.append(str(get_number(digits_max)))

        if parens_pairs > 0:
            tokens = apply_parentheses(tokens, parens_pairs)

        raw_expr = " ".join(tokens)
        ans = safe_bodmas_eval(raw_expr)

        if ans is None:
            continue

        # Prevent negative answers for beginner/intermediate tiers
        if q_level <= 6 and ans < 0:
            continue

        if raw_expr in _recent_questions:
            continue

        _recent_questions.append(raw_expr)
        return f"{raw_expr} = ?", ans

    # Safe fallback matching digits
    a, b = get_number(digits_max), get_number(digits_max)
    return f"{a} + {b} = ?", a + b