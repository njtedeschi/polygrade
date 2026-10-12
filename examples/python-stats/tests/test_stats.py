"""Autograder tests for the example statistics assignment.

Problems, weights and partial credit are configured in config.yaml. This file
supplies the test inputs for each problem, plus any tests written by hand.
"""
from unittest.mock import patch

from polygrade import find_config
from polygrade.python import Input, PythonGrader, PythonTestCase, ensure_return

grader = PythonGrader.from_config(
    find_config(__file__),
    # Students sometimes delete the provided `return totals` line. Put it back
    # rather than failing a problem over it.
    fixes=[ensure_return("running_total", "totals")],
)

# Test inputs. Each problem's function is called on every input, and its
# output compared with the solution's.

DATA = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
WITH_OUTLIER = [10.0, 11.0, 9.0, 10.0, 12.0, 8.0, 10.0, 11.0, 9.0, 30.0]
NEGATIVE = [-3.5, 0.0, 3.5, -1.0]

for name in ["mean", "variance", "standardize", "running_total"]:
    grader.set_test_inputs(name, Input.of(DATA), Input.of(WITH_OUTLIER), Input.of(NEGATIVE))

grader.set_test_inputs(
    "count_outliers",
    Input.of(DATA),
    Input.of(WITH_OUTLIER),
    Input.of(WITH_OUTLIER, threshold=1.0),
)

grader.set_test_inputs(
    "bootstrap_mean",
    Input.of(DATA, 5),
    Input.of(WITH_OUTLIER, n_samples=100),
)


@grader.build
class TestStats(PythonTestCase):
    """Generated tests are added to this class. Hand-written ones go below."""

    @grader.problem_test(5)
    def test_05_count_outliers(self, problem, set_score):
        """Problem 5: count_outliers (calls standardize once)"""
        with self.patch_context(problem):
            result = self.run_problem(problem)
            # Count calls to standardize, while still using the solution's version
            with patch.object(self.submission, "standardize", wraps=self.solution.standardize) as spy:
                self.submission.count_outliers(WITH_OUTLIER)

        if not result.passed:
            set_score(0)
            self.fail(result.message)
        if spy.call_count > 1:
            set_score(0.5 * problem.weight)
            self.fail(f"Correct output, but standardize was called {spy.call_count} times instead of once.")
        set_score(problem.weight)
        print(result.message)
