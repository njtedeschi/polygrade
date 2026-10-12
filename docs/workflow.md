# From an assignment to a Gradescope autograder

This guide covers the whole process: creating an autograder for an
assignment, testing it on your own machine, and putting it on Gradescope.
The language guides ([Python](python.md), [Clojure](clojure.md),
[other languages](other-languages.md)) cover step 2 in depth.

Gradescope's own documentation is the authority on its side of the process:

- [Autograder specification](https://gradescope-autograders.readthedocs.io/en/latest/specs/):
  the files an autograder needs, the environment it runs in, and the
  `results.json` format.
- [Gradescope help center](https://guides.gradescope.com/): creating and
  managing programming assignments.

polygrade is not affiliated with Gradescope. Gradescope's interface changes
over time, so if a button or setting described below has moved, its help
center is the place to check.

## What Gradescope expects

A Gradescope autograder is a zip file with two scripts at its root:

- **`setup.sh`** runs once, when Gradescope builds the autograder's Docker
  image. It installs whatever grading needs, e.g. Python packages, a JDK.
- **`run_autograder`** runs once per submission. The submitted files are in
  `/autograder/submission/`, and the script must write the results to
  `/autograder/results/results.json`.

Everything else in the zip is unpacked to `/autograder/source/`, where
`run_autograder` can use it. Students never see these files, so the solution
can safely be included.

Every example in this repository follows this layout, and its
`run_autograder` does two things:

```bash
python3 -m polygrade collect ...   # copy the submission into place
python3 -m polygrade run --results /autograder/results/results.json
```

## 1. Start from an example

Copy the example for your language into a new folder outside `examples/`:

```bash
mkdir -p my-course && cp -r examples/python-stats my-course/hw3
```

Delete the example's assignment files and sample submissions.

## 2. Describe the assignment

- **Starter code and solution.** Put the files you give students and your
  reference solution where `config.yaml`'s `paths` point.
- **Problems.** Under `problems` in `config.yaml`, add one entry per problem
  with the name of the function students implement and its weight in points.
  Add partial credit entries for mistakes you expect.
- **Tests.** For Python, set each problem's test inputs in `tests/`. For
  Clojure and other languages, write the unit tests in the language itself.
- **Submission filename** (Python). The config's `submission` path sets the
  filename students must submit, e.g. `assignment/hw3.py` means students
  submit `hw3.py`. Tell them in the assignment instructions. (For Clojure and
  other languages, students submit exactly one file with any name.)
- **Dependencies.** Add any packages that the solution or students' code
  needs (e.g. `torch`) to `requirements.txt`, and any system packages to
  `setup.sh`.

See the [configuration reference](configuration.md) for every option.

## 3. Test it locally

Write a few sample submissions in a `sample_submissions/` folder, one per
subfolder: a correct one, and one per mistake you want to check is graded the
way you intend. Then run:

```bash
polygrade local my-course/hw3 my-course/hw3/sample_submissions/*
```

For each submission, this:

1. creates a temporary mock of Gradescope's `/autograder` directory,
2. copies in your autograder (plus polygrade) and the submission,
3. runs your actual `run_autograder` script, and
4. summarizes the resulting `results.json`: each test's score, and the
   messages students would see for failed tests.

Useful options:

- `--json` prints the raw `results.json`.
- `--debug` shows the autograder's own output. For Clojure, it also prints
  the student's and the solution's output for every test.
- `--keep` keeps the temporary directory so you can inspect it.

Your local Python environment needs the packages in `requirements.txt`, and
for Clojure, a way to run Clojure scripts (see [Clojure](clojure.md#running-clojure)).
`setup.sh` itself is not run locally.

A folder counts as one submission. So once students have submitted, you can
download their submissions from Gradescope and run them all locally, e.g. to
check how a change to the tests would affect the class before you make it.

## 4. Bundle it

```bash
polygrade bundle my-course/hw3 -o hw3-autograder.zip
```

The zip contains the autograder folder's contents (without
`sample_submissions/`, caches or old zips) at its root, plus a copy of the
`polygrade` package. Nothing has to be installed from this repository on
Gradescope.

## 5. Upload it to Gradescope

1. In your course, create a new **Programming Assignment**. In its settings,
   enable the autograder. Set the total points to the sum of the problem
   weights in `config.yaml`, plus any manually graded points.
2. Open the assignment's autograder configuration page, choose to upload a
   zip file, and upload the bundle. Pick an Ubuntu base image. The examples'
   `setup.sh` scripts use `apt-get`, so they need an Ubuntu image.
3. Wait for the build to finish. Gradescope shows the output of `setup.sh`,
   so if the build fails, the error will be there.
4. **Test the autograder** with one of your sample submissions. Gradescope
   offers this on the configuration page. The results should match what
   `polygrade local` showed.

## 6. Grade and publish

- **While the assignment is open**, students see the prerequisite checks
  (file found, imports or compiles, required definitions) as soon as they
  submit, and can resubmit until they pass. Problem scores are hidden.
- **After the deadline**, review the results, then **publish grades**. Problem
  results are shown to students only once grades are published (Gradescope's
  `after_published` visibility). To change this for one problem or for the
  whole assignment, set `visibility` in `config.yaml`.

## Changing the autograder later

If you fix a test or adjust partial credit after students have submitted:

1. Make the change and check it with `polygrade local`, ideally on downloaded
   student submissions.
2. Bundle and upload the new zip, and wait for the build.
3. Rerun the autograder on all submissions from the assignment's submissions
   page. Results update only when it is rerun.

To grade a hand-corrected version of one student's submission (e.g. after
fixing a trivial syntax error), see
[Regrading a corrected submission](clojure.md#regrading-a-corrected-submission).
`run_autograder` uses this in the Clojure example, and you can use the same
`--overrides` option of `polygrade collect` in any `run_autograder` that
collects a single file.
