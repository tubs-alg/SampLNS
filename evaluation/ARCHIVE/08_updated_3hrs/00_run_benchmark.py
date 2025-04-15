from pathlib import Path
from zipfile import ZipFile

INSTANCES = [
    "calculate",
    "lcm",
    "email",
    "ChatClient",
    "toybox_2006-10-31_23-30-06",
    "car",
    "FeatureIDE",
    "FameDB",
    "APL",
    "SafeBali",
    "TightVNC",
    "APL-Model",
    "gpl",
    "SortingLine",
    "dell",
    "PPU",
    "berkeleyDB1",
    "axTLS",
    "Violet",
    "berkeleyDB2",
    "soletta_2015-06-26_18-38-56",
    "BattleofTanks",
    "BankingSoftware",
    "fiasco_2017-09-26_11-30-56",
    "fiasco_2020-12-01_14-09-14",
    "uclibc_2008-06-05_13-46-47",
    "uclibc_2020-12-24_11-54-53",
    "E-Shop",
    "toybox_2020-12-06_00-02-46",
    "DMIE",
    "soletta_2017-03-09_21-02-40",
    "busybox_2007-01-24_09-14-09",
    "fs_2017-05-22",
    "WaterlooGenerated",
    "financial_services",
    "busybox-1_18_0",
    "busybox-1_29_2",
    "busybox_2020-12-16_21-53-05",
    "am31_sim",
    "EMBToolkit",
    "atlas_mips32_4kc",
    "eCos-3-0_i386pc",
    "integrator_arm7",
    "XSEngine",
    "aaed2000",
    "FreeBSD-8_0_0",
    "ea2468",
    #    "Automotive01",
    #    "main_light",
    #    "freetz",
]

import slurminade

# ================================================
# SLURM CONFIGURATION FOR DISTRIBUTED EXECUTION
# ------------------------------------------------
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen05",
    mail_user="krupke@ibr.cs.tu-bs.de",
    exclusive=True,
    mail_type="FAIL",
)
slurminade.set_dispatch_limit(300)

import logging

from algbench import Benchmark
from samplns.baseline.algorithm import BaselineAlgorithm
from samplns.instances import parse, parse_dimacs
from samplns.lns.lns import LnsObserver
from samplns.lns.neighborhood import Neighborhood, RandomNeighborhood
from samplns.simple import SampLns
from samplns.utils import Timer


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


RESULT_FOLDER = "./results"
ITERATIONS = 10000
ITERATION_TIME_LIMIT = 180.0
CDS_ITERATION_TIME_LIMIT = 180.0
TIME_LIMIT = 3 * 60 * 60
benchmark = Benchmark(RESULT_FOLDER, save_output=True, hide_output=False)

logging.getLogger("SampLNS").addHandler(logging.StreamHandler())
logging.getLogger("SampLNS.CPSAT").setLevel(logging.WARNING)

benchmark.capture_logger("SampLNS", logging.INFO)


def prepare_instance(instance_name: str) -> Path:
    """
    Extract an instance file from the archive and return its path.
    """
    instance_archive = Path("../benchmark_models.zip")
    path_in_zip_xml = Path("models") / instance_name / Path("model.xml")
    path_in_zip_dimacs = Path("models") / instance_name / Path("model.dimacs")

    if instance_archive.is_file():
        with ZipFile(instance_archive) as zf:

            def exists(path: Path) -> bool:
                return str(path) in zf.namelist()

            # throw exception if both files exist -> ambiguous
            if exists(path_in_zip_xml) and exists(path_in_zip_dimacs):
                msg = f"Ambiguous: {path_in_zip_xml} and {path_in_zip_dimacs} found in {instance_archive}"
                raise RuntimeError(
                    msg
                )
            elif exists(path_in_zip_xml):
                if not path_in_zip_xml.exists():
                    print(f"Extracting {path_in_zip_xml} from {instance_archive}")
                    zf.extract(str(path_in_zip_xml))
                return path_in_zip_xml
            elif exists(path_in_zip_dimacs):
                if not path_in_zip_dimacs.exists():
                    print(f"Extracting {path_in_zip_dimacs} from {instance_archive}")
                    zf.extract(str(path_in_zip_dimacs))
                return path_in_zip_dimacs
            else:
                msg = f"Neither {path_in_zip_xml} nor {path_in_zip_dimacs} found in {instance_archive}"
                raise FileNotFoundError(
                    msg
                )
    else:
        msg = f"{instance_archive} not found"
        raise FileNotFoundError(msg)


@slurminade.slurmify
def run_distributed(instance_name: str, rep: int):
    benchmark.add(
        run_samplns,
        instance_name,
        iterations=ITERATIONS,
        iteration_time_limit=ITERATION_TIME_LIMIT,
        time_limit=TIME_LIMIT,
        cds_iteration_time_limit=CDS_ITERATION_TIME_LIMIT,
        verify=True,
        fast_verify=True,
        rep=rep,
    )


def run_samplns(
    instance_name: str,
    iterations,
    iteration_time_limit,
    time_limit,
    verify,
    fast_verify,
    cds_iteration_time_limit,
    rep: int,
):
    """
    Running SampLNS on an initial sample.
    """
    configure_grb_license_path()
    try:
        instance_path = prepare_instance(instance_name)
        if instance_path.suffix == ".xml":
            instance = parse(str(instance_path))
        else:
            instance = parse_dimacs(str(instance_path))
    except Exception as e:
        msg = f"Error while parsing instance {instance_name}: {e!s}"
        raise RuntimeError(msg)
    # measure time for running yasa
    timer = Timer()
    sample = BaselineAlgorithm(str(instance_path), seed=rep).optimize(time_limit)
    _yasa_time_used = timer.time()
    assert sample

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
            cds_iteration_time_limit=cds_iteration_time_limit,
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


import os


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



if __name__ == "__main__":
    Path("./results").mkdir(exist_ok=True)
    for rep in range(0, 5):
        for instance in INSTANCES:
            run_distributed.distribute(instance, rep)
    slurminade.join()
    pack_after_finish.distribute()
