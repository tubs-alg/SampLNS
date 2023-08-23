"""
Wrapper for FeatJAR that computes initial samples for the LNS algorithm. This is necessary
as the LNS algorithm requires a set of initial configurations to work. In order to provide an all in one solution, we
provide this wrapper that computes the initial samples for you.

Structure:
- algorith.py: The wrapper for FeatJAR.
"""
# flake8: noqa F401
from .algorithm import BaselineAlgorithm
