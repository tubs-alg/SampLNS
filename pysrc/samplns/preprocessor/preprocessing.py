from ..instances import Instance
from .cnf import to_cnf
from .eq_substitution import substitute_equivalent
from .index_instance import IndexInstance
from .int_labels import substitute_with_int_labels


class Preprocessor:
    """
    The preprocessor simplifies an instance and allows to map the solutions
    back to the original universe at the end.
    """

    def __init__(self, cnf: bool = True):
        self.cnf = cnf
        pass

    def preprocess(self, instance: Instance) -> IndexInstance:
        instance_, mapping = substitute_equivalent(instance, None)
        if self.cnf:
            instance_ = to_cnf(instance_)
        return substitute_with_int_labels(instance_, mapping)
