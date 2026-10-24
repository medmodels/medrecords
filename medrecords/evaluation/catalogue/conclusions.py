"""Conclusions over what an evaluation or a group found."""

from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING, Generic, List, Mapping, Optional, Sequence, TypeVar

from graphrecords import Identifier, Value

from medrecords.evaluation.analytic import Analytic, Assessment, Table
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.placement import ScopeType

if TYPE_CHECKING:
    from medrecords.evaluation.analytic import Detail
    from medrecords.evaluation.placement import Placement

CellType = TypeVar("CellType", bound=Value)


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
                value and the requirement it did not meet.
        """
        rows: List[List[Value]] = [
            [
                " / ".join(str(name) for name in path),
                check.value,
                check.requirement_label,
            ]
            for path, check in findings.each(Assessment)
            if not check.passed
        ]

        return Table(["check", "value", "requirement"], rows)

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
        return "Analytics failed"


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

    def parameters(self) -> Mapping[str, Detail]:
        """Records how many scores go into the mean.

        Returns:
            Mapping[str, Detail]: The number of scores.
        """
        return {"score_count": len(self._scores)}


class KeyedTable(Analytic[Findings[ScopeType], Table], Generic[ScopeType, CellType]):
    """One values_by_key result as a table: one row per key."""

    _values_by_key: Placement[ScopeType, Mapping[Value, CellType]]
    _key_heading: Identifier
    _value_heading: Identifier

    def __init__(
        self,
        values_by_key: Placement[ScopeType, Mapping[Value, CellType]],
        key_heading: Identifier,
        value_heading: Identifier,
    ) -> None:
        """Initializes a values_by_key table.

        Args:
            values_by_key (Placement[ScopeType, Mapping[Value, CellType]]): The
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
