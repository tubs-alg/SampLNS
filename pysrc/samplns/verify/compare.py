"""
Code for comparing two samples. This can be used to make sure they cover the same
interactions. If you know that one of the samples is feasible, you can use it
to make sure that another sample is feasible, too.
"""
import itertools
import typing

from ..instances import Instance


def _minimize_to_concrete_features(
    sample: typing.List[typing.Dict[str, bool]], concrete_features: typing.Set[str]
) -> typing.List[typing.Dict[str, bool]]:
    return [
        {k: v for k, v in conf.items() if k in concrete_features} for conf in sample
    ]


def _unique_interaction(f1, f1_val, f2, f2_val):
    if f1 < f2:
        return (f1, f1_val, f2, f2_val)
    else:
        return (f2, f2_val, f1, f1_val)


def have_equal_coverage(
    instance: Instance,
    sample_a: typing.List[typing.Dict[str, bool]],
    sample_b: typing.List[typing.Dict[str, bool]],
) -> bool:
    """
    Check if two samples have the exact same coverage. This is a good technique for
    verifying correctness.
    """
    concrete_features = set(instance.features)
    sample_a = _minimize_to_concrete_features(sample_a, concrete_features)
    interactions_a = {
        _unique_interaction(f0[0], f0[1], f1[0], f1[1])
        for conf in sample_a
        for f0, f1 in itertools.combinations(conf.items(), 2)
    }
    sample_b = _minimize_to_concrete_features(sample_b, concrete_features)
    interactions_b = {
        _unique_interaction(f0[0], f0[1], f1[0], f1[1])
        for conf in sample_b
        for f0, f1 in itertools.combinations(conf.items(), 2)
    }
    return interactions_a == interactions_b
