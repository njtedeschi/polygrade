import textwrap

from polygrade.python.fixes import ensure_return
from polygrade.python.loader import import_from_path


def make_module(tmp_path, name, source):
    path = tmp_path / f"{name}.py"
    path.write_text(textwrap.dedent(source))
    return import_from_path(path)


def test_ensure_return_adds_missing_return(tmp_path):
    module = make_module(tmp_path, "fix_missing", """
        OFFSET = 10

        def build(n):
            result = []
            for i in range(n):
                result.append(i + OFFSET)
        """)
    assert module.build(2) is None
    ensure_return("build", "result")(module)
    assert module.build(2) == [10, 11]  # module globals are still visible


def test_ensure_return_leaves_correct_function_alone(tmp_path):
    module = make_module(tmp_path, "fix_ok", """
        def build(n):
            result = list(range(n))
            return result
        """)
    original = module.build
    ensure_return("build", "result")(module)
    assert module.build is original


def test_ensure_return_ignores_missing_function(tmp_path):
    module = make_module(tmp_path, "fix_absent", "x = 1\n")
    ensure_return("build", "result")(module)
    assert not hasattr(module, "build")
