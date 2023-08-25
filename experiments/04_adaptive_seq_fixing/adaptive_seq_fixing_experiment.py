import argparse
import json
import os
from collections import namedtuple
from multiprocessing.pool import Pool
from os.path import abspath, expanduser
from typing import Dict, List

import slurminade
from aemeasure import Database, MeasurementSeries, read_as_pandas_table
from samplns.cds.cds_lns import LnsCds, TransactionGraph
from samplns.instances import parse
from samplns.preprocessor.preprocessing import IndexInstance, Preprocessor

slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mem_per_cpu="16G",
    cpus_per_task=1,
)

slurminade.set_dispatch_limit(100)

ITERATIONS = 50
TIME_LIMIT = 60.0

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
RESULT_FOLDER = os.path.join(
    SCRIPT_DIR, "results", f"be_smart_{ITERATIONS}it_{round(TIME_LIMIT)}sec"
)
EXPERIMENT_INSTANCE_ROOT = abspath(
    expanduser("~/git/software-configuration-problem/instances")
)
EXPERIMENT_INSTANCE_FOLDER = os.path.join(
    EXPERIMENT_INSTANCE_ROOT, "FinancialServices01"
)

Instance = namedtuple("Instance", ["name", "model_path", "solution_path"])


def generate_instance_tuple(model_path: str, solution_path: str):
    return (solution_path.split("/")[-1], model_path, solution_path)


@slurminade.slurmify
def optimize(instance_name, model_path, solution_path, smart: bool):
    configure_grb_license_path()

    print(f"Smart = {smart}")

    instance = Preprocessor().preprocess(parse(model_path))
    assert type(instance) == IndexInstance
    # sample = convert_sample_list_to_dicts(
    #     min(parse_solutions(solution_path)["yasa"].values(), key=len)
    # )
    # sample = [instance.to_mapped_universe(config) for config in sample]
    sample = None
    f_initial = os.path.join(solution_path, "initial.json")
    f_index = os.path.join(solution_path, "index_instance.json")
    with open(f_initial) as sample_file, open(f_index) as index_file:
        i_sample = json.load(sample_file)["initial_sample"]
        index = json.load(index_file)["to_original_universe"]["origins"]
        sample = [
            {abs(i) - 1: i > 0 for i in s if abs(i) <= instance.n_concrete}
            for s in i_sample
        ]
        sample = [
            {
                next(d["l1"][0] for d in index if d["feature"] == i): b
                for (i, b) in c.items()
            }
            for c in sample
        ]
        print(
            "Mapping instance to mapped universe... This can take VERY LONG, so multiprocessing is applied!"
        )
        with Pool() as pool:
            sample = pool.map(instance.to_mapped_universe, iterable=sample)
        assert len(sample) == len(i_sample)
        for c in sample:
            assert len(c) == instance.n_concrete
        # print(sample)

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
    samples: List[List[str]],
) -> List[Dict[str, bool]]:
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


def get_instances() -> List[Instance]:
    """
    Walk through all instance directories, find matching model and solution files,
    return them as tuples.
    """
    model_path = []
    sol_path = []

    print(EXPERIMENT_INSTANCE_ROOT)
    for root, dirs, _files in os.walk(EXPERIMENT_INSTANCE_FOLDER):
        for instance in dirs:
            # load best solution
            sol_path.append(os.path.join(root, instance))
            model_path.append(
                os.path.join(root, f"{instance[(len('financial-services-')):]}.xml")
            )

    return [generate_instance_tuple(m, s) for (m, s) in zip(model_path, sol_path)]


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

    instances: List[Instance] = get_instances()
    instances.sort(key=lambda t: t[0])
    instances = [instances[0], instances[-1]]
    print(instances)

    with slurminade.Batch(max_size=4) as batch:
        for instance in instances:
            instance_a = [*list(instance), True]
            batch.add(optimize, *instance_a)
            instance_b = [*list(instance), False]
            batch.add(optimize, *instance_b)
        if not args.debug:
            pack_after_finish.wait_for(batch.flush()).distribute()
