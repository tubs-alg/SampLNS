import json
import logging
import zipfile

from samplns.instances import parse
from samplns.lns import RandomNeighborhood
from samplns.simple import ConvertingLns

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

    feature_model = parse("./EMBToolkit/model.zip", logger=logger)

    with zipfile.ZipFile("./yasa_sample.zip") as zip, zip.open("yasa_sample.json") as f:
        initial_sample = json.load(f)
    solver = ConvertingLns(
        instance=feature_model,
        initial_solution=initial_sample,
        neighborhood_selector=RandomNeighborhood(logger=logger),
        logger=logger,
    )
    solver.optimize(
        iterations=5,
        iteration_timelimit=60.0,
        timelimit=90,
    )
    optimized_sample = solver.get_best_solution(verify=False)
    print(
        f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}"
    )
    print(f"Proved lower bound is {solver.get_lower_bound()}.")
