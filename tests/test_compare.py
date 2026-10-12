import numpy as np
import pytest

from polygrade.python.compare import assert_outputs_match, comparison_message, outputs_match


@pytest.mark.parametrize("actual, expected", [
    (1.0, 1.0 + 1e-9),
    ([1, 2, 3], np.array([1.0, 2.0, 3.0])),
    (np.array([[1.0, 2.0]]), np.array([[1.0, 2.0]])),
    ({"a": 1.0, "b": [1, 2]}, {"a": 1.0 + 1e-10, "b": [1, 2]}),
    ("text", "text"),
    ([("a", 1.0), ("b", 2.0)], [("a", 1.0), ("b", 2.0)]),
    (None, None),
])
def test_matches(actual, expected):
    assert_outputs_match(actual, expected)


@pytest.mark.parametrize("actual, expected", [
    (1.0, 1.1),
    ([1, 2], [1, 2, 3]),
    ({"a": 1}, {"b": 1}),
    ("text", "other"),
    (None, 1.0),
    (np.zeros(2), np.zeros(3)),
])
def test_mismatches(actual, expected):
    assert not outputs_match(actual, expected)


def test_tolerances():
    assert outputs_match(1.0, 1.05, rtol=0.1)
    assert not outputs_match(1.0, 1.05)


def test_comparison_message_truncates():
    message = comparison_message(list(range(1000)), [])
    assert "truncated" in message and len(message) < 1200


def test_torch_if_available():
    torch = pytest.importorskip("torch")
    assert_outputs_match(torch.tensor(2.0), torch.tensor([2.0]))
    model_a, model_b = torch.nn.Linear(2, 1), torch.nn.Linear(2, 1)
    model_b.load_state_dict(model_a.state_dict())
    assert_outputs_match(model_a, model_b)
