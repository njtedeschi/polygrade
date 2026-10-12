"""End-to-end tests: every example sample submission, through a simulated Gradescope run."""
import pytest

from conftest import EXAMPLES, requires_clojure
from polygrade.cli import simulate


def scores(results):
    return {test["number"]: test["score"] for test in results["tests"] if test.get("max_score")}


def run(example, submission):
    return simulate(EXAMPLES / example, EXAMPLES / example / "sample_submissions" / submission)


def assert_all_zero(results):
    assert set(scores(results).values()) == {0}


PYTHON_FULL = {"1": 4, "2": 4, "3": 4, "4": 4, "5": 4, "6": 4}


@pytest.mark.parametrize("submission", ["correct", "nested"])
def test_python_full_credit(submission):
    assert scores(run("python-stats", submission)) == PYTHON_FULL


def test_python_partial():
    results = run("python-stats", "partial")
    assert scores(results) == {"1": 4, "2": 2, "3": 4, "4": 4, "5": 2, "6": 0}
    visibility = {test["number"]: test.get("visibility") for test in results["tests"]}
    assert visibility["0.1"] == "visible" and visibility["1"] is None
    assert results["visibility"] == "after_published"


@pytest.mark.parametrize("submission, failed_check", [("syntax_error", "0.2"), ("missing_function", "0.3")])
def test_python_blocked(submission, failed_check):
    results = run("python-stats", submission)
    assert_all_zero(results)
    status = {test["number"]: test["status"] for test in results["tests"]}
    assert status[failed_check] == "failed"


def test_bash_example():
    assert scores(run("external-bash", "correct")) == {"1": 2, "2": 3}
    assert scores(run("external-bash", "partial")) == {"1": 0, "2": 1.5}


@requires_clojure
@pytest.mark.parametrize("submission, expected", [
    ("correct", {"1": 2, "2": 3, "3": 3, "4": 3, "5": 1}),
    ("partial", {"1": 2, "2": 3, "3": 1.5, "4": 3, "5": 0}),
    ("missing_function", {"1": 2, "2": 3, "3": 3, "4": 0, "5": 1}),
])
def test_clojure_scores(submission, expected):
    assert scores(run("clojure-stats", submission)) == expected


@requires_clojure
@pytest.mark.parametrize("submission", ["compile_error", "two_files"])
def test_clojure_blocked(submission):
    assert_all_zero(run("clojure-stats", submission))
