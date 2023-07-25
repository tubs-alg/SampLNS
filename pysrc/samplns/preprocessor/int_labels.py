import typing

from ..instances import Instance
from .index_instance import IndexInstance
from .universe_mapping import UniverseMapping


def substitute_with_int_labels(
    instance: Instance, mapping: typing.Optional[UniverseMapping] = None
) -> IndexInstance:
    """
    Substitutes all labels with efficient indices. The concrete features will
    be directly at the beginning.
    """
    counter = 0
    mapping = UniverseMapping(mapping)
    direct_substitutions = {}

    # concrete features get first n labels
    for label in instance.features:
        direct_substitutions[label] = counter
        mapping.map(origin_element=label, target_element=counter)
        counter += 1
    n_concrete = counter

    # rules
    rules = []
    for rule in instance.rules:
        for var in rule.all_variables():
            if var not in direct_substitutions:
                direct_substitutions[var] = counter
                mapping.map(origin_element=var, target_element=counter)
                counter += 1
        rule_ = rule.substitute(direct_substitutions, {})
        rules.append(rule_)

    # variables
    if instance.structure:
        for feature in instance.structure.all_features():
            if feature not in direct_substitutions:
                direct_substitutions[feature] = counter
                mapping.map(origin_element=feature, target_element=counter)
                counter += 1
        struct = instance.structure.substitute(direct_substitutions, {})
    else:
        struct = None

    iistance = IndexInstance(struct, rules, n_concrete, counter, mapping)
    iistance.instance_name = instance.instance_name
    return iistance
