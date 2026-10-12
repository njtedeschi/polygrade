"""Grading Clojure submissions with ``clojure.test``.

``autograde.clj`` loads the solution and the submission into separate
namespaces (``solution`` and ``student``), loads the macros in
``grading.clj`` and the assignment's unit tests, and runs the tests. The
tests' ``clojure.test`` output is then parsed by the external-language
machinery: test messages starting with ``Q<n>:`` belong to problem ``n``,
and those starting with ``PC<tag>:`` flag a known mistake for partial credit.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import List, Optional

from polygrade.external.grader import ExternalGrader
from polygrade.grader import Check
from polygrade.clojure.source import Definitions

CLOJURE_DIR = Path(__file__).resolve().parent
AUTOGRADE_SCRIPT = CLOJURE_DIR / "autograde.clj"
GRADING_LIBRARY = CLOJURE_DIR / "grading.clj"

DEFAULT_COMMAND = ["lein", "exec"]
# Overrides the config's command, e.g. to test locally without Leiningen:
#   POLYGRADE_CLOJURE_COMMAND="java -cp clojure.jar clojure.main"
COMMAND_ENV_VAR = "POLYGRADE_CLOJURE_COMMAND"


class ClojureGrader(ExternalGrader):
    """Grades a Clojure submission.

    Config paths: ``submission``, ``solution`` and ``tests`` (the unit tests
    file) are required. ``starter`` is optional.

    Config options:

    - ``command``: how to run a Clojure script (default ``["lein", "exec"]``).
    - ``required``: ``functions`` (a map from name to number of parameters)
      and ``variables`` (a list of names) that the submission must define.
      Defaults to everything defined in the starter file, if there is one.
    - ``timeout``: as for ``ExternalGrader``.
    """

    language = "clojure"

    def __init__(self, config):
        super().__init__(config)
        self.required_functions, self.required_variables = self._required_definitions()

    def _required_definitions(self):
        required = self.config.options.get("required")
        if required is not None:
            return dict(required.get("functions", {})), list(required.get("variables", []))
        starter = self.config.path("starter", required=False)
        if starter is not None:
            definitions = Definitions.from_file(starter)
            return ({name: arities[0] for name, arities in definitions.functions.items()},
                    list(definitions.variables))
        return {}, []

    # Commands

    def clojure_command(self) -> List[str]:
        if os.environ.get(COMMAND_ENV_VAR):
            return shlex.split(os.environ[COMMAND_ENV_VAR])
        return list(self.config.options.get("command", DEFAULT_COMMAND))

    def grade_command(self) -> List[str]:
        paths = self.config.paths
        return self.clojure_command() + [str(AUTOGRADE_SCRIPT), str(GRADING_LIBRARY), str(paths["tests"]),
                                         str(paths["solution"]), str(self.submission_path)]

    def compile_command(self) -> Optional[List[str]]:
        return self.clojure_command() + [str(self.submission_path)]

    # Prerequisite checks

    def prerequisite_checks(self) -> List[Check]:
        return super().prerequisite_checks() + [
            Check("definitions", "Required functions and variables defined", self._check_definitions,
                  blocking=False),
            Check("no_duplicates", "No duplicate definitions", self._check_no_duplicates, blocking=False),
        ]

    def _definitions(self) -> Definitions:
        return Definitions.from_file(self.submission_path)

    def _check_definitions(self):
        definitions = self._definitions()
        problems: List[str] = []
        for name, arity in self.required_functions.items():
            if name not in definitions.functions:
                problems.append(f"Missing function: {name}")
            elif arity not in definitions.functions[name]:
                problems.append(f"Wrong number of arguments for function {name} (expected {arity})")
        for name in self.required_variables:
            if name not in definitions.variables:
                problems.append(f"Missing variable: {name}")
        if problems:
            return False, "\n".join(problems)
        return True, "All required functions (with correct number of arguments) and variables are defined!"

    def _check_no_duplicates(self):
        duplicates = self._definitions().duplicates()
        if duplicates:
            return False, f"Defined more than once: {', '.join(duplicates)}"
        return True, "No duplicate functions or variables!"

