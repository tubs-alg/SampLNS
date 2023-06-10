from .feature import FeatureLiteral, AndFeature, OrFeature, AltFeature, ConcreteFeature
from .instance import Instance
from .sat_formula import AND, OR, NOT, VAR, IMPL, EQ, SatNode
import xml.etree.ElementTree as ET
import typing
import tarfile
from collections import defaultdict
import re
import zipfile

def parse(path: str) -> Instance:
    """
    Parse an instance. An exception is thrown when the instance does not look as we
    expect. In this case: tell us!

    Supports .tar.gz and .zip archives.

    :param path: The path to the instance.
    """
    if path.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.isreg():  # is File
                    if tarinfo.name.endswith(".xml"):
                        print("Parsing xml file", tarinfo.name)
                        return parse_source(tar.extractfile(tarinfo.name), path)
        raise ValueError("Could not extract xml file from archive")
    elif path.endswith(".zip"):
        with zipfile.ZipFile(path) as zip:
            for info in zip.infolist():
                if info.filename.endswith(".xml"):
                    print("Parsing xml file", info.filename)
                    return parse_source(zip.open(info.filename), path)
    else:
        with open(path) as f:
            return parse_source(f, path)


def parse_source(source_file, instance_name):
    tree = ET.parse(source_file)
    structure = parse_features(tree)
    features = list(structure.concrete_features())
    rules = parse_rules(tree)
    print(
        f"Parsed instance '{instance_name}' with {len(features)} features and {len(rules)} rules."
    )
    instance = Instance(features, structure, rules)
    instance.instance_name = instance_name
    return instance


def parse_features(xmltree: ET):
    return parse_feature(xmltree.find("struct"))


def parse_feature(feature_node):
    elements = [parse_feature(child) for child in feature_node]
    elements = [e for e in elements if e]
    mandatory = feature_node.attrib.get("mandatory", "false") == "true"
    feature_literal = FeatureLiteral(feature_node.attrib.get("name"))
    if feature_node.tag == "and":
        return AndFeature(feature_literal, mandatory=mandatory, elements=elements)
    elif feature_node.tag == "or":
        return OrFeature(feature_literal, mandatory=mandatory, elements=elements)
    elif feature_node.tag == "alt":
        if len(elements) == 1:
            print(
                f"Removing ALT-Feature {feature_literal.var_name} with only one element."
            )
            elements[0].mandatory = mandatory
            return elements[0]
        return AltFeature(feature_literal, mandatory=mandatory, elements=elements)
    elif feature_node.tag == "feature":
        return ConcreteFeature(feature_literal, mandatory=mandatory)
    elif feature_node.tag == "struct":
        assert len(elements) == 1
        return elements[0]
    elif feature_node.tag == "description":
        return None
    raise ValueError(f"Don't know tag {feature_node.tag}")


def parse_rule(rule_node):
    children = [parse_rule(child) for child in rule_node]
    tag = rule_node.tag
    if tag == "conj":
        if len(children) == 1:
            print("Warning: Conjunction with only one literal removed.")
            return children[0]
        return AND(*children)
    elif tag == "disj":
        if len(children) == 1:
            print("Warning: Disjunction with only one literal removed.")
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
    raise ValueError(f"Encountered an unknown tag in the XML rule: '{tag}'")


def parse_rules(xmltree: ET) -> typing.List[SatNode]:
    rules_node = xmltree.find("constraints")
    rules = []
    for rule in rules_node.findall("rule"):
        children = tuple(rule)
        assert len(children) == 1
        r = parse_rule(children[0])
        rules.append(r)
    return rules


def parse_solutions(path, algorithms: typing.List[str] = None):
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
                            list(
                                map(
                                    lambda x: x.decode("utf-8").rstrip("\n"),
                                    f.readlines(),
                                )
                            )
                        )

    return solutions
