"""Lenient fixes applied to a submission after it is imported.

A fix is any callable that takes the submission module and modifies it in
place. Pass fixes to ``PythonGrader(..., fixes=[...])``. They are meant for
slips that are irrelevant to what an assignment is assessing, where failing
every downstream test would be out of proportion to the mistake.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from types import ModuleType
from typing import Callable

Fix = Callable[[ModuleType], None]


def ensure_return(function_name: str, variable_name: str) -> Fix:
    """Make ``function_name`` return ``variable_name`` if it forgot to.

    For starter code where students fill in the body of a function that ends
    with a provided ``return <variable_name>``, and some delete or never
    write that line. If the function's last statement is not exactly that
    return, one is appended.
    """

    def fix(module: ModuleType):
        fn = getattr(module, function_name, None)
        if not inspect.isfunction(fn):
            return
        try:
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        except (OSError, TypeError, SyntaxError):
            return  # source unavailable; leave the function alone
        fn_def = next((node for node in tree.body
                       if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
        if fn_def is None:
            return
        last = fn_def.body[-1]
        if isinstance(last, ast.Return) and isinstance(last.value, ast.Name) and last.value.id == variable_name:
            return
        fn_def.body.append(ast.Return(value=ast.Name(id=variable_name, ctx=ast.Load())))
        # Keep line numbers in tracebacks pointing at the submitted file
        ast.increment_lineno(ast.fix_missing_locations(tree), fn.__code__.co_firstlineno - 1)
        namespace = {}
        exec(compile(tree, inspect.getsourcefile(fn) or "<fixed>", "exec"),
             module.__dict__, namespace)
        setattr(module, function_name, namespace[fn_def.name])

    fix.__name__ = f"ensure_return({function_name!r}, {variable_name!r})"
    return fix
