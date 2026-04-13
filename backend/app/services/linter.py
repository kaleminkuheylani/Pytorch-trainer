"""PyTorch code linter — basic static checks for common issues."""

from app.models.events import LintIssue

COMMON_ISSUES: list[tuple[str, str, str]] = [
    ("import torch", "info", "PyTorch import detected"),
    (".cuda()", "warning", "Explicit .cuda() call — consider using .to(device) for portability"),
    ("model.train()", "info", "Training mode set"),
    ("model.eval()", "info", "Evaluation mode set"),
    ("torch.no_grad", "info", "Gradient computation disabled for inference"),
    ("torch.save", "info", "Model checkpoint saving detected"),
    ("print(", "warning", "Consider using logging instead of print statements"),
    ("global ", "warning", "Global variable usage detected — may cause issues in training loops"),
    (
        "torch.nn.CrossEntropyLoss",
        "info",
        "CrossEntropyLoss detected — expects raw logits, not softmax output",
    ),
    (
        "optimizer.zero_grad()",
        "info",
        "Gradient zeroing detected — should be called before loss.backward()",
    ),
]

MISSING_CHECKS: list[tuple[str, str, str]] = [
    (
        "optimizer.zero_grad",
        "warning",
        "No optimizer.zero_grad() call found — gradients may accumulate",
    ),
    ("loss.backward", "warning", "No loss.backward() call found — model may not train"),
    ("optimizer.step", "warning", "No optimizer.step() call found — weights may not update"),
]


def lint_pytorch_code(code: str) -> list[LintIssue]:
    """Run basic lint checks on PyTorch code and return issues."""
    issues: list[LintIssue] = []
    lines = code.split("\n")

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for pattern, severity, message in COMMON_ISSUES:
            if pattern in line:
                issues.append(
                    LintIssue(line=line_num, severity=severity, message=message)
                )

    for pattern, severity, message in MISSING_CHECKS:
        if pattern not in code:
            issues.append(LintIssue(line=0, severity=severity, message=message))

    return issues
