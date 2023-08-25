import argparse
import json
import os
from collections import defaultdict, namedtuple
from os.path import abspath, expanduser
from random import shuffle
from typing import Dict, List

import slurminade
from aemeasure import Database, MeasurementSeries, read_as_pandas_table
from samplns.cds.cds_lns import LnsCds, TransactionGraph
from samplns.instances import parse, parse_solutions
from samplns.preprocessor.preprocessing import IndexInstance, Preprocessor

slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mem_per_cpu="16G",
    cpus_per_task=1,
)

slurminade.set_dispatch_limit(100)

ITERATIONS = 20
TIME_LIMIT = 60.0

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
RESULT_FOLDER = os.path.join(
    SCRIPT_DIR, "results", f"be_smart_{ITERATIONS}it_{round(TIME_LIMIT)}sec"
)
EXPERIMENT_INSTANCE_ROOT = abspath(
    expanduser("~/git/software-configuration-problem/instances")
)
EXPERIMENT_INSTANCE_FOLDERS = [
    EXPERIMENT_INSTANCE_ROOT + "/busybox-case_study",
    EXPERIMENT_INSTANCE_ROOT + "/fiasco-case-study",
    EXPERIMENT_INSTANCE_ROOT + "/soletta-case-study",
    EXPERIMENT_INSTANCE_ROOT + "/toybox-case-study",
    EXPERIMENT_INSTANCE_ROOT + "/uclibc-case-study",
]

Instance = namedtuple("Instance", ["name", "model_path", "solution_path"])


def generate_instance_tuple(model_path: str, solution_path: str):
    return (
        model_path.split("/")[-4] + "-" + model_path.split("/")[-1].split(".")[0],
        model_path,
        solution_path,
    )


@slurminade.slurmify
def optimize(instance_name, model_path, solution_path, smart):
    configure_grb_license_path()

    original_instance = parse(model_path)
    instance = Preprocessor().preprocess(parse(model_path))
    assert type(instance) == IndexInstance

    def to_internal_format(solution: List[Dict[str, bool]]) -> List[Dict[int, bool]]:
        """
        Converts a solution to the internal format.
        """

        # check if old format is used
        if type(solution[-1]) is list:
            solution = convert_sample_list_to_dicts(solution, original_instance)
        # if not all(original_instance.is_fully_defined(conf) for conf in solution):
        #     raise ValueError("Some configurations are not fully defined!")
        return [
            instance.to_mapped_universe(configuration) for configuration in solution
        ]

    def parse_all_solutions():
        for algo, solutions in parse_solutions(solution_path).items():
            for sol in solutions.values():
                yield (algo, sol)

    # parse all solutions, sort by size (ascending)
    all_solutions = list(parse_all_solutions())
    all_solutions.sort(key=lambda t: len(t[1]))

    sample = None
    sample_algo = None

    for algo, sol in all_solutions:
        try:
            sample = to_internal_format(sol)
            sample_alg = algo
            break
        except ValueError as e:
            print(f"Could not use {algo} solution of size {len(sol)}: {e}")

    if not sample:
        msg = "No usable solution found!"
        raise Exception(msg)

    graph = TransactionGraph(instance.n_concrete)
    for config in sample:
        graph.add_valid_configuration(
            [
                (i + 1 if b else -(i + 1))
                for (i, b) in config.items()
                if i < instance.n_concrete
            ]
        )
    solver = LnsCds(graph, use_heur=False, be_smart=smart)

    with MeasurementSeries(RESULT_FOLDER) as ms, ms.measurement() as m:
        m["increase_added_edges_per_iter"] = smart
        m["instance"] = instance_name
        m["time_limit"] = TIME_LIMIT
        m["iterations"] = ITERATIONS

        solver.optimize(
            [], max_iterations=ITERATIONS, time_limit=TIME_LIMIT, verbose=True
        )

        # unpack iteration stats
        stats = solver.get_iteration_statistics()
        for iteration_stats in stats:
            for key, value in iteration_stats.items():
                key = "cds_" + key
                if key not in m:
                    m[key] = []
                else:
                    m[key].append(value)

        m["runtime"] = m.time().total_seconds()


@slurminade.slurmify
def pack_after_finish():
    Database(RESULT_FOLDER).compress()
    os.system(
        "echo 'FINISHED' | mail -s 'Experiment Batch finished!' ggehrke@ibr.cs.tu-bs.de"
    )


def convert_sample_list_to_dicts(
    samples: List[List[str]], instance: Instance
) -> List[Dict[str, bool]]:
    """
    Converts the original solution format of lists of selected features to a
    dictionaries with the assignments of all mandatory features. This format
    is used by the preprocessor (because we may replace a concrete feature by some
    negated composite feature and this makes things more clearly).
    """
    features = list(instance.features)
    sample_dicts = []
    for sample in samples:
        sample_dicts.append({f: f in sample for f in features})
    return sample_dicts


def get_instances() -> List[Instance]:
    """
    Walk through all instance directories, find matching model and solution files,
    return them as tuples.
    """
    model_paths = []
    instances = []

    for path in EXPERIMENT_INSTANCE_FOLDERS:
        for root, _dirs, files in os.walk(os.path.join(path, "010_models")):
            for file in files:
                model_paths.append(os.path.join(root, file))

    for path in EXPERIMENT_INSTANCE_FOLDERS:
        for root, _dirs, files in os.walk(os.path.join(path, "020_samples")):
            for file in files:
                for i, model in enumerate(model_paths):
                    if model.split("/")[-1] == file:
                        instances.append(
                            generate_instance_tuple(model, os.path.join(root, file))
                        )
                        model_paths.pop(i)
                        break

    return instances


def configure_grb_license_path():
    # hack for gurobi license on alg workstations. TODO: Find a nicer way
    import socket
    from pathlib import Path

    # Only configure on workstations
    if "alg" not in socket.gethostname():
        return

    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # If debug we dont want to distribute and instead solve on the local machine
    if args.debug:
        slurminade.set_dispatcher(slurminade.SubprocessDispatcher())

    t = read_as_pandas_table(RESULT_FOLDER)
    print(RESULT_FOLDER)
    print(t)

    # only get first, middle and last of each group
    instances = get_instances()
    groups = defaultdict(list)
    for instance in instances:
        key = instance[0][:5]
        groups[key].append(instance)
    for _category, entries in groups.items():
        entries.sort(key=lambda t: t[0])
    instances = sum(
        (
            [
                entries[0],
                entries[3 * len(entries) // 4],
                entries[-1],
            ]
            for _, entries in groups.items()
        ),
        start=[],
    )
    print(json.dumps(instances, indent=4))
    shuffle(instances)

    with slurminade.Batch(max_size=4) as batch:
        for instance in instances:
            instance_a = [*list(instance), False]
            batch.add(optimize, *instance_a)
            instance_b = [*list(instance), True]
            batch.add(optimize, *instance_b)
        if not args.debug:
            pack_after_finish.wait_for(batch.flush()).distribute()
