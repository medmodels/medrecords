"""Analytics over one attribute of the nodes or edges of a MedRecord.

Every analytic takes the attribute and an expression selecting the elements to
look at: ``nodes()``, ``edges()``, or any filter of them such as
``nodes().filter(nodes().in_group("Patient"))``. Elements that do not carry the
attribute are left out, except in ``AttributeCompleteness``, which counts them.
An attribute set to null carries a value like any other, so it is counted as
present and reaches every question asked about the values.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, List, Mapping, Optional, TypeVar, Union

from medrecords.evaluation.analytic import (
    Analytic,
    Assessment,
    Distribution,
    Table,
)
from medrecords.evaluation.results import read, read_each, read_pairs
from medrecords.medrecord import MedRecord

if TYPE_CHECKING:
    from graphrecords import AttributeName, QueryError, Value, querying

    from medrecords.evaluation.analytic import Detail

IndexType = TypeVar("IndexType", "querying.NodeIndex", "querying.EdgeIndex")


class AttributeAnalytic(Analytic[MedRecord], Generic[IndexType]):
    """Base class for analytics over one attribute of the elements they look at.

    A subclass reads the elements carrying the attribute through ``_carrying``
    and their values through ``_values``. ``parameters`` records the attribute.
    """

    _attribute: AttributeName
    _elements: querying.ElementsExpression[IndexType, querying.Unordered]

    def __init__(
        self,
        attribute: AttributeName,
        elements: querying.ElementsExpression[IndexType, querying.Unordered],
    ) -> None:
        """Initializes an analytic over an attribute.

        Args:
            attribute (AttributeName): The attribute to look at.
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to look at.
        """
        self._attribute = attribute
        self._elements = elements

    def _carrying(
        self, medrecord: MedRecord
    ) -> querying.ElementsSeries[IndexType, querying.Unordered]:
        """Selects the elements that carry the attribute.

        Args:
            medrecord (MedRecord): The MedRecord to query.

        Returns:
            querying.ElementsSeries[IndexType, querying.Unordered]: The elements,
                bound to the MedRecord.
        """
        series = medrecord.query(self._elements)
        return series.filter(series.has_attribute(self._attribute))

    def _values(
        self, medrecord: MedRecord
    ) -> querying.BareValuesSeries[querying.Unordered]:
        """Reads the values of the attribute.

        Args:
            medrecord (MedRecord): The MedRecord to query.

        Returns:
            querying.BareValuesSeries[querying.Unordered]: One value per element
                carrying the attribute.
        """
        carrying = self._carrying(medrecord)
        return carrying.attribute(self._attribute).discard_index()

    def parameters(self) -> Mapping[str, Detail]:
        """Records the attribute.

        Returns:
            Mapping[str, Detail]: The attribute.
        """
        return {"attribute": self._attribute}


class AttributeMean(AttributeAnalytic[IndexType]):
    """The mean of an attribute."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the mean.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The mean, or None without values.
        """
        return self._values(medrecord).mean().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Mean {self._attribute}"


class AttributeMedian(AttributeAnalytic[IndexType]):
    """The median of an attribute."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the median.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The median, or None without values.
        """
        return self._values(medrecord).median().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Median {self._attribute}"


class AttributeStd(AttributeAnalytic[IndexType]):
    """The sample standard deviation of an attribute, as the query engine has it."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the standard deviation.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The standard deviation, or None without
                values.
        """
        return self._values(medrecord).std().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Standard deviation of {self._attribute}"


class AttributeMin(AttributeAnalytic[IndexType]):
    """The smallest value of an attribute."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the smallest value.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The smallest value, or None without values.
        """
        return self._values(medrecord).min().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Smallest {self._attribute}"


class AttributeMax(AttributeAnalytic[IndexType]):
    """The largest value of an attribute."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the largest value.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The largest value, or None without values.
        """
        return self._values(medrecord).max().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Largest {self._attribute}"


class AttributeSum(AttributeAnalytic[IndexType]):
    """The sum of an attribute."""

    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        """Computes the sum.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[Value, QueryError]: The sum, or None without values.
        """
        return self._values(medrecord).sum().evaluate()

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Sum of {self._attribute}"


class AttributeDistribution(AttributeAnalytic[IndexType]):
    """The distribution of a numeric attribute."""

    def compute(self, medrecord: MedRecord) -> Distribution:
        """Collects every value into a distribution.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Distribution: The values, of which there must be at least one.
        """
        return Distribution(read_each(self._values(medrecord).evaluate(), float))

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Distribution of {self._attribute}"


class AttributeCounts(AttributeAnalytic[IndexType]):
    """How often every value of an attribute occurs, most frequent first.

    Values that occur equally often come back in the reverse of the order the
    query engine hands them to the sort, so a limit can cut between two values
    that occur equally often.
    """

    _limit: Optional[int]

    def __init__(
        self,
        attribute: AttributeName,
        elements: querying.ElementsExpression[IndexType, querying.Unordered],
        limit: Optional[int] = None,
    ) -> None:
        """Initializes a count of attribute values.

        Args:
            attribute (AttributeName): The attribute to count.
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to look at.
            limit (Optional[int]): The most values to list, or None for all of
                them. Defaults to None.

        Raises:
            ValueError: If the limit is smaller than one.
        """
        super().__init__(attribute, elements)

        if limit is not None and limit < 1:
            msg = f"expected a limit of at least one, got {limit}"
            raise ValueError(msg)

        self._limit = limit

    def compute(self, medrecord: MedRecord) -> Table:
        """Counts the values.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Table: One row per value with its count and its share of all
                elements carrying the attribute.
        """
        carrying = self._carrying(medrecord)
        counts = carrying.group_by(carrying.attribute(self._attribute)).count()
        total = read(carrying.count().evaluate(), int)
        ranked = counts.ungroup_keyed().sort().reverse_order()

        if self._limit is not None:
            ranked = ranked.take(self._limit)

        rows: List[List[Value]] = [
            [value, count, count / total]
            for value, count in read_pairs(ranked.evaluate(), int)
        ]

        return Table(["value", "count", "share"], rows)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Values of {self._attribute}"

    def description(self) -> Optional[str]:
        """Explains the analytic.

        Returns:
            Optional[str]: The text under the heading.
        """
        return "Shares are of the elements that carry the attribute."

    def parameters(self) -> Mapping[str, Detail]:
        """Records the attribute and the limit.

        Returns:
            Mapping[str, Detail]: The details.
        """
        if self._limit is None:
            return super().parameters()

        return {**super().parameters(), "limit": self._limit}


class AttributeUniqueValues(AttributeAnalytic[IndexType]):
    """How many different values an attribute takes."""

    def compute(self, medrecord: MedRecord) -> int:
        """Counts the different values.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            int: The number of different values.
        """
        return read(self._values(medrecord).n_unique().evaluate(), int)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Different values of {self._attribute}"


class AttributeCompleteness(AttributeAnalytic[IndexType]):
    """The share of elements that carry an attribute, checked against a minimum."""

    _minimum: Optional[float]

    def __init__(
        self,
        attribute: AttributeName,
        elements: querying.ElementsExpression[IndexType, querying.Unordered],
        minimum: Optional[float] = None,
    ) -> None:
        """Initializes a completeness.

        Args:
            attribute (AttributeName): The attribute to look at.
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to look at.
            minimum (Optional[float]): The smallest acceptable share, between 0
                and 1, or None to report the share without a check. Defaults to
                None.

        Raises:
            ValueError: If the minimum is not between 0 and 1.
        """
        super().__init__(attribute, elements)

        if minimum is not None and not 0 <= minimum <= 1:
            msg = f"expected a minimum between 0 and 1, got {minimum}"
            raise ValueError(msg)

        self._minimum = minimum

    def compute(self, medrecord: MedRecord) -> Union[float, Assessment]:
        """Computes the share.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Union[float, Assessment]: The share of elements carrying the
                attribute, as an assessment against the minimum if one is given.

        Raises:
            ValueError: If there are no elements.
        """
        total = read(medrecord.query(self._elements).count().evaluate(), int)

        if total == 0:
            msg = "cannot compute the completeness of an attribute on no elements"
            raise ValueError(msg)

        carrying = read(self._carrying(medrecord).count().evaluate(), int)
        share = carrying / total

        if self._minimum is None:
            return share

        return Assessment(
            share, f"at least {self._minimum}", passed=share >= self._minimum
        )

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return f"Completeness of {self._attribute}"

    def description(self) -> Optional[str]:
        """Explains the analytic.

        Returns:
            Optional[str]: The text under the heading.
        """
        return "Share of the elements that carry the attribute."

    def parameters(self) -> Mapping[str, Detail]:
        """Records the attribute and the minimum.

        Returns:
            Mapping[str, Detail]: The details.
        """
        if self._minimum is None:
            return super().parameters()

        return {**super().parameters(), "minimum": self._minimum}
