import typing
import unittest


class EquivalenceClasses:
    """
    Saves which features are equivalent and provides unified substitutions
    for the elements of equivalence classes.
    """

    def __init__(self):
        self._class = dict()
        self._class_counter = 1  # we use negative to indicate inverse.

    def _merge(self, x: int, y: int):
        if x == -y:
            raise ValueError("Trying to merge inverse!")
        for key, val in self._class.items():
            if val == y:
                self._class[key] = x
            if val == -y:
                self._class[key] = -x

    def mark_equivalent(self, a: str, b: str, inverse: bool = False):
        """
        Mark two labels as equivalent (possibly inverse, i.e., a == not b).
        """
        a, b = min(a, b), max(a, b)
        if a in self._class and b not in self._class:
            if inverse:
                self._class[b] = -self._class[a]
            else:
                self._class[b] = self._class[a]
        elif b in self._class and a not in self._class:
            if inverse:
                self._class[a] = -self._class[b]
            else:
                self._class[a] = self._class[b]
        elif a not in self._class and b not in self._class:
            self._class_counter += 1
            self._class[a] = self._class_counter
            if inverse:
                self._class[b] = -self._class_counter
            else:
                self._class[b] = self._class_counter
        else:
            if inverse:
                self._merge(self._class[a], -self._class[b])
            else:
                self._merge(self._class[a], self._class[b])

    def get_substitutions(
        self,
    ) -> typing.Tuple[typing.Dict[str, str], typing.Dict[str, str]]:
        """
        Returns the equality substitutions and the inverse substitutions.
        """
        direct_subs = dict()
        inverse_subs = dict()
        subst = dict()
        for key, val in self._class.items():
            if abs(val) not in subst:
                subst[abs(val)] = f"SUB[{key}]"
            if val < 0:
                inverse_subs[key] = subst[abs(val)]
            else:
                direct_subs[key] = subst[abs(val)]
        return direct_subs, inverse_subs


class EquTest(unittest.TestCase):
    def test_trivial(self):
        ec = EquivalenceClasses()
        self.assertEqual(ec.get_substitutions(), (dict(), dict()))

    def test_two(self):
        ec = EquivalenceClasses()
        ec.mark_equivalent("a", "b")
        self.assertEqual(
            ec.get_substitutions(), ({"a": "SUB[a]", "b": "SUB[a]"}, dict())
        )

    def test_four(self):
        ec = EquivalenceClasses()
        ec.mark_equivalent("a", "b")
        ec.mark_equivalent("c", "d")
        self.assertEqual(
            ec.get_substitutions(),
            ({"a": "SUB[a]", "b": "SUB[a]", "c": "SUB[c]", "d": "SUB[c]"}, dict()),
        )

    def test_bad(self):
        ec = EquivalenceClasses()
        ec.mark_equivalent("a", "b")
        with self.assertRaises(ValueError):
            ec.mark_equivalent("a", "b", inverse=True)

    def test_two_inv(self):
        ec = EquivalenceClasses()
        ec.mark_equivalent("a", "b", True)
        self.assertEqual(ec.get_substitutions(), ({"a": "SUB[a]"}, {"b": "SUB[a]"}))
