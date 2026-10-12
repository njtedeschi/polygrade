import pytest

from polygrade.config import AssignmentConfig, ConfigError, PartialCredit, find_config


def load(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return AssignmentConfig.load(path)


def test_load_resolves_paths_and_sorts_problems(tmp_path):
    config = load(tmp_path, """
language: python
paths: {submission: a/sub.py, solution: a/sol.py}
problems:
  2: {name: g, weight: 3, seed: 1}
  1: {name: f, weight: 2, partial_credit: [{solution: f_alt, credit: 0.5}]}
""")
    assert config.path("submission") == tmp_path / "a" / "sub.py"
    assert [p.number for p in config.problems] == [1, 2]
    first, second = config.problems
    assert first.partial_credit[0].solution == "f_alt"
    assert first.title == "Problem 1: f"
    assert second.options == {"seed": 1}
    assert config.visibility == "after_published"


def test_extra_top_level_keys_become_options(tmp_path):
    config = load(tmp_path, "language: x\npaths: {}\nproblems: {}\ntimeout: 5\n")
    assert config.options == {"timeout": 5}


@pytest.mark.parametrize("text", [
    "paths: {}\nproblems: {}",
    "language: python\npaths: {}\nproblems: {1: {name: f}}",
])
def test_invalid_configs(tmp_path, text):
    with pytest.raises(ConfigError):
        load(tmp_path, text)


def test_partial_credit_validation():
    with pytest.raises(ConfigError):
        PartialCredit(credit=0.5)
    with pytest.raises(ConfigError):
        PartialCredit(credit=0.5, solution="a", tag="1.1")
    with pytest.raises(ConfigError):
        PartialCredit(credit=2, tag="1.1")
    assert PartialCredit(credit=0.5, tag=3.1, waive_if=[2.1]).waive_if == ["2.1"]


def test_test_name_is_a_valid_identifier():
    from polygrade.config import Problem
    assert Problem(number=3, name="sum-of-squares", weight=1).test_name == "test_03_sum_of_squares"


def test_find_config_searches_parents(tmp_path):
    (tmp_path / "config.yaml").write_text("")
    (tmp_path / "tests").mkdir()
    assert find_config(tmp_path / "tests" / "test_x.py") == tmp_path / "config.yaml"
    with pytest.raises(ConfigError):
        find_config(tmp_path / "tests", filename="missing.yaml")
