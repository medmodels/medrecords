"""Evaluation groups and the members a run computes them through."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from time import perf_counter
from typing import TYPE_CHECKING, Dict, Generic, List, Mapping, Optional

from medrecords.evaluation.analytic import DerivedType, InputsType
from medrecords.evaluation.report import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
)

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation._run import Run
    from medrecords.evaluation.analytic import Analytic, Derivation, Detail
    from medrecords.evaluation.report import Entry, EntryPath


class _Member(ABC, Generic[InputsType]):
    """One named member of a group; the single seam a run computes through."""

    _name: str

    def __init__(self, name: str) -> None:
        """Initializes a member under a name.

        Args:
            name (str): The name the member is reported under.
        """
        self._name = name

    @abstractmethod
    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> Entry:
        """Computes the member and returns its entry.

        Args:
            run (Run): The run the member is computed on.
            inputs (InputsType): What the member runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            Entry: The entry of the member.
        """


class _AnalyticMember(_Member[InputsType]):
    """An analytic placed in a group."""

    _analytic: Analytic[InputsType]
    _title: Optional[str]
    _description: Optional[str]

    def __init__(
        self,
        name: str,
        analytic: Analytic[InputsType],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes an analytic member.

        Args:
            name (str): The name the analytic is reported under.
            analytic (Analytic[InputsType]): The analytic placed.
            title (Optional[str]): The heading of the analytic, or None for the
                one the analytic gives itself.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself.
        """
        super().__init__(name)
        self._analytic = analytic
        self._title = title
        self._description = description or None

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> AnalyticEntry:
        """Computes the analytic and returns its entry.

        Args:
            run (Run): The run the analytic is computed on.
            inputs (InputsType): What the analytic runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            AnalyticEntry: The entry of the analytic.
        """
        return run._analytic(
            self._analytic,
            inputs,
            (*path, self._name),
            self._title,
            self._description,
        )


class _GroupMember(_Member[InputsType]):
    """A group placed in a group, over the same inputs."""

    _group: EvaluationGroup[InputsType]
    _title: str
    _description: Optional[str]

    def __init__(
        self,
        name: str,
        group: EvaluationGroup[InputsType],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes a nested group member.

        Args:
            name (str): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
        """
        super().__init__(name)
        self._group = group
        self._title = title or name
        self._description = description or None

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        """Computes the group over the same inputs and returns its entry.

        Args:
            run (Run): The run the group is computed on.
            inputs (InputsType): What the group runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            GroupEntry: The entry of the group.
        """
        return GroupEntry(
            self._name,
            self._title,
            self._description,
            InputEntry._from_inputs(inputs),
            None,
            self._group._entries(run, inputs, (*path, self._name)),
        )


class _GroupOverMember(_Member[InputsType], Generic[InputsType, DerivedType]):
    """A group placed in a group, over the inputs a derivation computes."""

    _derivation: Derivation[InputsType, DerivedType]
    _group: EvaluationGroup[DerivedType]
    _title: str
    _description: Optional[str]

    def __init__(
        self,
        name: str,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes a member holding a group over derived inputs.

        Args:
            name (str): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs.
            group (EvaluationGroup[DerivedType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
        """
        super().__init__(name)
        self._derivation = derivation
        self._group = group
        self._title = title or name
        self._description = description or None

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        """Derives the inputs, computes the group on them, and returns its entry.

        Args:
            run (Run): The run the group is computed on.
            inputs (InputsType): What the derivation runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            GroupEntry: The entry of the group.
        """
        parameters: Dict[str, Detail] = {}
        started: Optional[float] = None

        try:
            parameters = dict(self._derivation.parameters())
            started = perf_counter()
            derived = self._derivation.derive(inputs)
            summary = dict(self._derivation.summarize(derived))
        except Exception as error:
            failed = DerivationEntry(
                parameters,
                {},
                timedelta()
                if started is None
                else timedelta(seconds=perf_counter() - started),
                Failure._from_exception(error),
            )
            run._fail(error)
            return GroupEntry(
                self._name,
                self._title,
                self._description,
                InputEntry._from_inputs(inputs),
                failed,
                [],
            )

        derivation = DerivationEntry(
            parameters, summary, timedelta(seconds=perf_counter() - started), None
        )

        return GroupEntry(
            self._name,
            self._title,
            self._description,
            InputEntry._from_inputs(derived),
            derivation,
            self._group._entries(run, derived, (*path, self._name)),
        )


class _GroupOverEachMember(_Member[InputsType], Generic[InputsType, DerivedType]):
    """A group placed in a group once per key a derivation returns."""

    _derivation: Derivation[InputsType, Mapping[Value, DerivedType]]
    _group: EvaluationGroup[DerivedType]
    _title: str
    _description: Optional[str]

    def __init__(
        self,
        name: str,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes a member holding a group over each derived inputs.

        Args:
            name (str): The name the entries are reported under.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every entry, by key.
            group (EvaluationGroup[DerivedType]): The group placed under every key.
            title (Optional[str]): The heading of the entries, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
        """
        super().__init__(name)
        self._derivation = derivation
        self._group = group
        self._title = title or name
        self._description = description or None

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        """Derives the inputs, computes the group under every key, and reports it.

        Args:
            run (Run): The run the group is computed on.
            inputs (InputsType): What the derivation runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            GroupEntry: The entry holding one group per key.
        """
        parameters: Dict[str, Detail] = {}
        started: Optional[float] = None

        try:
            parameters = dict(self._derivation.parameters())
            started = perf_counter()
            derived = self._derivation.derive(inputs)
            summary = dict(self._derivation.summarize(derived))
        except Exception as error:
            failed = DerivationEntry(
                parameters,
                {},
                timedelta()
                if started is None
                else timedelta(seconds=perf_counter() - started),
                Failure._from_exception(error),
            )
            run._fail(error)
            return GroupEntry(
                self._name,
                self._title,
                self._description,
                InputEntry._from_inputs(inputs),
                failed,
                [],
            )

        derivation = DerivationEntry(
            parameters, summary, timedelta(seconds=perf_counter() - started), None
        )
        child_path = (*path, self._name)
        entries: List[Entry] = [
            GroupEntry(
                str(key),
                str(key),
                None,
                InputEntry._from_inputs(inner),
                None,
                self._group._entries(run, inner, (*child_path, str(key))),
            )
            for key, inner in derived.items()
        ]

        return GroupEntry(
            self._name,
            self._title,
            self._description,
            InputEntry._from_inputs(inputs),
            derivation,
            entries,
        )


class EvaluationGroup(Generic[InputsType]):
    """An ordered collection of analytics and groups over one inputs type."""

    _members: List[_Member[InputsType]]

    def __init__(self) -> None:
        """Initializes an empty group."""
        self._members = []

    @classmethod
    def _from_members(
        cls, members: List[_Member[InputsType]]
    ) -> EvaluationGroup[InputsType]:
        """Creates a group around members.

        Args:
            members (List[_Member[InputsType]]): The members, in order.

        Returns:
            EvaluationGroup[InputsType]: A group holding the members.
        """
        group: EvaluationGroup[InputsType] = cls()
        group._members = members
        return group

    def add_analytic(
        self,
        name: str,
        analytic: Analytic[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places an analytic over the group's inputs.

        Args:
            name (str): The name the analytic is reported under.
            analytic (Analytic[InputsType]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            EvaluationGroup[InputsType]: A group with the analytic as its last member.
        """
        return self._with_member(_AnalyticMember(name, analytic, title, description))

    def add_group(
        self,
        name: str,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over the same inputs.

        Args:
            name (str): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            EvaluationGroup[InputsType]: A group with the group as its last member.
        """
        return self._with_member(_GroupMember(name, group, title, description))

    def add_group_over(
        self,
        name: str,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over inputs a derivation computes once per run.

        Args:
            name (str): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs from this group's inputs.
            group (EvaluationGroup[DerivedType]): The group to run on the
                derived inputs.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            EvaluationGroup[InputsType]: A group with the nested group as
                its last member.
        """
        return self._with_member(
            _GroupOverMember(name, derivation, group, title, description)
        )

    def add_group_over_each(
        self,
        name: str,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over each of the inputs a derivation computes.

        Args:
            name (str): The name the entries are reported under; each key is
                reported below it, in mapping order.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every entry, by key.
            group (EvaluationGroup[DerivedType]): The group to run on every key.
            title (Optional[str]): The heading of the entries in a typeset
                report, or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            EvaluationGroup[InputsType]: A group with the entries as its last member.
        """
        return self._with_member(
            _GroupOverEachMember(name, derivation, group, title, description)
        )

    def _with_member(self, member: _Member[InputsType]) -> EvaluationGroup[InputsType]:
        """Creates a group with one more member.

        Args:
            member (_Member[InputsType]): The member to add last.

        Returns:
            EvaluationGroup[InputsType]: A group with the member as its last member.

        Raises:
            ValueError: If the name is already taken in this group.
        """
        if any(existing._name == member._name for existing in self._members):
            msg = f"name {member._name!r} is already taken"
            raise ValueError(msg)

        return EvaluationGroup._from_members([*self._members, member])

    def _entries(self, run: Run, inputs: InputsType, path: EntryPath) -> List[Entry]:
        """Computes every member in order and returns their entries.

        Args:
            run (Run): The run the members are computed on.
            inputs (InputsType): What the members run on.
            path (EntryPath): The names from the root to this group.

        Returns:
            List[Entry]: The entries, in definition order.
        """
        return [member._entry(run, inputs, path) for member in self._members]

    def __repr__(self) -> str:
        """Returns the string representation of the EvaluationGroup.

        Returns:
            str: The number of members the group holds.
        """
        return f"EvaluationGroup(members={len(self._members)})"
