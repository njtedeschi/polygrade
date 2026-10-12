"""Reference solution for the example statistics assignment."""
import numpy as np


def mean(xs):
    return sum(xs) / len(xs)


def variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def standardize(xs):
    return (np.array(xs) - mean(xs)) / np.sqrt(variance(xs))


def running_total(xs):
    totals = []
    for x in xs:
        totals.append(x + (totals[-1] if totals else 0))
    return totals


def count_outliers(xs, threshold=2.0):
    return int(np.sum(np.abs(standardize(xs)) > threshold))


def bootstrap_mean(xs, n_samples):
    return float(np.mean(np.random.choice(xs, n_samples)))


# Alternative, incorrect implementations that earn partial credit (see config.yaml)

def population_variance(xs):
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)
