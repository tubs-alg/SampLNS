"""
In this file we build the upper bound model using CP-SAT.
"""
import typing

import ortools.sat.python.cp_model as cp_model

from ..instances import (
    OR,
    VAR,
    AltFeature,
    AndFeature,
    CompositeFeature,
    ConcreteFeature,
    FeatureLiteral,
    FeatureNode,
    OrFeature,
    SatNode,
)
from ..preprocessor import IndexInstance


class BaseModelCreator:
    """
    This is a simple factory for creating the base model of the universe.
    Because the features are indexed, simply the model and a list of variables is
    returned.
    """

    def __init__(self, use_linear_parent_dependency: bool = False):
        """
        use_linear_parent_dependency seems to be minimally slower (54s vs 51s in one experiment)
        """
        self.use_linear_parent_dependency = use_linear_parent_dependency

    def _get_struct_var(
        self, variables: typing.List[cp_model.IntVar], structure_node: FeatureNode
    ) -> cp_model.IntVar:
        assert isinstance(structure_node.feature_literal.var_name, int), "IndexInstance"
        if structure_node.feature_literal.negated:
            return variables[structure_node.feature_literal.var_name].Not()
        else:
            return variables[structure_node.feature_literal.var_name]

    def _add_and_structure_constraint(
        self,
        structure: AndFeature,
        model: cp_model.CpModel,
        variables: typing.List[cp_model.IntVar],
    ):
        assert all(
            x.feature_literal == structure.feature_literal or not x.mandatory
            for x in structure.elements
        ), "Preprocessor should have substituted these."
        # if a child is active, the And-Feature has to be active too
        literals = [
            self._get_struct_var(variables, element)
            for element in structure.elements
            if not element.mandatory
        ]
        if not literals:
            return  # nothing to do
        if self.use_linear_parent_dependency:
            and_feature = self._get_struct_var(variables, structure)
            model.Add(sum(literals) <= len(literals) * and_feature)
        else:
            # forall elements: element active => or-feature active
            and_feature = self._get_struct_var(variables, structure)
            for lit in literals:
                # model.Add(lit <= and_feature) would be minimally slower
                model.AddBoolOr([lit.Not(), and_feature])

    def _add_alt_structure_constraint(
        self,
        structure: AltFeature,
        model: cp_model.CpModel,
        variables: typing.List[cp_model.IntVar],
    ):
        literals = [
            self._get_struct_var(variables, element) for element in structure.elements
        ]
        assert len(literals) > 1, "Should otherwise have been removed by preprocessor."
        alt_feature = self._get_struct_var(variables, structure)
        model.Add(sum(literals) == alt_feature)

    def _add_or_structure_constraint(
        self,
        structure: OrFeature,
        model: cp_model.CpModel,
        variables: typing.List[cp_model.IntVar],
    ):
        # Either a child is active, or the Or-feature is inactive
        literals = [
            self._get_struct_var(variables, element) for element in structure.elements
        ]
        model.AddBoolOr([*literals, self._get_struct_var(variables, structure).Not()])
        # if a child is active, the Or-Feature has to be active too
        if self.use_linear_parent_dependency:
            model.Add(sum(literals) <= self._get_struct_var(variables, structure))
        else:
            or_feature = self._get_struct_var(variables, structure)
            for lit in literals:
                model.AddBoolOr([lit.Not(), or_feature])

    def _add_structure_constraints(
        self,
        structure: FeatureNode,
        model: cp_model.CpModel,
        variables: typing.List[cp_model.IntVar],
    ):
        if isinstance(structure, ConcreteFeature):
            return  # Nothing needs to be added here
        assert isinstance(structure, CompositeFeature)
        if isinstance(structure, AndFeature):
            self._add_and_structure_constraint(structure, model, variables)
        elif isinstance(structure, OrFeature):
            self._add_or_structure_constraint(structure, model, variables)
        elif isinstance(structure, AltFeature):
            self._add_alt_structure_constraint(structure, model, variables)
        else:
            msg = f"Unexpected node encountered: {structure}!"
            raise ValueError(msg)
        for element in structure.elements:
            self._add_structure_constraints(element, model, variables)

    def _add_rule_constraints(
        self,
        rules: typing.List[SatNode],
        model: cp_model.CpModel,
        variables: typing.List[cp_model.IntVar],
    ):
        for rule in rules:
            if isinstance(rule, OR):
                if not all(isinstance(lit, VAR) for lit in rule.elements):
                    msg = "Rule is not in CNF!"
                    raise ValueError(msg)
                elements: typing.List[VAR] = rule.elements
                literals = [
                    variables[lit.var_name]
                    if not lit.negated
                    else variables[lit.var_name].Not()
                    for lit in elements
                ]
                model.AddBoolOr(literals)
            elif isinstance(rule, VAR):
                # todo: should be detected and forced by preprocessor
                model.Add(variables[rule.var_name] == (1 if not rule.negated else 0))
            else:
                msg = "Rule is not in CNF!"
                raise ValueError(msg)

    def create(
        self, instance: IndexInstance, model=None
    ) -> typing.Tuple[cp_model.CpModel, typing.List[cp_model.IntVar]]:
        model = cp_model.CpModel() if model is None else model
        variables = [model.NewBoolVar(f"F{i}") for i in range(instance.n_all)]
        if instance.structure is not None:
            self._add_structure_constraints(instance.structure, model, variables)
        self._add_rule_constraints(instance.rules, model, variables)
        # root node
        # if instance.structure.mandatory:
        if instance.structure is not None:
            model.Add(
                self._get_struct_var(variables, instance.structure) == 1
            )  # enforce root node
        return model, variables


class BaseSolver:
    """
    Just a simple wrapper to solve the base model with assumptions and different
    objectives.
    """

    def __init__(self, instance: IndexInstance):
        model, variables = BaseModelCreator().create(instance)
        self.instance = instance
        self.model = model
        self.all_vars = variables  # all vars
        self.cf_vars = variables[: self.instance.n_concrete]  # concrete feature vars
        self.solver = cp_model.CpSolver()

    def get_var(self, f: FeatureLiteral):
        i = int(f.var_name)
        return self.all_vars[i].Not() if f.negated else self.all_vars[i]

    def minimize(self, obj: cp_model.LinearExpr):
        self.model.Minimize(obj)

    def maximize(self, obj: cp_model.LinearExpr):
        self.model.Maximize(obj)

    def assume(self, i: int, val: bool):
        self.model.AddAssumption(self.all_vars[i] if val else self.all_vars[i].Not())

    def clear_assumptions(self):
        self.model.ClearAssumptions()

    def solve(self, cb: cp_model.CpSolverSolutionCallback):
        return self.solver.Solve(self.model, cb)

    def get_solution(self):
        return [self.solver.Value(x) for x in self.cf_vars]

    def get_obj_val(self):
        return round(self.solver.ObjectiveValue())
