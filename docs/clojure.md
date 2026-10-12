# Grading Clojure assignments

Gradescope has no Clojure tooling, so the tests themselves are ordinary
`clojure.test` tests. polygrade runs them, reads their output, and turns it
into scored Gradescope results. This guide walks through
[`examples/clojure-stats`](../examples/clojure-stats).

## Layout

```
clojure-stats/
  setup.sh                    installs Python, a JDK, Leiningen and lein-exec
  requirements.txt
  run_autograder              grades one submission
  config.yaml                 problems, weights, partial credit
  starter.clj                 the code students start from
  solution.clj                your solution
  unit-tests.clj              the clojure.test tests
  tests/test_problems.py      three lines: build Gradescope tests from config.yaml
  sample_submissions/
```

Students submit a single `.clj` file with any name. `run_autograder` copies it
to `submission.clj`. If they submit more or fewer than one `.clj` file,
nothing is copied, and the "submission found" check tells them to submit
exactly one.

## How a submission is graded

1. **Prerequisite checks** (zero points, always visible):
   1. The submission was found.
   2. It compiles, i.e. running it on its own succeeds. The student sees the
      end of the error output if it doesn't.
   3. It defines the required functions, with the right number of parameters,
      and variables. These default to everything `starter.clj` defines. You
      can also list them under `required` in `config.yaml`.
   4. Nothing is defined twice.

   If check 1 or 2 fails, every problem gets zero points. Checks 3 and 4 are
   informational. A missing function only affects the problems that use it.

2. **Unit tests.** `polygrade/clojure/autograde.clj` loads `solution.clj` into
   the namespace `solution` and the submission into `student`. Then it loads
   `unit-tests.clj` and runs its tests. Everything the solution defines but
   the submission doesn't is added to `student` as an unbound var. Tests that
   use it then fail with an error, instead of the whole test file failing to
   compile.

3. **Scoring.** Each failure message that starts with `Q<n>: ` fails problem
   `n`. The student sees the first such message, or "Runtime error for test
   input." if the test threw an exception. Messages that start with
   `PC<tag>: ` flag mistakes for partial credit (see below). If the test run
   itself fails, e.g. because a test file doesn't compile, every problem fails.

## Writing unit tests

A unit tests file starts by declaring the `unit-tests` namespace and referring
to polygrade's macros:

```clojure
(ns unit-tests
  (:require [clojure.test :refer :all]))
(refer 'polygrade.grading)
```

### `Q-tests`: comparing with the solution

```clojure
;; Problem 4: (variance xs), graded with the solution's mean and square
(Q-tests 4                      ; problem number
         "variance"             ; function name
         ["mean" "square"]      ; functions to replace with the solution's versions
         [[(almost-eq? 1e-9) [data] "incorrect results for test inputs"]
          [(almost-eq? 1e-9) [data-2] "incorrect results for test inputs"]])
```

Each test case is `[comparison-fn args fail-message]`. The test passes if
`(comparison-fn (student/variance ...args) (solution/variance ...args))` is
true. The functions in the mock list are replaced with the solution's versions
using `with-redefs`, so a mistake in `mean` isn't penalized again in
`variance`.

`Q-tests` expands to one `unit-test` per case. You can also use `unit-test`
directly:

```clojure
(unit-test "Q4-test-special" (almost-eq? 1e-9) "variance" ['(1 1 1)]
           "Q4: incorrect result for a constant list" ["mean"])
```

### `PC-test`: detecting a known mistake

```clojure
;; Flags submissions that return the sum instead of the mean (40 for `data`)
(PC-test "3.1"                  ; tag
         (almost-eq? 1e-9)      ; how to compare with the incorrect result
         "mean"
         40                     ; what a submission with the mistake returns
         [data]
         "returned the sum of the list instead of its mean"
         [])                    ; functions to mock, as for Q-tests
```

The test *fails*, flagging the mistake, when the student's output matches the
incorrect result. In `config.yaml`, map the tag to an amount of credit:

```yaml
  3:
    name: mean
    weight: 3
    partial_credit:
      - tag: "3.1"
        credit: 0.5
        # message: optional; defaults to the PC-test's message
  4:
    name: variance
    weight: 3
    partial_credit:
      - tag: "4.1"
        credit: 0.5
        waive_if: ["3.1"]   # the same mistake as 3.1: don't penalize it twice
```

Tags are checked in the order they're listed, and the first flagged tag
determines the credit. If no tag is flagged but a `Q` test failed, the problem
gets zero points. A `PC-test` that throws an exception never flags its tag.

### Hand-written tests

Any `deftest` works, as long as its failure messages start with `Q<n>: `.
`matches-solution?` helps when checking how a function behaves while other
functions are mocked:

```clojure
;; sum-of-squares shouldn't depend on mean
(deftest Q2-test-independent-of-mean
  (with-redefs [student/mean (constantly 0)]
    (is (matches-solution? (almost-eq? 1e-9) "sum-of-squares" [data])
        "Q2: sum-of-squares should not use mean")))

;; Variables can be tested directly
(deftest Q5-test
  (is ((almost-eq? 1e-9) student/sample-mean solution/sample-mean)
      "Q5: incorrect value"))
```

### Comparison functions

| Function | True when |
| --- | --- |
| `(almost-eq? eps)` | Two numbers are within `eps`. A student's `-Infinity` also matches a solution's `NaN` |
| `(not-almost-eq? eps)` | The opposite |
| `(lists-almost-eq? eps)` | Two sequences have the same length and are element-wise `almost-eq?` |

Any two-argument predicate works, e.g. `=`.

## Debugging tests

```bash
polygrade local examples/clojure-stats path/to/submission.clj --debug
```

`--debug` sets `POLYGRADE_DEBUG`, which makes every `unit-test` print the
student's and the solution's output side by side, along with the raw test
output:

```
Q3-test-0 Student: 40 Solution: 5
Q4-test-0 Student: 32 Solution: 4
```

Pass several submissions (or a folder of downloaded submissions) to see how a
whole class does before publishing grades.

## Regrading a corrected submission

Sometimes a submission fails to compile because of a trivial slip, and you
decide to fix it by hand and grade the result. Put the corrected file in
`corrected_submissions/`, named after the Gradescope submission id (e.g.
`123456789.clj`) or after the file the student submitted. Then re-upload the
autograder and rerun it on that submission. `run_autograder` uses the
corrected file instead of the original.

## Running Clojure

By default, scripts are run with `lein exec`, as installed by `setup.sh`. To use
something else, set `command` in `config.yaml`, e.g.
`command: [java, -cp, /path/to/clojure.jar, clojure.main]`. For local runs
only, you can set the `POLYGRADE_CLOJURE_COMMAND` environment variable
instead.

Neither the solution nor the submission should declare a namespace with `ns`,
since they are loaded into the `solution` and `student` namespaces.
