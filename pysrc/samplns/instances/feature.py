"""
feature: This module provides the elements for the feature structure.
"""

import abc
import logging
import typing

FeatureLabel = typing.Union[str, int]


class FeatureLiteral:
    """
    An identifier for features. They are natural choices for the literals in the
    mathematical model. The negation option is for optimization: If 'a <-> not b', we
    may replace all occurrences of 'b' by 'not a'. The original model does not have
    this option.
    """

    def __init__(self, var_name: FeatureLabel, negated: bool = False):
        self.var_name = var_name
        self.negated = negated

    def __neg__(self):
        return FeatureLiteral(self.var_name, not self.negated)

    def __eq__(self, other):
        return (
                isinstance(other, FeatureLiteral)
                and self.var_name == other.var_name
                and self.negated == other.negated
        )

    def __hash__(self):
        return hash((self.var_name, self.negated))

    def sub(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ):
        if self.var_name in direct:
            return FeatureLiteral(direct[self.var_name], self.negated)
        if self.var_name in inverse:
            return FeatureLiteral(inverse[self.var_name], not self.negated)
        return self

    def __repr__(self):
        return f"-{self.var_name}" if self.negated else str(self.var_name)

    def is_satisfied(self, assignment: typing.Dict[FeatureLabel, bool]):
        return assignment[self.var_name] != self.negated

    def to_json_data(self):
        return {"name": self.var_name, "negated": self.negated}

    @staticmethod
    def from_json_data(json_data):
        return FeatureLiteral(json_data["name"], json_data["negated"])


class FeatureNode(abc.ABC):
    """
    A feature node represent either an abstract or concrete feature. The root project
    is also a feature. Every feature has a name and may be declared mandatory.
    There are two changes to the original model:
    1. A feature may appear multiple times. It may even be that a node has the same feature multiple times as a child.
    2. Features do not just have names, but a FeatureLiteral. This can be negated as a result of an 'x= not y' rule optimization.
    """

    __counter = 0

    def __init__(
            self, feature_literal: FeatureLiteral, mandatory: bool = False
    ) -> None:
        self.feature_literal = feature_literal
        self.mandatory = mandatory
        self.__id = FeatureNode.__counter
        FeatureNode.__counter += 1

    def __hash__(self):
        return self.__id

    def __eq__(self, o):
        return isinstance(o, FeatureNode) and self.__id == o.__id

    def _add_base_info(self, json_data):
        json_data["feature_literal"] = self.feature_literal.to_json_data()
        json_data["mandatory"] = self.mandatory

    @abc.abstractmethod
    def concrete_features(self) -> typing.Iterable[FeatureLabel]:
        """
        Returns all concrete feature labels used in the tree.
        This does not differ between labels used in positive
        or negative literals.
        """

    @abc.abstractmethod
    def substitute(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ) -> "FeatureNode":
        """
        Return a feature tree that substituted all entries in
        `direct` with the value, and all entries in `inverse`
        with the negated value.
        """

    @abc.abstractmethod
    def all_features(self) -> typing.Iterable[FeatureLabel]:
        """
        Return all feature labels used in the tree.
        """

    @abc.abstractmethod
    def is_feasible(self, assignment: typing.Dict[FeatureLabel, bool]) -> bool:
        pass

    def is_active(self, assignment: typing.Dict[FeatureLabel, bool]) -> bool:
        """
        Checks if this feature tree is active in the corresponding assignment.
        """
        return self.feature_literal.is_satisfied(assignment)

    @abc.abstractmethod
    def __len__(self) -> int:
        """
        Number of nodes in this tree.
        """

    @abc.abstractmethod
    def all_concrete_literals(self) -> typing.Iterable[FeatureLiteral]:
        """
        Returns the literals of all concrete features used, i.e., that
        are used in some leaf.
        """

    @abc.abstractmethod
    def to_json_data(self):
        pass

    @staticmethod
    def from_json_data(json_data):
        if not json_data:
            return None
        return _feature_node_from_json(json_data)


class ConcreteFeature(FeatureNode):
    """
    A concrete feature represents an elementary feature that has an actual implementation
    and is not just a composition of other features. Thus, it does not have any
    sub-features.
    """

    def __init__(self, feature_literal: FeatureLiteral, mandatory: bool) -> None:
        super().__init__(feature_literal, mandatory)

    def concrete_features(self):
        yield self.feature_literal.var_name

    def substitute(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ) -> FeatureNode:
        x = self.feature_literal
        if x.var_name in direct:
            subst = self.feature_literal.sub(direct, inverse)
            return ConcreteFeature(subst, self.mandatory)
        if x.var_name in inverse:
            subst = self.feature_literal.sub(direct, inverse)
            return ConcreteFeature(subst, self.mandatory)
        return self

    def all_features(self) -> typing.Iterable[FeatureLabel]:
        yield self.feature_literal.var_name

    def all_concrete_literals(self) -> typing.Iterable[FeatureLiteral]:
        return (self.feature_literal,)

    def __repr__(self):
        m = "!" if self.mandatory else ""
        return f"F{m}[{self.feature_literal!s}]"

    def is_feasible(self, assignment: typing.Dict[FeatureLabel, bool]):
        return True

    def __len__(self):
        return 1

    def to_json_data(self):
        data = {"type": "CONCRETE"}
        self._add_base_info(data)
        return data


class CompositeFeature(FeatureNode, abc.ABC):
    def __init__(
            self,
            feature_literal: FeatureLiteral,
            elements: typing.List[FeatureNode],
            mandatory: bool,
    ) -> None:
        super().__init__(feature_literal, mandatory)
        self.elements = elements

    def mandatory_elements(self):
        return [e for e in self.elements if e.mandatory]

    def optional_elements(self):
        return [e for e in self.elements if not e.mandatory]

    def concrete_features(self):
        for element in self.elements:
            yield from element.concrete_features()

    def all_features(self) -> typing.Iterable[FeatureLabel]:
        already_yielded = []
        already_yielded.append(self.feature_literal)
        yield self.feature_literal.var_name
        for element in self.elements:
            for label in element.all_features():
                if label not in already_yielded:
                    yield label

    def all_concrete_literals(self) -> typing.Iterable[FeatureLiteral]:
        for element in self.elements:
            yield from element.all_concrete_literals()

    def __len__(self):
        return sum(len(e) for e in self.elements) + 1

    def _add_base_info(self, json_data):
        super()._add_base_info(json_data)
        json_data["elements"] = [e.to_json_data() for e in self.elements]


class AndFeature(CompositeFeature):
    """
    The 'and'-feature is actually just a composition of features and no logical 'and'.
    It can have optional and mandatory features. The mandatory features have to be
    active if and only if the 'and'-feature is active. The optional features can, but
    don't have to be, active whenever the 'and'-feature is active. They cannot be
    active without the 'and'-feature.
    """

    def __init__(
            self,
            feature_literal: FeatureLiteral,
            elements: typing.List[FeatureNode],
            mandatory: bool,
            logger: logging.Logger,
    ) -> None:
        super().__init__(feature_literal, elements, mandatory)
        self.logger = logger

    def substitute(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ) -> FeatureNode:
        elements = [e.substitute(direct, inverse) for e in self.elements]
        x = self.feature_literal.sub(direct, inverse)
        return AndFeature(x, elements, mandatory=self.mandatory, logger=self.logger)

    def is_feasible(self, assignment: typing.Dict[FeatureLabel, bool]) -> bool:
        if not all(el.is_feasible(assignment) for el in self.elements):
            return False
        if self.is_active(assignment):
            all_mandatory_elements_are_active = all(
                mand_el.is_active(assignment)
                for mand_el in self.elements
                if mand_el.mandatory
            )
            if not all_mandatory_elements_are_active:
                self.logger.warning("Not all mandatory elements of AND are active.")
            return all_mandatory_elements_are_active
        else:
            no_element_active = all(
                not el.is_active(assignment) for el in self.elements
            )
            if not no_element_active:
                self.logger.warning("AND not active, but elements of it are")
            return no_element_active

    def __repr__(self):
        m = "!" if self.mandatory else ""
        return f"AND{m}[{self.feature_literal}]({', '.join(str(e) for e in self.elements)})"

    def to_json_data(self):
        data = {"type": "AND"}
        self._add_base_info(data)
        return data


class OrFeature(CompositeFeature):
    """
    The 'or'-feature requires at least one of its sub-features to be active.
    The sub-features can only be active if the 'or'-feature is active.
    """

    def __init__(
            self,
            feature_literal: FeatureLiteral,
            elements: typing.List[FeatureNode],
            mandatory: bool,
            logger: logging.Logger,
    ) -> None:
        super().__init__(feature_literal, elements, mandatory)
        self.logger = logger
        if self.mandatory_elements():
            self.logger.warning("Making mandatory elements of OR non-mandatory.")
            for f in self.elements:
                f.mandatory = False
        assert not self.mandatory_elements()

    def substitute(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ) -> FeatureNode:
        elements = [e.substitute(direct, inverse) for e in self.elements]
        x = self.feature_literal.sub(direct, inverse)
        return OrFeature(x, elements, self.mandatory, logger=self.logger)

    def __repr__(self):
        m = "!" if self.mandatory else ""
        return (
            f"OR{m}[{self.feature_literal}]({', '.join(str(e) for e in self.elements)})"
        )

    def is_feasible(self, assignment: typing.Dict[FeatureLabel, bool]) -> bool:
        if not all(el.is_feasible(assignment) for el in self.elements):
            return False
        if self.is_active(assignment):
            satisfied = any(el.is_active(assignment) for el in self.elements)
            if not satisfied:
                self.logger.warning("OR active, but no element of it.")
            return satisfied
        else:
            no_element_active = all(
                not el.is_active(assignment) for el in self.elements
            )
            if not no_element_active:
                self.logger.warning("OR not active, but elements of it are")
            return no_element_active

    def to_json_data(self):
        data = {"type": "OR"}
        self._add_base_info(data)
        return data


class AltFeature(CompositeFeature):
    """
    The 'alt'-feature requires exactly one of its sub-features to be active.
    The sub-features can only be active if the 'alt'-feature is active.
    """

    def __init__(
            self,
            feature_literal: FeatureLiteral,
            elements: typing.List[FeatureNode],
            mandatory: bool,
            logger: logging.Logger,
    ) -> None:
        super().__init__(feature_literal, elements, mandatory)
        self.logger = logger
        if self.mandatory_elements():
            self.logger.warning("Making mandatory elements of ALT non-mandatory.")
            for f in self.elements:
                f.mandatory = False
        assert not self.mandatory_elements()

    def substitute(
            self,
            direct: typing.Dict[FeatureLabel, FeatureLabel],
            inverse: typing.Dict[FeatureLabel, FeatureLabel],
    ) -> FeatureNode:
        elements = [e.substitute(direct, inverse) for e in self.elements]
        x = self.feature_literal.sub(direct, inverse)
        return AltFeature(x, elements, self.mandatory, logger=self.logger)

    def __repr__(self):
        m = "!" if self.mandatory else ""
        return f"ALT{m}[{self.feature_literal}]({', '.join(str(e) for e in self.elements)})"

    def is_feasible(self, assignment: typing.Dict[FeatureLabel, bool]) -> bool:
        if not all(el.is_feasible(assignment) for el in self.elements):
            return False
        if self.is_active(assignment):
            n_active = sum(1 if el.is_active(assignment) else 0 for el in self.elements)
            one_active = n_active == 1
            if not one_active:
                self.logger.warning(f"ALT active and {n_active} elements.")
            return one_active
        else:
            no_element_active = all(
                not el.is_active(assignment) for el in self.elements
            )
            if not no_element_active:
                self.logger.warning("ALT not active, but elements of it are")
            return no_element_active

    def to_json_data(self):
        data = {"type": "ALT"}
        self._add_base_info(data)
        return data


def _feature_node_from_json(json_data):
    if "type" in json_data:
        t = json_data["type"]
        literal = FeatureLiteral.from_json_data(json_data["feature_literal"])
        mandatory = json_data["mandatory"]
        if t == "CONCRETE":
            return ConcreteFeature(literal, mandatory)
        conss = {"ALT": AltFeature, "OR": OrFeature, "AND": AndFeature}
        if t in conss:
            cons = conss[t]
            elements = [_feature_node_from_json(j) for j in json_data["elements"]]
            return cons(feature_literal=literal, mandatory=mandatory, elements=elements)
    msg = "Invalid JSON data for FeatureNode!"
    raise ValueError(msg)
