import typing
import unittest
import logging
from typing import Dict, Tuple, List
from ..instances import FeatureLabel


class UniverseMapping:
    """
    This class provides a mapping to convert a solution of a transformed
    universe to the original universe
    """

    def __init__(
        self,
        chain: typing.Optional["UniverseMapping"] = None,
        parent_logger: typing.Optional[logging.Logger] = None,
    ):
        self._origins: Dict[
            FeatureLabel, Tuple[List[FeatureLabel], List[FeatureLabel]]
        ] = dict()
        self._targets: Dict[FeatureLabel, Tuple[bool, FeatureLabel]] = dict()
        self._chain = chain
        if parent_logger is not None:
            self._logger = parent_logger.getChild(self.__class__.__name__)
        else:
            self._logger = logging.getLogger(self.__class__.__name__)

    def to_json_data(self):
        c = None if not self._chain else self._chain.to_json_data()
        return {
            "chain": c,
            "origins": [
                {"feature": fl, "l1": o[0], "l2": o[1]}
                for fl, o in self._origins.items()
            ],
        }

    def from_json_data(self, json_data):
        if json_data["chain"] is not None:
            self._chain = UniverseMapping()
            self._chain.from_json_data(json_data["chain"])
        else:
            self._chain = None
        self._origins = {d["feature"]: (d["l1"], d["l2"]) for d in json_data["origins"]}

    def map(
        self,
        origin_element: FeatureLabel,
        target_element: FeatureLabel,
        inverse: bool = False,
    ):
        if target_element not in self._origins:
            self._origins[target_element] = ([], [])
        if inverse:
            self._origins[target_element][1].append(origin_element)
        else:
            self._origins[target_element][0].append(origin_element)
        assert (
            origin_element not in self._targets
        ), "Every origin element can only be mapped once."
        self._targets[origin_element] = (inverse, target_element)

    def to_mapped_universe(self, assignment: typing.Dict[FeatureLabel, bool]):
        self._logger.debug("Starting to translate assignment to mapped universe.")
        assignment_ = dict(assignment)
        mapped_assignment = dict()
        if self._chain:
            assignment_.update(self._chain.to_mapped_universe(assignment))
        for var, val in assignment_.items():
            if var not in self._targets:
                continue  # Auxiliary variables are not mapped
            inversed, var_ = self._targets[var]
            mapped_assignment[var_] = val if not inversed else not val
        self._logger.debug("Finished translating assignment to mapped universe.")
        return mapped_assignment

    def to_origin_universe(
        self, assignment: typing.Dict[FeatureLabel, bool]
    ) -> typing.Dict[FeatureLabel, bool]:
        self._logger.debug("Starting to translate assignment to origin universe.")
        origin_assignment = dict()
        for var, val in assignment.items():
            if var in self._origins:
                for var_ in self._origins[var][0]:
                    origin_assignment[var_] = val
                for var_ in self._origins[var][1]:
                    origin_assignment[var_] = not val
            else:
                origin_assignment[var] = val
        if self._chain:
            origin_assignment = self._chain.to_origin_universe(origin_assignment)
        self._logger.debug("Finished translating assignment to origin universe.")
        return origin_assignment
