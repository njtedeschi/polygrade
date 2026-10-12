"""A submission that renamed one of the starter code's functions."""
import numpy as np


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def z_scores(xs):  # should be called standardize
    return (np.array(xs) - mean(xs)) / np.sqrt(variance(xs))


def running_total(xs):
    return list(np.cumsum(xs))


def count_outliers(xs, threshold=2.0):
    return int(np.sum(np.abs(z_scores(xs)) > threshold))


def bootstrap_mean(xs, n_samples):
    return float(np.mean(np.random.choice(xs, n_samples)))
