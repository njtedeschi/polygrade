import os
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"


def clojure_available() -> bool:
    return bool(os.environ.get("POLYGRADE_CLOJURE_COMMAND")) or shutil.which("lein") is not None


requires_clojure = pytest.mark.skipif(
    not clojure_available(),
    reason="needs Leiningen with lein-exec, or POLYGRADE_CLOJURE_COMMAND set to a Clojure script runner",
)
