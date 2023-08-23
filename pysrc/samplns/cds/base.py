import abc
import math
import typing

Tuples = typing.Iterable[typing.Tuple[typing.Tuple[int, bool], typing.Tuple[int, bool]]]
Samples = typing.List[typing.Dict[int, bool]]


class CdsAlgorithm(abc.ABC):
    @abc.abstractmethod
    def compute_independent_set(
        self, tuples: typing.Optional[Tuples], timelimit: float = math.inf, ub=math.inf
    ) -> Tuples:
        """
        None refers to all.
        Default timelimit is "unlimited" (as indicated by math.inf).
        Can be passed a known upper bound.
        """
        raise NotImplementedError()

    def get_lb(self) -> int:
        return len(list(self.compute_independent_set(None)))

    def __call__(self, *args, **kwargs):
        pass

    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError()
