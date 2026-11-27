"""Per-process timings for the Export Cote diagnostic, outside the PDF."""
from contextlib import contextmanager
from functools import wraps
from time import perf_counter

_samples = None


def start():
    global _samples
    _samples = {}


@contextmanager
def stage(name):
    samples = _samples
    if samples is None:
        yield
        return
    begin = perf_counter()
    try:
        yield
    finally:
        sample = samples.setdefault(name, [0, 0.0])
        sample[0] += 1
        sample[1] += perf_counter() - begin


def measured(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if _samples is None:
                return function(*args, **kwargs)
            with stage(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def observe(name, seconds):
    if _samples is not None:
        sample = _samples.setdefault(name, [0, 0.0])
        sample[0] += 1
        sample[1] += seconds


def snapshot():
    return {name: {"calls": sample[0], "seconds": round(sample[1], 6)}
            for name, sample in (_samples or {}).items()}


def stop():
    global _samples
    result = snapshot()
    _samples = None
    return result
