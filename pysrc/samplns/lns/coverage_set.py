"""
Some code for keeping track on the interactions to cover.
"""

import logging
import typing

Configuration = typing.Dict[int, bool]
Sample = typing.List[Configuration]
Literal = typing.Tuple[int, bool]

# Native code for significantly speeding up the computation of the coverage set.
from ._coverage_set import CoverageSet as _CoverageSet
from ._coverage_set import CoveredTuples as _CoveredTuples

_logger = logging.getLogger("SampLNS")


class CoverageSet:
    """
    The coverage set is for computing which interactions are covered.
    """

    def __init__(self, sample: Sample, n_concrete: int, logger=_logger):
        """
        sample: A feasible sample that can be used to deduce the feasible interactions
        n_concrete: The number of concrete features.
        """
        logger.info("Computing feasible tuples...")
        _sample = [[conf[f] for f in range(n_concrete)] for conf in sample]
        logger.info("Converted sample to list representation.")
        self.n_concrete = n_concrete
        self._feasible_tuples = _CoveredTuples(_sample, n_concrete)
        self._covered_tuples = _CoverageSet(self._feasible_tuples)
        logger.info(
            "Instance has %d feasible tuples.", self._feasible_tuples.num_covered_tuples
        )

    def cover(self, configuration: Configuration):
        """
        Cover all interactions with a configuration
        """
        self._covered_tuples.add_configuration(
            [configuration[f] for f in range(self.n_concrete)]
        )

    def missing_tuples(self):
        """
        List of not covered interactions.
        """
        return self._covered_tuples.get_missing_tuples()

    def num_missing(self) -> int:
        """
        Number of not covered interactions.
        """
        return int(self._covered_tuples.num_missing_tuples())

    def __len__(self):
        return int(self._feasible_tuples.num_covered_tuples)

    def clear(self):
        self._covered_tuples.clear()
