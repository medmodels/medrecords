"""Evaluation class holding the root group of a report."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, Mapping, Optional

from medrecords.evaluation._run import OnFailure, Run
from medrecords.evaluation.analytic import DerivedType, InputsType
from medrecords.evaluation.group import EvaluationGroup

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation._run import ProgressHandler
    from medrecords.evaluation.analytic import Analytic, Derivation
    from medrecords.evaluation.report import Report


class Evaluation(Generic[InputsType]):
    """A named root group that can be run on inputs.

    Every ``add_*`` returns a new evaluation; the name becomes the name of the
    report.
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
        """Creates an evaluation around a group.

        Args:
            name (str): The name of the evaluation.
            description (Optional[str]): The text under the name of the report.
            group (EvaluationGroup[InputsType]): The root group.

        Returns:
            Evaluation[InputsType]: An evaluation holding the group.
        """
        evaluation: Evaluation[InputsType] = cls(name, description)
        evaluation._group = group
        return evaluation

    def add_analytic(
        self,
        name: str,
        analytic: Analytic[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places an analytic over the evaluation's inputs.

        Args:
            name (str): The name the analytic is reported under.
            analytic (Analytic[InputsType]): The analytic to place.
            title (Optional[str]): The heading of the analytic in a typeset
                report, or None for the one the analytic gives itself. Defaults
                to None.
            description (Optional[str]): The text under the heading, or None for
                the one the analytic gives itself. Defaults to None.

        Returns:
            Evaluation[InputsType]: An evaluation with the analytic as its last
                member.
        """
        return Evaluation._from_group(
            self._name,
            self._description,
            self._group.add_analytic(name, analytic, title, description),
        )

    def add_group(
        self,
        name: str,
        group: EvaluationGroup[InputsType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a group over the same inputs.

        Args:
            name (str): The name the group is reported under.
            group (EvaluationGroup[InputsType]): The group to place.
            title (Optional[str]): The heading of the group in a typeset report, or
                None for the name. Defaults to None.
            description (Optional[str]): The text under the heading. Defaults to
                None.

        Returns:
            Evaluation[InputsType]: An evaluation with the group as its last
                member.
        """
        return Evaluation._from_group(
            self._name,
            self._description,
            self._group.add_group(name, group, title, description),
        )

    def add_group_over(
        self,
        name: str,
        derivation: Derivation[InputsType, DerivedType],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
        """Places a group over inputs a derivation computes once per run.

        Args:
            name (str): The name the group is reported under.
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
        return Evaluation._from_group(
            self._name,
            self._description,
            self._group.add_group_over(name, derivation, group, title, description),
        )

    def add_group_over_each(
        self,
        name: str,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        group: EvaluationGroup[DerivedType],
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Evaluation[InputsType]:
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
            Evaluation[InputsType]: An evaluation with the entries as its last
                member.
        """
        return Evaluation._from_group(
            self._name,
            self._description,
            self._group.add_group_over_each(
                name, derivation, group, title, description
            ),
        )

    def report(
        self,
        inputs: InputsType,
        on_failure: OnFailure = OnFailure.Record,
        on_progress: Optional[ProgressHandler] = None,
    ) -> Report:
        """Runs every analytic, in definition order, and reports what they found.

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
