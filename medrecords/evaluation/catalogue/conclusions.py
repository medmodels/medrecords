"""Conclusions over what an evaluation or a group found."""

from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Generic, List, Mapping, Optional, Sequence, TypeVar

from graphrecords import Identifier, Value

from medrecords.evaluation.analytic import Analytic, Assessment, Table
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.placement import ScopeType

if TYPE_CHECKING:
    from medrecords.evaluation.analytic import Cell
    from medrecords.evaluation.placement import Placement

KeyedValueType = TypeVar("KeyedValueType", bound=Value)


class ChecksRun(Analytic[Findings[ScopeType], int], Generic[ScopeType]):
    """How many checks were run: every assessment in the findings."""

    def compute(self, findings: Findings[ScopeType]) -> int:
        """Counts the assessments.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            int: The number of assessments, values_by_key ones once per key.
        """
        return sum(1 for _ in findings.each(Assessment))

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Checks run"


class ChecksFailed(Analytic[Findings[ScopeType], int], Generic[ScopeType]):
    """How many checks did not pass: every assessment in the findings that failed."""

    def compute(self, findings: Findings[ScopeType]) -> int:
        """Counts the assessments that did not pass.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            int: The number of assessments that did not pass.
        """
        return sum(1 for _, check in findings.each(Assessment) if not check.passed)

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Checks failed"


class FailedChecks(Analytic[Findings[ScopeType], Table], Generic[ScopeType]):
    """Which checks did not pass: every failed assessment, its value and requirement."""

    def compute(self, findings: Findings[ScopeType]) -> Table:
        """Lists the assessments that did not pass.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            Table: One row per failed assessment: the path it was found at, its
                value and the condition it did not meet.
        """
        rows: List[List[Cell]] = [
            [path, check.value, check.requirement_label]
            for path, check in findings.each(Assessment)
            if not check.passed
        ]

        return Table(["check", "value", "required"], rows)

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Failed checks"


class AnalyticsFailed(Analytic[Findings[ScopeType], int], Generic[ScopeType]):
    """How many computations failed: analytics, conclusions and derivations."""

    def compute(self, findings: Findings[ScopeType]) -> int:
        """Counts the failures.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            int: The number of failures, values_by_key ones once per key.
        """
        return sum(1 for _ in findings.failures())

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Entries not computed"


class FailedAnalytics(Analytic[Findings[ScopeType], Table], Generic[ScopeType]):
    """Which computations failed: every failure with its exception type and message."""

    def compute(self, findings: Findings[ScopeType]) -> Table:
        """Lists the failures.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            Table: One row per failure: the path it was found at, the type of
                the exception and its message.
        """
        rows: List[List[Cell]] = [
            [path, failure.exception_type, failure.message]
            for path, failure in findings.failures()
        ]

        return Table(["entry", "exception type", "message"], rows)

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Entries not computed, with their errors"


class Mean(Analytic[Findings[ScopeType], float], Generic[ScopeType]):
    """The mean of the scores other placements reported."""

    _scores: Sequence[Placement[ScopeType, float]]

    def __init__(self, scores: Sequence[Placement[ScopeType, float]]) -> None:
        """Initializes a mean.

        Args:
            scores (Sequence[Placement[ScopeType, float]]): The placements
                reporting the scores.
        """
        self._scores = scores

    def compute(self, findings: Findings[ScopeType]) -> float:
        """Averages the scores.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            float: The mean of the scores.
        """
        return mean(findings[score] for score in self._scores)

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Mean"


class KeyedMean(Analytic[Findings[ScopeType], float], Generic[ScopeType]):
    """The mean of the scores one placement reported, one per key."""

    _scores_by_key: Placement[ScopeType, Mapping[Value, float]]

    def __init__(
        self, scores_by_key: Placement[ScopeType, Mapping[Value, float]]
    ) -> None:
        """Initializes a keyed mean.

        Args:
            scores_by_key (Placement[ScopeType, Mapping[Value, float]]): The
                placement reporting one score per key.
        """
        self._scores_by_key = scores_by_key

    def compute(self, findings: Findings[ScopeType]) -> float:
        """Averages the scores over the keys.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            float: The mean of the scores.
        """
        return mean(findings[self._scores_by_key].values())

    def title(self) -> Optional[str]:
        """Names the conclusion.

        Returns:
            Optional[str]: The heading.
        """
        return "Mean"


class KeyedTable(
    Analytic[Findings[ScopeType], Table], Generic[ScopeType, KeyedValueType]
):
    """One values_by_key result as a table: one row per key."""

    _values_by_key: Placement[ScopeType, Mapping[Value, KeyedValueType]]
    _key_heading: Identifier
    _value_heading: Identifier

    def __init__(
        self,
        values_by_key: Placement[ScopeType, Mapping[Value, KeyedValueType]],
        key_heading: Identifier,
        value_heading: Identifier,
    ) -> None:
        """Initializes a values_by_key table.

        Args:
            values_by_key (Placement[ScopeType, Mapping[Value, KeyedValueType]]): The
                placement reporting one value per key.
            key_heading (Identifier): The heading of the key column.
            value_heading (Identifier): The heading of the value column.
        """
        self._values_by_key = values_by_key
        self._key_heading = key_heading
        self._value_heading = value_heading

    def compute(self, findings: Findings[ScopeType]) -> Table:
        """Tabulates the values by key.

        Args:
            findings (Findings[ScopeType]): What the group found.

        Returns:
            Table: One row per key, in key order.
        """
        rows: List[List[Value]] = [
            [key, value] for key, value in findings[self._values_by_key].items()
        ]

        return Table([self._key_heading, self._value_heading], rows)
