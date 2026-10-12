from polygrade.config import Problem
from polygrade.external.grader import (CRASH_MESSAGE, RUNTIME_ERROR_MESSAGE, TestReport,
                                       parse_test_output, score)

CLOJURE_STYLE_OUTPUT = """\
Testing unit-tests

FAIL in (Q2-test-0) (unit-tests.clj:20)
Q2: incorrect results for test inputs
expected: (= 1 2)
  actual: (not (= 1 2))

FAIL in (Q2-test-1) (unit-tests.clj:21)
Q2: a later failure for the same problem

ERROR in (Q4-test-0) (unit-tests.clj:30)
Q4: incorrect results
expected: ...
  actual: java.lang.ArithmeticException: Divide by zero

FAIL in (PC3_1-test) (unit-tests.clj:40)
PC3.1: forgot to divide

ERROR in (PC5_1-test) (unit-tests.clj:50)
PC5.1: crashed while checking for a mistake

Ran 6 tests containing 6 assertions.
"""


def test_parse_clojure_style_output():
    report = parse_test_output(CLOJURE_STYLE_OUTPUT)
    assert report.problem_failures == {2: "incorrect results for test inputs", 4: RUNTIME_ERROR_MESSAGE}
    # Crashes never flag a partial credit tag
    assert report.flagged_tags == {"3.1": "forgot to divide"}


def test_parse_single_line_output():
    report = parse_test_output("FAIL Q1: wrong\nsome noise\nERROR Q2: boom\nFAIL PC1.1: mistake\n")
    assert report.problem_failures == {1: "wrong", 2: RUNTIME_ERROR_MESSAGE}
    assert report.flagged_tags == {"1.1": "mistake"}


def problem(**kwargs):
    return Problem(number=3, name="f", weight=10, **kwargs)


def test_score_full_and_zero():
    assert score(problem(), TestReport()).credit == 1
    result = score(problem(), TestReport(problem_failures={3: "nope"}))
    assert (result.credit, result.passed, result.message) == (0, False, "nope")


def test_score_partial_credit_in_listed_order():
    p = problem(partial_credit=[{"tag": "3.2", "credit": 0.25}, {"tag": "3.1", "credit": 0.5, "message": "m"}])
    report = TestReport(problem_failures={3: "nope"}, flagged_tags={"3.1": "x", "3.2": "y"})
    assert score(p, report).credit == 0.25
    report = TestReport(problem_failures={3: "nope"}, flagged_tags={"3.1": "x"})
    assert (score(p, report).credit, score(p, report).message) == (0.5, "m")


def test_score_waives_repeated_mistake():
    p = problem(partial_credit=[{"tag": "3.1", "credit": 0.5, "waive_if": ["2.1"]}])
    result = score(p, TestReport(problem_failures={3: "nope"}, flagged_tags={"3.1": "x", "2.1": "y"}))
    assert result.credit == 1 and result.passed and "2.1" in result.message


def test_score_crash():
    result = score(problem(), TestReport(crashed=True, crash_message=CRASH_MESSAGE))
    assert result.credit == 0 and result.message == CRASH_MESSAGE
