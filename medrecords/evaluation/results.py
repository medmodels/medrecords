"""Readers for what the query engine hands back.

Every ``evaluate`` hands back either a value or a ``QueryError``, and a value is
any of the kinds a MedRecord holds. ``read`` raises the failure and, given a
kind, checks the value against it; ``read_each`` and ``read_pairs`` do the same
for a series and for the pairs ``ungroup_keyed`` yields.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple, Type, TypeVar, Union, overload

from graphrecords import QueryError
from graphrecords.types import Value

ValueKindType = TypeVar("ValueKindType", str, int, float, bool, datetime, timedelta)

ItemType = TypeVar("ItemType", bound=Value)

KeyType = TypeVar("KeyType")


@overload
def read(result: Union[Value, QueryError], /) -> Value: ...


@overload
def read(
    result: Union[Value, QueryError], kind: Type[ValueKindType], /
) -> ValueKindType: ...


def read(
    result: Union[Value, QueryError],
    kind: Optional[Type[ValueKindType]] = None,
    /,
) -> Union[Value, ValueKindType]:
    """Reads an evaluated result, as a kind if one is given.

    A failure the query engine handed back is raised. An integer is read as
    a number; a boolean is neither an integer nor a number.

    Args:
        result (Union[Value, QueryError]): The evaluated result.
        kind (Optional[Type[ValueKindType]]): The kind the value must be, or
            None to read it as it is. Defaults to None.

    Returns:
        Union[Value, ValueKindType]: The value, of that kind if one was given.

    Raises:
        TypeError: If the value is not of that kind.
    """
    if isinstance(result, QueryError):
        raise result

    if kind is None:
        return result

    if kind is float and isinstance(result, int) and not isinstance(result, bool):
        return float(result)

    if isinstance(result, bool) and kind is not bool:
        msg = f"expected {kind.__name__}, got {result!r}"
        raise TypeError(msg)

    if not isinstance(result, kind):
        msg = f"expected {kind.__name__}, got {result!r}"
        raise TypeError(msg)

    return result


@overload
def read_each(results: Iterable[Union[ItemType, QueryError]], /) -> List[ItemType]: ...


@overload
def read_each(
    results: Iterable[Union[ItemType, QueryError]], kind: Type[ValueKindType], /
) -> List[ValueKindType]: ...


def read_each(
    results: Iterable[Union[ItemType, QueryError]],
    kind: Optional[Type[ValueKindType]] = None,
    /,
) -> Union[List[ItemType], List[ValueKindType]]:
    """Reads every item of an evaluated series, as a kind if one is given.

    A failure the query engine handed back in place of an item is raised as it is.

    Args:
        results (Iterable[Union[ItemType, QueryError]]): The evaluated items.
        kind (Optional[Type[ValueKindType]]): The kind every value must be, or
            None to read the items as they are. Defaults to None.

    Returns:
        Union[List[ItemType], List[ValueKindType]]: The items, in order.
    """
    if kind is not None:
        return [read(result, kind) for result in results]

    items: List[ItemType] = []

    for result in results:
        if isinstance(result, QueryError):
            raise result

        items.append(result)

    return items


@overload
def read_pairs(
    results: Iterable[Tuple[KeyType, Union[ItemType, QueryError]]], /
) -> List[Tuple[KeyType, ItemType]]: ...


@overload
def read_pairs(
    results: Iterable[Tuple[KeyType, Union[ItemType, QueryError]]],
    kind: Type[ValueKindType],
    /,
) -> List[Tuple[KeyType, ValueKindType]]: ...


def read_pairs(
    results: Iterable[Tuple[KeyType, Union[ItemType, QueryError]]],
    kind: Optional[Type[ValueKindType]] = None,
    /,
) -> Union[List[Tuple[KeyType, ItemType]], List[Tuple[KeyType, ValueKindType]]]:
    """Reads every key and value of an evaluated keyed series.

    A failure the query engine handed back in place of a value is raised as it is.

    Args:
        results (Iterable[Tuple[KeyType, Union[ItemType, QueryError]]]): The
            evaluated pairs, as ungroup_keyed yields them.
        kind (Optional[Type[ValueKindType]]): The kind every value must be, or
            None to read the values as they are. Defaults to None.

    Returns:
        Union[List[Tuple[KeyType, ItemType]], List[Tuple[KeyType, ValueKindType]]]:
            The pairs, in order.
    """
    if kind is not None:
        return [(key, read(result, kind)) for key, result in results]

    pairs: List[Tuple[KeyType, ItemType]] = []

    for key, result in results:
        if isinstance(result, QueryError):
            raise result

        pairs.append((key, result))

    return pairs
