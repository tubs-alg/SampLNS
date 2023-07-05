import json
import logging

from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.simple import SampLns

if __name__ == "__main__":
    logger = logging.getLogger("samplns")
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.getChild("CPSAT").setLevel(logging.WARNING)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(message)s")

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    feature_model = parse("./toybox_2006-10-31_23-30-06/model.xml", logger=logger)
    with open("./yasa_sample.json") as f:
        initial_sample = json.load(f)
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
