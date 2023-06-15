import logging

from ..instances import AND, Instance


def to_cnf(instance: Instance, logger: logging.Logger):
    logger.info("Converting instance to CNF (%s).", str(instance))
    rules = []
    for rule in instance.rules:
        rule = rule.to_cnf()
        if isinstance(rule, AND):
            for clause in rule.elements:
                rules.append(clause)
        else:
            rules.append(rule)
    cnf_instance = Instance(instance.features, instance.structure, rules)
    cnf_instance.instance_name = instance.instance_name + "|CNF"
    logger.info("Finished converting instance to CNF (%s).", str(cnf_instance))
    return cnf_instance
