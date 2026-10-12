"""Command-line entry points.

    polygrade collect  copy a submission into place (called by run_autograder)
    polygrade run      run the tests and write Gradescope's results.json
    polygrade local    simulate Gradescope locally on one or more submissions
    polygrade bundle   zip an autograder (with polygrade itself) for upload
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import List, Optional

from polygrade.config import CONFIG_FILENAME, DEFAULT_VISIBILITY, AssignmentConfig

PACKAGE_DIR = Path(__file__).resolve().parent
TESTS_DIR = "tests"
# Files in an autograder directory that are never part of the uploaded autograder
EXCLUDED = ["__pycache__", "*.pyc", ".DS_Store", "*.zip", "results.json", "sample_submissions"]


def autograder_root() -> Path:
    """Gradescope's base directory, overridable for local runs."""
    return Path(os.environ.get("AUTOGRADER_ROOT", "/autograder"))


# collect


def _submission_id(root: Path) -> Optional[str]:
    try:
        with open(root / "submission_metadata.json") as f:
            return str(json.load(f)["id"])
    except (OSError, ValueError, KeyError):
        return None


def collect(pattern: str, dest: Path, submission_dir: Path, single: bool = False,
            overrides: Optional[Path] = None) -> List[Path]:
    """Copy submitted files matching ``pattern`` (searching subfolders) to ``dest``.

    By default every match is copied into the directory ``dest``, keeping its
    name. With ``single``, there must be exactly one match, which is copied to
    the file path ``dest``; otherwise nothing is copied, and the grader's
    "submission found" check fails.

    ``overrides`` is a directory of corrected submissions for regrading: a file
    there named after the Gradescope submission id (e.g. ``123456.clj``) or
    after the submitted file is used in place of the submitted file.
    """
    matches = sorted(p for p in submission_dir.rglob("*") if p.is_file() and fnmatch.fnmatch(p.name, pattern))
    if single:
        if len(matches) != 1:
            print(f"Expected exactly one file matching {pattern}, found {len(matches)}.", file=sys.stderr)
            return []
        source = matches[0]
        if overrides is not None:
            submission_id = _submission_id(submission_dir.parent)
            candidates = [overrides / source.name]
            if submission_id is not None:
                candidates.insert(0, overrides / f"{submission_id}{source.suffix}")
            source = next((c for c in candidates if c.is_file()), source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, dest)
        return [dest]
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for match in matches:
        shutil.copy(match, dest / match.name)
        copied.append(dest / match.name)
    return copied


# run


def run_tests(root: Path, results_path: Optional[Path] = None) -> bool:
    """Discover and run ``root/tests``, writing Gradescope JSON to ``results_path`` if given."""
    root = root.resolve()
    sys.path.insert(0, str(root))
    os.chdir(root)
    suite = unittest.defaultTestLoader.discover(TESTS_DIR)

    if results_path is None:
        return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()

    from gradescope_utils.autograder_utils.json_test_runner import JSONTestRunner

    visibility = DEFAULT_VISIBILITY
    if (root / CONFIG_FILENAME).is_file():
        visibility = AssignmentConfig.load(root / CONFIG_FILENAME).visibility
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        return JSONTestRunner(stream=f, visibility=visibility).run(suite).wasSuccessful()


# local


def _ignore(directory, names):
    return {name for name in names if any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED)}


def simulate(autograder_dir: Path, submission: Path, debug: bool = False, keep: bool = False) -> dict:
    """Run ``autograder_dir``'s ``run_autograder`` on ``submission`` in a mock Gradescope layout.

    Returns the parsed ``results.json``.
    """
    root = Path(tempfile.mkdtemp(prefix="polygrade-"))
    try:
        source = root / "source"
        shutil.copytree(autograder_dir, source, ignore=_ignore)
        if not (source / "polygrade").exists():
            shutil.copytree(PACKAGE_DIR, source / "polygrade", ignore=_ignore)
        if submission.is_dir():
            shutil.copytree(submission, root / "submission", ignore=_ignore)
        else:
            (root / "submission").mkdir()
            shutil.copy(submission, root / "submission")
        (root / "results").mkdir()

        env = dict(os.environ, AUTOGRADER_ROOT=str(root))
        # Make `python3` in run_autograder the interpreter running this command
        env["PATH"] = os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")])
        if debug:
            env["POLYGRADE_DEBUG"] = "1"
        process = subprocess.run(["bash", str(source / "run_autograder")], cwd=source, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if debug or process.returncode != 0:
            print(process.stdout)
        results_file = root / "results" / "results.json"
        if not results_file.is_file():
            raise RuntimeError(f"run_autograder produced no results.json (exit code {process.returncode}).")
        with open(results_file) as f:
            return json.load(f)
    finally:
        if keep:
            print(f"Kept simulated autograder at {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


def _sort_key(test: dict) -> float:
    try:
        return float(test.get("number", 0))
    except ValueError:
        return 0.0


def format_results(results: dict, show_output: bool = True) -> str:
    lines = []
    total = max_total = 0.0
    for test in sorted(results["tests"], key=_sort_key):
        score, max_score = test.get("score", 0.0), test.get("max_score", 0.0)
        total += score
        max_total += max_score
        status = "ok  " if test["status"] == "passed" else "FAIL"
        lines.append(f"  {status} {test.get('number', ''):>5}  {test['name'][:52]:<52} {score:g}/{max_score:g}")
        output = test.get("output", "").strip()
        if show_output and output and test["status"] != "passed":
            lines.extend(f"              | {line}" for line in output.splitlines())
    lines.append(f"  Total: {total:g}/{max_total:g}")
    return "\n".join(lines)


# bundle


def bundle(autograder_dir: Path, output: Path) -> Path:
    """Zip the contents of ``autograder_dir`` plus the polygrade package for upload to Gradescope."""
    output = output.resolve()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        def add_tree(directory: Path, prefix: str):
            for path in sorted(directory.rglob("*")):
                relative = path.relative_to(directory)
                if path.resolve() == output or any(_ignore(None, [part]) for part in relative.parts):
                    continue
                if path.is_file():
                    archive.write(path, f"{prefix}{relative.as_posix()}")

        add_tree(autograder_dir, "")
        if not (autograder_dir / "polygrade").exists():
            add_tree(PACKAGE_DIR, "polygrade/")
    return output


# Entry point


def main(argv=None):
    parser = argparse.ArgumentParser(prog="polygrade", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("collect", help="copy submitted files into the autograder")
    p.add_argument("--pattern", required=True, help='filename pattern, e.g. "*.py"')
    p.add_argument("--dest", type=Path, required=True,
                   help="directory to copy matches into (or, with --single, the destination file)")
    p.add_argument("--single", action="store_true", help="require exactly one match and rename it to --dest")
    p.add_argument("--overrides", type=Path, help="directory of corrected submissions to use instead")
    p.add_argument("--submission-dir", type=Path, help="default: $AUTOGRADER_ROOT/submission")

    p = commands.add_parser("run", help="run the autograder's tests")
    p.add_argument("--root", type=Path, default=Path("."), help="autograder directory (default: .)")
    p.add_argument("--results", type=Path, help="write Gradescope JSON here instead of printing results")

    p = commands.add_parser("local", help="simulate Gradescope on local submissions")
    p.add_argument("autograder", type=Path, help="autograder directory (containing run_autograder)")
    p.add_argument("submissions", type=Path, nargs="+",
                   help="submission files or folders (a folder is treated as one submission)")
    p.add_argument("--json", action="store_true", help="print raw results.json instead of a summary")
    p.add_argument("--debug", action="store_true", help="show autograder output and set POLYGRADE_DEBUG")
    p.add_argument("--keep", action="store_true", help="keep the temporary autograder directory")
    p.add_argument("--brief", action="store_true", help="omit failure messages from the summary")

    p = commands.add_parser("bundle", help="zip an autograder for upload to Gradescope")
    p.add_argument("autograder", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("autograder.zip"))

    args = parser.parse_args(argv)

    if args.command == "collect":
        submission_dir = args.submission_dir or autograder_root() / "submission"
        copied = collect(args.pattern, args.dest, submission_dir, args.single, args.overrides)
        for path in copied:
            print(f"Collected {path}")
    elif args.command == "run":
        run_tests(args.root, args.results)
    elif args.command == "local":
        for submission in args.submissions:
            results = simulate(args.autograder, submission, debug=args.debug, keep=args.keep)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print(f"== {submission} ==")
                print(format_results(results, show_output=not args.brief))
    elif args.command == "bundle":
        print(f"Wrote {bundle(args.autograder, args.output)}")


if __name__ == "__main__":
    main()
