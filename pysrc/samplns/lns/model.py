"""
The CP-SAT models for the optimization, as required by LNS.
"""
import logging
import typing

from .base_model import BaseModelCreator
from ..preprocessor import IndexInstance

import ortools.sat.python.cp_model as cp_model
import multiprocessing

from ..utils import Timer


class TupleIndex:
    def __init__(
        self, feature_i: int, i_positive: bool, feature_j: int, j_positive: bool
    ):
        assert feature_i != feature_j
        if feature_i < feature_j:
            self.i = feature_i
            self.i_pos = i_positive
            self.j = feature_j
            self.j_pos = j_positive
        else:
            self.i = feature_j
            self.i_pos = j_positive
            self.j = feature_i
            self.j_pos = i_positive

    def to_tuple(self):
        return (self.i, self.i_pos, self.j, self.j_pos)

    def __repr__(self):
        return f"TupleIndex[{self.i, self.i_pos, self.j, self.j_pos}]"

    def __eq__(self, other):
        return isinstance(other, TupleIndex) and self.to_tuple() == other.to_tuple()

    def __hash__(self):
        return hash(self.to_tuple())


class _SubModel:
    """
    A submodel for the vectorized edge model. It contains one feasible configuration
    if activated.
    """

    bmc = BaseModelCreator()

    def __init__(self, instance: IndexInstance, model: cp_model.CpModel, timer: Timer):
        timer.check()
        self.model = model
        self.variables = self.bmc.create(instance, model)[1]
        # A container with all the tuple variables.
        self.tuple_variables = dict()
        # A variable to indicated, that this configuration is activated.
        self.activated = model.NewBoolVar(f"ACT[{id(self)}]")
        timer.check()

    def get_configuration(self, solver):
        return {i: bool(solver.Value(x)) for i, x in enumerate(self.variables)}

    def set_hint(self, solution: typing.Dict[int, bool]):
        """
        Set a hint for this submodel/configuration.
        """
        self.model.AddHint(self.activated, True)
        for i, x in solution.items():
            self.model.AddHint(self.variables[i], x)

    def get_tuple_variable(self, edge_index: TupleIndex):
        """
        Creates and returns a variable that indicates if this tuple is covered.
        """
        if edge_index in self.tuple_variables:
            return self.tuple_variables[edge_index]
        # create new variable
        edge_var = self.model.NewBoolVar(str(edge_index))
        self.tuple_variables[edge_index] = edge_var

        # corresponding feature variables
        i_var = self.variables[edge_index.i]
        if not edge_index.i_pos:
            i_var = i_var.Not()
        j_var = self.variables[edge_index.j]
        if not edge_index.j_pos:
            j_var = j_var.Not()

        # Enforce consistency
        self.model.AddBoolOr([edge_var.Not(), i_var])
        self.model.AddBoolOr([edge_var.Not(), j_var])
        self.model.Add(edge_var <= self.activated)

        return edge_var


class VectorizedEdgeModel:
    """
    A model that tries to find up to k samples to cover specific edges.
    The edges to be covered can be added iteratively.
    """

    def __init__(self, instance: IndexInstance, k: int, timer: Timer, verbose=True):
        self.model = cp_model.CpModel()
        self.submodels = [_SubModel(instance, self.model, timer) for _ in range(k)]
        self.model.Minimize(sum(submodel.activated for submodel in self.submodels))
        self.solver = cp_model.CpSolver()
        self.solver.parameters.num_search_workers = (
            multiprocessing.cpu_count() - 1
        )  # all but one thread
        print(
            f"VectorizedEdgeModel uses {self.solver.parameters.num_search_workers} for search!"
        )
        if verbose:
            self.solver.parameters.log_search_progress = True
            self.solver.log_callback = print  # (str)->None
        self.status = None
        self._symmetry_breaking_tuples = dict()

    def break_symmetries(self, independent_tuples: typing.Iterable[TupleIndex]):
        independent_tuples = list(independent_tuples)
        for i, t in enumerate(independent_tuples):
            self.model.Add(self.submodels[i].get_tuple_variable(t) == 1)
            self._symmetry_breaking_tuples[t] = i
        for i, submodel in enumerate(self.submodels):
            if i > len(independent_tuples):
                self.model.Add(submodel.activated <= self.submodels[i - 1].activated)
                self.model.Add(
                    sum(submodel.variables) <= sum(self.submodels[i - 1].variables)
                )

    def is_feasible(self) -> bool:
        """
        Returns true if there is a feasible assignment available.
        """
        return self.status == cp_model.OPTIMAL or self.status == cp_model.FEASIBLE

    def set_initial_solution(self, solution: typing.List[typing.Dict[int, bool]]):
        """
        Set an initial solution, potentially speeding up the optimization process.
        """
        solution = list(solution)
        for t, i in self._symmetry_breaking_tuples.items():
            t: TupleIndex
            sol = None
            for sol_ in solution:
                if sol_.get(t.i, False) == t.i_pos and sol_.get(t.j, False) == t.j_pos:
                    sol = sol_
                    break
            assert sol is not None

            self.submodels[i].set_hint(sol)
            solution.remove(sol)
        solution.sort(key=lambda d: sum(d.values()), reverse=True)

        submods = self.submodels[len(self._symmetry_breaking_tuples) :]
        assert len(solution) <= len(submods)
        if len(solution) < len(submods):
            logging.getLogger("VecorizedEdgeModel").warning(
                "Unnecessary large k. Initial solution is smaller."
            )
        for conf, submod in zip(solution, submods):
            submod.set_hint(conf)

    def get_lb(self) -> int:
        """
        Returns the current lower bound. The trivial lower bound is always 0.
        """
        if self.status is None:
            return 0
        return self.solver.BestObjectiveBound()

    def optimize(self, timelimit: float = 600) -> bool:
        """
        Try to solve the model. The timelimit is in seconds.
        Returns true if a feasible solution has been found.
        """
        self.solver.parameters.max_time_in_seconds = timelimit
        self.status = self.solver.Solve(self.model)
        return self.is_feasible()

    def get_solution(self) -> typing.Iterable[typing.Dict[int, bool]]:
        """
        Return the best solution. Requires a successful optimization before.
        """
        if not self.is_feasible():
            raise ValueError("Cannot access solution without solving the model.")
        for submodel in self.submodels:
            if self.solver.Value(submodel.activated):
                yield submodel.get_configuration(self.solver)

    def enforce_tuple(self, edge_index: TupleIndex):
        """
        Enforce a tuple to be covered by one of the configurations in the solution.
        """
        vars = [submodel.get_tuple_variable(edge_index) for submodel in self.submodels]
        self.model.AddBoolOr(vars)
