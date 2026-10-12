"""Gradescope tests for the example Bash assignment, generated from config.yaml."""
from polygrade import find_config, load_grader

TestSubmission = load_grader(find_config(__file__)).build()
