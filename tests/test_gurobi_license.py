import math
import random

import gurobipy
import gurobipy as gp
from gurobipy import GRB


def test_gurobi_license():
    # Adapted example from Gurobi's official website.
    # Copyright 2023, Gurobi Optimization, LLC
    # Solve a traveling salesman problem on a randomly generated set of
    # points using lazy constraints.   The base MIP model only includes
    # 'degree-2' constraints, requiring each node to have exactly
    # two incident edges.  Solutions to this model may contain subtours -
    # tours that don't visit every city.

    n = 100  # n is sufficiently large for the automated gurobi license check to fail
    points = [(random.randint(0, 100), random.randint(0, 100)) for _ in range(n)]

    dist = {
        (i, j): math.sqrt(sum((points[i][k] - points[j][k]) ** 2 for k in range(2)))
        for i in range(n)
        for j in range(i)
    }
    try:
        m = gp.Model()

        # Create variables
        variables = m.addVars(dist.keys(), obj=dist, vtype=GRB.BINARY, name="e")
        for i, j in variables:
            variables[j, i] = variables[i, j]  # edge in opposite direction
        m.addConstrs(variables.sum(i, "*") == 2 for i in range(n))
        m._vars = variables
        m.setParam("OutputFlag", 0)
        m.setParam("TimeLimit", 5)
        m.optimize()
    except gurobipy.GurobiError as e:
        msg = f"There is most likely an issue with your gurobi license. Exception: {e}"
        raise AssertionError(
            msg
        )
