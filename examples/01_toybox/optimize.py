import json

from samplns.simple import ConvertingLns
from samplns.instances import parse
from samplns.lns import RandomNeighborhood

if __name__ == "__main__":
    feature_model = parse("./toybox_2006-10-31_23-30-06/model.xml")
    with open("./yasa_sample.json") as f:
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