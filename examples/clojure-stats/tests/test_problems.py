"""Gradescope tests for the example Clojure assignment, generated from config.yaml.

The unit tests themselves are in unit-tests.clj.
"""
from polygrade import find_config
from polygrade.clojure import ClojureGrader

TestSubmission = ClojureGrader.from_config(find_config(__file__)).build()
