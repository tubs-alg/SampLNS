import logging
import math
import typing

from ..preprocessor import IndexInstance
from ..utils import Timer
from ._cds_bindings import (
    AsyncLnsCds,
    FeatureTuple,
    GreedyCds,
    LnsCds,
    TransactionGraph,
)
from .base import CdsAlgorithm, Samples, Tuples

_logger = logging.getLogger("SampLNS.CdsLns")


class CdsLns(CdsAlgorithm):
    def __init__(
        self,
        instance: IndexInstance,
        initial_samples: Samples,
        logger: logging.Logger = _logger,
        iteration_timelimit: float = 60.0,
    ) -> None:
        self.instance = instance
        self._iteration_timelimit = iteration_timelimit
        self._logger = logger
        self._logger.info(
            "Building transaction graph for %s with %s concrete features!",
            instance.instance_name,
            instance.n_concrete,
        )

        self.graph = TransactionGraph(instance.n_concrete)
        self.cpp_sample = [
            [
                (i + 1 if b else -(i + 1))
                for (i, b) in configuration.items()
                if i < instance.n_concrete
            ]
            for configuration in initial_samples
        ]
        for config in self.cpp_sample:
            self.graph.add_valid_configuration(config)

        self._logger.info(
            "All valid configurations were added to the transaction graph."
        )

        self.solver = AsyncLnsCds(self.graph)
        self.greedy_solver = GreedyCds(self.graph, self.cpp_sample)
        self.initial_cds_cpp = self.greedy_solver.optimize([])

    def __enter__(self):
        self.solver.start(self.initial_cds_cpp, self._iteration_timelimit)
        self._logger.info(
            "Async Solver started with iteration timelimit %d",
            self._iteration_timelimit,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.solver:
            self.solver.stop()
            self._logger.info("Async Solver stopped")

    def __call__(self, **kwargs):
        if "iteration_timelimit" in kwargs:
            self._iteration_timelimit = kwargs.get("iteration_timelimit")
        return self

    def stop(self):
        self.solver.stop()

    def compute_independent_set(
        self, edges: typing.Optional[Tuples], timelimit: float = math.inf, ub=math.inf
    ) -> Tuples:
        # Stop time
        timer = Timer(timelimit)

        # Filter by the edges passed as an argument
        sol = self.__cpp_to_py_format(self.solver.get_best_solution())
        if edges is not None:
            edges = self.__py_to_cpp_format(edges)

            greedy_sol = self.greedy_solver.optimize(edges)

            for p, q in greedy_sol:
                assert self.graph.has_edge(p, q)
            for p, q in edges:
                assert self.graph.has_edge(p, q)

            sol = greedy_sol

            # While time left: call the lns solver
            lns = LnsCds(self.graph, subgraph=edges, use_heur=False)
            iter_without_improvement = 0
            while timer:
                assert (
                    len(sol) <= ub
                ), f"The provided upper bound {ub} is infeasible! A larger lower bound {len(sol)} was found!"

                # Break early if known upper bound is reached
                if len(sol) == ub:
                    self._logger.info(
                        "[Symmetry Breaking]: Optimal solution found (%d)!", len(sol)
                    )
                    break

                new_sol = lns.optimize(
                    initial_solution=sol,
                    max_iterations=1,
                    time_limit=timer.remaining(),
                    verbose=False,
                )

                # check for improvement. break early if no improvement was made for multiple iterations.
                if len(new_sol) > len(sol):
                    sol = new_sol
                    iter_without_improvement = 0
                    self._logger.info(
                        "[Symmetry Breaking]: (%fs left) Independent tuple set with size %d was found!",
                        timer.remaining(),
                        len(sol),
                    )
                else:
                    iter_without_improvement += 1
                    if iter_without_improvement >= 10:
                        break

            assert all(
                e in edges for e in sol
            ), "The solution contains edges that are not within the specified subgraph edges!"
            sol = self.__cpp_to_py_format(sol)
            self._logger.info(
                "[Symmetry Breaking]: The greedy solver found %d tuples, the LNS found %d tuples!",
                len(greedy_sol),
                len(sol),
            )

        return sol

    @staticmethod
    def __py_to_cpp_format(sol):
        return [
            FeatureTuple(i + 1 if a else -(i + 1), j + 1 if b else -(j + 1))
            for ((i, a), (j, b)) in sol
        ]

    @staticmethod
    def __cpp_to_py_format(sol):
        return [((abs(i) - 1, i > 0), (abs(j) - 1, j > 0)) for (i, j) in sol]
