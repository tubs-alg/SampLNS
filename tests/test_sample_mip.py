import itertools
import logging

from samplns.instances import (
    AndFeature,
    ConcreteFeature,
    FeatureLiteral,
    Instance,
    OrFeature,
)
from samplns.lns.model import TupleIndex, VectorizedEdgeModel
from samplns.preprocessor import Preprocessor
from samplns.utils import Timer

logger = logging.getLogger("SampLNS")


def test_sample_mip():
    concrete_features = ["1", "2", "3", "4"]
    tree = AndFeature(
        FeatureLiteral("and1"),
        [
            OrFeature(
                FeatureLiteral("Or1"),
                [
                    ConcreteFeature(FeatureLiteral("1"), mandatory=False),
                    ConcreteFeature(FeatureLiteral("2"), mandatory=False),
                ],
                mandatory=True,
                logger=logger,
            ),
            OrFeature(
                FeatureLiteral("Or2"),
                [
                    ConcreteFeature(FeatureLiteral("3"), mandatory=False),
                    ConcreteFeature(FeatureLiteral("4"), mandatory=False),
                ],
                mandatory=True,
                logger=logger,
            ),
        ],
        mandatory=True,
        logger=logger,
    )
    instance = Instance(concrete_features, structure=tree, rules=[])
    sample = []
    for conf in itertools.product([True, False], repeat=4):
        if (conf[0] or conf[1]) and (conf[2] or conf[3]):
            sample.append({concrete_features[i]: conf[i] for i in range(4)})
    assert len(sample) == 9
    index_instance = Preprocessor().preprocess(instance)
    mip = VectorizedEdgeModel(index_instance, 16, Timer(600), logger=logger)
    covered_tuples = set()
    print("Greedy solution")
    coverages = {}
    for conf in sample:
        conf_ = index_instance.to_mapped_universe(conf)
        is_needed = False
        for f0, f1 in itertools.combinations(conf_.keys(), 2):
            ti = TupleIndex(f0, conf_[f0], f1, conf_[f1])
            coverages[ti] = coverages.get(ti, 0) + 1
            if ti not in covered_tuples:
                is_needed = True
            covered_tuples.add(ti)
            mip.enforce_tuple(ti)
        if is_needed:
            conf_ = index_instance.to_original_universe(conf)
            for f in concrete_features:
                print(conf_[f], end="   ")
            print()

    for _i in range(9):
        for conf in sample:
            remove = True
            conf_ = index_instance.to_mapped_universe(conf)
            for f0, f1 in itertools.combinations(conf_.keys(), 2):
                ti = TupleIndex(f0, conf_[f0], f1, conf_[f1])
                if coverages[ti] <= 1:
                    remove = False
            if remove:
                sample.remove(conf)
                for f0, f1 in itertools.combinations(conf_.keys(), 2):
                    ti = TupleIndex(f0, conf_[f0], f1, conf_[f1])
                    coverages[ti] -= 1
                break
    print(f"{len(sample)} samples in greedy")
    for conf in sample:
        print(conf)

    subsample = [sample[1], sample[2], sample[5]]
    subcoverages = {}
    for conf in subsample:
        conf_ = index_instance.to_mapped_universe(conf)
        for f0, f1 in itertools.combinations(conf_.keys(), 2):
            ti = TupleIndex(f0, conf_[f0], f1, conf_[f1])
            subcoverages[ti] = coverages.get(ti, 0) + 1
    print(f"Subcov has {len(subcoverages.keys())} coverages")
    for cov in coverages:
        if cov not in subcoverages:
            print(
                "Missing",
                index_instance.to_original_universe(
                    {cov.i: cov.i_pos, cov.j: cov.j_pos}
                ),
            )

    print(len(covered_tuples), covered_tuples)

    mip.optimize()
    for conf in mip.get_solution():
        conf_ = index_instance.to_original_universe(conf)
        for f in concrete_features:
            print(conf_[f], end="   ")
        print()
    # print([index_instance.to_original_universe(conf) for conf in mip.get_solution()])
