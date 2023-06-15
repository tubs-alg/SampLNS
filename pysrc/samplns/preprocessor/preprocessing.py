import logging

from ..instances import Instance
from .cnf import to_cnf
from .eq_substitution import substitute_equivalent
from .index_instance import IndexInstance
from .int_labels import substitute_with_int_labels

_logger = logging.getLogger("SampLNS")


class Preprocessor:
    """
    The preprocessor simplifies an instance and allows to map the solutions
    back to the original universe at the end.
    """

    def __init__(self, cnf: bool = True, logger: logging.Logger = _logger):
        self.cnf = cnf
        self.logger = logger

    def preprocess(self, instance: Instance) -> IndexInstance:
        self.logger.info("Preprocessing instance (%s).", str(instance))
        instance_, mapping = substitute_equivalent(instance, None)
        if self.cnf:
            instance_ = to_cnf(instance_, logger=self.logger)
        preprocessed_instance = substitute_with_int_labels(instance_, mapping)
        self.logger.info("Finnished preprocessing (%s).", str(preprocessed_instance))
        return preprocessed_instance
