"""
The neighborhood is the essential part of an LNS. This file defines the interface
for the LNS and some examples.
"""

import abc
import logging
import random
import typing

from ..preprocessor import IndexInstance
from .coverage_set import CoverageSet

_logger = logging.getLogger("SampLNS")


class Neighborhood:
    """
    Neighborhood for the LNS. Defines the fixed and relaxed part. Our implementation
    also requires an initial solution, so it also contains an initial solution
    for the relaxed part.
    """

    def __init__(
        self,
        fixed_samples: typing.List[typing.Dict[int, bool]],
        missing_tuples: typing.List[
            typing.Tuple[typing.Tuple[int, bool], typing.Tuple[int, bool]]
        ],
        initial_solution: typing.List[typing.Dict[int, bool]],
    ):
        self.fixed_samples = fixed_samples  # the fixed part of the solution
        self.missing_tuples = missing_tuples  # the free part of the solution
        # an initial solution to cover the free part
        self.initial_solution = initial_solution

    def full_solution(
        self,
        relaxed_solution: typing.Optional[typing.List[typing.Dict[int, bool]]] = None,
    ) -> typing.List[typing.Dict[int, bool]]:
        """
        Returns the full solution the underlies this neighborhood.
        """
        if relaxed_solution:
            return self.fixed_samples + relaxed_solution
        return self.fixed_samples + self.initial_solution

    def global_ub(self):
        """
        Returns the upper bound of the full solution.
        """
        return len(self.fixed_samples) + len(self.initial_solution)


class NeighborhoodSelector(abc.ABC):
    """
    Inherit this class to build you own neighborhood.
    """

    @abc.abstractmethod
    def setup(
        self,
        instance: IndexInstance,
        initial_solution: typing.List[typing.Dict[int, bool]],
    ):
        """
        Called at the beginning. Use as a second constructor.
        """

    @abc.abstractmethod
    def add_solution(self, solution: typing.List[typing.Dict[int, bool]]):
        """
        Used by the solver to notify you about new solutions.
        """

    @abc.abstractmethod
    def next(self) -> Neighborhood:
        """
        Return the next neighborhood.
        """

    @abc.abstractmethod
    def feedback(
        self,
        on_neighborhood: Neighborhood,  # the neighborhood to give feedback on
        ub: int,  # the upper bound computed
        lb: int,  # the lower bound computed
        time_utilization: float,  # >=0.99 slow. ~0 very fast.
    ):
        """
        Allows the solver to give feedback on the neighborhood. Should always be
        the previous.
        """


class RandomNeighborhood(NeighborhoodSelector):
    """
    A simple neighborhood that just returns a neighborhood of specific size.
    The size will increase or decrease by a specified factor
    """

    def __init__(
        self,
        max_free_tuples: int = 250,
        incr_factor=1.25,
        decr_factor=0.75,
        logger: logging.Logger = _logger,
    ):
        self.log = logger
        self.instance = None
        self.coverage_set = None
        self.n = max_free_tuples
        self.best_solution = None
        self.incr_factor = incr_factor
        self.decr_factor = decr_factor

    def setup(
        self,
        instance: IndexInstance,
        initial_solution: typing.List[typing.Dict[int, bool]],
    ):
        self.log.info("Setting up random neighborhood selector.")
        self.instance = instance
        self.best_solution = initial_solution
        self.coverage_set = CoverageSet(initial_solution, instance.n_concrete, logger=self.log)
        self.n_interactions = len(self.coverage_set)
        self.log.info("Neighborhood selector is ready.")

    def add_solution(self, solution: typing.List[typing.Dict[int, bool]]):
        if self.best_solution is None or len(solution) < len(self.best_solution):
            assert all(self.instance.is_fully_defined(conf) for conf in solution)
            self.best_solution = solution

    def next(self) -> Neighborhood:
        initial_solution = list(self.best_solution)
        fixed_samples = []
        self.coverage_set.clear()

        while True:
            # print("num_missing", coverage_set.num_missing())
            if self.coverage_set.num_missing() < self.n:
                break
            to_fix = random.sample(initial_solution, 1)[0]
            initial_solution.remove(to_fix)
            self.coverage_set.cover(to_fix)
            fixed_samples.append(to_fix)
        free_tuples = list(self.coverage_set.missing_tuples())
        return Neighborhood(fixed_samples, free_tuples, initial_solution)

    def feedback(
        self, on_neighborhood: Neighborhood, ub: int, lb: int, time_utilization: float
    ):
        if lb == ub:  # computed to optimality
            self.increase()
        if ub != 0 and lb / ub <= 0.9:
            self.decrease()

    def decrease(self):
        self.n *= self.decr_factor
        self.log.info("Decreasing neighborhood size to %d tuples.", self.n)

    def increase(self):
        self.n *= self.incr_factor
        self.log.info("Increasing neighborhood size to %d tuples.", self.n)
