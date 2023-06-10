import json

from samplns.simple import ConvertingLns
from samplns.instances import parse
from samplns.lns import RandomNeighborhood
import zipfile

if __name__ == "__main__":
    feature_model = parse("./EMBToolkit/model.zip")

    with zipfile.ZipFile("./yasa_sample.zip") as zip:
        with zip.open("yasa_sample.json") as f:
            initial_sample = json.load(f)
    solver = ConvertingLns(
        instance=feature_model,
        initial_solution=initial_sample,
        neighborhood_selector=RandomNeighborhood(),
    )
    solver.optimize(
        iterations=10000,
        iteration_timelimit=60.0,
        timelimit=900,
    )
    optimized_sample = solver.get_best_solution(verify=True)
    print(f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}")
    print(f"Proved lower bound is {solver.get_lower_bound()}.")