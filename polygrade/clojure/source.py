"""Lightweight static analysis of Clojure source files.

Good enough to check that a submission defines the functions (with the right
number of parameters) and variables that an assignment asks for, without
running it. This is deliberately a regex-level approximation, not a reader.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# (defn name [params] ...) or (defn name "docstring" [params] ...)
_DEFN = re.compile(r'\(defn-?\s+([^\s\[\]()"]+)\s+(?:"(?:[^"\\]|\\.)*"\s+)?\[([^\]]*)\]', re.DOTALL)
_DEF = re.compile(r'\(def\s+([^\s\[\]()"]+)')


def strip_comments(source: str) -> str:
    """Remove ``;`` line comments, leaving semicolons inside strings alone."""
    stripped = []
    for line in source.splitlines():
        in_string = escaped = False
        for i, char in enumerate(line):
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = not in_string
            elif char == ";" and not in_string:
                line = line[:i]
                break
        stripped.append(line)
    return "\n".join(stripped)


@dataclass
class Definitions:
    # Function name -> parameter count of each definition (a list, to detect duplicates)
    functions: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    # Variable name -> number of definitions
    variables: Counter = field(default_factory=Counter)

    @classmethod
    def parse(cls, source: str) -> "Definitions":
        source = strip_comments(source)
        definitions = cls()
        for match in _DEFN.finditer(source):
            definitions.functions[match.group(1)].append(len(match.group(2).split()))
        for match in _DEF.finditer(source):
            definitions.variables[match.group(1)] += 1
        return definitions

    @classmethod
    def from_file(cls, path: Path) -> "Definitions":
        return cls.parse(Path(path).read_text(errors="replace"))

    def duplicates(self) -> List[str]:
        return ([name for name, arities in self.functions.items() if len(arities) > 1]
                + [name for name, count in self.variables.items() if count > 1])
