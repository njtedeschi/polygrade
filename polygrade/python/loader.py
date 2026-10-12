"""Importing submission, starter and solution files by path."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import List


def import_from_path(path: Path) -> ModuleType:
    """Import the Python file at ``path`` as a module named after its stem.

    The file's directory is put on ``sys.path`` so that multi-file
    submissions can import their own helper modules.
    """
    path = Path(path).resolve()
    module_dir = str(path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[path.stem]
        raise
    return module


def defined_functions_and_classes(module: ModuleType) -> List[str]:
    """Names of the functions and classes defined (not imported) in ``module``."""
    return [
        name for name, value in vars(module).items()
        if (inspect.isfunction(value) or inspect.isclass(value))
        and getattr(value, "__module__", None) == module.__name__
    ]


def has_function_or_class(module: ModuleType, name: str) -> bool:
    value = getattr(module, name, None)
    return inspect.isfunction(value) or inspect.isclass(value)
