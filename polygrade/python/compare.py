"""Comparing a submission's output with the solution's.

``assert_outputs_match`` raises ``AssertionError`` on a mismatch. Numbers,
NumPy arrays and PyTorch tensors are compared with a tolerance; PyTorch
modules are compared parameter by parameter; containers are compared
element-wise; anything else falls back to ``==``.

PyTorch is optional: it is only consulted if the code being graded has
already imported it.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping

import numpy as np

from polygrade.messages import truncate

DEFAULT_RTOL = 1e-5
DEFAULT_ATOL = 1e-8


def _torch():
    return sys.modules.get("torch")


def _is_module(x) -> bool:
    torch = _torch()
    return torch is not None and isinstance(x, torch.nn.Module)


def _is_tensor(x) -> bool:
    torch = _torch()
    return torch is not None and torch.is_tensor(x)


def _is_numeric(x) -> bool:
    if isinstance(x, (str, bytes)) or x is None:
        return False
    try:
        return np.asarray(x).dtype.kind in "biufc"
    except (ValueError, TypeError):  # e.g. ragged nested lists
        return False


def assert_outputs_match(actual, expected, rtol: float = DEFAULT_RTOL, atol: float = DEFAULT_ATOL):
    if _is_module(actual) and _is_module(expected):
        actual_params, expected_params = list(actual.parameters()), list(expected.parameters())
        assert len(actual_params) == len(expected_params), "Models have different numbers of parameters."
        for a, e in zip(actual_params, expected_params):
            _torch().testing.assert_close(a, e, rtol=rtol, atol=atol)
    elif _is_tensor(actual) and _is_tensor(expected):
        # Treat scalars and single-element vectors as interchangeable
        if actual.dim() <= 1 and expected.dim() <= 1:
            actual, expected = actual.reshape(-1), expected.reshape(-1)
        _torch().testing.assert_close(actual, expected, rtol=rtol, atol=atol)
    elif isinstance(expected, Mapping):
        assert isinstance(actual, Mapping), f"Expected a mapping, got {type(actual).__name__}."
        assert set(actual) == set(expected), "Keys do not match."
        for key in expected:
            assert_outputs_match(actual[key], expected[key], rtol, atol)
    elif _is_numeric(actual) and _is_numeric(expected):
        np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol)
    elif isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        assert len(actual) == len(expected), "Lengths do not match."
        for a, e in zip(actual, expected):
            assert_outputs_match(a, e, rtol, atol)
    else:
        assert actual == expected


def outputs_match(actual, expected, **tolerances) -> bool:
    try:
        assert_outputs_match(actual, expected, **tolerances)
    except Exception:  # comparison errors (e.g. incompatible shapes) count as mismatches
        return False
    return True


def comparison_message(actual, expected) -> str:
    if _is_module(actual) and _is_module(expected):
        return "Submission model parameters don't match the solution's (with a fixed random seed)."
    return (f"Submission output {truncate(repr(actual))} "
            f"did not match solution output {truncate(repr(expected))}")
