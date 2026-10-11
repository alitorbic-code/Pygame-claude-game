"""Count real source lines: excludes blanks, comment-only lines, and docstrings.

Usage:  python tools/count_lines.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv"}


def docstring_lines(tree: ast.AST) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines


def count_file(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    skip = docstring_lines(ast.parse(text))
    code = 0
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and number not in skip:
            code += 1
    return code, len(text.splitlines())


def main() -> int:
    rows = []
    for path in sorted(ROOT.rglob("*.py")):
        if SKIP_DIRS.intersection(path.parts):
            continue
        code, physical = count_file(path)
        rows.append((str(path.relative_to(ROOT)), code, physical))
    width = max(len(name) for name, _, _ in rows)
    for name, code, physical in rows:
        print(f"{name:<{width}}  {code:>5} code  {physical:>5} physical")
    print("-" * (width + 24))
    print(f"{'TOTAL':<{width}}  {sum(r[1] for r in rows):>5} code  {sum(r[2] for r in rows):>5} physical")
    game = [r for r in rows if r[0].startswith("srealms")]
    tests = [r for r in rows if r[0].startswith("tests")]
    print(f"\ngame package: {sum(r[1] for r in game)} code lines | tests: {sum(r[1] for r in tests)} code lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
