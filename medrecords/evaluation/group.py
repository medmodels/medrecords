"""Evaluation groups and the members a run computes them through."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Dict,
    Generic,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
)

from medrecords.evaluation.analytic import (
    DerivedType,
    InputsType,
    ResultType,
)
from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    Layout,
)
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.placement import (
    _UNKEYED,
    GroupPlacement,
    InGroup,
    KeyedGroupPlacement,
    Placement,
    ScopeType,
    _Shape,
    _Step,
)

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation._run import Run
    from medrecords.evaluation.analytic import (
        Analytic,
        Derivation,
        EntryPath,
        ReportValue,
    )
    from medrecords.evaluation.entry import Entry, KeyedEntry

EntryType = TypeVar("EntryType")


class _Member(ABC):
    """One named member of a group, holding the step placements refer to it by."""

    _step: _Step

    def __init__(self, name: Value, shape: _Shape) -> None:
        """Initializes a member under a name.

        Args:
            name (Value): The name the member is reported under.
            shape (_Shape): How the member's entries are laid out below it.
        """
        self._step = _Step(name, shape)

    def _owns(self, steps: Tuple[_Step, ...]) -> bool:
        """Tells whether steps below this member lead to one of its members.

        Args:
            steps (Tuple[_Step, ...]): The steps below this member.

        Returns:
            bool: True if there are none; a member holding a group overrides
                this to follow them.
        """
        return not steps


class _InputsMember(_Member, Generic[InputsType]):
    """A member computed over the inputs of its group, alone or across keys."""

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

    @abstractmethod
    def _entry_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> KeyedEntry:
        """Computes the member under every key and returns its keyed entry.

        Args:
            run (Run): The run the member is computed on.
            inputs_by_key (Mapping[Value, InputsType]): What the member runs on,
                by key.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            KeyedEntry: The keyed entry of the member.
        """


class _AnalyticMember(_InputsMember[InputsType]):
    """An analytic placed in a group."""

    _analytic: Analytic[InputsType, ReportValue]
    _title: Optional[str]
    _description: Optional[str]

    def __init__(
        self,
        name: Value,
        analytic: Analytic[InputsType, ReportValue],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes an analytic member.

        Args:
            name (Value): The name the analytic is reported under.
            analytic (Analytic[InputsType, ReportValue]): The analytic placed.
            title (Optional[str]): The heading of the analytic, or None for the
                one the analytic gives itself.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself.
        """
        super().__init__(name, _Shape.Plain)
        self._analytic = analytic
        self._title = title
        self._description = description or None

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> AnalyticEntry:
        return run._analytic(
            self._analytic,
            inputs,
            (*path, self._step._name),
            self._title,
            self._description,
        )

    def _entry_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> KeyedAnalyticEntry:
        return run._keyed_analytic(
            self._analytic,
            inputs_by_key,
            (*path, self._step._name),
            self._title,
            self._description,
        )


class _ConclusionMember(_Member, Generic[ScopeType]):
    """An analytic placed in a group over what the group found."""

    _conclusion: Analytic[Findings[ScopeType], ReportValue]
    _title: Optional[str]
    _description: Optional[str]

    def __init__(
        self,
        name: Value,
        conclusion: Analytic[Findings[ScopeType], ReportValue],
        title: Optional[str],
        description: Optional[str],
    ) -> None:
        """Initializes a conclusion member.

        Args:
            name (Value): The name the conclusion is reported under.
            conclusion (Analytic[Findings[ScopeType], ReportValue]): The
                analytic placed over the group's findings.
            title (Optional[str]): The heading of the conclusion, or None for
                the one the analytic gives itself.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself.
        """
        super().__init__(name, _Shape.Plain)
        self._conclusion = conclusion
        self._title = title
        self._description = description or None

    def _conclude(
        self, run: Run, path: EntryPath, findings: Findings[ScopeType]
    ) -> AnalyticEntry:
        return run._analytic(
            self._conclusion,
            findings,
            (*path, self._step._name),
            self._title,
            self._description,
        )

    def _conclude_across(
        self,
        run: Run,
        path: EntryPath,
        findings_by_key: Mapping[Value, Findings[ScopeType]],
    ) -> KeyedAnalyticEntry:
        return run._keyed_analytic(
            self._conclusion,
            findings_by_key,
            (*path, self._step._name),
            self._title,
            self._description,
        )


class _NestedGroupMember(_InputsMember[InputsType], Generic[InputsType, DerivedType]):
    """A member holding a group placed in a group."""

    _group: EvaluationGroup[DerivedType]
    _title: str
    _description: Optional[str]
    _layout: Layout

    def __init__(
        self,
        name: Value,
        shape: _Shape,
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a member holding a group.

        Args:
            name (Value): The name the group is reported under.
            shape (_Shape): How the group's entries are laid out below the name.
            group (EvaluationGroup[DerivedType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the group.
        """
        super().__init__(name, shape)
        self._group = group
        self._title = title or str(name)
        self._description = description or None
        self._layout = layout

    def _owns(self, steps: Tuple[_Step, ...]) -> bool:
        return not steps or self._group._owns(steps)

    def _unfilled(self, derivation: Optional[DerivationEntry]) -> GroupEntry:
        return GroupEntry(
            self._step._name,
            self._title,
            self._description,
            derivation,
            [],
            layout=self._layout,
        )


class _GroupMember(_NestedGroupMember[InputsType, InputsType]):
    """A group placed in a group, over the same inputs."""

    def __init__(
        self,
        name: Value,
        group: EvaluationGroup[InputsType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a nested group member.

        Args:
            name (Value): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the group.
        """
        super().__init__(name, _Shape.Plain, group, title, description, layout)

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        return self._group._filled(
            run, inputs, (*path, self._step._name), self._unfilled(None)
        )

    def _entry_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> KeyedGroupEntry:
        return KeyedGroupEntry(
            self._step._name,
            self._title,
            self._description,
            {},
            self._group._entries_across(run, inputs_by_key, (*path, self._step._name)),
            layout=self._layout,
        )


class _GroupOverMember(_NestedGroupMember[InputsType, DerivedType]):
    """A group placed in a group, over the inputs a derivation computes."""

    _derivation: Derivation[InputsType, DerivedType]

    def __init__(
        self,
        name: Value,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a member holding a group over derived inputs.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs.
            group (EvaluationGroup[DerivedType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the group.
        """
        super().__init__(name, _Shape.Plain, group, title, description, layout)
        self._derivation = derivation

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        derivation, derived = run._derivation(self._derivation, inputs)

        if isinstance(derived, Failure):
            return self._unfilled(derivation)

        return self._group._filled(
            run, derived, (*path, self._step._name), self._unfilled(derivation)
        )

    def _entry_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> KeyedGroupEntry:
        derivations, derived = run._derivations(self._derivation, inputs_by_key)

        return KeyedGroupEntry(
            self._step._name,
            self._title,
            self._description,
            derivations,
            self._group._entries_across(run, derived, (*path, self._step._name)),
            layout=self._layout,
        )


class _KeyedGroupMember(_NestedGroupMember[InputsType, DerivedType]):
    """A group placed in a group over the inputs a derivation computes by key.

    Nested in another group placed across keys, every child key the
    derivations return gets one keyed group holding the group computed across
    the keys that returned it, in the order the child keys were first seen,
    headed by the first title the derivation gives the child key.
    """

    _derivation: Derivation[InputsType, Mapping[Value, DerivedType]]

    def __init__(
        self,
        name: Value,
        shape: _Shape,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a member holding a group over derived inputs by key.

        Args:
            name (Value): The name the group is reported under.
            shape (_Shape): How the group's entries are laid out below the name.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every key.
            group (EvaluationGroup[DerivedType]): The group placed.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the group.
        """
        super().__init__(name, shape, group, title, description, layout)
        self._derivation = derivation

    def _entry_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> KeyedGroupEntry:
        """Derives the inputs under every key and computes the group per child key.

        Args:
            run (Run): The run the group is computed on.
            inputs_by_key (Mapping[Value, InputsType]): What the derivation runs
                on, by key.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            KeyedGroupEntry: The keyed entry holding one keyed group per child key.
        """
        derivations, derived, titles = run._keyed_derivations(
            self._derivation, inputs_by_key
        )
        inputs_by_child_key: Dict[Value, Dict[Value, DerivedType]] = {}

        for key, derived_by_child_key in derived.items():
            for child_key, child_inputs in derived_by_child_key.items():
                inputs_by_child_key.setdefault(child_key, {})[key] = child_inputs

        child_path = (*path, self._step._name)
        entries: List[KeyedEntry] = [
            KeyedGroupEntry(
                child_key,
                titles.get(child_key, str(child_key)),
                None,
                {},
                self._group._entries_across(
                    run, inputs_of_child, (*child_path, child_key)
                ),
            )
            for child_key, inputs_of_child in inputs_by_child_key.items()
        ]

        return KeyedGroupEntry(
            self._step._name,
            self._title,
            self._description,
            derivations,
            entries,
            layout=self._layout,
        )


class _GroupOverEachMember(_KeyedGroupMember[InputsType, DerivedType]):
    """A group placed in a group once per key a derivation returns."""

    def __init__(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a member holding a group over each derived inputs.

        Args:
            name (Value): The name the entries are reported under.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every entry, by key.
            group (EvaluationGroup[DerivedType]): The group placed under every key.
            title (Optional[str]): The heading of the entries, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the entries.
        """
        super().__init__(
            name, _Shape.Each, derivation, group, title, description, layout
        )

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        """Derives the inputs, computes the group under every key, and reports it.

        Every key's group is headed by the title the derivation gives the key,
        or by the key itself.

        Args:
            run (Run): The run the group is computed on.
            inputs (InputsType): What the derivation runs on.
            path (EntryPath): The names from the root to the enclosing group.

        Returns:
            GroupEntry: The entry holding one group per key, empty when the
                derivation failed.
        """
        derivation, derived, titles = run._keyed_derivation(self._derivation, inputs)

        if isinstance(derived, Failure):
            return self._unfilled(derivation)

        child_path = (*path, self._step._name)
        entries: List[Entry] = [
            self._group._filled(
                run,
                inner,
                (*child_path, key),
                GroupEntry(
                    key,
                    titles.get(key, str(key)),
                    None,
                    None,
                    [],
                ),
            )
            for key, inner in derived.items()
        ]
        entry = self._unfilled(derivation)

        return entry._with_entries(entries)


class _GroupAcrossMember(_KeyedGroupMember[InputsType, DerivedType]):
    """A group placed in a group across the keys a derivation returns."""

    def __init__(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str],
        description: Optional[str],
        layout: Layout,
    ) -> None:
        """Initializes a member holding a group across derived inputs.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every key.
            group (EvaluationGroup[DerivedType]): The group placed across the keys.
            title (Optional[str]): The heading of the group, or None for the
                name.
            description (Optional[str]): The text under the heading, if any.
            layout (Layout): How a typeset report sets the group.
        """
        super().__init__(
            name, _Shape.Across, derivation, group, title, description, layout
        )

    def _entry(self, run: Run, inputs: InputsType, path: EntryPath) -> GroupEntry:
        derivation, derived = run._derivation(self._derivation, inputs)

        if isinstance(derived, Failure):
            return self._unfilled(derivation)

        entry = self._unfilled(derivation)

        return entry._with_entries(
            self._group._entries_across(run, derived, (*path, self._step._name))
        )


class EvaluationGroup(Generic[InputsType]):
    """An ordered collection of analytics, groups and conclusions over one inputs type.

    Members are placed under names that are told apart the way a mapping tells
    its keys apart. Every ``add_*`` returns a new group; its ``place_*`` sibling
    returns the new group together with a placement, the handle a conclusion
    reads the member through. A run computes the analytics and groups first and
    the conclusions after them, each in definition order, and reports every
    member in definition order.
    """

    _members: List[_Member]

    def __init__(self) -> None:
        """Initializes an empty group."""
        self._members = []

    @classmethod
    def _from_members(cls, members: List[_Member]) -> EvaluationGroup[InputsType]:
        group: EvaluationGroup[InputsType] = cls()
        group._members = members
        return group

    def add_analytic(
        self,
        name: Value,
        analytic: Analytic[InputsType, ReportValue],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places an analytic over the group's inputs.

        Args:
            name (Value): The name the analytic is reported under.
            analytic (Analytic[InputsType, ReportValue]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            EvaluationGroup[InputsType]: A group with the analytic as its last member.
        """
        return self.place_analytic(name, analytic, title, description)[0]

    def place_analytic(
        self,
        name: Value,
        analytic: Analytic[InputsType, ResultType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[EvaluationGroup[InputsType], Placement[InGroup, ResultType]]:
        """Places an analytic over the group's inputs, with its placement.

        Args:
            name (Value): The name the analytic is reported under.
            analytic (Analytic[InputsType, ResultType]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Tuple[EvaluationGroup[InputsType], Placement[InGroup, ResultType]]:
                A group with the analytic as its last member, and the placement
                reading the analytic's result.
        """
        member = _AnalyticMember(name, analytic, title, description)

        return self._with_member(member), Placement((member._step,))

    def add_group(
        self,
        name: Value,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over the same inputs.

        Args:
            name (Value): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            EvaluationGroup[InputsType]: A group with the group as its last member.
        """
        return self.place_group(name, group, title, description, layout=layout)[0]

    def place_group(
        self,
        name: Value,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> Tuple[EvaluationGroup[InputsType], GroupPlacement[InGroup]]:
        """Places a group over the same inputs and hands back its placement.

        Args:
            name (Value): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            Tuple[EvaluationGroup[InputsType], GroupPlacement[InGroup]]: A group
                with the group as its last member, and the placement converting
                the placements made inside the group.
        """
        member = _GroupMember(name, group, title, description, layout)

        return self._with_member(member), GroupPlacement(member._step)

    def add_group_over(
        self,
        name: Value,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over inputs a derivation computes once per run.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs from this group's inputs.
            group (EvaluationGroup[DerivedType]): The group to run on the
                derived inputs.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            EvaluationGroup[InputsType]: A group with the nested group as
                its last member.
        """
        return self.place_group_over(
            name, derivation, group, title, description, layout=layout
        )[0]

    def place_group_over(
        self,
        name: Value,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> Tuple[EvaluationGroup[InputsType], GroupPlacement[InGroup]]:
        """Places a group over derived inputs and hands back its placement.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs from this group's inputs.
            group (EvaluationGroup[DerivedType]): The group to run on the
                derived inputs.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            Tuple[EvaluationGroup[InputsType], GroupPlacement[InGroup]]: A group
                with the nested group as its last member, and the placement
                converting the placements made inside the group.
        """
        member = _GroupOverMember(name, derivation, group, title, description, layout)

        return self._with_member(member), GroupPlacement(member._step)

    def add_group_over_each(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> EvaluationGroup[InputsType]:
        """Places a group over each of the inputs a derivation computes.

        Args:
            name (Value): The name the entries are reported under; each key is
                reported below it, in mapping order.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every entry, by key.
            group (EvaluationGroup[DerivedType]): The group to run on every key.
            title (Optional[str]): The heading of the entries in a typeset
                report, or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            EvaluationGroup[InputsType]: A group with the entries as its last member.
        """
        return self.place_group_over_each(
            name, derivation, group, title, description, layout=layout
        )[0]

    def place_group_over_each(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> Tuple[EvaluationGroup[InputsType], KeyedGroupPlacement[InGroup]]:
        """Places a group over each derived inputs and hands back its placement.

        Args:
            name (Value): The name the entries are reported under; each key is
                reported below it, in mapping order.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every entry, by key.
            group (EvaluationGroup[DerivedType]): The group to run on every key.
            title (Optional[str]): The heading of the entries in a typeset
                report, or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            Tuple[EvaluationGroup[InputsType], KeyedGroupPlacement[InGroup]]: A
                group with the entries as its last member, and the placement
                converting the placements made inside the group to one value
                per key.
        """
        member = _GroupOverEachMember(
            name, derivation, group, title, description, layout
        )

        return self._with_member(member), KeyedGroupPlacement(member._step)

    def add_group_across(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> EvaluationGroup[InputsType]:
        """Places a group across the inputs a derivation computes, by key.

        Every member of the group runs once per key and is reported once, with
        one result per key. A group nested inside runs across the same keys; a
        derivation nested inside runs once per key. Keys are told apart the way
        a mapping tells its keys apart.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every key.
            group (EvaluationGroup[DerivedType]): The group to run across the
                keys.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            EvaluationGroup[InputsType]: A group with the nested group as its last
                member.
        """
        return self.place_group_across(
            name, derivation, group, title, description, layout=layout
        )[0]

    def place_group_across(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
        *,
        layout: Layout = Layout.Section,
    ) -> Tuple[EvaluationGroup[InputsType], KeyedGroupPlacement[InGroup]]:
        """Places a group across derived inputs and hands back its placement.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation computing the inputs of every key.
            group (EvaluationGroup[DerivedType]): The group to run across the
                keys.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.

        Returns:
            Tuple[EvaluationGroup[InputsType], KeyedGroupPlacement[InGroup]]: A
                group with the nested group as its last member, and the
                placement converting the placements made inside the group to
                one value per key.
        """
        member = _GroupAcrossMember(name, derivation, group, title, description, layout)

        return self._with_member(member), KeyedGroupPlacement(member._step)

    def add_conclusion(
        self,
        name: Value,
        conclusion: Analytic[Findings[InGroup], ReportValue],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> EvaluationGroup[InputsType]:
        """Places a conclusion over what the group finds.

        A conclusion is an analytic over the group's findings: the results of
        the analytics and groups placed in this group, wherever its own line
        sits, and of the conclusions placed before it. It reads them through
        the placements made in this group. Inside a group run across keys it
        runs once per key, over the findings under that key.

        Args:
            name (Value): The name the conclusion is reported under.
            conclusion (Analytic[Findings[InGroup], ReportValue]): The analytic
                to place over the group's findings.
            title (Optional[str]): The heading of the conclusion in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            EvaluationGroup[InputsType]: A group with the conclusion as its last
                member.
        """
        return self.place_conclusion(name, conclusion, title, description)[0]

    def place_conclusion(
        self,
        name: Value,
        conclusion: Analytic[Findings[InGroup], ResultType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[EvaluationGroup[InputsType], Placement[InGroup, ResultType]]:
        """Places a conclusion over the group's findings, with its placement.

        Args:
            name (Value): The name the conclusion is reported under.
            conclusion (Analytic[Findings[InGroup], ResultType]): The analytic
                to place over the group's findings.
            title (Optional[str]): The heading of the conclusion in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Tuple[EvaluationGroup[InputsType], Placement[InGroup, ResultType]]:
                A group with the conclusion as its last member, and the
                placement reading the conclusion's result.
        """
        member = _ConclusionMember(name, conclusion, title, description)

        return self._with_member(member), Placement((member._step,))

    def _with_member(self, member: _Member) -> EvaluationGroup[InputsType]:
        if any(
            existing._step._name == member._step._name for existing in self._members
        ):
            msg = f"name {member._step._name!r} is already taken"
            raise ValueError(msg)

        return EvaluationGroup._from_members([*self._members, member])

    def _owns(self, steps: Tuple[_Step, ...]) -> bool:
        for member in self._members:
            if member._step is steps[0]:
                return member._owns(steps[1:])

        return False

    def _filled(
        self, run: Run, inputs: InputsType, path: EntryPath, entry: GroupEntry
    ) -> GroupEntry:
        """Computes every member and returns the group's entry with them.

        The analytics and groups are computed first and the conclusions after
        them, each in definition order; every conclusion reads the findings
        computed before it.

        Args:
            run (Run): The run the members are computed on.
            inputs (InputsType): What the members run on.
            path (EntryPath): The names from the root to this group.
            entry (GroupEntry): The entry of this group without its entries.

        Returns:
            GroupEntry: The entry holding every member's entry, in definition
                order.
        """
        computed: Dict[_Step, Entry] = {}

        for member in self._members:
            if isinstance(member, _InputsMember):
                computed[member._step] = member._entry(run, inputs, path)

        for member in self._members:
            if isinstance(member, _ConclusionMember):
                findings = Findings(self._ordered(computed), self, _UNKEYED, path)
                computed[member._step] = member._conclude(run, path, findings)

        return entry._with_entries(self._ordered(computed))

    def _entries_across(
        self, run: Run, inputs_by_key: Mapping[Value, InputsType], path: EntryPath
    ) -> List[KeyedEntry]:
        """Computes every member across the keys and returns their entries.

        The analytics and groups are computed first and the conclusions after
        them, each in definition order; every conclusion runs once per key over
        the findings under that key.

        Args:
            run (Run): The run the members are computed on.
            inputs_by_key (Mapping[Value, InputsType]): What the members run on,
                by key.
            path (EntryPath): The names from the root to this group.

        Returns:
            List[KeyedEntry]: The keyed entries, in definition order.
        """
        computed: Dict[_Step, KeyedEntry] = {}

        for member in self._members:
            if isinstance(member, _InputsMember):
                computed[member._step] = member._entry_across(run, inputs_by_key, path)

        for member in self._members:
            if isinstance(member, _ConclusionMember):
                findings_by_key = {
                    key: Findings(self._ordered(computed), self, key, path)
                    for key in inputs_by_key
                }
                computed[member._step] = member._conclude_across(
                    run, path, findings_by_key
                )

        return self._ordered(computed)

    def _ordered(self, computed: Mapping[_Step, EntryType]) -> List[EntryType]:
        return [
            computed[member._step]
            for member in self._members
            if member._step in computed
        ]

    def __repr__(self) -> str:
        """Returns the string representation of the EvaluationGroup.

        Returns:
            str: The number of members the group holds.
        """
        return f"EvaluationGroup(members={len(self._members)})"
