"""Formatting helpers for messages shown to students."""
from __future__ import annotations

import traceback

MAX_REPR_LENGTH = 500


def error_message(e: BaseException, lines: int = 3) -> str:
    """The last few lines of an exception's traceback.

    The tail of a traceback names the failing line of student code and the
    error itself, without exposing the autograder's internals.
    """
    formatted = "".join(traceback.format_exception(type(e), e, e.__traceback__)).strip()
    if not formatted:
        return "No traceback available"
    return "\n".join(formatted.split("\n")[-lines:])


def truncate(text: str, limit: int = MAX_REPR_LENGTH) -> str:
    return text if len(text) <= limit else text[:limit] + " ...[truncated]"


def tail(text: str, lines: int = 30) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])
