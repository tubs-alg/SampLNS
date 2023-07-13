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
from .parser import parse, parse_solutions, parse_source
from .parse_dimacs import parse_dimacs

# The feature structure elements
from .feature import (
    FeatureLabel,
    FeatureLiteral,
    AltFeature,
    AndFeature,
    OrFeature,
    ConcreteFeature,
    CompositeFeature,
    FeatureNode,
)

# The rule elements
from .sat_formula import AND, OR, VAR, EQ, IMPL, SatNode, VariableLabel

# Container for instance
from .instance import Instance
