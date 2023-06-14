"""
The LNS Algorithm
"""
import typing

from ..cds import CdsAlgorithm
from ..preprocessor import IndexInstance
from ..utils.timer import Timer
from .model import TupleIndex, VectorizedEdgeModel
from .neighborhood import Neighborhood, NeighborhoodSelector

InternalSolution = typing.List[typing.Dict[int, bool]]  # Solution for working instance


class LnsLogger:
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
        print(
            f"Iteration {iteration} finished in {runtime}s. LB={lb}, UB={len(solution)}. Events: {events}."
        )
        pass

    def __call__(self, *args, **kwargs):
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
        logger=LnsLogger(),
    ):
        """
        instance: The instance we want to find a sample for.
        initial_solution: A (good) initial solution we want to improve.
        neighborhood_selector: The heart of the LNS algorithm, its neighborhood.
        use_hints: Use CP-SAT hints using the previous solution.
        on_new_solution: A callback that notifies about every new solution.
        """
        self.index_instance = instance
        self.neighborhood_selector = neighborhood_selector
        solution = initial_solution
        self.neighborhood_selector.setup(self.index_instance, solution)
        self._cds = cds_algorithm
        self.lb = 0
        self._solution_pool = [solution]
        self.on_new_solution = on_new_solution
        self.logger = logger

    def add_lower_bound(self, lb: int) -> None:
        """
        Add a lower bound.
        """
        if lb > self.lb:
            self.lb = lb
            self.logger.report_new_lb(lb)

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
        self.logger.report_new_solution(solution)

    def _build_neighborhood_model(
        self, neighborhood: Neighborhood, independent: typing.List, timer: Timer
    ):
        """
        Build the CP-SAT model for optimizing the neighborhood.
        The independent interactions are an important speed-up.
        """
        k = len(neighborhood.initial_solution)
        model = VectorizedEdgeModel(self.index_instance, k, timer)
        self.logger(f"Using {len(independent)} tuples to break symmetry!")
        model.break_symmetries(
            TupleIndex(t[0][0], t[0][1], t[1][0], t[1][1]) for t in independent
        )
        timer.check()
        model.set_initial_solution(neighborhood.initial_solution)
        for i, t in enumerate(neighborhood.missing_tuples):
            if i % 1000 == 0:
                timer.check()
            model.enforce_tuple(TupleIndex(t[0][0], t[0][1], t[1][0], t[1][1]))
        return model

    def optimize_neighborhood(
        self,
        neighborhood: Neighborhood,
        timelimit: float,
        timer: typing.Optional[Timer] = None,
    ) -> typing.Tuple[int, int]:
        """
        A single iteration of the LNS to optimize one neighborhood.
        Return lower and upper bound.
        """
        if timer is None:
            timer = Timer(timelimit)  # create an empty dummy timer
        self.logger.report_neighborhood_optimization(neighborhood)
        k = len(neighborhood.initial_solution)

        # Trivial cases
        if not neighborhood.missing_tuples:
            self.logger("No missing tuples!")
            return 0, 0
        if k <= 1:
            return k, k
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
            self.logger("Optimal by independent tuples.")
            return k, k

        # Optimize neighborhood
        lb = 1
        try:
            model = self._build_neighborhood_model(neighborhood, independent, timer)
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
                return model.get_lb(), len(samples)
            lb = model.get_lb()
        except TimeoutError:
            self.logger("Timeout in iteration")
        return lb, k

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
        self.logger(
            f"Beginning optimization with iterations={iterations}, iteration_timelimit={iteration_timelimit}, timelimit={timelimit}"
        )
        opt_timer = Timer(timelimit)
        with self._cds(iteration_timelimit=iteration_timelimit):
            self.add_lower_bound(self._cds.get_lb())  # Set initial lower bound
            opt_timer.lap("initial_lb_computed")
            for i in range(iterations):
                # Check time
                if opt_timer.is_out_of_time():
                    self.logger("Global timeout")
                    break
                self.logger.report_iteration_begin(i)
                iter_timer = Timer(min(iteration_timelimit, opt_timer.remaining()))
                # Optimize
                nbrhd = self.neighborhood_selector.next()
                iter_timer.lap("neighborhood_selected")
                lb, ub = self.optimize_neighborhood(
                    nbrhd, iter_timer.remaining(), iter_timer
                )
                iter_timer.lap("neighborhood_optimized")

                # lb and ub are regarding neighborhood, not global.
                # Give the CDS algorithm a chance to update the lower bound.
                self.add_lower_bound(self._cds.get_lb())
                iter_timer.lap("global_lb_iteration_finished")
                self.logger.report_iteration_end(
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
                self.neighborhood_selector.feedback(
                    nbrhd, lb=lb, ub=ub, time_utilization=tu
                )
            opt_timer.lap("iterations_ended")
        return False
