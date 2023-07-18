"""
This script runs SampLNS on all the samples.
Requires:
- `00_benchmark_instances.zip`: The feature models to evaluate SampLNS on.
- `00_baseline/*.zip`: Initial samples for the feature models to optimize by other algorithms.
Provides:
- `01_results`: A database with optimized samples and information on the optimization process in

It will automatically check which samples have already been optimized, such that it
can be restarted without doing repetitive work.
"""
import os
import logging
import slurminade
from _utils import get_instance, parse_sample, parse_solution_overview
from algbench import Benchmark
from samplns.lns.lns import LnsObserver
from samplns.lns.neighborhood import Neighborhood, RandomNeighborhood
from samplns.simple import SampLns
from samplns.utils import Timer

# ================================================
# SLURM CONFIGURATION FOR DISTRIBUTED EXECUTION
# ------------------------------------------------
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mail_user="krupke@ibr.cs.tu-bs.de",
    mail_type="FAIL",
)

slurminade.set_dispatch_limit(100)
# ================================================

# ================================================
# EXPERIMENT SETUP
# ------------------------------------------------
ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 90

BASE = "900_seconds_5_it"
INPUT_SAMPLE_ARCHIVE = f"../01_ICSE_2024_0/00_baseline/{BASE}.zip"
INSTANCE_ARCHIVE = "../01_ICSE_2024_0//00_benchmark_instances.zip"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"


# ================================================


class MyLnsLogger(LnsObserver):
    """
    A logger that will save information on the SampLNS iterations for us to evaluate
    later.
    """

    def __init__(self):
        self.timer = Timer(0)
        self.iterations = []

    def report_neighborhood_optimization(self, neighborhood: Neighborhood):
        self.iterations[-1]["nbrhd_tuples"] = len(neighborhood.missing_tuples)
        self.iterations[-1]["nbrhd_confs"] = len(neighborhood.initial_solution)

    def report_iteration_begin(self, iteration: int):
        self.iterations.append({})

    def report_iteration_end(
        self, iteration: int, runtime: float, lb: int, solution, events
    ):
        self.iterations[-1].update(
            {
                "iteration": iteration,
                "lb": lb,
                "ub": len(solution),
                "time": self.timer.time(),
                "iteration_time": runtime,
                "events": events,
            }
        )


benchmark = Benchmark(RESULT_FOLDER, save_output=False, hide_output=True)

logging.getLogger("SampLNS").addHandler(logging.StreamHandler())
logging.getLogger("SampLNS.CPSAT").setLevel(logging.WARNING)

benchmark.capture_logger("SampLNS", logging.INFO)



@slurminade.slurmify
def run_distributed(instance_name: str, initial_sample_path: str):
    benchmark.add(
        run_samplns,
        instance_name,
        initial_sample_path,
        instance_archive=INSTANCE_ARCHIVE,
        input_sample_archive=INPUT_SAMPLE_ARCHIVE,
        iterations=ITERATIONS,
        iteration_time_limit=ITERATION_TIME_LIMIT,
        time_limit=TIME_LIMIT,
    )


def run_samplns(
    instance_name: str,
    initial_sample_path: str,
    instance_archive,
    input_sample_archive,
    iterations,
    iteration_time_limit,
    time_limit,
):
    """
    Running SampLNS on an initial sample.
    """
    configure_grb_license_path()
    try:
        instance = get_instance(instance_name, instance_archive)
    except Exception as e:
        print("Skipping due to parser error:", instance_name, str(e))
        return None
    sample = parse_sample(
        sample_path=initial_sample_path, archive_path=input_sample_archive
    )

    # setup (needs time measurement as already involves calculations)
    logger = MyLnsLogger()
    solver = SampLns(
        instance=instance,
        initial_solution=sample,
        neighborhood_selector=RandomNeighborhood(),
        observer=logger,
    )

    solver.optimize(
        iterations=iterations,
        iteration_timelimit=iteration_time_limit,
        timelimit=time_limit,
    )
    # get optimized sample and verify its correctness (takes some time).
    return {
        "solution": solver.get_best_solution(verify=True, fast_verify=True),
        "lower_bound": solver.get_lower_bound(),
        "upper_bound": len(solver.get_best_solution()),
        "optimal": solver.get_lower_bound() == len(solver.get_best_solution()),
        "iteration_info": logger.iterations,
    }


@slurminade.slurmify(mail_type="ALL")
def pack_after_finish():
    """
    Compress the database after the experiment has finished.
    """
    benchmark.compress()


def configure_grb_license_path():
    # hack for gurobi license on alg workstations. TODO: Find a nicer way
    import socket
    from pathlib import Path

    # if "alg" not in socket.gethostname():
    #    return

    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )
    if not os.path.exists(os.environ["GRB_LICENSE_FILE"]):
        msg = "Gurobi License File does not exist."
        raise RuntimeError(msg)
import random

if __name__ == "__main__":
    samples = parse_solution_overview(INPUT_SAMPLE_ARCHIVE)
    indices = list(samples.index)
    random.shuffle(indices)
    with slurminade.Batch(max_size=40) as batch:
        for idx in indices:
            if not samples["Path"][idx]:
                print("Skipping unsuccessful row", samples.loc[idx])
                continue
            if samples["#Variables"][idx] > 250:
                print("Skipping", samples["Instance"][idx], "due to its size.")
                continue
            path = samples["Path"][idx]
            instance = samples["Instance"][idx]
            if "uclibc" in instance:
                print("Skipping uclibc instance! They seem to be inconsistent.")
                continue
            run_distributed.distribute(instance, path)
        pack_after_finish.wait_for(batch.flush()).distribute()
