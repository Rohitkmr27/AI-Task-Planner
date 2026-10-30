"""
Safe Mathematical Calculator Tool.

Evaluates mathematical expressions using AST-based parsing without
calling unsafe functions like eval() or exec().
"""

from __future__ import annotations

import ast
import math
import operator
import time
from typing import Any, Callable

from langchain_core.tools import tool

from src.agent.tools.base import ToolResult


# Supported binary operators
_SAFE_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
_SAFE_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Supported math functions and constants
_SAFE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "factorial": math.factorial,
    "pow": math.pow,
}

_SAFE_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _eval_node(node: ast.AST) -> float | int:
    """Recursively evaluate an AST node safely."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        # Prevent huge exponents that cause denial of service
        if op_type is ast.Pow and (abs(right) > 1000 or (abs(left) > 1000 and right > 10)):
            raise ValueError("Exponent or base too large for safe evaluation")
        return _SAFE_OPERATORS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_UNARY_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_node(node.operand)
        return _SAFE_UNARY_OPERATORS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only direct function calls are supported")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Unsupported function: '{func_name}'")
        args = [_eval_node(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Unsupported variable or constant: '{node.id}'")

    raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def evaluate_expression(expression: str) -> float | int:
    """
    Safely evaluate a mathematical expression string using an AST visitor.

    Parameters
    ----------
    expression : str
        The mathematical expression to evaluate (e.g. '2 + 2', 'sqrt(144) * 3').

    Returns
    -------
    float | int
        The calculated numerical result.
    """
    clean_expr = expression.strip()
    if not clean_expr:
        raise ValueError("Empty mathematical expression")

    try:
        parsed = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid math syntax: {e}") from e

    return _eval_node(parsed)


def run_calculator(expression: str) -> ToolResult:
    """
    Run mathematical calculation and return a standardised ToolResult.
    """
    start_time = time.perf_counter()
    tool_name = "calc"
    try:
        result = evaluate_expression(expression)
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=True,
            output=str(result),
            error=None,
            duration_s=round(duration, 4),
            tokens_used=max(10, len(expression) // 2),
            requires_approval=False,
            metadata={"expression": expression, "numeric_result": result},
        )
    except Exception as e:
        duration = time.perf_counter() - start_time
        return ToolResult(
            tool_name=tool_name,
            success=False,
            output="",
            error=f"Calculation error: {e}",
            duration_s=round(duration, 4),
            tokens_used=5,
            requires_approval=False,
            metadata={"expression": expression},
        )


@tool("calc")
def calculator_tool(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    Supports basic arithmetic (+, -, *, /, **, %, //), functions (sqrt, sin, cos, tan, log, exp, abs, round, ceil, floor, factorial),
    and constants (pi, e, tau).
    """
    res = run_calculator(expression)
    if res.success:
        return f"Result: {res.output}"
    return f"Error: {res.error}"
