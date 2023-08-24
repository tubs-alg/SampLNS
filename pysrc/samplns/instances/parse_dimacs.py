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
import zipfile
from collections import defaultdict

from .instance import Instance
from .sat_formula import OR, VAR

_logger = logging.getLogger("SampLNS")


def parse_dimacs(path: str, logger: logging.Logger = _logger) -> Instance:
    """
    Parse an instance. An exception is thrown when the instance does not look as we
    expect. In this case: tell us!

    Supports .tar.gz and .zip archives.

    :param path: The path to the instance.
    """
    if path.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tar:
            for tarinfo in tar:
                if tarinfo.isreg() and tarinfo.name.endswith(".dimacs"):
                    logger.info("Parsing dimacs file: %s", tarinfo.name)
                    return parse_source(
                        tar.extractfile(tarinfo.name), path, logger=logger
                    )
        error_msg = "Could not extract dimacs file from archive"
        raise ValueError(error_msg)
    elif path.endswith(".zip"):
        with zipfile.ZipFile(path) as zip:
            for info in zip.infolist():
                if info.filename.endswith(".dimacs"):
                    logger.info("Parsing xml file: %s", info.filename)
                    return parse_source(zip.open(info.filename), path, logger=logger)
        error_msg = "Could not extract dimacs file from archive"
        raise ValueError(error_msg)
    else:
        with open(path) as f:
            return parse_source(f, path, logger=logger)


def parse_source(source_file, instance_name, logger: logging.Logger = _logger):
    source = source_file.read().decode("utf-8")
    features = parse_features(source, logger=logger)
    rules = parse_rules(source, features=features, logger=logger)
    logger.info(
        "Parsed instance '%s' with %d features and %d rules.",
        instance_name,
        len(features),
        len(rules),
    )
    instance = Instance(list(features.values()), None, rules)
    instance.instance_name = instance_name
    return instance


def parse_features(dimacs: str, logger: logging.Logger):
    features = {}
    for line in dimacs.split("\n"):
        if line.startswith("c"):
            i = int(line.split(" ")[1].strip())
            feature = line.split(" ")[2].strip()
            if feature in features.values():
                msg = (
                    "Feature name is not unique: "
                    + feature
                    + " parsed from line: "
                    + line
                )
                raise ValueError(msg)
            assert feature not in features.values()
            features[i] = feature
    return features


def parse_rules(dimacs: str, features: dict, logger: logging.Logger):
    num_vars = 0
    num_clauses = 0
    rules = []
    for line in dimacs.split("\n"):
        if line.startswith("p"):
            if line.split(" ")[1].strip() != "cnf":
                msg = "Only cnf is supported as format."
                raise ValueError(msg)
            num_vars = int(line.split(" ")[2].strip())
            if num_vars != len(features):
                msg = "Number of variables does not match number of features."
                raise ValueError(msg)
            num_clauses = int(line.split(" ")[3].strip())
            continue
        if num_clauses > 0:
            num_clauses -= 1
            literals = []
            for literal in line.split(" "):
                literal = literal.strip()
                if literal == "0":
                    break
                if literal.startswith("-"):
                    literals.append(VAR(features[int(literal[1:])], negated=True))
                else:
                    literals.append(VAR(features[int(literal)], negated=False))
            if not literals:
                raise ValueError("Empty clause: " + line)
            rules.append(OR(*literals))
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
