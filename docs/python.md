# Grading Python assignments

This guide walks through [`examples/python-stats`](../examples/python-stats),
a small assignment with six functions to implement.

## Layout

```
python-stats/
  setup.sh                    installs Python packages (run once by Gradescope)
  requirements.txt
  run_autograder              grades one submission (run by Gradescope)
  config.yaml                 problems, weights, partial credit
  assignment/
    stats_starter.py          the code students start from
    stats_solution.py         your solution, plus any known-incorrect variants
  tests/
    test_stats.py             test inputs and hand-written tests
  sample_submissions/         for local testing; excluded from the bundle
```

`run_autograder` copies every `.py` file the student submitted, from any
subfolder, into `assignment/`. The submission is then expected at the
`submission` path in `config.yaml` (`assignment/stats.py`). Students can split
their work across several files: the submission can import its own modules.

## Problems and grading

Each problem in `config.yaml` names a function (or class) in the starter code:

```yaml
problems:
  1:
    name: mean
    weight: 4
  2:
    name: variance
    weight: 4
```

For each problem, the generated test calls the submission's function and the
solution's function on every test input and compares the outputs. The
submission earns the problem's full weight if they match on every input. If
they don't, the student sees the first mismatch, either the two outputs or the
end of the traceback if the submission raised an error. The test inputs
themselves aren't shown.

**Earlier problems are patched with the solution.** While problem *n* is
graded, the submission's functions for problems 1 to *n* − 1 are replaced by
the solution's. A `variance` that calls a broken `mean` still earns full
credit if `variance` itself is right. If a problem uses a helper that isn't
an earlier problem, list it under `additional_prerequisites`.

**Inputs are copied for each call**, so a submission that modifies its
arguments in place can't affect the solution's result or later calls. Turn
this off with `copy_inputs: false`, e.g. if a problem *should* mutate its
input and you grade that by hand.

## Test inputs

`tests/test_stats.py` creates the grader and sets each problem's inputs:

```python
from polygrade import find_config
from polygrade.python import Input, PythonGrader, PythonTestCase, ensure_return

grader = PythonGrader.from_config(
    find_config(__file__),
    fixes=[ensure_return("running_total", "totals")],
)

grader.set_test_inputs(
    "count_outliers",                     # problem name or number
    Input.of(DATA),                       # count_outliers(DATA)
    Input.of(WITH_OUTLIER, threshold=1),  # count_outliers(WITH_OUTLIER, threshold=1)
)
```

`Input.of(*args, **kwargs)` is shorthand for `Input(args=[...], kwargs={...})`.
Inputs can be anything, including data that the solution module generates
(`grader.solution` is the imported solution module).

Finally, build the test class:

```python
@grader.build
class TestStats(PythonTestCase):
    ...  # hand-written tests, if any
```

or, with no hand-written tests, just `TestStats = grader.build()`.

## Partial credit

To give partial credit for a specific mistake, write a function in the solution
module that makes that mistake, and list it under the problem:

```yaml
  2:
    name: variance
    weight: 4
    partial_credit:
      - solution: population_variance
        credit: 0.5
        message: "Computed the population variance instead of the sample variance."
```

If the submission doesn't match the solution, it is compared with each
alternative in turn. The first one it matches on *every* input determines
the credit (a fraction of the weight) and the message the student sees.

## Comparing outputs

The default comparison, `polygrade.python.assert_outputs_match`, handles:

| Outputs | Compared with |
| --- | --- |
| PyTorch modules | `torch.testing.assert_close` on each pair of parameters |
| PyTorch tensors | `torch.testing.assert_close`. Scalars and one-element vectors are interchangeable |
| Mappings | Same keys, values compared recursively |
| Numbers and numeric arrays/lists | `numpy.testing.assert_allclose` |
| Other lists and tuples | Same length, elements compared recursively |
| Anything else | `==` |

Set `rtol` and `atol` on a problem to change the tolerances. For anything
else, register your own comparator, which should raise an exception on a
mismatch:

```python
def same_elements(actual, expected):
    assert sorted(actual) == sorted(expected)

grader.set_comparator("unique_words", same_elements)
```

## Randomness

If a problem uses random numbers, set `seed` in its config. `random`, NumPy
and (if imported) PyTorch are reseeded before each call to the submission's
and the solution's function, so both see the same random numbers:

```yaml
  6:
    name: bootstrap_mean
    weight: 4
    seed: 0
```

## Hand-written tests

Set `generate_test: false` on a problem and write its test yourself. The
`grader.problem_test` decorator gives the method the problem's number and
weight. It passes the method the `Problem` and a `set_score` callback, and it
fails the test automatically if the submission didn't pass the prerequisite
checks. `PythonTestCase` provides the same tools the generated tests use:

```python
@grader.build
class TestStats(PythonTestCase):

    @grader.problem_test(5)
    def test_05_count_outliers(self, problem, set_score):
        """Problem 5: count_outliers (calls standardize once)"""
        with self.patch_context(problem):          # patch earlier problems
            result = self.run_problem(problem)     # the standard comparison
            with patch.object(self.submission, "standardize",
                              wraps=self.solution.standardize) as spy:
                self.submission.count_outliers(WITH_OUTLIER)

        if not result.passed:
            set_score(0)
            self.fail(result.message)
        if spy.call_count > 1:
            set_score(0.5 * problem.weight)
            self.fail("Correct output, but standardize was called more than once.")
        set_score(problem.weight)
        print(result.message)
```

Within a test, `self.submission` and `self.solution` are the two modules.
`self.patch_context(problem, additional_patches=[...])` can patch more
functions than usual. A common pattern is to grade a problem twice, once as
usual and once with a helper replaced by the solution's version. If only the
second passes, the bug is in the helper, and you can award partial credit.

## Prerequisite checks

Three zero-point checks run first and are always visible to students:

1. The submission file exists.
2. It can be imported. If it can't, the student sees the end of the traceback.
3. It defines every function and class that the starter code defines. Without
   a `starter` path, it must define every problem's function.

If any of these fail, every problem gets zero points with a message pointing
to the failed check. Students can resubmit until the checks pass.

## Fixes

Fixes are applied to the submission right after it's imported. They're meant
for slips that aren't what the assignment is assessing. The built-in
`ensure_return(function, variable)` appends `return <variable>` to a function
whose last statement isn't already that return. This is for starter code that
ends a function with a provided `return`, which some students delete. A fix is
any function that takes the submission module, so you can write your own.

## Testing locally

```bash
polygrade local examples/python-stats examples/python-stats/sample_submissions/*
```

This runs your actual `run_autograder` in a temporary mock of Gradescope's
`/autograder` directory and summarizes `results.json` for each submission.
`--json` prints the raw results, `--debug` shows the autograder's own output,
and `--keep` keeps the temporary directory for inspection. A folder counts as
one submission, so you can point `local` at a folder of downloaded
submissions.

To run the tests directly without simulating Gradescope, use
`polygrade run --root examples/python-stats`. Make sure a submission is at
the configured path first.

## Uploading

```bash
polygrade bundle examples/python-stats -o autograder.zip
```

The zip contains the autograder directory (without `sample_submissions`) and a
copy of polygrade itself, so `setup.sh` only has to install the packages in
`requirements.txt`. Add anything your assignment needs there, e.g. `torch`.
