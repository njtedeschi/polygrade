import json
import zipfile

from conftest import EXAMPLES
from polygrade.cli import bundle, collect


def test_collect_all_flattens_subfolders(tmp_path):
    submission = tmp_path / "submission"
    (submission / "folder").mkdir(parents=True)
    (submission / "main.py").write_text("")
    (submission / "folder" / "helper.py").write_text("")
    (submission / "notes.txt").write_text("")
    collect("*.py", tmp_path / "dest", submission)
    assert sorted(p.name for p in (tmp_path / "dest").iterdir()) == ["helper.py", "main.py"]


def test_collect_single_requires_exactly_one_match(tmp_path):
    submission = tmp_path / "submission"
    submission.mkdir()
    dest = tmp_path / "source" / "submission.clj"
    (submission / "a b.clj").write_text("a")  # spaces in names are fine
    assert collect("*.clj", dest, submission, single=True) == [dest]
    assert dest.read_text() == "a"

    dest.unlink()
    (submission / "c.clj").write_text("c")
    assert collect("*.clj", dest, submission, single=True) == []
    assert not dest.exists()


def test_collect_single_prefers_corrected_submission(tmp_path):
    submission = tmp_path / "submission"
    submission.mkdir()
    (submission / "hw.clj").write_text("original")
    overrides = tmp_path / "corrected"
    overrides.mkdir()
    dest = tmp_path / "submission.clj"

    (overrides / "hw.clj").write_text("corrected by filename")
    collect("*.clj", dest, submission, single=True, overrides=overrides)
    assert dest.read_text() == "corrected by filename"

    (tmp_path / "submission_metadata.json").write_text(json.dumps({"id": 123}))
    (overrides / "123.clj").write_text("corrected by id")
    collect("*.clj", dest, submission, single=True, overrides=overrides)
    assert dest.read_text() == "corrected by id"


def test_bundle_includes_framework_and_excludes_samples(tmp_path):
    archive = bundle(EXAMPLES / "python-stats", tmp_path / "autograder.zip")
    names = zipfile.ZipFile(archive).namelist()
    assert "setup.sh" in names and "run_autograder" in names and "config.yaml" in names
    assert "polygrade/python/grader.py" in names
    assert "polygrade/clojure/autograde.clj" in names
    assert not any("sample_submissions" in name or "__pycache__" in name for name in names)
    mode = zipfile.ZipFile(archive).getinfo("run_autograder").external_attr >> 16
    assert mode & 0o111, "run_autograder must stay executable"
