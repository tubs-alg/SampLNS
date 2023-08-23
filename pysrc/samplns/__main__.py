import argparse
import json
import logging

from samplns.baseline import BaselineAlgorithm
from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.simple import SampLns


def get_parser():
    parser = argparse.ArgumentParser(
        "samplns",
        description="Starts samplns either with a given initial sample or runs "
        "another sampling algorithm before.",
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="File path to the instance (either FeatJAR xml or DIMACS format.)",
    )

    initial_sample_group = parser.add_mutually_exclusive_group(required=True)
    initial_sample_group.add_argument(
        "--initial-sample",
        help="Set this when you already have an initial sample. "
        "File path to an initial sample (JSON) that should be used.",
    )
    initial_sample_group.add_argument(
        "--initial-sample-algorithm",
        choices=["YASA", "YASA3", "YASA5", "YASA10"],
        help="Set this if you want to run a sampling algorithm to "
        "generate an initial sample. YASA has several versions for "
        "different values of m.",
    )
    parser.add_argument(
        "--initial-sample-algorithm-timelimit",
        default=60,
        help="Timelimit of the initial sampling algorithm in seconds.",
        type=int,
    )

    parser.add_argument(
        "--samplns-timelimit",
        default=900,
        help="Timelimit of samplns in seconds.",
        type=int,
    )
    parser.add_argument(
        "--samplns-max-iterations",
        default=10000,
        help="Maximum number of iterations for samplns.",
        type=int,
    )
    parser.add_argument(
        "--samplns-iteration-timelimit",
        default=10000,
        help="Timelimit for each iteration of samplns in seconds.",
        type=int,
    )
    return parser


def main():
    parser = get_parser()
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

    if args.initial_sample:
        with open(args.initial_sample) as f:
            initial_sample = json.load(f)
    else:  # args.baseline
        baseline = BaselineAlgorithm(
            instance_path, algorithm=args.initial_sample_algorithm, logger=logger
        )
        initial_sample = baseline.optimize(args.initial_sample_algorithm_timelimit)

    if initial_sample is None:
        print("Could not load valid initial sample.")
        exit(1)

    print("Received a valid sample. Starting Samplns.")

    solver = SampLns(
        instance=feature_model,
        initial_solution=initial_sample,
        neighborhood_selector=RandomNeighborhood(logger=logger),
        logger=logger,
    )

    solver.optimize(
        iterations=args.samplns_max_iterations,
        iteration_timelimit=args.samplns_iteration_timelimit,
        timelimit=args.samplns_timelimit,
    )
    optimized_sample = solver.get_best_solution(verify=True, fast_verify=True)
    print(
        f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}"
    )
    print(f"Proved lower bound is {solver.get_lower_bound()}.")


if __name__ == "__main__":
    main()
