"""The language-agnostic core: turning a config into Gradescope tests.

A ``Grader`` subclass supplies two things:

- ``prerequisite_checks()``: ordered checks that a submission can be graded at
  all (file present, compiles, defines what the starter code defines, ...).
  They are always visible to students and are worth no points.
- ``grade_problem(problem)``: a ``ProblemResult`` for one problem.

``Grader.build()`` then produces a ``unittest.TestCase`` with one test method
per check and per problem, decorated for ``gradescope_utils``.
"""
from __future__ import annotations

import functools
import unittest
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

from gradescope_utils.autograder_utils.decorators import number, partial_credit, visibility, weight

from polygrade.config import AssignmentConfig, Problem
from polygrade.results import ProblemResult


@dataclass
class Check:
    """A prerequisite check.

    ``run`` returns ``(passed, message)``. If a *blocking* check fails, later
    checks are skipped and every problem receives zero points with a pointer
    to the failed check, instead of a confusing cascade of errors.
    """

    key: str
    title: str
    run: Callable[[], Tuple[bool, str]]
    blocking: bool = True


@dataclass
class CheckResult:
    check: Check
    passed: bool
    message: str


class Assignment:
    """The problems of an assignment, indexable by number or by name."""

    def __init__(self, problems: List[Problem]):
        self._problems = sorted(problems, key=lambda p: p.number)
        self._by_key: Dict[Union[int, str], Problem] = {}
        for problem in self._problems:
            self._by_key[problem.number] = problem
            self._by_key[problem.name] = problem

    def __iter__(self):
        return iter(self._problems)

    def __len__(self):
        return len(self._problems)

    def __getitem__(self, key: Union[int, str]) -> Problem:
        try:
            return self._by_key[key]
        except KeyError:
            raise KeyError(f"No problem with number or name {key!r}.") from None


class GraderTestCase(unittest.TestCase):
    """Base class for generated test cases. ``grader`` is set by ``Grader.build``."""

    grader: "Grader"


class Grader:
    language: str = ""
    test_case_class = GraderTestCase

    def __init__(self, config: AssignmentConfig):
        self.config = config
        self.problems = Assignment(config.problems)
        self._check_results: Optional[List[CheckResult]] = None

    @classmethod
    def from_config(cls, path, **kwargs):
        config = AssignmentConfig.load(path)
        if cls.language and config.language != cls.language:
            raise ValueError(f"{cls.__name__} cannot grade a '{config.language}' assignment.")
        return cls(config, **kwargs)

    # To be provided by subclasses

    def prerequisite_checks(self) -> List[Check]:
        raise NotImplementedError

    def grade_problem(self, problem: Problem) -> ProblemResult:
        raise NotImplementedError

    # Prerequisites

    def check_results(self) -> List[CheckResult]:
        """Run the prerequisite checks (once) and return their results."""
        if self._check_results is None:
            self._check_results = []
            blocked_by = None
            for check in self.prerequisite_checks():
                if blocked_by is not None:
                    passed, message = False, f"Skipped because an earlier check failed: {blocked_by.title}."
                else:
                    passed, message = check.run()
                    if not passed and check.blocking:
                        blocked_by = check
                self._check_results.append(CheckResult(check, passed, message))
        return self._check_results

    def not_graded_reason(self) -> Optional[str]:
        """Why problems can't be graded, or ``None`` if they can."""
        for result in self.check_results():
            if result.check.blocking and not result.passed:
                return (f"Submission could not be graded because a prerequisite check failed "
                        f"({result.check.title}). See that check's output for details.")
        return None

    @property
    def ready(self) -> bool:
        return self.not_graded_reason() is None

    # Building the Gradescope test case

    def build(self, cls: Optional[type] = None) -> type:
        """Add generated tests to ``cls`` (or a new class) and return it.

        Usable as a class decorator, so hand-written tests can live alongside
        the generated ones::

            @grader.build
            class TestSubmission(PythonTestCase):
                @grader.problem_test(5)
                def test_05_custom(self, problem, set_score): ...
        """
        if cls is None:
            cls = type("TestSubmission", (self.test_case_class,), {})
        cls.grader = self
        for index, check in enumerate(self.prerequisite_checks(), start=1):
            setattr(cls, f"test_00_{index:02d}_{check.key}", self._check_method(index, check))
        for problem in self.problems:
            if problem.generate_test:
                setattr(cls, problem.test_name, self._problem_method(problem))
        return cls

    def _check_method(self, index: int, check: Check):
        grader = self

        def test_method(test_case):
            result = grader.check_results()[index - 1]
            if not result.passed:
                test_case.fail(result.message)
            print(result.message)

        test_method.__doc__ = check.title
        test_method = weight(0)(test_method)
        test_method = visibility("visible")(test_method)
        return number(f"0.{index}")(test_method)

    def _problem_method(self, problem: Problem):
        grader = self

        def run(test_case, problem, set_score):
            result = grader.grade_problem(problem)
            set_score(problem.weight * result.credit)
            if not result.passed:
                test_case.fail(result.message)
            print(result.message)

        run.__doc__ = problem.title
        return self.problem_test(problem.number)(run)

    def problem_test(self, problem_number: int):
        """Decorator for a hand-written problem test.

        The decorated method receives the ``Problem`` and a ``set_score``
        callback. It is given the problem's number and weight, and it is
        automatically failed with zero points if the submission did not pass
        the blocking prerequisite checks.
        """
        problem = self.problems[problem_number]
        grader = self

        def decorator(fn):
            @functools.wraps(fn)
            def test_method(test_case, set_score=None):
                reason = grader.not_graded_reason()
                if reason is not None:
                    set_score(0)
                    test_case.fail(reason)
                return fn(test_case, problem, set_score)

            test_method.__doc__ = fn.__doc__ or problem.title
            test_method = partial_credit(problem.weight)(test_method)
            if problem.visibility:
                test_method = visibility(problem.visibility)(test_method)
            return number(str(problem.number))(test_method)

        return decorator
