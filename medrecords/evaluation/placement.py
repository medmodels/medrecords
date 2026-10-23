"""Placements: typed handles to what the place_* methods put into a group."""

from __future__ import annotations

from enum import Enum, auto
from typing import (
    TYPE_CHECKING,
    Generic,
    Mapping,
    Tuple,
    TypeAlias,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from graphrecords import Value


class NoResultError(LookupError):
    """Raised when a placement has nothing to read: not in the findings, or failed."""


class _Unkeyed:
    """Marks findings that are not read under one key of a group run across keys."""


_UNKEYED = _Unkeyed()


class AtRoot:
    """The scope of a placement made on an evaluation, read by its conclusions."""


class InGroup:
    """The scope of a placement made on a group, read by the group's conclusions."""


ScopeType = TypeVar("ScopeType")

ReadType = TypeVar("ReadType", covariant=True)

ValueType = TypeVar("ValueType")


class _Shape(Enum):
    """Enumeration of how a member's entries are laid out below its name."""

    Plain = auto()
    Each = auto()
    Across = auto()


class _Step:
    """One member on the way to a placement: its name and how it fans out.

    A step is created when the member is placed and stored by the member, so
    two placements refer to the same member only if they hold the same step.
    """

    _name: Value
    _shape: _Shape

    def __init__(self, name: Value, shape: _Shape) -> None:
        """Initializes a step.

        Args:
            name (Value): The name the member is reported under.
            shape (_Shape): How the member's entries are laid out below it.
        """
        self._name = name
        self._shape = shape

    def __repr__(self) -> str:
        """Returns the string representation of the step.

        Returns:
            str: The name of the member.
        """
        return repr(self._name)


class Placement(Generic[ScopeType, ReadType]):
    """A handle to one placed analytic or conclusion, read as ReadType.

    The scope says where the placement can be read. A placement made on a
    group is read by that group's conclusions. A placement made on an
    evaluation is read by the evaluation's conclusions, and so is a group's
    placement converted through the group's handle. The read type is what the
    placement yields, wrapped in one mapping by key for every group placed over
    each key or across keys above it.
    """

    _steps: Tuple[_Step, ...]

    def __init__(self, steps: Tuple[_Step, ...]) -> None:
        """Initializes a placement.

        Args:
            steps (Tuple[_Step, ...]): The members from the group the placement
                is read in down to the one it refers to.
        """
        self._steps = steps

    def __eq__(self, other: object) -> bool:
        """Compares the placement with another one by the members it refers to.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both refer to the same members, otherwise False.
        """
        if not isinstance(other, Placement):
            return NotImplemented

        return self._steps == other._steps

    def __hash__(self) -> int:
        """Hashes the placement by the members it refers to.

        Returns:
            int: The hash.
        """
        return hash(self._steps)

    def __repr__(self) -> str:
        """Returns the string representation of the placement.

        Returns:
            str: The names from the group the placement is read in down to the
                member it refers to.
        """
        names = ", ".join(repr(step) for step in self._steps)
        return f"Placement({names})"


class GroupPlacement(Generic[ScopeType]):
    """A handle to a group placed over the same or over derived inputs.

    Indexing it with a placement made inside the group gives that placement
    as read from where the group was placed.
    """

    _step: _Step

    def __init__(self, step: _Step) -> None:
        """Initializes a group placement.

        Args:
            step (_Step): The member holding the group.
        """
        self._step = step

    def __getitem__(
        self, placement: Placement[InGroup, ValueType]
    ) -> Placement[ScopeType, ValueType]:
        """Converts a placement made inside the group.

        Args:
            placement (Placement[InGroup, ValueType]): A placement returned by
                one of the group's place_* methods.

        Returns:
            Placement[ScopeType, ValueType]: The same placement, read from
                where the group was placed.
        """
        return Placement((self._step, *placement._steps))

    def __repr__(self) -> str:
        """Returns the string representation of the group placement.

        Returns:
            str: The name of the group.
        """
        return f"{type(self).__name__}({self._step!r})"


class KeyedGroupPlacement(Generic[ScopeType]):
    """A handle to a group placed over each key or across keys.

    Indexing it with a placement made inside the group gives that placement
    with one value per key.
    """

    _step: _Step

    def __init__(self, step: _Step) -> None:
        """Initializes a keyed group placement.

        Args:
            step (_Step): The member holding the group.
        """
        self._step = step

    def __getitem__(
        self, placement: Placement[InGroup, ValueType]
    ) -> Placement[ScopeType, Mapping[Value, ValueType]]:
        """Converts a placement made inside the group to one value per key.

        Args:
            placement (Placement[InGroup, ValueType]): A placement returned by
                one of the group's place_* methods.

        Returns:
            Placement[ScopeType, Mapping[Value, ValueType]]: The same
                placement, read from where the group was placed, by key.
        """
        return Placement((self._step, *placement._steps))

    def __repr__(self) -> str:
        """Returns the string representation of the keyed group placement.

        Returns:
            str: The name of the group.
        """
        return f"{type(self).__name__}({self._step!r})"


#: A type alias for the placement of a group of any kind.
AnyGroupPlacement: TypeAlias = Union[
    GroupPlacement[ScopeType], KeyedGroupPlacement[ScopeType]
]
