# Configuration reference

An autograder's `config.yaml` sits at the root of the autograder directory.
Paths in it are relative to that directory.

## Top level

| Key | Required | Description |
| --- | --- | --- |
| `language` | yes | `python`, `clojure` or `external` |
| `paths` | yes | Named file paths (see below) |
| `problems` | yes | Problems, keyed by problem number |
| `visibility` | no | Gradescope visibility of the problem tests (default `after_published`). Prerequisite checks are always `visible` |

Other top-level keys are options for the language's grader:

| Key | Languages | Description |
| --- | --- | --- |
| `grade_command` | external | Command that runs the tests (a list). `{<path name>}` and `{root}` are replaced with absolute paths |
| `compile_command` | external | Optional command that must succeed for the submission to be graded |
| `command` | clojure | How to run a Clojure script (default `[lein, exec]`) |
| `required` | clojure | `functions` (name → number of parameters) and `variables` (list) the submission must define. Defaults to the starter's definitions |
| `submission_pattern` | external, clojure | Filename pattern shown to students when no submission was found |
| `timeout` | external, clojure | Seconds before a command is killed (default 600) |

## `paths`

| Name | Languages | Description |
| --- | --- | --- |
| `submission` | all | Where `run_autograder` puts the submission |
| `solution` | all | The reference solution |
| `starter` | python, clojure (optional) | The starter code. The submission must define everything it defines |
| `tests` | clojure (and external, by convention) | The unit tests file |

## Problems

```yaml
problems:
  3:                          # problem number (an integer), used for ordering and on Gradescope
    name: standardize         # the function/variable students implement
    weight: 4                 # points
    title: "Problem 3: z-scores"   # optional; the test's name on Gradescope
    visibility: visible       # optional; overrides the top-level visibility
    generate_test: false      # optional; write this problem's test by hand
    partial_credit: [...]     # optional; see below
```

### Python-only problem options

| Key | Default | Description |
| --- | --- | --- |
| `additional_prerequisites` | `[]` | Names to replace with the solution's versions while grading, in addition to earlier problems' functions |
| `rtol`, `atol` | `1e-5`, `1e-8` | Comparison tolerances |
| `seed` | none | Reseed `random`, NumPy and PyTorch with this before every call |
| `copy_inputs` | `true` | Pass each call a deep copy of the test inputs |

### Partial credit

Each entry gives a fraction of the problem's weight (`credit`, between 0 and
1) for a specific mistake. Entries are tried in order, and the first that
applies wins.

| Key | Description |
| --- | --- |
| `credit` | Fraction of the weight to award |
| `message` | Shown to the student. Defaults to "Partial credit." (Python) or the detecting test's message (other languages) |
| `solution` | **Python:** the name of an incorrect implementation in the solution module. Applies when the submission matches it on every input |
| `tag` | **Other languages:** applies when a test reported `PC<tag>:` |
| `waive_if` | **Other languages:** tags of earlier mistakes. If any of them was also flagged, this one is a repeat and gets full credit |
