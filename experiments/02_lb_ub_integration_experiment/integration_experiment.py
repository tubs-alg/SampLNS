from aemeasure import MeasurementSeries, Measurement, read_as_pandas_table, Database
from samplns.cds import CdsLns
from samplns.preprocessor import index_instance
from samplns.preprocessor.preprocessing import Preprocessor, IndexInstance
from samplns.instances import parse, parse_solutions
from samplns.cds import CdsLns
from samplns.lns import ModularLns, LnsLogger
from samplns.lns.neighborhood import RandomNeighborhood
from os.path import abspath, expanduser
import random
from collections import defaultdict, namedtuple
from typing import List, Tuple, Dict
from time import time
import slurminade
import itertools
import argparse
import json
import os
import multiprocessing

slurminade.update_default_configuration(partition="alg", constraint="alggen03")

slurminade.set_dispatch_limit(100)

ITERATIONS = 60
TIME_LIMIT = 60.0

RESULT_FOLDER = abspath(f"results/integration_{ITERATIONS}it_{round(TIME_LIMIT)}sec")
EXPERIMENT_INSTANCE_ROOT = abspath(
    expanduser("~/git/software-configuration-problem/instances")
)
EXPERIMENT_INSTANCE_FOLDERS = [
    EXPERIMENT_INSTANCE_ROOT + "/FinancialServices01",
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


class MyLnsLogger(LnsLogger):
    def __init__(self, measurement: Measurement) -> None:
        self.tstart = time()
        self.measurement = measurement
        self.measurement["iter_lb"] = list()
        self.measurement["iter_ub"] = list()
        self.measurement["iter_stop"] = list()
        self.measurement["iter_ub_events"] = list()

    def report_iteration_end(
        self,
        iteration: int,
        runtime: float,
        lb: int,
        solution,
        events,
    ):
        print(
            f"Iteration {iteration} finished in {runtime}s. LB={lb}, UB={len(solution)}. Events: {events}."
        )
        self.measurement["iter_ub"].append(len(solution))
        self.measurement["iter_lb"].append(lb)
        self.measurement["iter_stop"].append(time() - self.tstart)
        self.measurement["optimal"] = lb == len(solution)
        self.measurement["iter_ub_events"].append(
            events if events is not None else dict()
        )

        # with open("bobo.json", "w") as f:
        #     json.dump(self.measurement, f)


@slurminade.slurmify
def optimize(instance_name, model_path, solution_path, use_lns_in_ub: bool):
    configure_grb_license_path()

    original_instance = parse(model_path)
    instance = Preprocessor().preprocess(original_instance)
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
        print("Transforming solution into internal format (multiprocessing)...")
        with multiprocessing.Pool() as pool:
            return pool.map(instance.to_mapped_universe, solution)

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
        print(algo)
        try:
            sample = to_internal_format(sol)
            sample_algo = algo
            break
        except ValueError as e:
            print(f"Could not use {algo} solution of size {len(sol)}: {e}")

    if not sample:
        raise Exception("No usable solution found!")

    print(f"Using {sample_algo} solution with {len(sample)} configurations!")

    with MeasurementSeries(RESULT_FOLDER) as ms:
        with ms.measurement() as m:
            m["instance"] = instance_name
            m["n_concrete"] = instance.n_concrete
            m["n_all"] = instance.n_all
            m["iter_time_limit"] = TIME_LIMIT
            m["iterations"] = ITERATIONS
            m["lns_symmetry_breaking"] = use_lns_in_ub

            print(f"STARTING EXPERIMENT. USE LNS IN SYMMETRY BREAKING: {use_lns_in_ub}")

            # setup (needs time measurement as already involves calculations)
            cds = CdsLns(
                instance=instance, initial_samples=sample, be_smart=use_lns_in_ub
            )
            solver = ModularLns(
                instance=instance,
                initial_solution=sample,
                neighborhood_selector=RandomNeighborhood(),
                cds_algorithm=cds,
                logger=MyLnsLogger(m),
            )

            sol_optimal = solver.optimize(
                iterations=ITERATIONS, iteration_timelimit=TIME_LIMIT
            )

            cds.stop()

            m["solution"] = solver.get_best_solution()
            m["lb_solution"] = cds.solver.get_best_solution()
            m["score"] = len(solver.get_best_solution())
            m["runtime"] = m.time().total_seconds()

            # unpack iteration stats
            # stats = cds.solver.get_iteration_statistics()
            # for iteration_stats in stats:
            #     for key, value in iteration_stats.items():
            #         key = "cds_" + key
            #         if not key in m.keys():
            #             m[key] = list()
            #         else:
            #             m[key].append(value)


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
    model_paths = list()
    instances = list()

    for path in EXPERIMENT_INSTANCE_FOLDERS:
        for root, dirs, files in os.walk(os.path.join(path, "010_models")):
            for file in files:
                model_paths.append(os.path.join(root, file))

    for path in EXPERIMENT_INSTANCE_FOLDERS:
        for root, dirs, files in os.walk(os.path.join(path, "020_samples")):
            for file in files:
                for (i, model) in enumerate(model_paths):
                    if (
                        model.split("/")[-1] == file
                        or model.split("/")[-1].split(".")[0] == file.split(".")[0]
                    ):
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

    if not "alg" in socket.gethostname():
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

    # only get first and last of each group
    instances = get_instances()
    print(instances)
    groups = defaultdict(list)
    for instance in instances:
        key = instance[0][:5]
        groups[key].append(instance)
    for category, entries in groups.items():
        entries.sort(key=lambda t: t[0])
    instances = sum(
        (random.sample(entries, 6) for _, entries in groups.items()),
        start=list(),
    )
    print(json.dumps(instances, indent=4))

    t = read_as_pandas_table(RESULT_FOLDER)

    print(RESULT_FOLDER)
    print(t)

    random.shuffle(instances)

    with slurminade.Batch(max_size=len(instances) // 6) as batch:
        for instance in instances:
            for b in (False, True):
                instance_ = list(instance) + [b]
                batch.add(optimize, *instance_)
            break
        if not args.debug:
            pack_after_finish.wait_for(batch.flush()).distribute()
