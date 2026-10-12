"""polygrade: a Gradescope autograding framework.

Python submissions are graded natively (``polygrade.python``). Other
languages plug in through a small external-process protocol
(``polygrade.external``), with Clojure support built on it
(``polygrade.clojure``).
"""
from polygrade.config import AssignmentConfig, ConfigError, PartialCredit, Problem, find_config
from polygrade.grader import Check, Grader, GraderTestCase
from polygrade.results import ProblemResult

__version__ = "0.1.0"

__all__ = [
    "AssignmentConfig",
    "Check",
    "ConfigError",
    "Grader",
    "GraderTestCase",
    "PartialCredit",
    "Problem",
    "ProblemResult",
    "find_config",
    "load_grader",
]


def load_grader(config_path, **kwargs) -> Grader:
    """Create the right kind of grader for the ``language`` in a config file."""
    from polygrade.clojure import ClojureGrader
    from polygrade.external import ExternalGrader
    from polygrade.python import PythonGrader

    config = AssignmentConfig.load(config_path)
    graders = {grader.language: grader for grader in (PythonGrader, ExternalGrader, ClojureGrader)}
    if config.language not in graders:
        raise ConfigError(f"Unknown language '{config.language}'. Choose from: {', '.join(graders)}.")
    return graders[config.language](config, **kwargs)
