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

from aemeasure import MeasurementSeries, read_as_pandas_table, Database
import slurminade

from samplns.simple import ConvertingLns
from samplns.utils import Timer
from samplns.lns.lns import LnsLogger
from samplns.lns.neighborhood import RandomNeighborhood, Neighborhood

from _utils import get_instance, parse_solution_overview, parse_sample

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
TIME_LIMIT = 900

BASE = "900_seconds_5_it"
INPUT_SAMPLE_ARCHIVE = f"./00_baseline/{BASE}.zip"
INSTANCE_ARCHIVE = "./00_benchmark_instances.zip"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"


# ================================================


class MyLnsLogger(LnsLogger):
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

    def __call__(self, *args, **kwargs):
        print(f"LOG[{self.timer.time()}]", *args)


@slurminade.slurmify
def optimize(instance_name: str, solution_path: str):
    """
    Running SampLNS on an initial sample.
    """
    configure_grb_license_path()
    try:
        instance = get_instance(instance_name, INSTANCE_ARCHIVE)
    except Exception as e:
        print("Skipping due to parser error:", instance_name, str(e))
        return
    sample = parse_sample(sample_path=solution_path, archive_path=INPUT_SAMPLE_ARCHIVE)

    with MeasurementSeries(RESULT_FOLDER) as ms:
        with ms.measurement() as m:
            m["instance"] = instance_name
            m["initial_sample_path"] = solution_path
            m["iteration_time_limit"] = ITERATION_TIME_LIMIT
            m["iterations"] = ITERATIONS
            m["time_limit"] = TIME_LIMIT

            # setup (needs time measurement as already involves calculations)
            logger = MyLnsLogger()
            solver = ConvertingLns(
                instance=instance,
                initial_solution=sample,
                neighborhood_selector=RandomNeighborhood(),
                logger=logger,
            )

            solver.optimize(
                iterations=ITERATIONS,
                iteration_timelimit=ITERATION_TIME_LIMIT,
                timelimit=TIME_LIMIT,
            )
            # get optimized sample and verify its correctness (takes some time).
            m["solution"] = solver.get_best_solution(verify=True)
            m["lower_bound"] = solver.get_lower_bound()
            m["upper_bound"] = len(solver.get_best_solution())
            m["optimal"] = solver.get_lower_bound() == len(solver.get_best_solution())
            m["runtime"] = m.time().total_seconds()
            m["iteration_info"] = logger.iterations


@slurminade.slurmify(mail_type="ALL")
def pack_after_finish():
    """
    Compress the database after the experiment has finished.
    """
    Database(RESULT_FOLDER).compress()


def configure_grb_license_path():
    # hack for gurobi license on alg workstations. TODO: Find a nicer way
    import socket
    from pathlib import Path

    os.environ["GRB_LICENSE_FILE"] = os.path.join(
        Path.home(), ".gurobi", socket.gethostname(), "gurobi.lic"
    )
    if not os.path.exists(os.environ["GRB_LICENSE_FILE"]):
        raise RuntimeError("Gurobi License File does not exist.")


if __name__ == "__main__":
    samples = parse_solution_overview(INPUT_SAMPLE_ARCHIVE)
    data = read_as_pandas_table(RESULT_FOLDER)
    already_done = data["initial_sample_path"].unique() if len(data) else []
    with slurminade.Batch(max_size=1) as batch:
        for idx in samples.index:
            if not samples["Path"][idx]:
                print("Skipping unsuccessful row", samples.loc[idx])
                continue
            if samples["#Variables"][idx] > 1500:
                print("Skipping", samples["Instance"][idx], "due to its size.")
                continue
            path = samples["Path"][idx]
            if path in already_done:
                print("Skipping", path)
                continue
            instance = samples["Instance"][idx]
            if "uclibc" in instance:
                print("Skipping uclibc instance! They seem to be inconsistent.")
                continue
            optimize.distribute(instance, path)
        pack_after_finish.wait_for(batch.flush()).distribute()
