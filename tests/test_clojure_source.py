from polygrade.clojure.source import Definitions, strip_comments

SOURCE = r'''
;; (defn commented-out [x] x)
(def greeting "hello; world")   ; a semicolon in a string isn't a comment
(defn plain [x y] (+ x y))
(defn with-docstring
  "A docstring with a [bracket] and an escaped \" quote."
  [xs]
  (count xs))
(defn- private-helper [] 1)
(defn variadic [x & more] x)
(def total 0)
(def total 1)
(defn plain [x] x)
'''


def test_strip_comments_respects_strings():
    stripped = strip_comments(SOURCE)
    assert "commented-out" not in stripped
    assert '"hello; world"' in stripped
    assert "a semicolon" not in stripped


def test_parse_definitions():
    definitions = Definitions.parse(SOURCE)
    assert dict(definitions.functions) == {
        "plain": [2, 1],
        "with-docstring": [1],
        "private-helper": [0],
        "variadic": [3],
    }
    assert definitions.variables == {"greeting": 1, "total": 2}
    assert sorted(definitions.duplicates()) == ["plain", "total"]
