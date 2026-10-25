"""The findings a conclusion reads: results so far, looked up through placements."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    cast,
)

from medrecords.evaluation.entry import (
    AnalyticEntry,
    Failure,
    GroupEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
)
from medrecords.evaluation.placement import (
    AnyGroupPlacement,
    NoResultError,
    Placement,
    ScopeType,
    ValueType,
    _Shape,
    _Unkeyed,
)

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation.analytic import EntryPath, ReportValue
    from medrecords.evaluation.entry import Entry
    from medrecords.evaluation.group import EvaluationGroup
    from medrecords.evaluation.placement import _Step

KindType = TypeVar("KindType")

#: A type alias for what a placement reads: a result, nested in one mapping by
#: key for every keyed group above it.
_Found: TypeAlias = Union["ReportValue", Mapping["Value", "_Found"]]

#: A type alias for found values with the keys of the keyed groups above them,
#: outermost group first.
_KeyedValues: TypeAlias = List[Tuple[Tuple["Value", ...], _Found]]


class Findings(Generic[ScopeType]):
    """What a group found, read through placements or scanned by kind.

    A conclusion receives the findings of the group it is placed in once the
    group's analytics and nested groups are computed; a report offers the
    findings of its root. Inside a group run across keys, a conclusion's
    findings are read under its own key.
    """

    _entries: Sequence[Entry]
    _owner: Optional[EvaluationGroup[Any]]
    _key: Union[Value, _Unkeyed]
    _path: EntryPath

    def __init__(
        self,
        entries: Sequence[Entry],
        owner: Optional[EvaluationGroup[Any]],
        key: Union[Value, _Unkeyed],
        path: EntryPath,
    ) -> None:
        """Initializes findings.

        Args:
            entries (Sequence[Entry]): The entries of the group, in definition
                order.
            owner (Optional[EvaluationGroup[Any]]): The group whose placements
                the findings answer to, or None for a report.
            key (Union[Value, _Unkeyed]): The key the findings are read under,
                or unkeyed.
            path (EntryPath): The names from the report root to the group the
                findings belong to; empty for the root.
        """
        self._entries = entries
        self._owner = owner
        self._key = key
        self._path = path

    def __getitem__(self, placement: Placement[ScopeType, ValueType]) -> ValueType:
        """Reads what a placement refers to.

        Args:
            placement (Placement[ScopeType, ValueType]): The placement to read.

        Returns:
            ValueType: The value; one per key for every keyed group above it,
                outermost group first.

        Raises:
            NoResultError: If the placement was not made in this group, or what it
                refers to failed or was never computed.
        """
        if self._owner is not None and not self._owner._owns(placement._steps):
            msg = f"{placement!r} was not placed in this group"
            raise NoResultError(msg)

        keyed_values = self._keyed_values(self._entries, placement._steps, ())

        return cast("ValueType", self._nested(keyed_values))

    def path(self, placement: Placement[ScopeType, object], *keys: Value) -> EntryPath:
        """Names the entry a placement refers to by its path from the report root.

        Every group on the way that holds one group per key takes the next of
        the keys, outermost first. A group placed across keys holds no entry
        per key, so its keys are not part of a path.

        Args:
            placement (Placement[ScopeType, object]): The placement, made in or
                converted to the findings' group.
            *keys (Value): One key for every group on the way that holds one
                group per key.

        Returns:
            EntryPath: The names of the groups on the way and of the entry.

        Raises:
            NoResultError: If the placement was not made in this group.
            ValueError: If the keys are not one per group on the way that holds
                one group per key.
        """
        if self._owner is not None and not self._owner._owns(placement._steps):
            msg = f"{placement!r} was not placed in this group"
            raise NoResultError(msg)

        remaining = list(keys)
        entries = self._entries
        here: EntryPath = ()

        for step in placement._steps[:-1]:
            entry = self._entry_named(entries, step._name, here)
            here = (*here, step._name)
            entries = self._children(entry, here)

            if self._fans_out(step, entry):
                if not remaining:
                    msg = f"expected a key for {self._path_text(here)}"
                    raise ValueError(msg)

                key = remaining.pop(0)
                child = self._entry_named(entries, key, here)
                here = (*here, key)
                entries = self._children(child, here)

        if remaining:
            msg = f"expected {len(keys) - len(remaining)} keys, got {len(keys)}"
            raise ValueError(msg)

        return (*self._path, *here, placement._steps[-1]._name)

    def each(
        self,
        kind: Type[KindType],
        within: Optional[AnyGroupPlacement[ScopeType]] = None,
    ) -> Iterator[Tuple[EntryPath, KindType]]:
        """Yields every result of one kind, with its path from the report root.

        A result under a key has the key at the end of its path. Results are
        matched by class, so an integer is not a float and a failure is a
        Failure.

        Args:
            kind (Type[KindType]): The class of the results to yield.
            within (Optional[AnyGroupPlacement[ScopeType]]): The group to scan,
                or None for everything. Defaults to None.

        Yields:
            Tuple[EntryPath, KindType]: The path and the result.
        """
        for path, entries in self._scoped(within):
            for result_path, result in self._results(entries, path):
                if type(result) is kind:
                    yield result_path, result

    def failures(
        self, within: Optional[AnyGroupPlacement[ScopeType]] = None
    ) -> Iterator[Tuple[EntryPath, Failure]]:
        """Yields every failure, of an analytic, a conclusion or a derivation.

        Paths lead from the report root.

        Args:
            within (Optional[AnyGroupPlacement[ScopeType]]): The group to scan,
                or None for everything. Defaults to None.

        Yields:
            Tuple[EntryPath, Failure]: The path and the failure.
        """
        for path, entries in self._scoped(within):
            yield from self._failures(entries, path)

    def _scoped(
        self, within: Optional[AnyGroupPlacement[ScopeType]]
    ) -> List[Tuple[EntryPath, Sequence[Entry]]]:
        """Finds the entries a scan ranges over.

        Args:
            within (Optional[AnyGroupPlacement[ScopeType]]): The group to scan,
                or None for everything.

        Returns:
            List[Tuple[EntryPath, Sequence[Entry]]]: The entries of the group
                at every place it was computed, with their paths from the
                report root.

        Raises:
            NoResultError: If the group was not placed in this group.
        """
        if within is None:
            return [(self._path, self._entries)]

        if self._owner is not None and not self._owner._owns((within._step,)):
            msg = f"{within!r} was not placed in this group"
            raise NoResultError(msg)

        entry = self._entry_named(self._entries, within._step._name, ())
        path: EntryPath = (*self._path, within._step._name)

        if not self._fans_out(within._step, entry):
            return [(path, self._children(entry, (within._step._name,)))]

        return [
            ((*path, child.name), child.entries)
            for child in self._children(entry, path)
            if isinstance(child, (GroupEntry, KeyedGroupEntry))
        ]

    def _results(
        self, entries: Sequence[Entry], path: EntryPath
    ) -> Iterator[Tuple[EntryPath, Union[ReportValue, Failure]]]:
        """Yields the result of every analytic below the entries, depth first.

        Args:
            entries (Sequence[Entry]): The entries to walk.
            path (EntryPath): The names from the report root down to the
                entries.

        Yields:
            Tuple[EntryPath, Union[ReportValue, Failure]]: The path and the
                result; a result under a key has the key at the end.
        """
        for entry in entries:
            here = (*path, entry.name)

            if isinstance(entry, AnalyticEntry):
                yield here, entry.result
            elif isinstance(entry, KeyedAnalyticEntry):
                yield from self._keyed_results(entry, here)
            else:
                yield from self._results(entry.entries, here)

    def _keyed_results(
        self, entry: KeyedAnalyticEntry, path: EntryPath
    ) -> Iterator[Tuple[EntryPath, Union[ReportValue, Failure]]]:
        for keyed in entry.results:
            if self._in_scope(keyed.key):
                yield self._keyed_path(path, keyed.key), keyed.result

    def _failures(
        self, entries: Sequence[Entry], path: EntryPath
    ) -> Iterator[Tuple[EntryPath, Failure]]:
        """Yields every failure below the entries, derivations first, depth first.

        Args:
            entries (Sequence[Entry]): The entries to walk.
            path (EntryPath): The names from the report root down to the
                entries.

        Yields:
            Tuple[EntryPath, Failure]: The path and the failure; a failure
                under a key has the key at the end.
        """
        for entry in entries:
            here = (*path, entry.name)

            if isinstance(entry, GroupEntry):
                derivation = entry.derivation

                if derivation is not None and derivation.failure is not None:
                    yield here, derivation.failure

                yield from self._failures(entry.entries, here)
            elif isinstance(entry, KeyedGroupEntry):
                for key, derivation in entry.derivations.items():
                    if derivation.failure is None or not self._in_scope(key):
                        continue

                    yield self._keyed_path(here, key), derivation.failure

                yield from self._failures(entry.entries, here)
            else:
                for result_path, result in self._results([entry], path):
                    if isinstance(result, Failure):
                        yield result_path, result

    def _keyed_values(
        self,
        entries: Sequence[Entry],
        steps: Tuple[_Step, ...],
        path: EntryPath,
    ) -> _KeyedValues:
        """Follows steps through entries and collects what sits at their end.

        A group placed over each key holds one group per key, so the steps
        continue in every one of them. A group placed across keys holds keyed
        entries, so the steps continue once and the keys appear at the end;
        they are moved to the front, where the group's placement sits.

        Args:
            entries (Sequence[Entry]): The entries the first step is in.
            steps (Tuple[_Step, ...]): The steps left to follow.
            path (EntryPath): The names from the findings down to the entries.

        Returns:
            _KeyedValues: Every value at the end of the steps, with the keys of the
                keyed groups on the way, outermost first.
        """
        step, rest = steps[0], steps[1:]
        entry = self._entry_named(entries, step._name, path)
        here = (*path, step._name)

        if not rest:
            return self._keyed_values_at_end(entry, here)

        self._derived(entry, here)
        children = self._children(entry, here)

        if self._fans_out(step, entry):
            return [
                ((child.name, *keys), value)
                for child in children
                for keys, value in self._keyed_values(
                    self._children(child, (*here, child.name)),
                    rest,
                    (*here, child.name),
                )
            ]

        keyed_values = self._keyed_values(children, rest, here)

        if step._shape is _Shape.Across:
            return [((keys[-1], *keys[:-1]), value) for keys, value in keyed_values]

        return keyed_values

    def _keyed_values_at_end(self, entry: Entry, path: EntryPath) -> _KeyedValues:
        """Collects the result a placement's last step refers to.

        Args:
            entry (Entry): The entry at the end of the steps.
            path (EntryPath): The names from the findings down to the entry.

        Returns:
            _KeyedValues: The result, or one result per key with the key in front.

        Raises:
            NoResultError: If the entry is a group, the result failed, or it
                was not computed under the findings' key.
        """
        if isinstance(entry, AnalyticEntry):
            return [((), self._completed(entry.result, path))]

        if isinstance(entry, KeyedAnalyticEntry):
            keyed_values: _KeyedValues = [
                (
                    self._keyed_path((), keyed.key),
                    self._completed(keyed.result, self._keyed_path(path, keyed.key)),
                )
                for keyed in entry.results
                if self._in_scope(keyed.key)
            ]

            if keyed_values or isinstance(self._key, _Unkeyed):
                return keyed_values

            msg = f"{self._path_text(path)} was not computed under {self._key!r}"
            raise NoResultError(msg)

        msg = f"{self._path_text(path)} is a group, not an analytic"
        raise NoResultError(msg)

    def _completed(
        self, result: Union[ReportValue, Failure], path: EntryPath
    ) -> ReportValue:
        if isinstance(result, Failure):
            msg = f"{self._path_text(path)} failed: {result.message}"
            raise NoResultError(msg)

        return result

    def _keyed_path(self, path: EntryPath, key: Value) -> EntryPath:
        """Appends a key to a path, unless the findings are read under that key.

        Args:
            path (EntryPath): The names from the findings down to the entry.
            key (Value): The key the item sits under.

        Returns:
            EntryPath: The path, with the key at the end when every key is in
                scope.
        """
        return path if not isinstance(self._key, _Unkeyed) else (*path, key)

    def _in_scope(self, key: Value) -> bool:
        return isinstance(self._key, _Unkeyed) or self._key == key

    def _entry_named(
        self, entries: Sequence[Entry], name: Value, path: EntryPath
    ) -> Entry:
        for entry in entries:
            if entry.name == name:
                return entry

        msg = f"{self._path_text((*path, name))} is not in the findings"
        raise NoResultError(msg)

    def _children(self, entry: Entry, path: EntryPath) -> Sequence[Entry]:
        if isinstance(entry, (GroupEntry, KeyedGroupEntry)):
            return entry.entries

        msg = f"{self._path_text(path)} is an analytic, not a group"
        raise NoResultError(msg)

    def _derived(self, entry: Entry, path: EntryPath) -> None:
        if isinstance(entry, GroupEntry) and entry.derivation is not None:
            derivations = {(): entry.derivation}
        elif isinstance(entry, KeyedGroupEntry):
            derivations = {
                self._keyed_path((), key): derivation
                for key, derivation in entry.derivations.items()
                if self._in_scope(key)
            }
        else:
            derivations = {}

        for keys, derivation in derivations.items():
            if derivation.failure is not None:
                msg = (
                    f"{self._path_text((*path, *keys))} failed: "
                    f"{derivation.failure.message}"
                )
                raise NoResultError(msg)

    @staticmethod
    def _fans_out(step: _Step, entry: Entry) -> bool:
        """Tells whether a group step holds one child group per key.

        A group placed over each key does so everywhere; a group placed across
        keys does so only inside another group run across keys, where its
        entry is keyed, and keys its leaves otherwise.

        Args:
            step (_Step): The step of the group.
            entry (Entry): The entry the step found.

        Returns:
            bool: True if the step's children are one group per key.
        """
        return step._shape is _Shape.Each or (
            step._shape is _Shape.Across and isinstance(entry, KeyedGroupEntry)
        )

    @staticmethod
    def _nested(keyed_values: _KeyedValues) -> _Found:
        """Builds the value a placement reads from the collected keyed_values.

        The entries hold the union of every result kind and the placement's
        type parameter says which one sits here, so the caller casts the value
        to it; this is the one place the declared result type is asserted.

        Args:
            keyed_values (_KeyedValues): The values with the keys above them.

        Returns:
            _Found: The single value, or a mapping by key, nested outermost
                group first.
        """
        if len(keyed_values) == 1 and not keyed_values[0][0]:
            return keyed_values[0][1]

        nested: Dict[Value, _KeyedValues] = {}

        for keys, value in keyed_values:
            nested.setdefault(keys[0], []).append((keys[1:], value))

        return {key: Findings._nested(inner) for key, inner in nested.items()}

    @staticmethod
    def _path_text(path: EntryPath) -> str:
        return " / ".join(str(name) for name in path)

    def __repr__(self) -> str:
        """Returns the string representation of the findings.

        Returns:
            str: The number of entries the findings hold.
        """
        return f"Findings(entries={len(self._entries)})"
