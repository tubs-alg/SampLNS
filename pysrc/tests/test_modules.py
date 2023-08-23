import logging
import json
from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.preprocessor import Preprocessor
from samplns.simple import SampLns
import os

"""
A module to easily read the benchmark instances and their solutions.
"""


def path_to_instance(path):
    return os.path.join(os.path.dirname(__file__), "instances", path)


def path_to_solution(path):
    return os.path.join(os.path.dirname(__file__), "solutions", path)


def test_instance():
    instance = parse(path_to_instance("Automotive02_V1/model.xml"))


def test_preprocessor():
    instance = parse(path_to_instance("Automotive02_V1/model.xml"))
    index_instance = Preprocessor().preprocess(instance)


def test_lns():
    logger = logging.getLogger("samplns")

    instance = parse(path_to_instance("toybox_2006-10-31_23-30-06/model.xml"))

    with open(path_to_solution("toybox_2006-10-31_23-30-06/yasa_sample.json"), "r") as f:
        best_solution = json.load(f)

    lns = SampLns(
        instance=instance,
        initial_solution=best_solution,
        neighborhood_selector=RandomNeighborhood(200),
        logger=logger
    )
    lns.optimize(10, 60)
    print(len(lns.get_best_solution()))
