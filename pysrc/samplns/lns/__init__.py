"""
Large Neighborhood Search (LNS) is a heuristic which uses MIP/CP/SAT-solver to find
the best solution within a large neighborhood of a solution. While most heuristics
either choose the best solution by linear search from a list or by random sampling,
LNS considers the search for the best neighbor as an optimization problem of its own.
By modelling the neighbor search as a MIP/CP/SAT of limited size, we can find the
best neighbor within a huge (exponential) neighborhood.

A simple example may be coloring: Start with a reasonably good coloring. Select k random
colors of the solution and uncolor all vertices with this color. Color the now uncolored
part of the graph using a MIP/CP/SAT-optimization. By dynamically scaling k, we can
control the size of the subproblem. In general, we want to obtain a subproblem that can
still induce change but is small enough to be solved within a few seconds or at most
minutes. Note that the subproblem is a slightly constrained coloring problem, as we
need to respect the colors of the fixed neighbors.

The primary problem in building an LNS-algorithm is to find a good neighborhood. The
implementation in this module, allows you to simply write your own neighborhood. The
remaining part is reasonably straight forward, and you do not really need to worry about
it.
```
lns = ModularLns(instance, best_solution, RandomNeighborhood(200))  # start with a random neighborhood with up to 200 uncovered tuples.
lns.optimize(iterations=30, iteration_timelimit=60)  # run 30 iterations of up to 60 seconds.
lns.get_best_solution()  # get best solution
lns.lb  # get lower bound on the instance
```

Structure:
- lns.py: The LNS-algorithm.
- independent_tuples.py: A tool for lower bounds and symmetry breaking. Used by the LNS.
- model.py: The model of the searching for the best neighbor using CP-SAT.
- coverage_set.py: A tool for checking which tuples need to be covered.
- neighborhood.py: Abstract neighborhood and implementation of random neighborhood.
"""
# flake8: noqa F401
