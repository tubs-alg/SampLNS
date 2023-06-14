"""
Substituting variables that always have to be equally (or inverse) assigned.
The easiest such case is the equal-rule that is frequent in many models.
Another are mandatory features of mandatory features that always have to be
select at the same time.
"""
import typing

from ..instances import EQ, VAR, AndFeature, CompositeFeature, FeatureNode, Instance
from .equivalence import EquivalenceClasses
from .universe_mapping import UniverseMapping


def substitute_equivalent(
    instance: Instance, mapping: typing.Optional[UniverseMapping]
) -> typing.Tuple[Instance, UniverseMapping]:
    """
    Substitute variables of which we know that they are equivalent.
    To get the original labels back, you can use the mapping.
    """
    instance, mapping = EqualityOptimizer().transform(instance, mapping)
    return instance, mapping


class EqualityOptimizer:
    def _filter_rules(self, instance, eq):
        for rule in instance.rules:
            if isinstance(rule, EQ) and rule.is_variable_equivalence():
                assert isinstance(rule.a, VAR)
                assert isinstance(rule.b, VAR)
                inverse = rule.a.negated != rule.b.negated
                eq.mark_equivalent(rule.a.var_name, rule.b.var_name, inverse)
            else:
                yield rule

    def _search_ands(self, feature_tree: FeatureNode, eq):
        if isinstance(feature_tree, AndFeature):
            for element in feature_tree.elements:
                if element.mandatory:
                    a = feature_tree.feature_literal
                    b = element.feature_literal
                    inverse = a.negated != b.negated
                    eq.mark_equivalent(a.var_name, b.var_name, inverse)
        if isinstance(feature_tree, CompositeFeature):
            for element in feature_tree.elements:
                self._search_ands(element, eq)

    def _sub_features(self, features: typing.List[str], direct, indirect):
        sub_features = set()
        for feature in features:
            if feature in direct:
                sub_features.add(direct[feature])
            elif feature in indirect:
                sub_features.add(indirect[feature])
            else:
                sub_features.add(feature)
        return list(sub_features)

    def transform(
        self, instance: Instance, mapping_: typing.Optional[UniverseMapping]
    ) -> typing.Tuple[Instance, UniverseMapping]:
        eq = EquivalenceClasses()
        rules = list(self._filter_rules(instance, eq))
        self._search_ands(instance.structure, eq)
        direct, inverse = eq.get_substitutions()
        mapping = UniverseMapping(mapping_)
        for key, val in direct.items():
            mapping.map(origin_element=key, target_element=val)
        for key, val in inverse.items():
            mapping.map(origin_element=key, target_element=val, inverse=True)
        rules = [rule.substitute(direct, inverse) for rule in rules]
        struct = instance.structure.substitute(direct, inverse)
        features = self._sub_features(instance.features, direct, inverse)
        instance_ = Instance(features=features, rules=rules, structure=struct)
        instance_.instance_name = instance.instance_name + "|EQ"
        return instance_, mapping
