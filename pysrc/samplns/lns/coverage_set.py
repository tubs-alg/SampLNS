"""
Some code for keeping track on the interactions to cover.
"""

import itertools
import typing

Configuration = typing.Dict[int, bool]
Sample = typing.List[Configuration]
Literal = typing.Tuple[int, bool]


class CoverageSet:
    """
    The coverage set is for computing which interactions are covered.
    """

    def __init__(self, sample: Sample, n_concrete):
        """
        sample: A feasible sample that can be used to deduce the feasible interactions
        n_concrete: The number of concrete features.
        """
        self._features = {i for i in range(n_concrete)}
        self._nodes = [(f, True) for f in self._features] + [
            (f, False) for f in self._features
        ]  # nodes in the interaction graph (caveat: contains isolated vertices)
        self._feasible_tuples = set(self.get_covered_tuples(sample))
        self._missing = set(self._feasible_tuples)

    def get_covered_tuples(self, sample: Sample):
        """
        Returns the interactions covered by the sample
        """
        for v, w in itertools.combinations(self._nodes, 2):
            if any(
                (sample[v[0]] == v[1] and sample[w[0]] == w[1]) for sample in sample
            ):
                if v > w:
                    v, w = w, v
                yield v, w

    def cover(self, configuration: Configuration):
        """
        Cover all interactions with a configuration
        """
        nodes = [(f, configuration[f]) for f in self._features]
        for v, w in itertools.combinations(nodes, 2):
            if v > w:
                v, w = w, v
            self._missing.discard((v, w))
            # assert (v,w) in self._feasible_tuples

    def missing_tuples(self):
        """
        List of not covered interactions.
        """
        return self._missing

    def num_missing(self):
        """
        Number of not covered interactions.
        """
        return len(self._missing)

    def __len__(self):
        return len(self._feasible_tuples)

    def is_feasible(self, v: Literal, w: Literal) -> bool:
        if v > w:
            v, w = w, v
        return (v, w) in self._feasible_tuples

    def is_covered(self, v: Literal, w: Literal) -> bool:
        if v > w:
            v, w = w, v
        return (v, w) not in self._missing

    def clear(self):
        self._missing = set(self._feasible_tuples)
