import typing
import unittest
from typing import Dict, Tuple, List
from ..instances import FeatureLabel


class UniverseMapping:
    """
    This class provides a mapping to convert a solution of a transformed
    universe to the original universe
    """

    def __init__(self, chain: typing.Optional["UniverseMapping"] = None):
        self._origins: Dict[
            FeatureLabel, Tuple[List[FeatureLabel], List[FeatureLabel]]
        ] = dict()
        self._chain = chain

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

    def to_mapped_universe(self, assignment: typing.Dict[FeatureLabel, bool]):
        assignment_ = dict(assignment)
        mapped_assignment = dict()
        if self._chain:
            assignment_.update(self._chain.to_mapped_universe(assignment))
        for var, val in assignment_.items():
            for var_ in self._origins:
                if var in self._origins[var_][0]:
                    mapped_assignment[var_] = val
                elif var in self._origins[var_][1]:
                    mapped_assignment[var_] = not val

        return mapped_assignment

    def to_origin_universe(
        self, assignment: typing.Dict[FeatureLabel, bool]
    ) -> typing.Dict[FeatureLabel, bool]:
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
            return self._chain.to_origin_universe(origin_assignment)
        return origin_assignment


class MappingTest(unittest.TestCase):
    def test_trivial(self):
        um = UniverseMapping()
        um.map("old_a", "new_b")
        self.assertEqual(um.to_origin_universe({"new_b": True}), {"old_a": True})

    def test_2(self):
        um = UniverseMapping()
        um.map("old_a", "new_a")
        um.map("old_b", "new_a")
        self.assertEqual(
            um.to_origin_universe({"new_a": True}), {"old_a": True, "old_b": True}
        )

    def test_3(self):
        um = UniverseMapping()
        um.map("old_a", "new_a")
        um.map("old_b", "new_a", inverse=True)
        self.assertEqual(
            um.to_origin_universe({"new_a": True}), {"old_a": True, "old_b": False}
        )
