"""
This file provides boolean satisfiability logic for the rules of an instance.
"""
import typing
import abc

from .feature import FeatureLabel

VariableLabel = typing.Union[str, int]


class SatNode(abc.ABC):
    @abc.abstractmethod
    def NEG(self):
        pass

    @abc.abstractmethod
    def to_cnf(self):
        pass

    @abc.abstractmethod
    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        pass

    @abc.abstractmethod
    def all_variables(self) -> typing.Iterable[VariableLabel]:
        pass

    @abc.abstractmethod
    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        pass

    @abc.abstractmethod
    def to_json_data(self):
        pass

    @staticmethod
    def from_json_data(json_data):
        return _sat_node_from_json(json_data)


class VAR(SatNode):
    __aux_index = 0

    def __init__(
        self, var_name: VariableLabel, negated: bool = False, auxiliary: bool = False
    ):
        self.var_name = var_name
        self.negated = negated
        self.auxiliary = auxiliary

    @staticmethod
    def create_auxiliary():
        VAR.__aux_index += 1
        return VAR(f"__AUX[{VAR.__aux_index}]", False, True)

    def __repr__(self):
        if self.negated:
            return f"NVAR[{self.var_name}]"
        return f"VAR[{self.var_name}]"

    def __eq__(self, other):
        return (
            isinstance(other, VAR)
            and self.var_name == other.var_name
            and self.negated == other.negated
            and self.auxiliary == other.auxiliary
        )

    def NEG(self):
        return VAR(self.var_name, not self.negated)

    def to_cnf(self):
        return self

    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        if self.var_name in direct:
            return VAR(direct[self.var_name], self.negated, self.auxiliary)
        if self.var_name in inverse:
            return VAR(inverse[self.var_name], not self.negated, self.auxiliary)
        return self

    def all_variables(self) -> typing.Iterable[VariableLabel]:
        yield self.var_name

    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        return assignment[self.var_name] == (not self.negated)

    def to_json_data(self):
        return {
            "type": "VAR",
            "name": self.var_name,
            "negated": self.negated,
            "auxiliary": self.auxiliary,
        }


def NOT(x: SatNode):
    return x.NEG()


class AND(SatNode):
    def __init__(self, *elements: SatNode):
        if len(elements) <= 1:
            raise ValueError("Conjunction should have at least two elements.")
        self.elements = []
        for element in elements:
            if isinstance(element, AND):
                self.elements += element.elements
            else:
                self.elements.append(element)

    def __repr__(self):
        return f"AND({', '.join(str(e) for e in self.elements)})"

    def NEG(self):
        return OR(*[element.NEG() for element in self.elements])

    def to_cnf(self):
        return AND(*[e.to_cnf() for e in self.elements])

    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        return AND(*[e.substitute(direct, inverse) for e in self.elements])

    def all_variables(self) -> typing.Iterable[VariableLabel]:
        already_yielded = []
        for element in self.elements:
            for var in element.all_variables():
                if var not in already_yielded:
                    already_yielded.append(var)
                    yield var

    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        return all(element.evaluate(assignment) for element in self.elements)

    def to_json_data(self):
        return {"type": "AND", "elements": [e.to_json_data() for e in self.elements]}


class OR(SatNode):
    def __init__(self, *elements: SatNode):
        if len(elements) <= 1:
            raise ValueError("Disjunction should have at least two elements.")
        self.elements = []
        for element in elements:
            if isinstance(element, OR):
                self.elements += element.elements
            else:
                self.elements.append(element)

    def __repr__(self):
        return f"OR({', '.join(str(e) for e in self.elements)})"

    def NEG(self):
        return AND(*[element.NEG() for element in self.elements])

    def to_cnf(self):
        # Make sure we have only AND-clauses or VARs as children.
        elements = OR(*[e.to_cnf() for e in self.elements]).elements

        # if only VARs -> is a CNF-clause
        if all(isinstance(e, VAR) for e in elements):
            return self

        aux_vars = []
        clauses = []
        for and_clause in elements:
            aux = VAR.create_auxiliary()
            aux_vars.append(aux)
            if isinstance(and_clause, AND):
                for or_clause in and_clause.elements:
                    assert isinstance(or_clause, VAR) or isinstance(or_clause, OR)
                    clauses.append(OR(aux.NEG(), or_clause))
            else:
                assert isinstance(and_clause, VAR)
                clauses.append(OR(aux.NEG(), and_clause))
        clauses.append(OR(*aux_vars))
        return AND(*clauses)

    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        return OR(*[e.substitute(direct, inverse) for e in self.elements])

    def all_variables(self) -> typing.Iterable[VariableLabel]:
        already_yielded = []
        for element in self.elements:
            for var in element.all_variables():
                if var not in already_yielded:
                    already_yielded.append(var)
                    yield var

    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        return any(element.evaluate(assignment) for element in self.elements)

    def to_json_data(self):
        return {"type": "OR", "elements": [e.to_json_data() for e in self.elements]}


class IMPL(SatNode):
    def __init__(self, condition: SatNode, implication: SatNode):
        assert condition and implication
        self.condition = condition
        self.implication = implication

    def __repr__(self):
        return f"{self.condition}=>{self.implication}"

    def NEG(self):
        return AND(self.condition, self.implication.NEG())

    def to_cnf(self):
        return OR(self.condition.NEG(), self.implication).to_cnf()

    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        return IMPL(
            self.condition.substitute(direct, inverse),
            self.implication.substitute(direct, inverse),
        )

    def all_variables(self) -> typing.Iterable[VariableLabel]:
        already_yielded = []
        for var in self.condition.all_variables():
            if var not in already_yielded:
                yield var
        for var in self.implication.all_variables():
            if var not in already_yielded:
                already_yielded.append(var)
                yield var

    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        return (not self.condition.evaluate(assignment)) or self.implication.evaluate(
            assignment
        )

    def to_json_data(self):
        return {
            "type": "IMPL",
            "condition": self.condition.to_json_data(),
            "implication": self.implication.to_json_data(),
        }


class EQ(SatNode):
    def __init__(self, a: SatNode, b: SatNode):
        self.a = a
        self.b = b
        assert a and b

    def is_variable_equivalence(self) -> bool:
        return isinstance(self.a, VAR) and isinstance(self.b, VAR)

    def __repr__(self):
        return f"{self.a}=={self.b}"

    def NEG(self):
        return EQ(self.a, self.b.NEG())

    def to_cnf(self):
        return OR(AND(self.a, self.b), AND(self.a.NEG(), self.b.NEG())).to_cnf()

    def substitute(
        self,
        direct: typing.Dict[VariableLabel, VariableLabel],
        inverse: typing.Dict[VariableLabel, VariableLabel],
    ):
        return EQ(
            self.a.substitute(direct, inverse), self.b.substitute(direct, inverse)
        )

    def all_variables(self) -> typing.Iterable[VariableLabel]:
        already_yielded = []
        for var in self.a.all_variables():
            if var not in already_yielded:
                already_yielded.append(var)
                yield var
        for var in self.b.all_variables():
            if var not in already_yielded:
                already_yielded.append(var)
                yield var

    def evaluate(self, assignment: typing.Dict[FeatureLabel, bool]):
        return self.a.evaluate(assignment) == self.b.evaluate(assignment)

    def to_json_data(self):
        return {"type": "EQ", "a": self.a.to_json_data(), "b": self.b.to_json_data()}


def _sat_node_from_json(json_data):
    if "type" in json_data:
        t = json_data["type"]
        if t == "VAR":
            return VAR(json_data["name"], json_data["negated"], json_data["auxiliary"])
        if t == "AND":
            return AND(*[_sat_node_from_json(j) for j in json_data["elements"]])
        if t == "OR":
            return OR(*[_sat_node_from_json(j) for j in json_data["elements"]])
        if t == "IMPL":
            return IMPL(
                _sat_node_from_json(json_data["condition"]),
                _sat_node_from_json(json_data["implication"]),
            )
        if t == "EQ":
            return EQ(
                _sat_node_from_json(json_data["a"]), _sat_node_from_json(json_data["b"])
            )
    raise ValueError("Invalid value/json data for SatNode!")
