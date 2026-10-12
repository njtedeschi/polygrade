"""Starter code for the example statistics assignment.

Fill in each function. Do not rename functions or change their parameters.
"""
import numpy as np


def mean(xs):
    """The arithmetic mean of the numbers in xs."""
    raise NotImplementedError


def variance(xs):
    """The sample variance of xs (dividing by n - 1). Use mean."""
    raise NotImplementedError


def standardize(xs):
    """A NumPy array of the z-scores of xs. Use mean and variance."""
    raise NotImplementedError


def running_total(xs):
    """A list whose i-th element is the sum of xs[0], ..., xs[i]."""
    totals = []
    # Your code here
    return totals


def count_outliers(xs, threshold=2.0):
    """How many elements of xs have a z-score above threshold in absolute value.

    Call standardize only once.
    """
    raise NotImplementedError


def bootstrap_mean(xs, n_samples):
    """The mean of n_samples values drawn from xs with replacement using np.random.choice."""
    raise NotImplementedError
