"""A submission with a mix of mistakes, to show how each is graded."""
import random

import numpy as np


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    # Mistake: population variance. Earns partial credit (see config.yaml).
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def standardize(xs):
    # Correct. Graded with the solution's variance, so the mistake above
    # isn't penalized a second time.
    return (np.array(xs) - mean(xs)) / np.sqrt(variance(xs))


def running_total(xs):
    totals = []
    total = 0
    for x in xs:
        total += x
        totals.append(total)
    # Slip: deleted the provided `return totals`. Fixed automatically by the
    # ensure_return fix in tests/test_stats.py.


def count_outliers(xs, threshold=2.0):
    # Correct answer, but calls standardize once per element: half credit.
    return sum(1 for i in range(len(xs)) if abs(standardize(xs)[i]) > threshold)


def bootstrap_mean(xs, n_samples):
    # Mistake: uses the random module instead of np.random.choice.
    return float(np.mean(random.choices(xs, k=n_samples)))
