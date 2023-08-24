"""
This module provides instance representation and parser.
The instance representation will automatically perform simple transformations
such as converting binary AND/OR to n-ary.
Features and rules have different syntax.

```
from instance import parse
instance = parse("../instances/Automotive02/Automotive02_V1.xml")
```
"""
# flake8: noqa F401
# The feature structure elements
from .feature import (
    AltFeature,
    AndFeature,
    CompositeFeature,
    ConcreteFeature,
    FeatureLabel,
    FeatureLiteral,
    FeatureNode,
    OrFeature,
)

# Container for instance
from .instance import Instance
from .parse_dimacs import parse_dimacs
from .parser import parse, parse_solutions, parse_source

# The rule elements
from .sat_formula import AND, EQ, IMPL, OR, VAR, SatNode, VariableLabel

__all__ = [
    "parse",
    "parse_solutions",
    "parse_source",
    "parse_dimacs",
    "FeatureLabel",
    "FeatureLiteral",
    "AltFeature",
    "AndFeature",
    "OrFeature",
    "ConcreteFeature",
    "CompositeFeature",
    "FeatureNode",
    "AND",
    "OR",
    "VAR",
    "EQ",
    "IMPL",
    "SatNode",
    "VariableLabel",
    "Instance",
]
