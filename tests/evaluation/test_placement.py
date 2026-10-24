import unittest
from typing import Mapping

from graphrecords import Value

from medrecords.evaluation.placement import (
    AtRoot,
    GroupPlacement,
    InGroup,
    KeyedGroupPlacement,
    Placement,
    _Shape,
    _Step,
)


def create_step(name: Value = "lorem", shape: _Shape = _Shape.Plain) -> _Step:
    return _Step(name, shape)


def create_placement(step: _Step) -> Placement[InGroup, int]:
    return Placement((step,))


class TestStep(unittest.TestCase):
    def test_init(self) -> None:
        step = create_step("ipsum", _Shape.Each)

        assert step._name == "ipsum"
        assert step._shape is _Shape.Each

    def test_repr(self) -> None:
        assert repr(create_step("ipsum")) == "'ipsum'"
        assert repr(create_step(3)) == "3"


class TestPlacement(unittest.TestCase):
    def test_init(self) -> None:
        step = create_step()

        placement = Placement((step,))

        assert placement._steps == (step,)

    def test_eq(self) -> None:
        step = create_step()

        assert create_placement(step) == create_placement(step)
        assert create_placement(step) != create_placement(create_step())
        assert create_placement(step) != "lorem"

    def test_hash(self) -> None:
        step = create_step()

        assert hash(create_placement(step)) == hash(create_placement(step))
        assert len({create_placement(step), create_placement(step)}) == 1

    def test_repr(self) -> None:
        outer = create_step("ipsum", _Shape.Across)
        inner = create_step("dolor")

        assert repr(Placement((outer, inner))) == ("Placement('ipsum', 'dolor')")


class TestGroupPlacement(unittest.TestCase):
    def test_getitem(self) -> None:
        group = create_step("ipsum")
        inner = create_placement(create_step())

        rooted: Placement[AtRoot, int] = GroupPlacement(group)[inner]

        assert rooted == Placement((group, *inner._steps))

    def test_repr(self) -> None:
        assert repr(GroupPlacement(create_step("ipsum"))) == "GroupPlacement('ipsum')"


class TestKeyedGroupPlacement(unittest.TestCase):
    def test_getitem(self) -> None:
        group = create_step("ipsum", _Shape.Each)
        inner = create_placement(create_step())

        keyed: Placement[AtRoot, Mapping[Value, int]] = KeyedGroupPlacement(group)[
            inner
        ]

        assert keyed == Placement((group, *inner._steps))

    def test_repr(self) -> None:
        assert repr(KeyedGroupPlacement(create_step("ipsum", _Shape.Across))) == (
            "KeyedGroupPlacement('ipsum')"
        )


if __name__ == "__main__":
    unittest.main()
