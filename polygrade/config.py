"""Loading and validating an assignment's ``config.yaml``.

A config describes *what* is graded (paths and problems); the language-specific
graders decide *how*. Paths are resolved relative to the directory containing
the config file, which is also the root of the autograder archive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CONFIG_FILENAME = "config.yaml"

# Gradescope shows a test's results to students only after grades are
# published. Prerequisite checks override this so students can fix problems
# with their submission before the deadline.
DEFAULT_VISIBILITY = "after_published"


class ConfigError(ValueError):
    """Raised when an assignment config is missing or malformed."""


@dataclass
class PartialCredit:
    """One way a submission can earn partial credit on a problem.

    Exactly one of ``solution`` or ``tag`` is set, depending on the language:

    - ``solution`` (Python): the name of an alternative, *incorrect*
      implementation in the solution module. A submission whose outputs match
      it receives ``credit``.
    - ``tag`` (external languages): the tag of a test in the language's own
      test file that flags a specific mistake, e.g. ``"3.1"`` for a test whose
      failure message starts with ``PC3.1:``.
    """

    credit: float = 0.0
    message: Optional[str] = None
    solution: Optional[str] = None
    tag: Optional[str] = None
    # Tags of mistakes (usually from earlier problems) that, if also flagged,
    # mean this mistake is a repeat and should not be penalized again.
    waive_if: List[str] = field(default_factory=list)

    def __post_init__(self):
        if (self.solution is None) == (self.tag is None):
            raise ConfigError("Each partial_credit entry needs exactly one of 'solution' or 'tag'.")
        if not 0 <= self.credit <= 1:
            raise ConfigError(f"Partial credit must be a fraction in [0, 1], got {self.credit}.")
        if self.tag is not None:
            self.tag = str(self.tag)
        self.waive_if = [str(tag) for tag in self.waive_if]


@dataclass
class Problem:
    number: int
    name: str
    weight: float
    title: Optional[str] = None
    visibility: Optional[str] = None
    # Set to false to write the problem's test by hand (see Grader.problem_test).
    generate_test: bool = True
    partial_credit: List[PartialCredit] = field(default_factory=list)
    # Language-specific settings (e.g. tolerances or seeds for Python) are kept
    # here and interpreted by the grader that understands them.
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.partial_credit = [
            entry if isinstance(entry, PartialCredit) else PartialCredit(**entry)
            for entry in self.partial_credit
        ]
        if self.title is None:
            self.title = f"Problem {self.number}: {self.name}"

    @property
    def test_name(self) -> str:
        slug = "".join(c if c.isalnum() else "_" for c in self.name).strip("_")
        return f"test_{self.number:02d}_{slug}"


_PROBLEM_FIELDS = {"name", "weight", "title", "visibility", "generate_test", "partial_credit"}


@dataclass
class AssignmentConfig:
    root: Path
    language: str
    paths: Dict[str, Path]
    problems: List[Problem]
    visibility: str = DEFAULT_VISIBILITY
    # Everything else at the top level of the YAML file, for the grader to use.
    options: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path) -> "AssignmentConfig":
        path = Path(path).resolve()
        if not path.is_file():
            raise ConfigError(f"Config file '{path}' not found.")
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls.from_dict(raw, root=path.parent)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any], root: Path) -> "AssignmentConfig":
        raw = dict(raw)
        try:
            language = raw.pop("language")
            raw_paths = raw.pop("paths")
            raw_problems = raw.pop("problems")
        except KeyError as e:
            raise ConfigError(f"Config is missing required key {e}.") from None

        problems = []
        for number, spec in sorted(raw_problems.items()):
            spec = dict(spec)
            known = {k: spec.pop(k) for k in list(spec) if k in _PROBLEM_FIELDS}
            if "name" not in known or "weight" not in known:
                raise ConfigError(f"Problem {number} needs a 'name' and a 'weight'.")
            problems.append(Problem(number=int(number), options=spec, **known))

        return cls(
            root=root,
            language=language,
            paths={key: (root / value).resolve() for key, value in raw_paths.items()},
            problems=problems,
            visibility=raw.pop("visibility", DEFAULT_VISIBILITY),
            options=raw,
        )

    def path(self, key: str, required: bool = True) -> Optional[Path]:
        if key in self.paths:
            return self.paths[key]
        if required:
            raise ConfigError(f"Config is missing required path '{key}'.")
        return None


def find_config(start, filename: str = CONFIG_FILENAME) -> Path:
    """Find ``config.yaml`` in the directory of ``start`` or one of its parents.

    Test files call ``find_config(__file__)`` so that they work both on
    Gradescope and when run locally from anywhere.
    """
    start = Path(start).resolve()
    for directory in [start, *start.parents]:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    raise ConfigError(f"No {filename} found in {start} or any parent directory.")
