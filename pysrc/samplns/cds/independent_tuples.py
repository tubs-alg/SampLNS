import itertools
import math
import random

from .base import CdsAlgorithm, Samples, Tuples


class IndependentTuples(CdsAlgorithm):
    """
    A simple greedy algorithm for computing an independent set of tuples.
    Each of these tuples has to be in a different configuration, making it not only
    a reasonably good lower bound but also a great symmetry breaker.
    An important part of this greedy algorithm is the sorting of the tuples, as
    the solutions are terrible otherwise. The sorting is based on expected difficulty,
    approximated by how often a tuple is covered in the initial solution.
    """

    def __init__(self, n_concrete: int, initial_solution: Samples):
        """
        You need to provide the number of concrete features and a solution for a
        preprocessed IndexInstance.
        ```
        index_instance = Preprocessor().preprocess(instance)
        # converting a solution
        features = list(set([f for s in solution for f in s]))
        list_of_dicts = [{f: f in sample for f in features} for sample in solution]
        converted_solution =  [
            self.index_instance.to_mapped_universe(configuration)
            for configuration in list_of_dicts
        ]
        ```
        """
        self.coverage_count = {}
        self._non_unique = set()
        self._features = set(range(n_concrete))
        self._nodes = [(f, True) for f in self._features] + [
            (f, False) for f in self._features
        ]
        self.recompute(initial_solution)
        """
        If the best solution has significantly changed, it may be beneficial to
        recompute the number of occurrences used for the sorting. This may result
        in better independent tuples, of which already a small improvement can save
        us quite some time.
        """
        self.coverage_count = {}
        for v, w in itertools.combinations(self._nodes, 2):
            if v > w:
                v, w = w, v
            assert v < w
            cov = sum(
                (conf[v[0]] == v[1] and conf[w[0]] == w[1]) for conf in initial_solution
            )
            if cov > 0:
                self.coverage_count[(v, w)] = cov

    def _is_feasible(self, v, w):
        if v == w:
            return True
        if v > w:
            v, w = w, v
            assert v < w
        return (v, w) in self.coverage_count

    def compute_independent_set(
        self, tuples: Tuples, timelimit: float = math.inf, ub=math.inf
    ) -> Tuples:
        """
        Compute an independent set from the given tuples.
        (Time limit not supported)
        """

        if timelimit != math.inf:
            msg = "This implementation does currently not support time limits!"
            raise NotImplementedError(
                msg
            )

        if tuples is None:
            tuples = self.get_feasible_tuples()
        sorted_tuples = list(tuples)
        random.shuffle(sorted_tuples)
        sorted_tuples.sort(key=lambda t: self.coverage_count[t])
        independent_tuples = []

        def is_independent(v, w):
            # Approximation only based on transaction graph.
            return not any(
                self._is_feasible(v, v_)
                and self._is_feasible(v, w_)
                and self._is_feasible(w, v_)
                and self._is_feasible(w, w_)
                for v_, w_ in independent_tuples
            )

        for v, w in sorted_tuples:
            if is_independent(v, w):
                independent_tuples.append((v, w))
        return independent_tuples

    def get_feasible_tuples(self) -> Tuples:
        """
        Returns all feasible tuples.
        """
        return self.coverage_count.keys()
