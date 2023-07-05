"""
The LNS Algorithm
"""
import logging
import typing

from ..cds import CdsAlgorithm
from ..preprocessor import IndexInstance
from ..utils.timer import Timer
from .model import TupleIndex, VectorizedEdgeModel
from .neighborhood import Neighborhood, NeighborhoodSelector

InternalSolution = typing.List[typing.Dict[int, bool]]  # Solution for working instance

_logger = logging.getLogger("SampLNS")


class LnsObserver:
    def report_new_lb(self, lb: int):
        pass

    def report_new_solution(self, solution: InternalSolution):
        pass

    def report_neighborhood_optimization(self, neighborhood: Neighborhood):
        pass

    def report_iteration_begin(self, iteration: int):
        pass

    def report_iteration_end(
        self,
        iteration: int,
        runtime: float,
        lb: int,
        solution: InternalSolution,
        events,
    ):
        pass


class ModularLns:
    """
    The Large Neighborhood Search algorithm.
    - It converts and simplifies the problem internally.
    - There shouldn't be much need to adapt this algorithm. All important parameters are
        in the neighborhood selection.
    """

    def __init__(
        self,
        instance: IndexInstance,
        initial_solution: InternalSolution,
        neighborhood_selector: NeighborhoodSelector,
        cds_algorithm: CdsAlgorithm,
        on_new_solution: typing.Optional[
            typing.Callable[[InternalSolution], None]
        ] = None,
        observer=LnsObserver(),
        logger: logging.Logger = _logger,
    ):
        """
        instance: The instance we want to find a sample for.
        initial_solution: A (good) initial solution we want to improve.
        neighborhood_selector: The heart of the LNS algorithm, its neighborhood.
        use_hints: Use CP-SAT hints using the previous solution.
        on_new_solution: A callback that notifies about every new solution.
        """
        self.log = logger
        self.index_instance = instance
        self.neighborhood_selector = neighborhood_selector
        solution = initial_solution
        self.neighborhood_selector.setup(self.index_instance, solution)
        self._cds = cds_algorithm
        self.lb = 0
        self._solution_pool = [solution]
        self.on_new_solution = on_new_solution
        self.observer = observer
        self._times_failed_to_build_model = 0

    def add_lower_bound(self, lb: int) -> None:
        """
        Add a lower bound.
        """
        if lb > self.lb:
            self.log.info("Increased lower bound to %d (from %d).", lb, self.lb)
            self.lb = lb
            self.observer.report_new_lb(lb)

    def get_best_solution(self) -> InternalSolution:
        """
        Returns the best solution.
        """
        best = min(self._solution_pool, key=len)
        return best

    def get_solution_pool(self) -> typing.List[InternalSolution]:
        """
        Return a list of solutions found during the optimization process.
        """
        return list(self._solution_pool)

    def _add_new_solution(self, solution: InternalSolution):
        self._solution_pool.append(solution)
        self.neighborhood_selector.add_solution(solution)
        if self.on_new_solution is not None:
            self.on_new_solution(solution)
        self.observer.report_new_solution(solution)

    def _build_neighborhood_model(
        self, neighborhood: Neighborhood, independent: typing.List, timer: Timer
    ):
        """
        Build the CP-SAT model for optimizing the neighborhood.
        The independent interactions are an important speed-up.
        """
        k = len(neighborhood.initial_solution)
        self.log.info("Building model for neighborhood of size %d.", k)
        model = VectorizedEdgeModel(self.index_instance, k, timer, logger=self.log)
        self.log.info("Using %d tuples to break symmetries.", len(independent))
        model.break_symmetries(
            TupleIndex(t[0][0], t[0][1], t[1][0], t[1][1]) for t in independent
        )
        timer.check()
        model.set_initial_solution(neighborhood.initial_solution)
        for i, t in enumerate(neighborhood.missing_tuples):
            if i % 1000 == 0:
                timer.check()
            model.enforce_tuple(TupleIndex(t[0][0], t[0][1], t[1][0], t[1][1]))
        self.log.info("Model built.")
        return model

    def optimize_neighborhood(
        self,
        neighborhood: Neighborhood,
        timelimit: float,
        timer: typing.Optional[Timer] = None,
    ) -> typing.Tuple[int, int, bool]:
        """
        A single iteration of the LNS to optimize one neighborhood.
        Return lower and upper bound. Additional flag indicates whether it
        was not skipped, e.g., because there was no optimization necessary.
        """
        if timer is None:
            timer = Timer(timelimit)  # create an empty dummy timer
        self.observer.report_neighborhood_optimization(neighborhood)
        k = len(neighborhood.initial_solution)

        # Trivial cases
        if not neighborhood.missing_tuples:
            self.log.info("No optimization necessary: no missing tuples.")
            return 0, 0, False
        if k <= 1:
            return k, k, False
        independent = list(
            self._cds.compute_independent_set(neighborhood.missing_tuples)
        )
        neighborhood.missing_tuples = [
            (min(t), max(t)) for t in neighborhood.missing_tuples
        ]
        independent = [(min(t), max(t)) for t in independent]
        timer.lap("local_cds_computed")
        # assert all(
        #    t in neighborhood.missing_tuples for t in independent
        # ), "All independent tuples should be missing tuples."
        if len(independent) == k:
            self.log.info(
                "No optimization necessary: lower bound fits available solution."
            )
            return k, k, False

        # Optimize neighborhood
        lb = 1
        try:
            self._times_failed_to_build_model += 1
            model = self._build_neighborhood_model(neighborhood, independent, timer)
            self._times_failed_to_build_model -= 1
            timer.lap("model_built")
            model.optimize(max(1.0, timer.remaining()))
            timer.lap("model_optimized")

            # update solution
            self.add_lower_bound(model.get_lb())
            if model.is_feasible():  # can a new solution be constructed?
                samples = list(model.get_solution())
                assert all(
                    self.index_instance.is_fully_defined(conf) for conf in samples
                )
                solution = neighborhood.fixed_samples + samples
                self._add_new_solution(solution)
                return model.get_lb(), len(samples), True
            lb = model.get_lb()
        except TimeoutError:
            self.log.info("Timeout in iteration.")
        return lb, k, True

    def optimize(
        self,
        iterations: int = 15,
        iteration_timelimit: float = 60.0,
        timelimit: float = 3600.0,
    ) -> bool:
        """
        Optimize the problem for a number of iterations, where each iteration
        has a timelimit. You can use it multiple times.

        Returns, whether the solution was optimal in the end.
        """
        self.log.info(
            "Beginning optimization with the following parameters: iterations=%d, iteration_timelimit=%f, timelimit=%f",
            iterations,
            iteration_timelimit,
            timelimit,
        )
        opt_timer = Timer(timelimit)
        with self._cds(iteration_timelimit=iteration_timelimit):
            self.add_lower_bound(self._cds.get_lb())  # Set initial lower bound
            opt_timer.lap("initial_lb_computed")
            for i in range(iterations):
                # Check time
                if opt_timer.is_out_of_time():
                    self.log.info("Optimization reached time limit.")
                    break
                self.log.info("Beginning iteration %d.", i)
                self.observer.report_iteration_begin(i)
                iter_timer = Timer(min(iteration_timelimit, opt_timer.remaining()))
                # Optimize
                nbrhd = self.neighborhood_selector.next()
                self.log.info(
                    "Selected neighborhood, removing %d configurations, leaving %d tuples uncovered.",
                    len(nbrhd.initial_solution),
                    len(nbrhd.missing_tuples),
                )
                iter_timer.lap("neighborhood_selected")
                lb, ub, not_skipped = self.optimize_neighborhood(
                    nbrhd, iter_timer.remaining(), iter_timer
                )
                self.log.info("Optimized neighborhood, lb=%d, ub=%d.", lb, ub)
                iter_timer.lap("neighborhood_optimized")

                # lb and ub are regarding neighborhood, not global.
                # Give the CDS algorithm a chance to update the lower bound.
                self.add_lower_bound(self._cds.get_lb())
                iter_timer.lap("global_lb_iteration_finished")
                self.observer.report_iteration_end(
                    i,
                    iter_timer.time(),
                    self.lb,
                    self.get_best_solution(),
                    iter_timer.get_laps(),
                )
                # Check optimality
                complete_and_optimal = lb == ub and not nbrhd.fixed_samples
                solution_matches_lb = self.lb == len(self.get_best_solution())
                if complete_and_optimal or solution_matches_lb:
                    return True  # optimal solution
                # Tune size for next iteration
                tu = iter_timer.time() / iteration_timelimit
                if not_skipped or self._times_failed_to_build_model == 0:
                    self.neighborhood_selector.feedback(
                        nbrhd, lb=lb, ub=ub, time_utilization=tu
                    )
            opt_timer.lap("iterations_ended")
        return False
