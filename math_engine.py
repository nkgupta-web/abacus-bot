import ast
import random
from collections import deque
from typing import Tuple, Optional, Deque, List
from config import LEVEL_SPECS, LevelRule

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
                        raise ValueError("Invalid division")
                    return left // right
            raise ValueError("Invalid AST")
        return int(_eval(node))
    except Exception:
        return None

def get_number(level: int, digits_max: int, is_multiplier: bool = False, is_divisor: bool = False) -> int:
    if is_divisor:
        return random.randint(2, 9) if digits_max <= 2 else random.randint(3, 15)
    if is_multiplier:
        if digits_max == 2:
            return random.randint(2, 9)
        return random.randint(2, 7) if level <= 11 else random.randint(2, 9)

    # Base operand sizes
    if digits_max == 2:
        return random.randint(11, 99)
    # L5-L7: mix 2-digit and small 3-digit
    if level <= 7:
        return random.randint(25, 250)
    return random.randint(50, 600)

def pick_operator_slots(total_ops: int, high_count: int) -> List[str]:
    """Generates an operator sequence without chained high operations (no × ÷ side-by-side)."""
    low_count = total_ops - high_count
    for _ in range(100):
        ops = (["HIGH"] * high_count) + (["LOW"] * low_count)
        random.shuffle(ops)
        # Prevent consecutive high operators
        valid = True
        for i in range(len(ops) - 1):
            if ops[i] == "HIGH" and ops[i+1] == "HIGH":
                valid = False
                break
        if valid:
            concrete_ops = []
            for item in ops:
                if item == "HIGH":
                    concrete_ops.append(random.choice(["×", "÷"]))
                else:
                    concrete_ops.append(random.choice(["+", "−"]))
            return concrete_ops

    # Fallback alternating sequence
    res = []
    for i in range(total_ops):
        res.append(random.choice(["×", "÷"]) if (i % 2 == 1 and high_count > 0) else random.choice(["+", "−"]))
    return res

def generate_question(level: int) -> Tuple[str, int]:
    rule: LevelRule = LEVEL_SPECS.get(level, LEVEL_SPECS[15])

    for _ in range(400):
        # 1. Choose operator sequence matching level rules
        if not rule.allow_high:
            ops = [random.choice(["+", "−"]) for _ in range(rule.total_ops)]
        elif not rule.allow_low:
            ops = [random.choice(["×", "÷"]) for _ in range(rule.total_ops)]
        else:
            ops = pick_operator_slots(rule.total_ops, rule.high_ops)

        # 2. Build operand tokens safely
        tokens: List[str] = [str(get_number(level, rule.digits_max))]

        for op in ops:
            if op == "÷":
                divisor = get_number(level, rule.digits_max, is_divisor=True)
                mult = random.randint(3, 15 if rule.digits_max <= 2 else 25)
                dividend = divisor * mult
                tokens[-1] = str(dividend)
                tokens.append("÷")
                tokens.append(str(divisor))
            elif op == "×":
                multiplier = get_number(level, rule.digits_max, is_multiplier=True)
                # Keep first number within reasonable mental bounds
                if int(tokens[-1]) > 250:
                    tokens[-1] = str(random.randint(15, 120))
                tokens.append("×")
                tokens.append(str(multiplier))
            else:
                tokens.append(op)
                tokens.append(str(get_number(level, rule.digits_max)))

        raw_expr = " ".join(tokens)
        ans = safe_bodmas_eval(raw_expr)

        if ans is None:
            continue
        # Beginner non-negative rule
        if level <= 6 and ans < 0:
            continue
        # Intermediate/final result limits
        if ans > 3000 or ans < -1000:
            continue
        if raw_expr in _recent_questions:
            continue

        _recent_questions.append(raw_expr)
        return f"{raw_expr} = ?", ans

    # Fallback
    return "25 + 35 = ?", 60