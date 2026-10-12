"""Grading Python submissions by comparing them with a reference solution.

Each problem names a function (or class) that students implement. For every
test input, the submission's output is compared with the solution's.

- Functions from *earlier* problems (plus any ``additional_prerequisites``)
  are patched with the solution's versions while a problem is graded, so a
  mistake is only penalized once.
- ``partial_credit`` entries name alternative, incorrect implementations in
  the solution module. If the submission matches one of them on every input,
  it earns that entry's credit.
"""
from __future__ import annotations

import copy
import functools
import random
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from unittest.mock import patch

import numpy as np

from polygrade.config import Problem
from polygrade.grader import Check, Grader, GraderTestCase
from polygrade.messages import error_message
from polygrade.python import compare
from polygrade.python.fixes import Fix
from polygrade.python.loader import (defined_functions_and_classes, has_function_or_class,
                                     import_from_path)
from polygrade.results import ProblemResult


@dataclass
class Input:
    """The positional and keyword arguments of one call to a problem's function."""

    args: Sequence[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def of(cls, *args, **kwargs) -> "Input":
        """``Input.of(x, y, k=2)`` is shorthand for ``Input(args=[x, y], kwargs={"k": 2})``."""
        return cls(args=list(args), kwargs=kwargs)


@dataclass
class Mismatch:
    """Why a submission's output differed from a target implementation's for one input."""

    test_input: Input
    error: Optional[str] = None
    actual: Any = None
    expected: Any = None

    def describe(self) -> str:
        if self.error is not None:
            return f"An error occurred:\n{self.error}"
        return compare.comparison_message(self.actual, self.expected)


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch = sys.modules.get("torch")
    if torch is not None:
        torch.manual_seed(seed)


class PythonTestCase(GraderTestCase):
    """Test case base class with conveniences for hand-written Python problem tests."""

    grader: "PythonGrader"

    @property
    def submission(self):
        return self.grader.submission

    @property
    def solution(self):
        return self.grader.solution

    def patch_context(self, problem: Problem, additional_patches: Iterable[str] = ()):
        return self.grader.patch_context(problem, additional_patches)

    def run_problem(self, problem: Problem) -> ProblemResult:
        return self.grader.grade_problem(problem)

    def assert_outputs_match(self, actual, expected, **tolerances):
        compare.assert_outputs_match(actual, expected, **tolerances)


class PythonGrader(Grader):
    """Grades a Python submission against a solution module.

    Config paths: ``submission`` and ``solution`` are required. ``starter``
    is optional; if given, the submission must define every function and
    class the starter defines, otherwise every problem's function.

    Per-problem options: ``additional_prerequisites`` (names to patch with the
    solution's version besides earlier problems' functions), ``rtol`` and
    ``atol`` (comparison tolerances), ``seed`` (reseed ``random``, NumPy and
    PyTorch before each call), and ``copy_inputs`` (default true: pass each
    call a deep copy of the inputs, so in-place mutation by one call cannot
    affect the next).
    """

    language = "python"
    test_case_class = PythonTestCase

    def __init__(self, config, fixes: Iterable[Fix] = ()):
        super().__init__(config)
        self.fixes = list(fixes)
        self.test_inputs: Dict[int, List[Input]] = {problem.number: [] for problem in self.problems}
        self.comparators: Dict[int, Callable[[Any, Any], None]] = {}

        self.submission_path = config.path("submission")
        self.solution = import_from_path(config.path("solution"))
        starter_path = config.path("starter", required=False)
        if starter_path is not None:
            self.required_items = defined_functions_and_classes(import_from_path(starter_path))
        else:
            self.required_items = [problem.name for problem in self.problems]

        self.submission = None
        self.import_error: Optional[str] = None
        if self.submission_path.is_file():
            try:
                self.submission = import_from_path(self.submission_path)
            except (Exception, SystemExit) as e:
                self.import_error = error_message(e)
        if self.submission is not None:
            for fix in self.fixes:
                try:
                    fix(self.submission)
                except Exception:  # a fix is best-effort; never let it break grading
                    pass

    # Setting up problems

    def set_test_inputs(self, problem_id, *test_inputs: Input):
        self.test_inputs[self.problems[problem_id].number] = list(test_inputs)

    def set_comparator(self, problem_id, comparator: Callable[[Any, Any], None]):
        """Use ``comparator(actual, expected)``, which raises on a mismatch, for one problem."""
        self.comparators[self.problems[problem_id].number] = comparator

    def prerequisites(self, problem: Problem) -> List[str]:
        earlier = [p.name for p in self.problems if p.number < problem.number]
        return earlier + list(problem.options.get("additional_prerequisites", []))

    # Prerequisite checks

    def prerequisite_checks(self) -> List[Check]:
        filename = self.submission_path.name
        return [
            Check("submitted", "Submission file found", self._check_submitted),
            Check("imports", f"{filename} can be imported", self._check_imports),
            Check("follows_starter", f"{filename} defines everything the starter code does",
                  self._check_follows_starter),
        ]

    def _check_submitted(self):
        name = self.submission_path.name
        if self.submission_path.is_file():
            return True, f"{name} submitted!"
        return False, f"{name} not found. Check that you named your file correctly."

    def _check_imports(self):
        name = self.submission_path.name
        if self.submission is not None:
            return True, f"{name} successfully imported!"
        return False, f"{name} found but could not be imported due to the following error:\n{self.import_error}"

    def _check_follows_starter(self):
        name = self.submission_path.name
        missing = [item for item in self.required_items
                   if not has_function_or_class(self.submission, item)]
        if missing:
            return False, f"{name} is missing required items from the starter code: {', '.join(missing)}"
        return True, f"{name} follows the starter code!"

    # Grading

    def patch_context(self, problem: Problem, additional_patches: Iterable[str] = ()):
        """Replace ``problem``'s prerequisites in the submission with the solution's versions."""
        names = self.prerequisites(problem) + list(additional_patches)
        patches = {name: getattr(self.solution, name) for name in names}
        return patch.multiple(self.submission, create=True, **patches) if patches else nullcontext()

    def grade_problem(self, problem: Problem) -> ProblemResult:
        with self.patch_context(problem):
            return self.compare_with_solutions(problem)

    def compare_with_solutions(self, problem: Problem) -> ProblemResult:
        """Grade ``problem`` without patching anything (see ``grade_problem``)."""
        if not self.test_inputs[problem.number]:
            raise ValueError(f"No test inputs were set for problem {problem.number}.")
        mismatch = self.first_mismatch(problem, problem.name)
        if mismatch is None:
            return ProblemResult.full()
        for option in problem.partial_credit:
            if self.first_mismatch(problem, option.solution) is None:
                return ProblemResult.partial(option.credit, option.message or "Partial credit.")
        if problem.partial_credit:
            return ProblemResult.zero(
                "Submission did not match any case for full or partial credit:\n" + mismatch.describe())
        return ProblemResult.zero(mismatch.describe())

    def first_mismatch(self, problem: Problem, solution_name: str) -> Optional[Mismatch]:
        """The first input on which the submission differs from ``solution_name`` in the solution module."""
        submission_fn = getattr(self.submission, problem.name)
        solution_fn = getattr(self.solution, solution_name)
        options = problem.options
        copy_inputs = options.get("copy_inputs", True)
        comparator = self.comparators.get(problem.number) or functools.partial(
            compare.assert_outputs_match,
            **{key: options[key] for key in ("rtol", "atol") if key in options})

        for test_input in self.test_inputs[problem.number]:
            args, kwargs = test_input.args, test_input.kwargs

            def call(fn):
                if "seed" in options:
                    seed_everything(options["seed"])
                if copy_inputs:
                    return fn(*copy.deepcopy(args), **copy.deepcopy(kwargs))
                return fn(*args, **kwargs)

            try:
                actual = call(submission_fn)
            except Exception as e:
                return Mismatch(test_input, error=error_message(e))
            # Errors in the solution are the autograder's problem: let them propagate
            expected = call(solution_fn)
            try:
                comparator(actual, expected)
            except Exception:  # incompatible types or shapes count as mismatches too
                return Mismatch(test_input, actual=actual, expected=expected)
        return None


__all__ = ["Input", "PythonGrader", "PythonTestCase", "seed_everything"]
