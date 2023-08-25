import argparse
import json
import os
from abc import ABC, abstractmethod
from collections import defaultdict, namedtuple
from os.path import abspath, expanduser
from time import time
from typing import Dict, List

import slurminade
from aemeasure import Database, MeasurementSeries, read_as_pandas_table
from samplns.cds import CdsLns
from samplns.instances import Instance, parse, parse_solutions
from samplns.lns import ModularLns
from samplns.lns.neighborhood import RandomNeighborhood
from samplns.preprocessor.preprocessing import IndexInstance, Preprocessor

slurminade.update_default_configuration(partition="alg", constraint="alggen03")

slurminade.set_dispatch_limit(100)

ITERATIONS = 5
TIME_LIMIT = 60.0

InstanceTuple = namedtuple("Instance", ["name", "model_path", "solution_path"])


class InstanceLoader(ABC):
    @abstractmethod
    def get_instances(self) -> List[InstanceTuple]:
        pass

    @abstractmethod
    def load_model(self, instance: InstanceTuple) -> Instance:
        pass

    @abstractmethod
    def load_sample(self, instance: InstanceTuple) -> List[Dict[int, bool]]:
        pass


class StandardInstanceLoader(InstanceLoader):
    def get_instances(self) -> List[InstanceTuple]:
        """
        Walk through all instance directories, find matching model and solution files,
        return them as tuples.
        """
        model_paths = []
        instances = []

        for path in EXPERIMENT_INSTANCE_FOLDERS:
            print(path)
            for root, _dirs, files in os.walk(os.path.join(path, "010_models")):
                for file in files:
                    model_paths.append(os.path.join(root, file))

        for path in EXPERIMENT_INSTANCE_FOLDERS:
            print(path)
            for root, _dirs, files in os.walk(os.path.join(path, "020_samples")):
                for file in files:
                    for i, model in enumerate(model_paths):
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

    def load_model(self, instance: InstanceTuple) -> Instance:
        return parse(instance.model_path)

    def load_sample(self, instance: InstanceTuple) -> List[Dict[int, bool]]:
        def sol_generator():
            for algo, solutions in parse_solutions(instance.solution_path).items():
                for sol in solutions.values():
                    yield (algo, sol)

        return min((sol for alg, sol in sol_generator()), key=len)


class FinancialServicesInstanceLoader(InstanceLoader):
    def get_instances(self) -> List[InstanceTuple]:
        """
        Walk through all instance directories, find matching model and solution files,
        return them as tuples.
        """
        model_path = []
        sol_path = []

        print(EXPERIMENT_INSTANCE_ROOT)
        for root, dirs, _files in os.walk(os.join(EXPERIMENT_INSTANCE_ROOT)):
            for instance in dirs:
                # load best solution
                sol_path.append(os.path.join(root, instance))
                model_path.append(
                    os.path.join(root, f"{instance[(len('financial-services-')):]}.xml")
                )

        return [generate_instance_tuple(m, s) for (m, s) in zip(model_path, sol_path)]


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


def generate_instance_tuple(model_path: str, solution_path: str):
    return (
        model_path.split("/")[-4] + "-" + model_path.split("/")[-1].split(".")[0],
        model_path,
        solution_path,
    )


@slurminade.slurmify
def optimize(instance_name, model_path, solution_path):
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
        return [
            instance.to_mapped_universe(configuration) for configuration in solution
        ]

    def parse_all_solutions():
        for algo, solutions in parse_solutions(solution_path).items():
            for sol in solutions.values():
                yield (algo, sol)

    # parse all solutions, sort by size (ascending)
    all_solutions = list(parse_all_solutions())
    print("BLA")
    all_solutions.sort(key=lambda t: len(t[1]))

    sample = None
    sample_algo = None

    for algo, sol in all_solutions:
        print(algo, sol)
        try:
            sample = to_internal_format(sol)
            sample_alg = algo
            break
        except ValueError as e:
            print(f"Could not use {algo} solution of size {len(sol)}: {e}")

    if not sample:
        msg = "No usable solution found!"
        raise Exception(msg)

    print(f"Using {sample_algo} solution with {len(sample)} configurations!")

    with MeasurementSeries(RESULT_FOLDER) as ms, ms.measurement() as m:
        m["instance"] = instance_name
        m["time_limit"] = TIME_LIMIT

        lbs = []
        ubs = []

        # setup (needs time measurement as already involves calculations)
        cds = CdsLns(instance=instance, initial_samples=sample)
        solver = ModularLns(
            instance=instance,
            initial_solution=sample,
            neighborhood_selector=RandomNeighborhood(),
            cds_algorithm=cds,
        )

        for _ in range(ITERATIONS):
            t = time()
            sol_optimal = solver.optimize(
                iterations=1, iteration_timelimit=TIME_LIMIT
            )

            iter_info = cds.solver.get_iteration_statistics()
            assert type(iter_info) == list
            assert type(iter_info[0]) == dict
            assert len(iter_info) > 0

            lbs.append(solver.lb)
            ubs.append(len(solver.get_best_solution()))
            if sol_optimal:
                print("Solution is optimal!")
                break

        cds.stop()

        m["iterations"] = ITERATIONS
        m["solution"] = solver.get_best_solution()
        m["lb_solution"] = cds.solver.get_best_solution()
        m["score"] = len(solver.get_best_solution())
        m["optimal"] = lbs[-1] == ubs[-1]
        m["runtime"] = m.time().total_seconds()
        m["iteration_lb_values"] = lbs
        m["iteration_ub_values"] = ubs

        # unpack iteration stats
        stats = cds.solver.get_iteration_statistics()
        for iteration_stats in stats:
            for key, value in iteration_stats.items():
                key = "cds_" + key
                if key not in m:
                    m[key] = []
                else:
                    m[key].append(value)


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


def configure_grb_license_path():
    # hack for gurobi license on alg workstations. TODO: Find a nicer way
    import socket
    from pathlib import Path

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

    # only get first and last of each group
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
                entries[-1],
            ]
            for _, entries in groups.items()
        ),
        start=[],
    )
    print(json.dumps(instances, indent=4))

    t = read_as_pandas_table(RESULT_FOLDER)

    print(RESULT_FOLDER)
    print(t)

    # if len(t) > 1:
    #     solved_instance_names = set(t["instance"])
    #     instances = [t for t in instances if not t[0] in solved_instance_names]

    # shuffle(instances)
    print(f"{len(instances)} remaining instances!")

    with slurminade.Batch(max_size=30) as batch:
        for instance in instances:
            batch.add(optimize, *instance)
            break
        if not args.debug:
            pack_after_finish.wait_for(batch.flush()).distribute()
