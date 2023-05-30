import typing

from samplns.verify import have_equal_coverage

from ..cds import CdsLns
from ..lns.lns import ModularLns, InternalSolution, LnsLogger
from ..lns.neighborhood import NeighborhoodSelector
from ..instances import Instance
from ..preprocessor import Preprocessor

ExternalSolution = typing.List[
    typing.Dict[str, bool]
]  # Solution for the original instance


class ConvertingLns:
    def __init__(
        self,
        instance: Instance,
        initial_solution: ExternalSolution,
        neighborhood_selector: NeighborhoodSelector,
        on_new_solution: typing.Optional[
            typing.Callable[[ExternalSolution], None]
        ] = None,
        logger=LnsLogger(),
    ):
        """
        instance: The instance we want to find a sample for.
        initial_solution: A (good) initial solution we want to improve.
        neighborhood_selector: The heart of the LNS algorithm, its neighborhood.
        use_hints: Use CP-SAT hints using the previous solution.
        on_new_solution: A callback that notifies about every new solution.
        """
        self.original_instance = instance
        self.index_instance = Preprocessor().preprocess(instance)
        self.initial_solution = initial_solution
        solution = self._import_solution(initial_solution)
        neighborhood_selector = neighborhood_selector
        neighborhood_selector.setup(self.index_instance, solution)

        if on_new_solution is not None:
            # callback needs exporting solution to original format
            on_new_solution = lambda sol: on_new_solution(self._export_solution(sol))

        cds_algorithm = CdsLns(self.index_instance, solution, log=logger)

        self._lns = ModularLns(
            instance=self.index_instance,
            initial_solution=solution,
            neighborhood_selector=neighborhood_selector,
            cds_algorithm=cds_algorithm,
            on_new_solution=on_new_solution,
            logger=logger,
        )

        # cds_algorithm.register_ub_alg(self._lns)

    def _import_solution(self, solution: ExternalSolution) -> InternalSolution:
        """
        Converts a solution to the internal format.
        """
        assert all(self.original_instance.is_fully_defined(conf) for conf in solution)
        return [
            self.index_instance.to_mapped_universe(configuration)
            for configuration in solution
        ]

    def _export_solution(self, solution: InternalSolution) -> ExternalSolution:
        """
        Converts a solution to the original format.
        """
        solution = [
            self.index_instance.to_original_universe(configuration)
            for configuration in solution
        ]
        assert all(self.original_instance.is_fully_defined(conf) for conf in solution)
        return solution

    def add_lower_bound(self, lb: int) -> None:
        """
        Add a lower bound.
        """
        self._lns.add_lower_bound(lb)

    def get_lower_bound(self) -> int:
        return self._lns.lb

    def get_best_solution(self, verify=False) -> ExternalSolution:
        """
        Returns the best solution.
        """
        sol = self._export_solution(self._lns.get_best_solution())
        if verify:
            assert have_equal_coverage(
                self.original_instance, self.initial_solution, sol
            )
        return sol

    def get_solution_pool(self) -> typing.List[ExternalSolution]:
        """
        Return a list of solutions found during the optimization process.
        """
        return [
            self._export_solution(solution)
            for solution in self._lns.get_solution_pool()
        ]

    def optimize(
        self,
        iterations: int = 15,
        iteration_timelimit: float = 60.0,
        timelimit: float = 3600.0,
    ):
        """
        Optimize the problem for a number of iterations, where each iteration
        has a timelimit. You can use it multiple times.
        """
        self._lns.optimize(
            iterations=iterations,
            iteration_timelimit=iteration_timelimit,
            timelimit=timelimit,
        )
