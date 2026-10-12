# Supporting other languages

polygrade treats a language other than Python as a black box. Some command
runs your tests against the submission, and polygrade reads which tests failed
from its output. You can write the tests in whatever language suits the
assignment. Nothing about the language has to be taught to polygrade.
[`examples/external-bash`](../examples/external-bash) grades Bash scripts this
way, with no Python beyond the three-line test file every autograder has.

## The protocol

The test command prints one report per failed test, in either of two forms:

```
FAIL Q2: incorrect count for four words
```

or a marker line followed by the message on the next line, which is what
`clojure.test` and many other test frameworks print:

```
FAIL in (word-count-test) (tests.clj:12)
Q2: incorrect count for four words
```

- `FAIL` means a wrong answer, and `ERROR` means the test crashed.
- `Q<n>: message` fails problem `n`. The student sees the first message for
  each problem. For `ERROR`, they see "Runtime error for test input." instead,
  so stack traces from your tests aren't shown to them.
- `PC<tag>: message` (`FAIL` only) flags a known mistake. The problem's
  `partial_credit` entries in `config.yaml` map tags to credit.
- All other output is ignored.
- If the command exits with a nonzero status, every problem fails.

## Configuration

```yaml
language: external

paths:
  submission: submission.sh
  solution: solution.sh
  tests: run_tests.sh

submission_pattern: "*.sh"          # shown to students if no file was found

compile_command: [bash, -n, "{submission}"]                    # optional
grade_command: [bash, "{tests}", "{solution}", "{submission}"]
timeout: 60

problems:
  1: {name: greet, weight: 2}
  2:
    name: word_count
    weight: 3
    partial_credit:
      - tag: "2.1"
        credit: 0.5
        message: "Counted characters instead of words."
```

In commands, `{key}` is replaced with the absolute path of any entry under
`paths`, and `{root}` with the autograder directory. `compile_command` is
optional. If it's given, it becomes a blocking prerequisite check, and
students see the end of its error output when it fails.

Then `tests/test_problems.py` builds the Gradescope tests:

```python
from polygrade import find_config, load_grader

TestSubmission = load_grader(find_config(__file__)).build()
```

`run_autograder` collects the single submitted file, and `setup.sh` installs
the language's toolchain. See the example for both.

## Going further: a language adapter

When a language needs more than configuration, subclass `ExternalGrader`.
[`polygrade/clojure/grader.py`](../polygrade/clojure/grader.py) does this in
about 100 lines. It:

- builds `grade_command()` and `compile_command()` from a configurable script
  runner and the bundled `autograde.clj` driver, and
- adds two prerequisite checks: required definitions and duplicate
  definitions. These use a little static analysis
  ([`source.py`](../polygrade/clojure/source.py)).

A `Check` is a key, a title, a function returning `(passed, message)`, and
whether it's blocking:

```python
from polygrade.external import ExternalGrader
from polygrade.grader import Check


class RacketGrader(ExternalGrader):
    language = "racket"

    def grade_command(self):
        paths = self.config.paths
        return ["racket", str(paths["tests"]), str(paths["solution"]), str(self.submission_path)]

    def prerequisite_checks(self):
        return super().prerequisite_checks() + [
            Check("lang_line", "File starts with #lang racket", self._check_lang_line, blocking=False),
        ]

    def _check_lang_line(self):
        first_line = self.submission_path.read_text().splitlines()[:1]
        if first_line == ["#lang racket"]:
            return True, "Found #lang racket"
        return False, "The first line of your file should be #lang racket"
```

Use it with `language: racket` in `config.yaml` and
`TestSubmission = RacketGrader.from_config(find_config(__file__)).build()`.

`grade_problem(problem)` can be overridden too, if the protocol's scoring
isn't enough. It returns a `ProblemResult` with a credit fraction, a
pass/fail status and a message.
