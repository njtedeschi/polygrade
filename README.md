# polygrade

A unified framework for building [Gradescope](https://www.gradescope.com/)-compatible
autograders for Python and other languages. Python submissions are graded
natively; any other language can be added with a thin wrapper, and Clojure
support is included as a worked example.

> **Not affiliated with Gradescope.** This is an independent project, not
> made or endorsed by Gradescope or Turnitin. It builds autograders in the
> format Gradescope's
> [autograder specification](https://gradescope-autograders.readthedocs.io/en/latest/specs/)
> describes, and it uses Gradescope's open-source helper library,
> [`gradescope-utils`](https://github.com/gradescope/gradescope-utils), to
> produce results.

You describe an assignment's problems, weights and partial credit in a YAML
file. polygrade generates the Gradescope tests from it: checks that the
submission can be graded at all, one scored test per problem, and the
`results.json` that Gradescope expects.

```yaml
# config.yaml
language: python
paths:
  submission: assignment/stats.py
  starter: assignment/stats_starter.py
  solution: assignment/stats_solution.py
problems:
  1:
    name: mean
    weight: 4
  2:
    name: variance
    weight: 4
    partial_credit:
      - solution: population_variance   # a known, incorrect implementation
        credit: 0.5
        message: "Divided by n instead of n - 1."
```

```python
# tests/test_stats.py
from polygrade import find_config
from polygrade.python import Input, PythonGrader

grader = PythonGrader.from_config(find_config(__file__))
grader.set_test_inputs("mean", Input.of([1, 2, 3]), Input.of([-1.5, 4.0]))
grader.set_test_inputs("variance", Input.of([1, 2, 3]), Input.of([2, 4, 4, 5]))

TestStats = grader.build()
```

## Features

- **Pre-deadline feedback without giving away answers.** Students always see
  the prerequisite checks (file submitted, imports or compiles, defines what
  the starter code defines), so they can fix a broken submission before the
  deadline. Problem results stay hidden until grades are published.
- **No cascading failures.** While a problem is graded, the functions from
  earlier problems are swapped for the solution's versions. A mistake in
  problem 1 costs points only on problem 1, not on every problem that uses it.
- **Partial credit for known mistakes.** You can award partial credit when a
  submission matches a known, incorrect implementation (Python) or when a test
  detects a specific mistake (other languages). A rule can waive the penalty
  for a mistake already penalized in an earlier problem.
- **Sensible comparisons.** Numbers, NumPy arrays and PyTorch tensors are
  compared within a tolerance. PyTorch models are compared parameter by
  parameter, containers element by element, and everything else with `==`.
  You can set tolerances per problem or supply your own comparator.
- **Hand-written tests when you need them**, e.g. a test that counts calls to
  a function, reusing the same patching and scoring machinery.
- **Reproducible randomness.** You can reseed `random`, NumPy and PyTorch
  before each call, so the submission and the solution draw the same random
  numbers.
- **Leniency for slips.** Optional fixes repair mistakes that aren't what an
  assignment is about, such as deleting a provided `return` statement.
- **Local testing that mirrors Gradescope.** `polygrade local` runs your real
  `run_autograder` script in a mock `/autograder` directory on any number of
  sample submissions, and `polygrade bundle` builds the zip to upload.
- **Regrading by hand.** You can drop a corrected copy of a submission into the
  autograder, and it is graded in place of the original.

## Getting started

```bash
pip install -e .            # or: pip install -e ".[dev]" to also run the test suite

# Grade the example assignment's sample submissions in a simulated Gradescope
polygrade local examples/python-stats examples/python-stats/sample_submissions/*
```

## From an assignment to a Gradescope autograder

On Gradescope, an autograder is a zip file that you upload to a programming
assignment. Gradescope builds it once, then runs it on every submission. With
polygrade, the process is:

1. **Start from an example.** Copy the example for your language into a new
   folder. It already has the `setup.sh` and `run_autograder` scripts
   Gradescope requires.
2. **Describe the assignment.** Add your starter code and solution, list the
   problems and their weights in `config.yaml`, and write the test inputs
   (Python) or unit tests (other languages).
3. **Test it locally.** Write a few sample submissions, correct and
   incorrect, and run `polygrade local <autograder> <submissions...>`. This
   runs your real `run_autograder` script in a mock of Gradescope's
   environment and shows the scores and messages students would see.
4. **Bundle it.** `polygrade bundle <autograder> -o autograder.zip` zips the
   autograder together with polygrade itself.
5. **Upload it to Gradescope.** Create a programming assignment, upload the
   zip on its autograder settings page, and wait for the build to finish. Then
   test it with one of your sample submissions.
6. **Grade and publish.** Students see the prerequisite checks right away,
   and their problem scores once you publish grades.

[docs/workflow.md](docs/workflow.md) walks through each step in detail,
including what to do on Gradescope, regrading, and rerunning the autograder
after changes.

For step 2, follow the guide for your language and use its example as a
template:

| Example | Guide | What it shows |
| --- | --- | --- |
| [`examples/python-stats`](examples/python-stats) | [Python](docs/python.md) | Dependency patching, alternative-solution partial credit, a hand-written test, seeding, fixes |
| [`examples/clojure-stats`](examples/clojure-stats) | [Clojure](docs/clojure.md) | `clojure.test` macros, mocking with `with-redefs`, mistake detectors, waived penalties |
| [`examples/external-bash`](examples/external-bash) | [Other languages](docs/other-languages.md) | Supporting a new language from configuration alone |

The [configuration reference](docs/configuration.md) lists every config
option, and the [design notes](docs/design.md) explain how the pieces fit
together.

## How it works

Every Gradescope autograder is a zip file with two scripts at its root:
`setup.sh`, which installs dependencies once, and `run_autograder`, which
grades each submission and writes `/autograder/results/results.json`. With
polygrade, `run_autograder` has two steps:

```bash
python3 -m polygrade collect --pattern "*.py" --dest assignment   # copy the submission into place
python3 -m polygrade run --results /autograder/results/results.json
```

`polygrade run` discovers the `unittest` tests in `tests/`. These are the test
classes that `grader.build()` generates from `config.yaml`, plus any tests you
wrote by hand. It runs them with
[`gradescope-utils`](https://github.com/gradescope/gradescope-utils)' JSON
runner.

```
polygrade/
  config.py          config.yaml loading and validation
  grader.py          language-agnostic core: checks, problems -> unittest methods
  cli.py             collect / run / local / bundle
  python/            Python grading: importing, patching, comparing, fixes
  external/          the protocol for languages tested by an external process
  clojure/           Clojure support built on it, plus its .clj driver and macros
examples/            complete autograders with sample submissions
tests/               the framework's own test suite
```

## Background and use of AI

I wrote the original autograders over several years as a teaching assistant
for two university courses. One course had Python assignments and the other
had Clojure assignments. I built them for my own grading and for the rest of
the instructional team. Each course's autograder lived in its own private
repository and was copied and adapted for each assignment. Those versions
included real assignment material, so they can't be published.

This repository is a public adaptation of that work, made with an AI coding
assistant ([Claude Code](https://claude.com/claude-code)). I gave the
assistant the most recent versions of both autograders and asked it to:

- combine them into one framework, primarily for Python, that new languages
  can be added to with little wrapping;
- keep every feature the originals had;
- improve readability, organization and efficiency without moving far from the
  originals' design; and
- write documentation and examples that reveal nothing about the original
  assignments.

**From the originals (my design):** the overall approach and the features.
That means:

- visible prerequisite checks paired with problem results that stay hidden
  until grades are published;
- grading each problem with earlier problems' functions replaced by the
  solution's;
- partial credit for specific, known mistakes, in Python and Clojure;
- tolerant comparison of numbers, arrays, tensors and models;
- the Clojure driver, test macros, and checks for required and duplicate
  definitions;
- regrading hand-corrected submissions; and
- the lenient "missing return statement" fix.

**Done with the AI assistant:**

- **Restructuring** into the `polygrade` package. Configuration lives in one
  YAML file per assignment, and Gradescope tests are generated from it, so
  they're no longer copied into every assignment.
- **Generalizing** the Clojure integration into a small, documented protocol
  that other languages can use.
- **A command-line tool** for collecting submissions, simulating Gradescope
  locally and bundling autograders for upload.
- **New examples, documentation and an automated test suite.** The examples
  are generic toy assignments.
- **Fixing bugs** and making a few behavior changes:
  - Problems are no longer dropped when a prerequisite check fails.
  - A missing Clojure function costs only the problems that use it.
  - A crashed partial-credit test no longer counts as detecting a mistake.
  - Inputs are copied for each call, so a submission can't change them.
  - A broken "no double penalty" rule and a broken NaN comparison now work.

[`docs/design.md`](docs/design.md) lists every behavior change.

I reviewed the result. The test suite runs every example's sample
submissions through a simulated Gradescope run.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The Clojure end-to-end tests run only if `lein` (with the `lein-exec` plugin)
is installed, or if `POLYGRADE_CLOJURE_COMMAND` names another way to run a
Clojure script, e.g.
`POLYGRADE_CLOJURE_COMMAND="java -cp clojure.jar clojure.main"`.
