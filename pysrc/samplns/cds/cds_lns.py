from .base import CdsAlgorithm, Tuples, Samples
from ..preprocessor import IndexInstance
from ._cds_bindings import TransactionGraph, LnsCds, AsyncLnsCds, GreedyCds
import typing
from time import sleep


class CdsLns(CdsAlgorithm):
    def __init__(
        self, instance: IndexInstance, initial_samples: Samples, verbose=True, log=print
    ) -> None:
        self.instance = instance
        self._verbose = verbose
        self._iteration_timelimit = 60.0
        self._logger = log
        self.log(
            f"Building transaction graph for {instance.instance_name} "
            f"with {instance.n_concrete} concrete features!"
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

        self.log(f"All valid configurations were added to the transaction graph.")

        self.solver = AsyncLnsCds(self.graph)
        self.greedy_solver = GreedyCds(self.graph, self.cpp_sample)
        self.initial_cds_cpp = self.greedy_solver.optimize(list())

    def __enter__(self):
        self.solver.start(self.initial_cds_cpp, self._iteration_timelimit)
        self.log(
            "Async Solver started with iteration timelimit", self._iteration_timelimit
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.solver:
            self.solver.stop()
            self.log("Async Solver stopped")

    def __call__(self, **kwargs):
        if "iteration_timelimit" in kwargs:
            self._iteration_timelimit = kwargs.get("iteration_timelimit")
        return self

    def stop(self):
        self.solver.stop()

    def log(self, *args):
        if self._verbose:
            self._logger("[CdsLns]", *args)

    def compute_independent_set(self, edges: typing.Optional[Tuples]) -> Tuples:
        # Filter by the edges passed as an argument
        sol = self.__cpp_to_py_format(self.solver.get_best_solution())
        if edges is not None:
            edges = self.__py_to_cpp_format(edges)

            greedy_sol = self.greedy_solver.optimize(edges)

            for (p, q) in greedy_sol:
                assert self.graph.has_edge(p, q)
            for (p, q) in edges:
                assert self.graph.has_edge(p, q)
                
            sol = LnsCds(self.graph, subgraph=edges, use_heur=False).optimize(
                initial_solution=greedy_sol,
                max_iterations=5,
                time_limit=6.0,
                verbose=False,
            )
            assert all(
                (p, q) in edges or (q, p) in edges for (p, q) in sol
            ), "The solution contains edges that are not within the specified subgraph edges!"
            sol = self.__cpp_to_py_format(sol)
            self.log(
                f"The greedy solver found {len(greedy_sol)} tuples, the LNS found {len(sol)} tuples!"
            )

        return sol

    @staticmethod
    def __py_to_cpp_format(sol):
        return [
            (i + 1 if a else -(i + 1), j + 1 if b else -(j + 1))
            for ((i, a), (j, b)) in sol
        ]

    @staticmethod
    def __cpp_to_py_format(sol):
        return [((abs(i) - 1, i > 0), (abs(j) - 1, j > 0)) for (i, j) in sol]
