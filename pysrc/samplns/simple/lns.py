import logging
import typing

from ..cds import CdsLns
from ..instances import Instance
from ..lns._coverage_set import CoveredTuples
from ..lns.lns import InternalSolution, LnsObserver, ModularLns
from ..lns.neighborhood import NeighborhoodSelector, RandomNeighborhood
from ..preprocessor import Preprocessor
from ..verify import have_equal_coverage

ExternalSolution = typing.List[
    typing.Dict[str, bool]
]  # Solution for the original instance

_logger = logging.getLogger("SampLNS")


class SampLns:
    """
    A simple interface to the LNS algorithm. It takes care of the preprocessing
    and converting the solutions back to the original universe.
    """

    def __init__(
        self,
        instance: Instance,
        initial_solution: ExternalSolution,
        neighborhood_selector: typing.Optional[NeighborhoodSelector] = None,
        on_new_solution: typing.Optional[
            typing.Callable[[ExternalSolution], None]
        ] = None,
        observer=LnsObserver(),
        logger: logging.Logger = _logger,
        cds_iteration_time_limit: float = 60.0,
    ):
        """
        :param instance: The instance we want to find a sample for.
        :param initial_solution: A (good) initial solution we want to improve.
        :param neighborhood_selector: The heart of the LNS algorithm, its neighborhood.
        :param on_new_solution: A callback that notifies about every new solution.
        :param observer: An observer that is notified about the progress.
        :param logger: A logger.
        """
        self.log = logger
        self.original_instance = instance
        if neighborhood_selector is None:
            neighborhood_selector = RandomNeighborhood(logger=logger)
        self.index_instance = Preprocessor(logger=logger).preprocess(instance)
        self.initial_solution = initial_solution
        solution = self._import_solution(initial_solution)
        self.neighborhood_selector = neighborhood_selector
        neighborhood_selector.setup(self.index_instance, solution)

        on_new_solution_ = None
        if on_new_solution is not None:
            # callback needs exporting solution to original format
            def on_new_solution_(sol):
                return on_new_solution(self._export_solution(sol))

        cds_algorithm = CdsLns(
            self.index_instance,
            solution,
            logger=self.log.getChild("CDS"),
            iteration_timelimit=cds_iteration_time_limit,
        )

        self._lns = ModularLns(
            instance=self.index_instance,
            initial_solution=solution,
            neighborhood_selector=neighborhood_selector,
            cds_algorithm=cds_algorithm,
            on_new_solution=on_new_solution_,
            observer=observer,
            logger=self.log,
        )

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

    def get_best_solution(self, verify=False, fast_verify=False) -> ExternalSolution:
        """
        Returns the best solution.
        """
        if fast_verify:
            initial_solution = self._import_solution(self.initial_solution)
            final_solution = self._lns.get_best_solution()
            n = self.index_instance.n_concrete
            assert CoveredTuples(
                [[conf[f] for f in range(n)] for conf in initial_solution], n
            ) == CoveredTuples(
                [[conf[f] for f in range(n)] for conf in final_solution], n
            )
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
