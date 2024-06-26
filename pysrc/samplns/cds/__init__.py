"""
Clique Disjoint Sets represent lower bounds on the instances. Each element, i.e., feature
literal tuple, in such a set needs to be in a different sample, because they have some
conflict. The most trivial conflict is between a tuple that contains
'feature 1 is active' and a tuple that contains 'feature 1 is deactivated'.
"""
# flake8: noqa F401
from ._cds_bindings import CDSNodeHeuristic, GreedyCds, LnsCds, TransactionGraph
from .base import CdsAlgorithm
from .cds_lns import CdsLns

__all__ = [
    "CdsAlgorithm",
    "CdsLns",
    "CDSNodeHeuristic",
    "LnsCds",
    "TransactionGraph",
    "GreedyCds",
]
