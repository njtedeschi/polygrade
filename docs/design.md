# Design notes

polygrade grew out of two separate sets of course autograders, one for Python
and one for Clojure, that evolved over several years of teaching. This
document explains the shared design they converged on, and the choices made
when merging them.

## One core, many languages

Both autograders had the same shape. A few zero-point checks tell students
whether their submission can be graded at all. Then one scored test per
problem compares the submission with a reference solution. The core
([`grader.py`](../polygrade/grader.py)) captures only that shape. A grader
provides an ordered list of `Check`s and a `grade_problem` method returning a
`ProblemResult`. `Grader.build()` turns these into `unittest` methods
decorated for `gradescope-utils`. Everything that produces Gradescope's
results is in one place, and nothing in it is language-specific.

The two grading strategies differ only in where the comparison happens:

- **In-process (Python).** The submission is imported, and the comparison
  happens in Python. This allows patching functions, counting calls,
  comparing tensors and models, and reseeding random number generators
  between calls.
- **Out-of-process (everything else).** The language's own test framework
  compares the outputs, and polygrade only reads the results. The protocol (a
  `FAIL`/`ERROR` line plus a `Q<n>:` or `PC<tag>:` message) is what
  `clojure.test` already prints. That made the Clojure integration small, and
  it's easy to reproduce in any language.

## Grading principles

- **Penalize each mistake once.** Earlier problems' functions are replaced
  with the solution's while a later problem is graded: `unittest.mock.patch`
  in Python, `with-redefs` in Clojure. In the other direction, `waive_if`
  forgives a mistake that repeats one already penalized.
- **Give partial credit for specific mistakes.** Partial credit is defined by
  what a wrong answer looks like, either an alternative implementation or a
  known incorrect output. It's never "passed 3 of 5 inputs". Grades stay
  explainable, and the student gets a precise message.
- **Let students fix what isn't the assignment.** Prerequisite checks are
  always visible, so a misnamed file, a syntax error or a renamed function is
  caught before the deadline. Problem results stay hidden until grades are
  published.
- **Fail clearly, and in one place.** When a blocking check fails, each
  problem's test says so, instead of showing a cascade of import errors.
  Missing Clojure definitions are stubbed so that only the problems using
  them fail.

## Changes from the original autograders

These are the behavior changes made while unifying them, beyond the
reorganization itself:

- **Configuration lives in one YAML file** for every language. Before, the
  Clojure problems and weights were hard-coded in Python test methods.
- **Prerequisite checks and problem tests are generated** rather than copied
  into every assignment. Hand-written problem tests use
  `@grader.problem_test(n)` instead of stacking decorators by hand.
- **Problems are never silently dropped.** The Python autograder used to
  delete problem tests when a prerequisite failed, which also removed their
  points from the total. Now they stay, with zero points and an explanation.
- **Comparison errors count as mismatches.** Comparing, say, `None` with an
  array used to be reported as an error inside the autograder. Comparison
  also falls back to `==` for non-numeric outputs, such as strings.
- **Inputs are deep-copied per call**, so a submission that mutates its
  arguments can't change the solution's result.
- **Python modules are imported by path**, and only functions and classes
  *defined* in the starter count as required. Previously, names the starter
  merely imported counted too.
- **Missing Clojure definitions are stubbed.** Previously, one missing
  function made the whole unit test file fail to compile, so every problem
  got zero points.
- **Partial credit detectors that crash are ignored.** Previously, an
  exception in a `PC` test counted as detecting the mistake.
- **Fixed `almost-eq?`'s NaN check.** `(= y Double/NaN)` is always false;
  the check now uses `Double/isNaN`.
- **`PC-test` takes a "matches the mistake" predicate**, e.g.
  `(almost-eq? 1e-6)`, instead of its negation.
- **The ensure-return fix is reusable** (`ensure_return(function, variable)`)
  rather than written for one assignment, and it keeps decorators and line
  numbers intact.
- **Corrected-submission overrides** can be keyed by Gradescope submission
  id, not only by the submitted filename, since many students upload files
  with the same name.
- **Commands have timeouts**, and the Clojure script runner is configurable.
  `lein exec` is still the default.
- **`polygrade local` and `polygrade bundle`** replace ad hoc local testing
  and manual zipping.
