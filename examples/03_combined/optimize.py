import argparse
import logging

from samplns.baseline import BaselineAlgorithm
from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.simple import SampLns

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument(
        "-a",
        "--baseline-algorithm",
        choices=["YASA", "YASA3", "YASA5", "YASA10"],
        default="YASA",
        help="Algorithm to use for the baseline. YASA has several versions for different values of m.",
    )
    parser.add_argument(
        "--baseline-timeout", default=60, help="Timeout in seconds", type=int
    )

    args = parser.parse_args()

    logger = logging.getLogger("SampLNS")
    logger.setLevel(logging.WARNING)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.getChild("CPSAT").setLevel(logging.WARNING)
    logger.getChild("Baseline").setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(message)s")

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    instance_path = args.file
    feature_model = parse(instance_path, logger=logger)

    baseline = BaselineAlgorithm(
        instance_path, algorithm=args.baseline_algorithm, logger=logger
    )
    initial_sample = baseline.optimize(args.baseline_timeout)

    if initial_sample is None:
        print(
            "Could not calculate a valid baseline sample within the given runtime.",
            "Try setting baseline timeout to a higher value",
        )
        exit(1)

    print("Received a valid sample. Starting Samplns.")

    solver = SampLns(
        instance=feature_model,
        initial_solution=initial_sample,
        neighborhood_selector=RandomNeighborhood(logger=logger),
        logger=logger,
    )

    solver.optimize(
        iterations=10000,
        iteration_timelimit=60.0,
        timelimit=900,
    )
    optimized_sample = solver.get_best_solution(verify=True, fast_verify=True)
    print(
        f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}"
    )
    print(f"Proved lower bound is {solver.get_lower_bound()}.")
