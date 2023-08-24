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
import logging
import os

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
from _conf import (
    INPUT_SAMPLE_ARCHIVE,
    INSTANCE_ARCHIVE,
    ITERATION_TIME_LIMIT,
    ITERATIONS,
    RESULT_FOLDER,
    TIME_LIMIT,
)

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


benchmark = Benchmark(RESULT_FOLDER, save_output=True, hide_output=False)

logging.getLogger("SampLNS").addHandler(logging.StreamHandler())
logging.getLogger("SampLNS.CPSAT").setLevel(logging.WARNING)

benchmark.capture_logger("SampLNS", logging.INFO)


@slurminade.slurmify
def run_distributed(
    instance_name: str, initial_sample_path: str, time_used_by_yasa: float
):
    benchmark.add(
        run_samplns,
        instance_name,
        initial_sample_path,
        instance_archive=INSTANCE_ARCHIVE,
        input_sample_archive=INPUT_SAMPLE_ARCHIVE,
        iterations=ITERATIONS,
        iteration_time_limit=ITERATION_TIME_LIMIT,
        time_limit=TIME_LIMIT,
        verify=True,
        fast_verify=True,
        _yasa_time_used=time_used_by_yasa,
    )


def run_samplns(
    instance_name: str,
    initial_sample_path: str,
    instance_archive,
    input_sample_archive,
    iterations,
    iteration_time_limit,
    time_limit,
    verify,
    fast_verify,
    _yasa_time_used,
):
    """
    Running SampLNS on an initial sample.
    """
    configure_grb_license_path()
    try:
        instance = get_instance(instance_name, instance_archive)
    except Exception as e:
        msg = f"Error while parsing instance {instance_name}: {e!s}"
        raise RuntimeError(msg)
    sample = parse_sample(
        sample_path=initial_sample_path, archive_path=input_sample_archive
    )

    remaining_time = time_limit - _yasa_time_used
    solver = None
    logger = MyLnsLogger()
    if remaining_time > 0:
        # setup (needs time measurement as already involves calculations)
        solver = SampLns(
            instance=instance,
            initial_solution=sample,
            neighborhood_selector=RandomNeighborhood(),
            observer=logger,
        )

        solver.optimize(
            iterations=iterations,
            iteration_timelimit=iteration_time_limit,
            timelimit=remaining_time,
        )

        solution = solver.get_best_solution(verify=verify, fast_verify=fast_verify)
    else:
        solution = sample

    # get optimized sample and verify its correctness (takes some time).
    return {
        "samplns_used": solver is not None,
        "time_used_by_yasa": _yasa_time_used,
        "timelimit_for_samplns": remaining_time,
        "solution": solution,
        "lower_bound": solver.get_lower_bound() if solver else 1,
        "upper_bound": len(solution),
        "optimal": solver.get_lower_bound() == len(solver.get_best_solution())
        if solver
        else False,
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

    if "alg" not in socket.gethostname():
        return

    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )
    if not os.path.exists(os.environ["GRB_LICENSE_FILE"]):
        msg = "Gurobi License File does not exist."
        raise RuntimeError(msg)


import random

if __name__ == "__main__":
    samples = parse_solution_overview(INPUT_SAMPLE_ARCHIVE)
    yasa_m1 = samples[
        (samples["Algorithm"] == "FIDE-YASA") & (samples["Settings"] == "t2_m1_null")
    ].dropna()
    indices = list(yasa_m1.index)
    random.shuffle(indices)
    with slurminade.Batch(max_size=40) as batch:
        for idx in indices:
            if not yasa_m1["Path"][idx]:
                print("Skipping unsuccessful row", yasa_m1.loc[idx])
                continue
            if yasa_m1["#Variables"][idx] > 1500:
                print("Skipping", yasa_m1["Instance"][idx], "due to its size.")
                continue
            path = yasa_m1["Path"][idx]
            instance = yasa_m1["Instance"][idx]
            if "soletta_2017-03-09_21-02-40" in instance:
                print(
                    "Skipping soletta_2017-03-09_21-02-40 because it defines a variable name twice."
                )
                continue
            # if "uclibc" in instance:
            #    print("Skipping uclibc instance! They seem to be inconsistent.")
            #    continue
            run_distributed.distribute(
                instance, path, time_used_by_yasa=yasa_m1["Time(s)"][idx]
            )
        pack_after_finish.wait_for(batch.flush()).distribute()
