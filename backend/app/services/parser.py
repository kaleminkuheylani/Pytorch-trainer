"""Code parser — detects function definitions and extracts signatures."""

import re

from app.models.events import PendingFunction

DEF_PATTERN = re.compile(
    r"^(\s*)def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^:]+)?\s*:\s*$",
    re.MULTILINE,
)

CLASS_PATTERN = re.compile(
    r"^(\s*)class\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*$",
    re.MULTILINE,
)


def detect_pending_functions(code: str) -> list[PendingFunction]:
    """Scan code for function definitions and return them as pending."""
    functions: list[PendingFunction] = []
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):
        match = DEF_PATTERN.match(line)
        if match:
            _indent, name, params = match.groups()
            signature = f"def {name}({params})"
            functions.append(
                PendingFunction(
                    name=name,
                    line=line_num,
                    signature=signature,
                    status="pending",
                )
            )

    return functions


def has_new_defs(old_code: str, new_code: str) -> list[PendingFunction]:
    """Return only the NEW function definitions added between old and new code."""
    old_funcs = {f.name for f in detect_pending_functions(old_code)}
    new_funcs = detect_pending_functions(new_code)
    return [f for f in new_funcs if f.name not in old_funcs]


def extract_imports(code: str) -> list[str]:
    """Extract import statements from code."""
    imports: list[str] = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
    return imports
