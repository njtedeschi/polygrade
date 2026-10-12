"""A correct submission uploaded inside a folder, split across two files."""
import numpy as np

from helpers import total


def mean(xs):
    return total(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return total([(x - m) ** 2 for x in xs]) / (len(xs) - 1)


def standardize(xs):
    return (np.asarray(xs, dtype=float) - mean(xs)) / variance(xs) ** 0.5


def running_total(xs):
    totals = []
    for x in xs:
        totals.append(x + (totals[-1] if totals else 0))
    return totals


def count_outliers(xs, threshold=2.0):
    return int((abs(standardize(xs)) > threshold).sum())


def bootstrap_mean(xs, n_samples):
    return float(np.random.choice(xs, n_samples).mean())
