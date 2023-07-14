import typing

from ..instances import FeatureLabel, FeatureNode, SatNode
from .universe_mapping import UniverseMapping


class IndexInstance:
    """
    The index instance is an instance where all labels are integers.
    For further simplification, the concrete features will be labeled 0 to n.
    This allows to directly use these indices for efficient querying.
    """

    def __init__(
        self,
        structure: typing.Optional[FeatureNode],
        rules: typing.List[SatNode],
        n_concrete: int,
        n_all: int,
        to_original_universe: UniverseMapping,
    ):
        self.structure = structure
        self.rules = rules
        self.n_concrete = n_concrete
        self.n_all = n_all
        self._to_original_universe = to_original_universe
        self.instance_name = None

    def to_json_data(self):
        """
        Unfortunately, the parser is not deterministic.
        The integer labels of features usually change from run to run.
        For certain purposes, such as scripts that do not want to deal
        with string labels and the mapping, it thus makes sense
        to be able to export IndexInstance objects to a JSON format
        that can be reimported, keeping the mapping to string labels
        and the integer indices intact.
        """
        return {
            "name": self.instance_name,
            "n_all": self.n_all,
            "n_concrete": self.n_concrete,
            "to_original_universe": self._to_original_universe.to_json_data(),
            "rules": [r.to_json_data() for r in self.rules],
            "structure": self.structure.to_json_data() if self.structure else None,
        }

    @staticmethod
    def from_json_data(json_data):
        umap = UniverseMapping()
        umap.from_json_data(json_data["to_original_universe"])
        result = IndexInstance(
            structure=FeatureNode.from_json_data(json_data.get("structure", None)),
            rules=[SatNode.from_json_data(j) for j in json_data["rules"]],
            n_concrete=json_data["n_concrete"],
            n_all=json_data["n_all"],
            to_original_universe=umap,
        )
        result.instance_name = json_data["name"]
        return result

    def to_original_universe(
        self, assignment: typing.Dict[int, bool]
    ) -> typing.Dict[FeatureLabel, bool]:
        return self._to_original_universe.to_origin_universe(assignment)

    def to_mapped_universe(
        self, assignment: typing.Dict[typing.Union[int, str], bool], strict: bool = True
    ) -> typing.Dict[FeatureLabel, bool]:
        conf = self._to_original_universe.to_mapped_universe(assignment)
        if strict and not self.is_fully_defined(conf):
            msg = "Configuration does not match the concrete features."
            raise ValueError(msg)
        return conf

    def is_fully_defined(
        self, conf: typing.Dict[int, bool], exact: bool = False
    ) -> bool:
        if any(i not in conf for i in range(self.n_concrete)):
            return False
        return not exact or len(conf.keys()) == self.n_concrete

    def __repr__(self):
        if self.instance_name:
            return f"Instance[{self.instance_name}]<{self.n_concrete} features, {len(self.rules)} rules>"
        else:
            return f"Instance[UNNAMED]<{self.n_concrete} features, {len(self.rules)} rules>"
