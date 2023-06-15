import logging

from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.preprocessor import Preprocessor
from samplns.simple import SampLns


def test_instance():
    instance = parse("../../../instances/Automotive02/Automotive02_V1.xml")


def test_preprocessor():
    instance = parse("../../../instances/Automotive02/Automotive02_V1.xml")
    index_instance = Preprocessor().preprocess(instance)


"""
A module to easily read the benchmark instances and their solutions.
"""
import os
import tarfile
import typing
from collections import defaultdict


def list_benchmark_instances() -> typing.Iterable[str]:
    """
    Return a list with instance identifiers for which we have samples to compare to.
    """
    root = os.path.dirname(__file__)
    instance_folder = os.path.join(root, "../../instances")
    for root, _dirs, files in os.walk(instance_folder):
        if "/020_samples/" in root:  # list only the instances with available sampels
            for f in files:
                if f.endswith(".tar.gz"):
                    group = root.split("/")[-3]
                    subgroup = root.split("/")[-1]
                    instance = f.split(".")[0]
                    yield "|".join([group, subgroup, instance])


def list_latest_benchmark_instances() -> typing.Iterable[str]:
    """
    Return a list with instance identifiers for which we have samples to compare to.
    """
    root = os.path.dirname(__file__)
    instance_folder = os.path.join(root, "../../instances")
    instances_for_class = {}
    for root, _dirs, files in os.walk(instance_folder):
        if "/020_samples/" in root:  # list only the instances with available sampels
            for f in files:
                if f.endswith(".tar.gz"):
                    group = root.split("/")[-3]
                    subgroup = root.split("/")[-1]
                    instance = f.split(".")[0]
                    if group not in instances_for_class:
                        instances_for_class[group] = []
                    instances_for_class[group].append(
                        "|".join([group, subgroup, instance])
                    )
    for group, instances in instances_for_class.items():
        yield max(instances)


def _get_instance_path(instance_name: str):
    group, subgroup, instance = instance_name.split("|")
    root = os.path.dirname(__file__)
    instance_folder = os.path.join(root, "../../../instances")
    path = os.path.join(
        instance_folder, group, "010_models", subgroup, f"{instance}.tar.gz"
    )
    assert os.path.exists(path)
    return os.path.abspath(path)


def _get_solution_path(instance_name: str):
    group, subgroup, instance = instance_name.split("|")
    root = os.path.dirname(__file__)
    instance_folder = os.path.join(root, "../../../instances")
    path = os.path.join(
        instance_folder, group, "020_samples", subgroup, f"{instance}.tar.gz"
    )
    if not os.path.exists(path):
        return False
    return os.path.abspath(path)


def get_solutions_from_file(path) -> typing.Dict[str, list]:
    """
    Parses all solutions contained in a .tar.gz
    """
    solutions = defaultdict(list)
    with tarfile.open(path, "r") as tar:
        solution_paths = []
        for member in tar.getmembers():
            if member.isdir():
                parts = member.name.split("/")
                if len(parts) == 3:
                    solution_paths.append(member.name)

        for solution_path in solution_paths:
            for member in tar.getmembers():
                if member.isfile() and member.name.startswith(solution_path):
                    f = tar.extractfile(member)
                    if not f:
                        msg = f"Could not read {member}."
                        raise Exception(msg)
                    # print("Read sample", member.name)
                    sol = f.readlines()
                    solutions[solution_path].append([s.strip().decode() for s in sol])

    return solutions


def get_solutions(instance) -> typing.Dict[str, list]:
    """
    Returns a dictionary of different solutions.
    """
    path = _get_solution_path(instance)

    if not path:
        return {}
    return get_solutions_from_file(path)


def convert_sample_list_to_dicts(
    samples: typing.List[typing.List[str]],
) -> typing.List[typing.Dict[str, bool]]:
    """
    Converts the original solution format of lists of selected features to a
    dictionaries with the assignments of all mandatory features. This format
    is used by the preprocessor (because we may replace a concrete feature by some
    negated composite feature and this makes things more clearly).
    """
    features = list({f for s in samples for f in s})
    sample_dicts = []
    for sample in samples:
        sample_dicts.append({f: f in sample for f in features})
    return sample_dicts


def get_instance(instance):
    return parse(_get_instance_path(instance))


def test_lns():
    logger = logging.getLogger("samplns")
    instance_name = "toybox-case-study|2020|2020-12-06_00-02-46"
    solutions = get_solutions(instance_name)
    best_solution = min(solutions.values(), key=len)
    instance = get_instance(instance_name)
    best_solution = [
        {f: f in conf for f in instance.features} for conf in best_solution
    ]
    lns = SampLns(
        instance=instance,
        initial_solution=best_solution,
        neighborhood_selector=RandomNeighborhood(logger, 200),
    )
    lns.optimize(10, 60)
    print(len(lns.get_best_solution()))
