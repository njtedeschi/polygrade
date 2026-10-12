from __future__ import annotations

from dataclasses import dataclass

PASS_MESSAGE = "All tests passed!"


@dataclass
class ProblemResult:
    """The outcome of grading one problem.

    ``credit`` is a fraction of the problem's weight. ``passed`` controls
    whether the Gradescope test is shown as passed; a result can award full
    credit and still carry an explanatory message (e.g. a waived penalty).
    """

    credit: float
    passed: bool
    message: str = PASS_MESSAGE

    @classmethod
    def full(cls, message: str = PASS_MESSAGE) -> "ProblemResult":
        return cls(credit=1.0, passed=True, message=message)

    @classmethod
    def partial(cls, credit: float, message: str) -> "ProblemResult":
        return cls(credit=credit, passed=False, message=message)

    @classmethod
    def zero(cls, message: str) -> "ProblemResult":
        return cls(credit=0.0, passed=False, message=message)
