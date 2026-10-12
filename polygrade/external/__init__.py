"""Grading languages whose tests run in an external process."""
from polygrade.external.grader import ExternalGrader, TestReport, parse_test_output, score

__all__ = ["ExternalGrader", "TestReport", "parse_test_output", "score"]
