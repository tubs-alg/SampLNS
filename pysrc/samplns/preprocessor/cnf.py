from ..instances import AND, Instance


def to_cnf(instance: Instance):
    rules = []
    for rule in instance.rules:
        rule = rule.to_cnf()
        if isinstance(rule, AND):
            for clause in rule.elements:
                rules.append(clause)
        else:
            rules.append(rule)
    instance_ = Instance(instance.features, instance.structure, rules)
    instance_.instance_name = instance.instance_name + "|CNF"
    return instance_
