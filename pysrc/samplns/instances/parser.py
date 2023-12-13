"""
This file contains the parser for the XML format.
Currently, we only support the feature tree based format.
Pure CNF, e.g. in DIMACS, is not supported, yet.
We use the feature tree to extract the concrete features (leaves)
and the ALT-nodes which can be expressed more efficiently than in pure CNF.
"""
import logging
import re
import tarfile
import typing
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

from .feature import AltFeature, AndFeature, ConcreteFeature, FeatureLiteral, OrFeature
from .instance import Instance
from .sat_formula import AND, EQ, IMPL, NOT, OR, VAR, SatNode

_logger = logging.getLogger("SampLNS")


def parse(path: str, logger: logging.Logger = _logger) -> Instance:
    """
    Parse an instance. An exception is thrown when the instance does not look as we
    expect. In this case: tell us!

    Supports .tar.gz and .zip archives.

    :param path: The path to the instance.
    """
    if path.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.isreg() and tarinfo.name.endswith(".xml"):
                    logger.info("Parsing xml file: %s", tarinfo.name)
                    return parse_source(
                        tar.extractfile(tarinfo.name), path, logger=logger
                    )
        error_msg = "Could not extract xml file from archive"
        raise ValueError(error_msg)
    elif path.endswith(".zip"):
        with zipfile.ZipFile(path) as zip:
            for info in zip.infolist():
                if info.filename.endswith(".xml"):
                    logger.info("Parsing xml file: %s", info.filename)
                    return parse_source(zip.open(info.filename), path, logger=logger)
        error_msg = "Could not extract xml file from archive"
        raise ValueError(error_msg)
    else:
        with open(path) as f:
            return parse_source(f, path, logger=logger)


def parse_source(source_file, instance_name, logger: logging.Logger = _logger):
    tree = ET.parse(source_file)
    structure = parse_features(tree, logger=logger)
    features = list(structure.concrete_features())
    rules = parse_rules(tree, logger=logger)
    logger.info(
        "Parsed instance '%s' with %d features and %d rules.",
        instance_name,
        len(features),
        len(rules),
    )
    instance = Instance(features, structure, rules)
    instance.instance_name = instance_name
    return instance


def parse_features(xmltree: ET, logger: logging.Logger):
    return parse_feature(xmltree.find("struct"), logger=logger)


def parse_feature(feature_node, logger: logging.Logger):
    elements = [parse_feature(child, logger=logger) for child in feature_node]
    elements = [e for e in elements if e]
    mandatory = feature_node.attrib.get("mandatory", "false") == "true"
    feature_literal = FeatureLiteral(feature_node.attrib.get("name"))
    if feature_node.tag == "and":
        return AndFeature(
            feature_literal, mandatory=mandatory, elements=elements, logger=logger
        )
    elif feature_node.tag == "or":
        return OrFeature(
            feature_literal, mandatory=mandatory, elements=elements, logger=logger
        )
    elif feature_node.tag == "alt":
        if len(elements) == 1:
            logger.warning(
                "Removing ALT-Feature %s with only one element.",
                feature_literal.var_name,
            )
            elements[0].mandatory = mandatory
            return elements[0]
        return AltFeature(
            feature_literal, mandatory=mandatory, elements=elements, logger=logger
        )
    elif feature_node.tag == "feature":
        return ConcreteFeature(feature_literal, mandatory=mandatory)
    elif feature_node.tag == "struct":
        assert len(elements) == 1
        return elements[0]
    elif feature_node.tag == "description":
        return None
    elif feature_node.tag == "graphics":
        return None
    elif feature_node.tag == "attribute":
        return None
    error_msg = f"Don't know tag '{feature_node.tag}'"
    raise ValueError(error_msg)


def parse_rule(rule_node, logger: logging.Logger):
    children = [parse_rule(child, logger) for child in rule_node]
    tag = rule_node.tag
    if tag == "conj":
        if len(children) == 1:
            logger.warning("Conjunction with only one literal removed.")
            return children[0]
        return AND(*children)
    elif tag == "disj":
        if len(children) == 1:
            logger.warning("Disjunction with only one literal removed.")
            return children[0]
        return OR(*children)
    elif tag == "not":
        child = children[0]
        if isinstance(child, VAR):
            return child.NEG()
        else:
            return NOT(child)
    elif tag == "var":
        return VAR(rule_node.text)
    elif tag == "imp":
        return IMPL(children[0], children[1])
    elif tag == "eq":
        return EQ(children[0], children[1])
    error_msg = f"Encountered an unknown tag in the XML rule: '{tag}'"
    raise ValueError(error_msg)


def parse_rules(xmltree: ET, logger: logging.Logger) -> typing.List[SatNode]:
    rules_node = xmltree.find("constraints")
    if rules_node is None:
        logger.warning("No constraints found in the instance.")
        return []
    rules = []
    for rule in rules_node.findall("rule"):
        children = tuple(
            r for r in rule if r.tag in ("conj", "disj", "not", "var", "imp", "eq")
        )
        assert len(children) == 1, "Expecting exactly one logical expression per rule."
        r = parse_rule(children[0], logger=logger)
        rules.append(r)
    return rules


def parse_solutions(path, algorithms: typing.Optional[typing.List[str]] = None):
    if algorithms is None:
        algorithms = ["random", "incling", "icpl", "chvatal", "yasa", "phillip"]
    solutions = {a: defaultdict(list) for a in algorithms}

    regex = r".+\/(" + "|".join(algorithms) + r")\/([0-9]+)\/.+\.config"

    if path.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tar:
            for tarinfo in tar:
                match = re.match(regex, tarinfo.name)
                if tarinfo.isreg() and match:
                    with tar.extractfile(tarinfo.name) as f:
                        solutions[match.group(1)][match.group(2)].append(
                            [l.decode("utf-8").rstrip("\n") for l in f.readlines()]
                        )

    return solutions
