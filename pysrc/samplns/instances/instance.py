import typing

from .feature import FeatureLabel, FeatureNode
from .sat_formula import SatNode


class Instance:
    """
    The instance object contains all the information necessary to understand the instance.
    It may be the product of multiple preprocessing steps.

    There are three fundamental containers:
    1. features: A list with all concrete features to build the universe on. It can be redundant to the structure, but due to optimization, it may be necessary.
    2. structure: The tree of features, or the structure of the configuration.
    3. rules: A list with additional rules that have to be satisfied by all elements in the universe.
    """

    def __init__(
            self,
            features: typing.List[FeatureLabel],
            structure: typing.Optional[FeatureNode],
            rules: typing.List[SatNode],
    ):
        self.instance_name = "UNNAMED"
        self.features: typing.List[FeatureLabel] = features
        self.structure: typing.Optional[FeatureNode] = structure
        self.rules: typing.List[SatNode] = rules

    def __repr__(self):
        if self.instance_name:
            return f"Instance[{self.instance_name}]<{len(self.features)} features, {len(self.rules)} rules>"
        else:
            return f"Instance[UNNAMED]<{len(self.features)} features, {len(self.rules)} rules>"

    def is_fully_defined(
            self,
            conf: typing.Dict[FeatureLabel, bool],
            exact: bool = False,
            verbose: bool = False,
    ) -> bool:
        """
        Checks if a configuration is fully defined, i.e., exactly defines the concrete
        features.
        """
        if any(f not in conf for f in self.features):
            if verbose:
                print("Not all features defined")
                print("Missing:", set(self.features) - set(conf.keys()))
            return False
        return not exact or len(conf.keys()) == len(self.features)

    def is_feasible(
            self, conf: typing.Dict[FeatureLabel, bool], verbose: bool = False
    ) -> bool:
        """
        Checks if a configuration is feasible, i.e., satisfies all rules and matches the structure.
        """
        if not isinstance(conf, dict):
            msg = "Configuration must be a dictionary"
            raise ValueError(msg)
        if not self.is_fully_defined(conf, verbose=verbose):
            if verbose:
                print("Not fully defined")
            return False
        if not all(rule.evaluate(conf) for rule in self.rules):
            if verbose:
                print("Does not satisfy rules")
            return False
        if self.structure and not self.structure.is_feasible(conf):
            if verbose:
                print("Does not match structure")
            return False
        return True
