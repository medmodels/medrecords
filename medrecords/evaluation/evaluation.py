"""Evaluation class holding the root group of a report."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Mapping, Optional, Tuple

from medrecords.evaluation._run import OnFailure, Run
from medrecords.evaluation.analytic import (
    DerivedType,
    InputsType,
    ResultType,
)
from medrecords.evaluation.group import EvaluationGroup, _ConclusionMember
from medrecords.evaluation.placement import (
    AtRoot,
    GroupPlacement,
    KeyedGroupPlacement,
    Placement,
)

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation._run import ProgressHandler
    from medrecords.evaluation.analytic import Analytic, Derivation, ReportValue
    from medrecords.evaluation.findings import Findings
    from medrecords.evaluation.report import Report


class Evaluation(Generic[InputsType]):
    """A named root group that can be run on inputs.

    Every ``add_*`` returns a new evaluation; its ``place_*`` sibling returns
    the new evaluation together with a placement, the handle a conclusion of
    the evaluation reads the member through. The name becomes the name of the
    report. Members are placed under names that are told apart the way a
    mapping tells its keys apart.
    """

    _name: str
    _description: Optional[str]
    _group: EvaluationGroup[InputsType]

    def __init__(self, name: str, description: Optional[str] = None) -> None:
        """Initializes an empty evaluation.

        Args:
            name (str): The name of the evaluation.
            description (Optional[str]): The text under the name of the report.
                Defaults to None.
        """
        self._name = name
        self._description = description
        self._group = EvaluationGroup[InputsType]()

    @classmethod
    def _from_group(
        cls, name: str, description: Optional[str], group: EvaluationGroup[InputsType]
    ) -> Evaluation[InputsType]:
        evaluation: Evaluation[InputsType] = cls(name, description)
        evaluation._group = group
        return evaluation

    def _with_group(self, group: EvaluationGroup[InputsType]) -> Evaluation[InputsType]:
        return Evaluation._from_group(self._name, self._description, group)

    def add_analytic(
        self,
        name: Value,
        analytic: Analytic[InputsType, ReportValue],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places an analytic over the evaluation's inputs.

        Args:
            name (Value): The name the analytic is reported under.
            analytic (Analytic[InputsType, ReportValue]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Evaluation[InputsType]: An evaluation with the analytic as its last
                member.
        """
        return self.place_analytic(name, analytic, title, description)[0]

    def place_analytic(
        self,
        name: Value,
        analytic: Analytic[InputsType, ResultType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], Placement[AtRoot, ResultType]]:
        """Places an analytic over the evaluation's inputs, with its placement.

        Args:
            name (Value): The name the analytic is reported under.
            analytic (Analytic[InputsType, ResultType]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Tuple[Evaluation[InputsType], Placement[AtRoot, ResultType]]: An
                evaluation with the analytic as its last member, and the
                placement reading the analytic's result.
        """
        group, placement = self._group.place_analytic(
            name, analytic, title, description
        )

        return self._with_group(group), Placement(placement._steps)

    def add_group(
        self,
        name: Value,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a group over the same inputs.

        Args:
            name (Value): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report, or
                None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            Evaluation[InputsType]: An evaluation with the group as its last
                member.
        """
        return self.place_group(name, group, title, description)[0]

    def place_group(
        self,
        name: Value,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], GroupPlacement[AtRoot]]:
        """Places a group over the same inputs and hands back its placement.

        Args:
            name (Value): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report, or
                None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            Tuple[Evaluation[InputsType], GroupPlacement[AtRoot]]: An evaluation
                with the group as its last member, and the placement converting
                the placements made inside the group.
        """
        root, placement = self._group.place_group(name, group, title, description)

        return self._with_group(root), GroupPlacement(placement._step)

    def add_group_over(
        self,
        name: Value,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a group over inputs a derivation computes once per run.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs from the evaluation's inputs.
            group (EvaluationGroup[DerivedType]): The group to run on the
                derived inputs.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            Evaluation[InputsType]: An evaluation with the nested group as its
                last member.
        """
        return self.place_group_over(name, derivation, group, title, description)[0]

    def place_group_over(
        self,
        name: Value,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], GroupPlacement[AtRoot]]:
        """Places a group over derived inputs and hands back its placement.

        Args:
            name (Value): The name the group is reported under.
            derivation (Derivation[InputsType, DerivedType]): The derivation
                computing the group's inputs from the evaluation's inputs.
            group (EvaluationGroup[DerivedType]): The group to run on the
                derived inputs.
            title (Optional[str]): The heading of the group in a typeset report,
                or None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            Tuple[Evaluation[InputsType], GroupPlacement[AtRoot]]: An evaluation
                with the nested group as its last member, and the placement
                converting the placements made inside the group.
        """
        root, placement = self._group.place_group_over(
            name, derivation, group, title, description
        )
        return self._with_group(root), GroupPlacement(placement._step)

    def add_group_over_each(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
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

        Returns:
            Evaluation[InputsType]: An evaluation with the entries as its last
                member.
        """
        return self.place_group_over_each(name, derivation, group, title, description)[
            0
        ]

    def place_group_over_each(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], KeyedGroupPlacement[AtRoot]]:
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

        Returns:
            Tuple[Evaluation[InputsType], KeyedGroupPlacement[AtRoot]]: An
                evaluation with the entries as its last member, and the
                placement converting the placements made inside the group to
                one value per key.
        """
        root, placement = self._group.place_group_over_each(
            name, derivation, group, title, description
        )

        return self._with_group(root), KeyedGroupPlacement(placement._step)

    def add_group_across(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a group across the inputs a derivation computes, by key.

        Every member of the group runs once per key and is reported once, with
        one result per key.

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

        Returns:
            Evaluation[InputsType]: An evaluation with the nested group as its
                last member.
        """
        return self.place_group_across(name, derivation, group, title, description)[0]

    def place_group_across(
        self,
        name: Value,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], KeyedGroupPlacement[AtRoot]]:
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

        Returns:
            Tuple[Evaluation[InputsType], KeyedGroupPlacement[AtRoot]]: An
                evaluation with the nested group as its last member, and the
                placement converting the placements made inside the group to
                one value per key.
        """
        root, placement = self._group.place_group_across(
            name, derivation, group, title, description
        )

        return self._with_group(root), KeyedGroupPlacement(placement._step)

    def add_conclusion(
        self,
        name: Value,
        conclusion: Analytic[Findings[AtRoot], ReportValue],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a conclusion over what the evaluation finds.

        A conclusion is an analytic over the evaluation's findings: the results
        of the analytics and groups placed on the evaluation, wherever its own
        line sits, and of the conclusions placed before it. It reads them
        through the placements made on the evaluation, and through the
        placements of groups for what was placed inside them.

        Args:
            name (Value): The name the conclusion is reported under.
            conclusion (Analytic[Findings[AtRoot], ReportValue]): The analytic
                to place over the evaluation's findings.
            title (Optional[str]): The heading of the conclusion in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Evaluation[InputsType]: An evaluation with the conclusion as its
                last member.
        """
        return self.place_conclusion(name, conclusion, title, description)[0]

    def place_conclusion(
        self,
        name: Value,
        conclusion: Analytic[Findings[AtRoot], ResultType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Tuple[Evaluation[InputsType], Placement[AtRoot, ResultType]]:
        """Places a conclusion over the evaluation's findings, with its placement.

        Args:
            name (Value): The name the conclusion is reported under.
            conclusion (Analytic[Findings[AtRoot], ResultType]): The analytic
                to place over the evaluation's findings.
            title (Optional[str]): The heading of the conclusion in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Tuple[Evaluation[InputsType], Placement[AtRoot, ResultType]]: An
                evaluation with the conclusion as its last member, and the
                placement reading the conclusion's result.
        """
        member = _ConclusionMember(name, conclusion, title, description)

        return (
            self._with_group(self._group._with_member(member)),
            Placement((member._step,)),
        )

    def report(
        self,
        inputs: InputsType,
        on_failure: OnFailure = OnFailure.Record,
        on_progress: Optional[ProgressHandler] = None,
    ) -> Report:
        """Runs every member and reports what they found.

        The analytics and groups run in definition order, the conclusions after
        them.

        Args:
            inputs (InputsType): What the analytics run on.
            on_failure (OnFailure): Whether a failing analytic or derivation is
                recorded or ends the run. Defaults to OnFailure.Record.
            on_progress (Optional[ProgressHandler]): Called after every analytic
                finishes. An exception it raises ends the run. Defaults to None.

        Returns:
            Report: The report of the run.
        """
        return Run(on_failure, on_progress).report(
            self._name, self._description, self._group, inputs
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Evaluation.

        Returns:
            str: The name and the number of members the root group holds.
        """
        return f"Evaluation({self._name!r}, members={len(self._group._members)})"
