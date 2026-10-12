"""Grading submissions in languages that are tested by an external process.

The external test runner can be written in any language. It only has to
print one report per failing test, in either of these forms::

    FAIL Q3: message shown to the student          (one line)

    FAIL in (some-test-name) (tests.clj:12)        (marker line, then the
    Q3: message shown to the student                message on the next line)

with ``ERROR`` in place of ``FAIL`` when the test crashed rather than
returned a wrong answer. The label is either

- ``Q<problem number>``: the problem fails (zero points, unless a partial
  credit tag below applies), or
- ``PC<tag>``: a *partial credit detector* for a specific known mistake
  failed, meaning the submission made that mistake. Problems map tags to
  credit in ``config.yaml``. Crashes (``ERROR``) never trigger a tag.

Everything else in the output is ignored. If the runner exits with a nonzero
status, every problem fails. This is exactly the format ``clojure.test``
prints, which is how the Clojure support works.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from polygrade.config import Problem
from polygrade.grader import Check, Grader
from polygrade.messages import tail
from polygrade.results import ProblemResult

DEFAULT_TIMEOUT = 600  # seconds

RUNTIME_ERROR_MESSAGE = "Runtime error for test input."
CRASH_MESSAGE = "Submission causes a compilation error for the autograder."
WAIVED_MESSAGE = ("Correct apart from repeating a mistake already penalized in an earlier problem "
                  "({tags}). No additional penalty.")

_MARKER = re.compile(r"^\s*(FAIL|ERROR)\b(.*)$")
_LABEL = re.compile(r"(?:^|\s)(Q\d+|PC[\w.\-]+):\s?(.*)$")


@dataclass
class TestReport:
    """The parsed output of one run of the external test runner."""

    __test__ = False  # not a test class, despite the name

    crashed: bool = False
    crash_message: str = ""
    # First failure message for each problem number
    problem_failures: Dict[int, str] = field(default_factory=dict)
    # First failure message for each flagged partial credit tag
    flagged_tags: Dict[str, str] = field(default_factory=dict)

    def record(self, kind: str, label: str, message: str):
        if label.startswith("Q"):
            number = int(label[1:])
            if kind == "ERROR":
                message = RUNTIME_ERROR_MESSAGE
            self.problem_failures.setdefault(number, message)
        elif kind == "FAIL":
            self.flagged_tags.setdefault(label[2:], message)


def parse_test_output(output: str) -> TestReport:
    report = TestReport()
    lines = output.splitlines()
    for i, line in enumerate(lines):
        marker = _MARKER.match(line)
        if not marker:
            continue
        kind, rest = marker.groups()
        label = _LABEL.search(rest)
        if label is None and i + 1 < len(lines):
            label = _LABEL.match(lines[i + 1].strip())
        if label is not None:
            report.record(kind, label.group(1), label.group(2).strip())
    return report


def score(problem: Problem, report: TestReport) -> ProblemResult:
    """Score ``problem`` given a test report.

    Partial credit entries are tried in the order they are listed, so list
    more specific mistakes first.
    """
    if report.crashed:
        return ProblemResult.zero(report.crash_message)
    for option in problem.partial_credit:
        if option.tag not in report.flagged_tags:
            continue
        repeated = [tag for tag in option.waive_if if tag in report.flagged_tags]
        if repeated:
            return ProblemResult.full(WAIVED_MESSAGE.format(tags=", ".join(repeated)))
        return ProblemResult.partial(option.credit, option.message or report.flagged_tags[option.tag])
    if problem.number in report.problem_failures:
        return ProblemResult.zero(report.problem_failures[problem.number])
    return ProblemResult.full()


class ExternalGrader(Grader):
    """Grades a submission by running an external test command.

    Config options (top level of ``config.yaml``):

    - ``grade_command`` (required): the command that runs the tests, as a
      list. ``{submission}``, ``{solution}``, ``{tests}`` and any other key
      under ``paths`` are replaced by absolute paths, ``{root}`` by the
      autograder directory.
    - ``compile_command`` (optional): a command that fails if the submission
      does not compile/load on its own. Used as a blocking prerequisite.
    - ``timeout``: seconds before a command is killed (default 600).
    """

    language = "external"

    def __init__(self, config):
        super().__init__(config)
        self.submission_path = config.path("submission")
        self.timeout = config.options.get("timeout", DEFAULT_TIMEOUT)
        self._report: Optional[TestReport] = None

    # Commands

    def format_command(self, command: List[str]) -> List[str]:
        values = {key: str(path) for key, path in self.config.paths.items()}
        values["root"] = str(self.config.root)
        return [str(part).format(**values) for part in command]

    def grade_command(self) -> List[str]:
        return self.format_command(self.config.options["grade_command"])

    def compile_command(self) -> Optional[List[str]]:
        command = self.config.options.get("compile_command")
        return self.format_command(command) if command else None

    def run(self, command: List[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, cwd=self.config.root, env=os.environ.copy(),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              timeout=self.timeout)

    # Prerequisite checks

    def prerequisite_checks(self) -> List[Check]:
        checks = [Check("submitted", "Submission file found", self._check_submitted)]
        if self.compile_command():
            checks.append(Check("compiles", "Submission compiles", self._check_compiles))
        return checks

    def _check_submitted(self):
        name = self.submission_path.name
        if self.submission_path.is_file():
            return True, "Required file submitted!"
        pattern = self.config.options.get("submission_pattern")
        hint = f" Submit exactly one file matching {pattern}." if pattern else ""
        return False, f"{name} not found.{hint}"

    def _check_compiles(self):
        try:
            result = self.run(self.compile_command())
        except subprocess.TimeoutExpired:
            return False, f"Running the submission timed out after {self.timeout} seconds."
        if result.returncode != 0:
            return False, f"Submission failed to compile:\n{tail(result.stderr or result.stdout)}"
        return True, "Submission compiled successfully!"

    # Grading

    @property
    def report(self) -> TestReport:
        """The parsed test output. The tests are run once, the first time this is needed."""
        if self._report is None:
            self._report = self.run_tests()
        return self._report

    def run_tests(self) -> TestReport:
        command = self.grade_command()
        try:
            result = self.run(command)
        except subprocess.TimeoutExpired:
            return TestReport(crashed=True, crash_message=f"Tests timed out after {self.timeout} seconds.")
        if os.environ.get("POLYGRADE_DEBUG"):
            # Bypass the test runner's output capture so this never reaches results.json
            print(f"$ {shlex.join(command)}", result.stdout, result.stderr, sep="\n", file=sys.__stderr__)
        if result.returncode != 0:
            return TestReport(crashed=True, crash_message=CRASH_MESSAGE)
        return parse_test_output(result.stdout)

    def grade_problem(self, problem: Problem) -> ProblemResult:
        return score(problem, self.report)
