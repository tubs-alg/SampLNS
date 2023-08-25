import json
import os
from collections import namedtuple
from multiprocessing.pool import Pool
from os.path import abspath, expanduser
from time import time
from typing import Dict, List

import slurminade
from aemeasure import Database, MeasurementSeries
from samplns.cds import CdsLns
from samplns.instances import parse
from samplns.lns import ModularLns
from samplns.lns.neighborhood import RandomNeighborhood
from samplns.preprocessor.preprocessing import IndexInstance, Preprocessor

slurminade.update_default_configuration(partition="alg", constraint="alggen03")

slurminade.set_dispatch_limit(100)

ITERATIONS = int(60 * 2.0)
TIME_LIMIT = float(60.0 * 10.0)

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
RESULT_FOLDER = os.path.join(
    SCRIPT_DIR, "results", f"financial_{ITERATIONS}it_{round(TIME_LIMIT)}sec"
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
def optimize(instance_name, model_path, solution_path):
    configure_grb_license_path()

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

    with MeasurementSeries(RESULT_FOLDER) as ms, ms.measurement() as m:
        m["instance"] = instance_name
        m["time_limit"] = TIME_LIMIT

        lbs = []
        ubs = []
        times = []

        # setup (needs time measurement as already involves calculations)
        cds = CdsLns(
            instance=instance, initial_samples=sample, time_lim=TIME_LIMIT / 2
        )
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
            lbs.append(solver.lb)
            ubs.append(len(solver.get_best_solution()))
            times.append(time() - t)
            if sol_optimal:
                break

        m["iterations"] = ITERATIONS
        m["solution"] = solver.get_best_solution()
        m["lb_solution"] = cds.solver.get_best_solution()
        m["score"] = len(solver.get_best_solution())
        m["optimal"] = lbs[-1] == ubs[-1]
        m["runtime"] = m.time().total_seconds()
        m["iteration_runtimes"] = times
        m["iteration_lb_values"] = lbs
        m["iteration_ub_values"] = ubs

        cds.stop()


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
            if "financial" not in instance:
                continue
            print(instance)
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
    instances: List[Instance] = get_instances()
    instances = [t for t in instances if "financial" in t[0]]
    print(json.dumps(instances, indent=4))

    for name, model_path, solution_path in instances:
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
            year = name.split("-")[-3]
            month = name.split("-")[-2]
            day = name.split("-")[-1]
            p = f"/home/gabriel/git/software-configuration-problem/instances/FinancialServices01/020_samples/{year}/{year}-{month}-{day}_00-00-00"
            os.makedirs(f"{p}/phillip/0", exist_ok=True)

            for i, config in enumerate(sample):
                fp = f"{p}/phillip/0/{i+1:05d}.config"
                with open(fp, "w") as f:
                    f.writelines(s + "\n" for s, b in config.items() if b)

            # subprocess.run(["tar", "-czvf", f"{p}.tar.gz", "-C", f"{p}", "."])

            # print(
            #     "Mapping instance to mapped universe... This can take VERY LONG, so multiprocessing is applied!"
            # )
            # with Pool() as pool:
            #     sample = pool.map(instance.to_mapped_universe, iterable=sample)
            # assert len(sample) == len(i_sample)
            # for c in sample:
            #     assert len(c) == instance.n_concrete
            # print(sample)
