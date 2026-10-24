"""Analytic and derivation base classes and the values they report."""

from __future__ import annotations

import copy
import math
from abc import ABC, abstractmethod
from bisect import bisect_right
from datetime import datetime, timedelta
from enum import Enum
from fractions import Fraction
from io import BytesIO
from itertools import pairwise
from statistics import NormalDist, mean, stdev
from typing import (
    TYPE_CHECKING,
    BinaryIO,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
)

import polars as pl

if TYPE_CHECKING:
    from graphrecords import Identifier, QueryError, Value


class Unit(Enum):
    """Enumeration of what a number measures, beyond what its type says.

    A typeset report prints a share as percent and points as percentage points;
    the numbers themselves stay fractions. Durations and datetimes carry no unit.
    """

    Share = "share"
    Points = "points"


class Table:
    """A tabular report value: headings and rows of values.

    A column may declare the unit of its numbers; the cells stay as given.
    """

    _headings: List[Identifier]
    _rows: List[List[Value]]
    _units: Dict[Identifier, Unit]

    def __init__(
        self,
        headings: Iterable[Identifier],
        rows: Iterable[Iterable[Value]],
        *,
        units: Optional[Mapping[Identifier, Unit]] = None,
    ) -> None:
        """Initializes a table from its headings and rows.

        Args:
            headings (Iterable[Identifier]): One heading per position in a row.
            rows (Iterable[Iterable[Value]]): The rows, each as long as the headings.
            units (Optional[Mapping[Identifier, Unit]]): The unit of the numbers
                of a column, by heading, for the columns that have one. Defaults
                to None.

        Raises:
            ValueError: If a heading repeats, a row does not hold one value per
                heading, or a unit names a heading the table does not have.
        """
        self._headings = list(headings)
        self._rows = [list(row) for row in rows]
        self._units = {} if units is None else dict(units)

        if len(set(self._headings)) != len(self._headings):
            msg = "every heading must be different"
            raise ValueError(msg)

        for row in self._rows:
            if len(row) != len(self._headings):
                msg = "every row must hold one value per heading"
                raise ValueError(msg)

        for heading in self._units:
            if heading not in self._headings:
                msg = f"a unit names the heading {heading!r}, which the table does not have"
                raise ValueError(msg)

    @classmethod
    def from_polars(
        cls,
        dataframe: pl.DataFrame,
        *,
        units: Optional[Mapping[Identifier, Unit]] = None,
    ) -> Table:
        """Converts a Polars DataFrame to a table, one heading per column.

        A DataFrame with an unnamed column, or with two columns of the same
        name, is rejected the way a table rejects such headings.

        Args:
            dataframe (pl.DataFrame): The DataFrame to convert.
            units (Optional[Mapping[Identifier, Unit]]): The unit of the numbers
                of a column, by column name, for the columns that have one.
                Defaults to None.

        Returns:
            Table: The DataFrame as a table.

        Raises:
            TypeError: If a cell holds something a table cannot report, such as
                a date, a list or a decimal.
        """
        rows: List[List[Value]] = []

        for row in dataframe.iter_rows():
            values: List[Value] = []

            for heading, cell in zip(dataframe.columns, row, strict=True):
                if cell is not None and not isinstance(
                    cell, (str, int, float, datetime, timedelta)
                ):
                    msg = f"column {heading!r} holds {cell!r}, which a table cannot report"
                    raise TypeError(msg)

                values.append(cell)

            rows.append(values)
        return cls(dataframe.columns, rows, units=units)

    def to_polars(self) -> pl.DataFrame:
        """Converts the table to a Polars DataFrame, one column per heading.

        An integer heading becomes the text of the number, because a column
        name is a string. A column holding values of more than one kind is
        rejected by Polars.

        Returns:
            pl.DataFrame: The table as a DataFrame.
        """
        return pl.DataFrame(
            {
                str(heading): [row[position] for row in self._rows]
                for position, heading in enumerate(self._headings)
            }
        )

    @property
    def headings(self) -> List[Identifier]:
        """The headings of the Table.

        Returns:
            List[Identifier]: One heading per position in a row.
        """
        return list(self._headings)

    @property
    def rows(self) -> List[List[Value]]:
        """The rows of the Table.

        Returns:
            List[List[Value]]: Every row, in order.
        """
        return [list(row) for row in self._rows]

    @property
    def units(self) -> Dict[Identifier, Unit]:
        """The units of the columns that declare one.

        Returns:
            Dict[Identifier, Unit]: The unit by heading.
        """
        return dict(self._units)

    def __eq__(self, other: object) -> bool:
        """Compares the Table with another one by its headings, rows and units.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same headings, rows and units, otherwise
                False.
        """
        if not isinstance(other, Table):
            return NotImplemented

        return (
            self._headings == other._headings
            and self._rows == other._rows
            and self._units == other._units
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Table.

        Returns:
            str: The headings and rows of the Table, and its units when it
                declares any.
        """
        if not self._units:
            return f"Table(headings={self._headings!r}, rows={self._rows!r})"

        return (
            f"Table(headings={self._headings!r}, rows={self._rows!r}, "
            f"units={self._units!r})"
        )


class Figure(Protocol):
    """Protocol for figures that save themselves as SVG."""

    def savefig(
        self, file: BinaryIO, /, *, format: str, bbox_inches: Literal["tight"]
    ) -> None:
        """Saves the figure.

        Args:
            file (BinaryIO): Where the figure is written to.
            format (str): The image format.
            bbox_inches (Literal["tight"]): How the bounding box is chosen.
        """
        ...


class Plot:
    """A plot as SVG text."""

    _svg: str

    def __init__(self, svg: str) -> None:
        """Initializes a plot from SVG text.

        Args:
            svg (str): The plot as SVG text.
        """
        self._svg = svg

    @classmethod
    def from_figure(cls, figure: Figure) -> Plot:
        """Creates a plot from a figure by saving it as SVG.

        Args:
            figure (Figure): The figure to save, such as a matplotlib figure or a
                seaborn grid.

        Returns:
            Plot: The figure as a plot.
        """
        buffer = BytesIO()
        figure.savefig(buffer, format="svg", bbox_inches="tight")
        return cls(buffer.getvalue().decode())

    @property
    def svg(self) -> str:
        """The plot as SVG text.

        Returns:
            str: The SVG text.
        """
        return self._svg

    def __eq__(self, other: object) -> bool:
        """Compares the Plot with another one by its SVG text.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same SVG text, otherwise False.
        """
        if not isinstance(other, Plot):
            return NotImplemented

        return self._svg == other._svg

    def __repr__(self) -> str:
        """Returns the string representation of the Plot.

        Returns:
            str: The length of the SVG text.
        """
        return f"Plot({len(self._svg)} characters of SVG)"


class Measurement:
    """A number with the uncertainty of its estimation.

    The uncertainty is an interval, a p-value, or both.
    """

    _value: float
    _lower: Optional[float]
    _upper: Optional[float]
    _p_value: Optional[float]
    _unit: Optional[Unit]

    def __init__(
        self,
        value: float,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
        p_value: Optional[float] = None,
        *,
        unit: Optional[Unit] = None,
    ) -> None:
        """Initializes a measurement.

        Args:
            value (float): The estimate.
            lower (Optional[float]): The lower end of its interval. Defaults to
                None.
            upper (Optional[float]): The upper end of its interval. Defaults to
                None.
            p_value (Optional[float]): The p-value of the test it came from.
                Defaults to None.
            unit (Optional[Unit]): What the estimate and its interval measure,
                or None for a plain number. Defaults to None.
        """
        self._value = float(value)
        self._lower = None if lower is None else float(lower)
        self._upper = None if upper is None else float(upper)
        self._p_value = None if p_value is None else float(p_value)
        self._unit = unit

    @classmethod
    def from_proportion(
        cls, successes: int, total: int, confidence: float = 0.95
    ) -> Measurement:
        """Estimates a share with a Wilson score interval.

        The measurement carries the share unit.

        Args:
            successes (int): How many of the trials succeeded.
            total (int): How many trials there were.
            confidence (float): The confidence level of the interval. Defaults
                to 0.95.

        Returns:
            Measurement: The share with its interval.

        Raises:
            ValueError: If there are no trials, more successes than trials, or
                the confidence level is not strictly between 0 and 1.
        """
        if total < 1:
            msg = "a proportion needs at least one trial"
            raise ValueError(msg)

        if not 0 <= successes <= total:
            msg = f"expected between 0 and {total} successes, got {successes}"
            raise ValueError(msg)

        if not 0 < confidence < 1:
            msg = f"expected a confidence level between 0 and 1, got {confidence}"
            raise ValueError(msg)

        z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
        share = successes / total
        denominator = 1 + z * z / total
        centre = (share + z * z / (2 * total)) / denominator
        half = (
            z * math.sqrt(share * (1 - share) / total + z * z / (4 * total * total))
        ) / denominator
        return cls(
            share,
            lower=max(0.0, centre - half),
            upper=min(1.0, centre + half),
            unit=Unit.Share,
        )

    @property
    def value(self) -> float:
        """The estimate.

        Returns:
            float: The estimate.
        """
        return self._value

    @property
    def lower(self) -> Optional[float]:
        """The lower end of the interval.

        Returns:
            Optional[float]: The lower end, or None.
        """
        return self._lower

    @property
    def upper(self) -> Optional[float]:
        """The upper end of the interval.

        Returns:
            Optional[float]: The upper end, or None.
        """
        return self._upper

    @property
    def p_value(self) -> Optional[float]:
        """The p-value of the test the measurement came from.

        Returns:
            Optional[float]: The p-value, or None.
        """
        return self._p_value

    @property
    def unit(self) -> Optional[Unit]:
        """What the estimate and its interval measure.

        Returns:
            Optional[Unit]: The unit, or None for a plain number.
        """
        return self._unit

    def __eq__(self, other: object) -> bool:
        """Compares the Measurement with another one by its numbers and unit.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same numbers and unit, otherwise False.
        """
        if not isinstance(other, Measurement):
            return NotImplemented

        return (
            self._value == other._value
            and self._lower == other._lower
            and self._upper == other._upper
            and self._p_value == other._p_value
            and self._unit == other._unit
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Measurement.

        Returns:
            str: The numbers of the Measurement, and its unit when it has one.
        """
        numbers = (
            f"Measurement({self._value!r}, lower={self._lower!r}, "
            f"upper={self._upper!r}, p_value={self._p_value!r}"
        )

        if self._unit is None:
            return numbers + ")"

        return f"{numbers}, unit={self._unit!r})"


class Assessment:
    """A value checked against a requirement, with the verdict of the check."""

    _value: Value
    _requirement_label: str
    _passed: bool
    _unit: Optional[Unit]

    def __init__(
        self,
        value: Value,
        requirement_label: str,
        *,
        passed: bool,
        unit: Optional[Unit] = None,
    ) -> None:
        """Initializes an assessment.

        Args:
            value (Value): The value that was found.
            requirement_label (str): What was required of the value, in words
                that follow "passed" or "failed", such as "at least 99.0%".
            passed (bool): Whether the value met the requirement.
            unit (Optional[Unit]): What a numeric value measures, or None for a
                plain value. Defaults to None.
        """
        self._value = value
        self._requirement_label = requirement_label
        self._passed = passed
        self._unit = unit

    @property
    def value(self) -> Value:
        """The value that was found.

        Returns:
            Value: The value.
        """
        return self._value

    @property
    def requirement_label(self) -> str:
        """What was required of the value.

        Returns:
            str: The requirement label.
        """
        return self._requirement_label

    @property
    def passed(self) -> bool:
        """Whether the value met the requirement.

        Returns:
            bool: True if the assessment passed, otherwise False.
        """
        return self._passed

    @property
    def unit(self) -> Optional[Unit]:
        """What the assessed value measures.

        Returns:
            Optional[Unit]: The unit, or None for a plain value.
        """
        return self._unit

    def __eq__(self, other: object) -> bool:
        """Compares the Assessment with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same value, requirement label, verdict
                and unit, otherwise False.
        """
        if not isinstance(other, Assessment):
            return NotImplemented

        return (
            self._value == other._value
            and self._requirement_label == other._requirement_label
            and self._passed == other._passed
            and self._unit == other._unit
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Assessment.

        Returns:
            str: The value, requirement label and verdict of the Assessment, and
                its unit when it has one.
        """
        contents = (
            f"Assessment({self._value!r}, {self._requirement_label!r}, "
            f"passed={self._passed!r}"
        )

        if self._unit is None:
            return contents + ")"

        return f"{contents}, unit={self._unit!r})"


class Bin(TypedDict):
    """One bin of a histogram."""

    lower: float
    upper: float
    count: int


class Statistics(TypedDict):
    """The summary statistics of numeric values."""

    count: int
    mean: float
    standard_deviation: float
    minimum: float
    lower_quartile: float
    median: float
    upper_quartile: float
    maximum: float


def _rounded_width(span: float) -> Fraction:
    exponent = math.floor(math.log10(span))
    fraction = span / 10.0**exponent

    if fraction <= 1:
        step = 1
    elif fraction <= 2:
        step = 2
    elif fraction <= 5:
        step = 5
    else:
        step = 10

    return step * Fraction(10) ** exponent


class Distribution:
    """The values of a numeric distribution and their summary statistics."""

    _values: List[float]
    _bin_count: Optional[int]

    def __init__(
        self, values: Iterable[float], bin_count: Optional[int] = None
    ) -> None:
        """Initializes a distribution from its values.

        Args:
            values (Iterable[float]): The values, at least one, all finite.
            bin_count (Optional[int]): The number of bins its histogram aims
                for, or None for Sturges' rule. Defaults to None.

        Raises:
            ValueError: If there is no value, a value is not finite, or fewer
                than one bin is asked for.
        """
        self._values = [float(value) for value in values]
        self._bin_count = bin_count

        if not self._values:
            msg = "a distribution must hold at least one value"
            raise ValueError(msg)

        if not all(math.isfinite(value) for value in self._values):
            msg = "every value of a distribution must be finite"
            raise ValueError(msg)

        if bin_count is not None and bin_count < 1:
            msg = "a histogram needs at least one bin"
            raise ValueError(msg)

    @property
    def values(self) -> List[float]:
        """The values of the Distribution.

        Returns:
            List[float]: Every value, in the order given.
        """
        return list(self._values)

    @property
    def bin_count(self) -> Optional[int]:
        """The number of bins the histogram of the Distribution aims for.

        Returns:
            Optional[int]: The number of bins, or None for Sturges' rule.
        """
        return self._bin_count

    @property
    def count(self) -> int:
        """The number of values.

        Returns:
            int: The number of values.
        """
        return len(self._values)

    @property
    def mean(self) -> float:
        """The arithmetic mean of the values.

        Returns:
            float: The mean.
        """
        return mean(self._values)

    @property
    def standard_deviation(self) -> float:
        """The standard deviation of the values, over one degree less.

        Returns:
            float: The standard deviation, or 0.0 for a single value.
        """
        if len(self._values) == 1:
            return 0.0

        return stdev(self._values)

    @property
    def minimum(self) -> float:
        """The smallest value.

        Returns:
            float: The minimum.
        """
        return min(self._values)

    @property
    def lower_quartile(self) -> float:
        """The value a quarter of the values lie below, interpolated linearly.

        Returns:
            float: The lower quartile.
        """
        return self._quantile(0.25)

    @property
    def median(self) -> float:
        """The value half of the values lie below.

        Returns:
            float: The median.
        """
        return self._quantile(0.5)

    @property
    def upper_quartile(self) -> float:
        """The value three quarters of the values lie below, interpolated linearly.

        Returns:
            float: The upper quartile.
        """
        return self._quantile(0.75)

    @property
    def maximum(self) -> float:
        """The largest value.

        Returns:
            float: The maximum.
        """
        return max(self._values)

    @property
    def statistics(self) -> Statistics:
        """The summary statistics of the values.

        Returns:
            Statistics: The count, mean, standard deviation, minimum, quartiles
                and maximum.
        """
        ordered = sorted(self._values)

        return {
            "count": len(ordered),
            "mean": mean(ordered),
            "standard_deviation": self.standard_deviation,
            "minimum": ordered[0],
            "lower_quartile": self._interpolated(ordered, 0.25),
            "median": self._interpolated(ordered, 0.5),
            "upper_quartile": self._interpolated(ordered, 0.75),
            "maximum": ordered[-1],
        }

    def histogram(self, bin_count: Optional[int] = None) -> Histogram:
        """Counts the values in bins of equal, rounded width.

        Args:
            bin_count (Optional[int]): The number of bins to aim for, or None
                for the number the Distribution was given, or Sturges' rule if
                it was given none. Defaults to None.

        Returns:
            Histogram: The counts per bin from the lowest edge to the highest,
                with the statistics of the values.
        """
        return Distribution.shared_histograms([self], bin_count)[0]

    @classmethod
    def shared_histograms(
        cls, distributions: Sequence[Distribution], bin_count: Optional[int] = None
    ) -> List[Histogram]:
        """Counts the values of several distributions in the same bins.

        The bins span the smallest and the largest value over all distributions
        in equal, rounded widths, so that the histograms can be drawn on one
        axis.

        Args:
            distributions (Sequence[Distribution]): The distributions, at least
                one.
            bin_count (Optional[int]): The number of bins to aim for, or None
                for the largest number a distribution was given, or Sturges'
                rule on the largest distribution if none was given any.
                Defaults to None.

        Returns:
            List[Histogram]: One histogram per distribution, in the order given,
                each over the shared edges and with its own statistics.

        Raises:
            ValueError: If there is no distribution, or fewer than one bin is
                asked for.
        """
        if not distributions:
            msg = "shared histograms need at least one distribution"
            raise ValueError(msg)

        given = [
            distribution._bin_count
            for distribution in distributions
            if distribution._bin_count is not None
        ]
        asked = max(given, default=None) if bin_count is None else bin_count
        largest = max(len(distribution._values) for distribution in distributions)
        count = math.ceil(math.log2(largest)) + 1 if asked is None else asked

        if count < 1:
            msg = "a histogram needs at least one bin"
            raise ValueError(msg)

        minimum = min(distribution.minimum for distribution in distributions)
        maximum = max(distribution.maximum for distribution in distributions)
        span = (maximum - minimum) / count
        edges = cls._shared_edges(distributions, minimum, maximum, span)

        return [
            Histogram._from_distribution(distribution, edges)
            for distribution in distributions
        ]

    @staticmethod
    def _shared_edges(
        distributions: Sequence[Distribution],
        minimum: float,
        maximum: float,
        span: float,
    ) -> List[float]:
        """Chooses the rounded edges shared histograms are counted over.

        Args:
            distributions (Sequence[Distribution]): The distributions binned.
            minimum (float): The smallest value over all distributions.
            maximum (float): The largest value over all distributions.
            span (float): The width a bin would have before rounding.

        Returns:
            List[float]: The edges, from the lowest to the highest; one bin
                spanning the values when they cannot be told apart by rounded
                edges, or one bin of width one when they are all the same.
        """
        if minimum == maximum:
            return [minimum, minimum + 1]

        if span == 0:
            return [minimum, maximum]

        width = _rounded_width(span)

        if all(
            value.is_integer()
            for distribution in distributions
            for value in distribution._values
        ):
            width = max(width, Fraction(1))

        start = Fraction(minimum) // width * width
        edges = [float(start)]

        while edges[-1] <= maximum:
            edges.append(float(start + len(edges) * width))

        if any(lower == upper for lower, upper in pairwise(edges)):
            return [minimum, maximum]

        if all(
            not any(edges[0] <= value < edges[1] for value in distribution._values)
            for distribution in distributions
        ):
            return edges[1:]

        return edges

    def _quantile(self, fraction: float) -> float:
        return self._interpolated(sorted(self._values), fraction)

    @staticmethod
    def _interpolated(ordered: Sequence[float], fraction: float) -> float:
        """Interpolates the value a fraction of sorted values lie below.

        Args:
            ordered (Sequence[float]): The values, sorted, at least one.
            fraction (float): The fraction, between 0 and 1.

        Returns:
            float: The interpolated quantile.
        """
        position = fraction * (len(ordered) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)

        if ordered[lower] == ordered[upper]:
            return ordered[lower]

        weight = position - lower
        return ordered[lower] * (1 - weight) + ordered[upper] * weight

    def __eq__(self, other: object) -> bool:
        """Compares the Distribution with another one by its values and bins.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same values in the same order and aim
                for the same number of bins, otherwise False.
        """
        if not isinstance(other, Distribution):
            return NotImplemented

        return self._values == other._values and self._bin_count == other._bin_count

    def __repr__(self) -> str:
        """Returns the string representation of the Distribution.

        Returns:
            str: The number of values of the Distribution.
        """
        return f"Distribution({len(self._values)} values)"


class Histogram:
    """Counts of numeric values in bins over fixed edges, without the values.

    Every bin holds the values from its lower edge up to, excluding, its upper
    edge; the last bin includes its upper edge. Values below the first edge and
    above the last are counted apart, so that nothing is lost silently. The
    statistics describe every value, the ones outside the edges included.
    """

    _edges: List[float]
    _counts: List[int]
    _below_count: int
    _above_count: int
    _statistics: Optional[Statistics]

    def __init__(
        self,
        edges: Iterable[float],
        counts: Iterable[int],
        *,
        below_count: int = 0,
        above_count: int = 0,
        statistics: Optional[Statistics] = None,
    ) -> None:
        """Initializes a histogram from its edges and counts.

        Args:
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing.
            counts (Iterable[int]): One count per bin, so one fewer than the
                edges.
            below_count (int): How many values lay below the first edge.
                Defaults to 0.
            above_count (int): How many values lay above the last edge.
                Defaults to 0.
            statistics (Optional[Statistics]): The statistics of every value
                counted, or None when there is none. Defaults to None.

        Raises:
            ValueError: If there are fewer than two edges, an edge is not finite
                or not above the one before, the counts are not one per bin, or
                a count is negative.
        """
        self._edges = self._checked_edges(edges)
        self._counts = list(counts)
        self._below_count = below_count
        self._above_count = above_count
        self._statistics = copy.copy(statistics)

        if len(self._counts) != len(self._edges) - 1:
            msg = "a histogram needs one count per bin"
            raise ValueError(msg)

        if any(count < 0 for count in (*self._counts, below_count, above_count)):
            msg = "every count of a histogram must be zero or more"
            raise ValueError(msg)

    @classmethod
    def from_values(cls, values: Iterable[float], edges: Iterable[float]) -> Histogram:
        """Counts values into bins over given edges.

        Args:
            values (Iterable[float]): The values to count, all finite.
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing.

        Returns:
            Histogram: The counts per bin, the counts outside the edges, and the
                statistics of the values, or none when there is no value.
        """
        materialized = [float(value) for value in values]

        if not materialized:
            bounds = cls._checked_edges(edges)
            return cls(bounds, [0] * (len(bounds) - 1))

        return cls._from_distribution(Distribution(materialized), edges)

    @classmethod
    def _from_distribution(
        cls, distribution: Distribution, edges: Iterable[float]
    ) -> Histogram:
        """Counts the values of a distribution into bins over given edges.

        Args:
            distribution (Distribution): The values to count, with their
                statistics.
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing.

        Returns:
            Histogram: The counts per bin, the counts outside the edges, and the
                statistics of the distribution.
        """
        bounds = cls._checked_edges(edges)
        counts = [0] * (len(bounds) - 1)
        below_count = 0
        above_count = 0

        for value in distribution._values:
            if value < bounds[0]:
                below_count += 1
            elif value > bounds[-1]:
                above_count += 1
            else:
                counts[min(bisect_right(bounds, value), len(bounds) - 1) - 1] += 1

        return cls(
            bounds,
            counts,
            below_count=below_count,
            above_count=above_count,
            statistics=distribution.statistics,
        )

    @staticmethod
    def _checked_edges(edges: Iterable[float]) -> List[float]:
        """Checks bin edges and returns them as floats.

        Args:
            edges (Iterable[float]): The bin edges.

        Returns:
            List[float]: The edges, from the lowest to the highest.

        Raises:
            ValueError: If there are fewer than two edges, an edge is not finite,
                or an edge is not above the one before.
        """
        bounds = [float(edge) for edge in edges]

        if len(bounds) < 2:
            msg = "a histogram needs at least two edges"
            raise ValueError(msg)

        if not all(math.isfinite(edge) for edge in bounds):
            msg = "every edge of a histogram must be finite"
            raise ValueError(msg)

        if any(lower >= upper for lower, upper in pairwise(bounds)):
            msg = "the edges of a histogram must be increasing"
            raise ValueError(msg)

        return bounds

    @property
    def edges(self) -> List[float]:
        """The bin edges of the Histogram.

        Returns:
            List[float]: The edges, from the lowest to the highest.
        """
        return list(self._edges)

    @property
    def counts(self) -> List[int]:
        """The counts per bin of the Histogram.

        Returns:
            List[int]: One count per bin, from the lowest bin to the highest.
        """
        return list(self._counts)

    @property
    def below_count(self) -> int:
        """How many values lay below the first edge.

        Returns:
            int: The count below the edges.
        """
        return self._below_count

    @property
    def above_count(self) -> int:
        """How many values lay above the last edge.

        Returns:
            int: The count above the edges.
        """
        return self._above_count

    @property
    def statistics(self) -> Optional[Statistics]:
        """The statistics of every value counted, the ones outside included.

        Returns:
            Optional[Statistics]: The statistics, or None without values.
        """
        return copy.copy(self._statistics)

    @property
    def count(self) -> int:
        """How many values were counted, the ones outside the edges included.

        Returns:
            int: The number of values.
        """
        return sum(self._counts) + self._below_count + self._above_count

    @property
    def bins(self) -> List[Bin]:
        """The bins of the Histogram.

        Returns:
            List[Bin]: One bin per count, from the lowest edge to the highest.
        """
        return [
            {"lower": lower, "upper": upper, "count": count}
            for (lower, upper), count in zip(
                pairwise(self._edges), self._counts, strict=True
            )
        ]

    def to_polars(self) -> pl.DataFrame:
        """Converts the bins to a Polars DataFrame.

        Returns:
            pl.DataFrame: One row per bin with its lower edge, upper edge and
                count.
        """
        return pl.DataFrame(
            {
                "lower": self._edges[:-1],
                "upper": self._edges[1:],
                "count": self._counts,
            }
        )

    def __eq__(self, other: object) -> bool:
        """Compares the Histogram with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same edges, counts, outside counts and
                statistics, otherwise False.
        """
        if not isinstance(other, Histogram):
            return NotImplemented

        return (
            self._edges == other._edges
            and self._counts == other._counts
            and self._below_count == other._below_count
            and self._above_count == other._above_count
            and self._statistics == other._statistics
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Histogram.

        Returns:
            str: The number of bins and values of the Histogram.
        """
        return f"Histogram({len(self._counts)} bins, {self.count} values)"


class Counts:
    """How often every value of a set occurs, with the total the shares are of.

    The total is the number of values counted, which exceeds the sum of the
    counts when only the most frequent values are listed. Values are told apart
    the way a mapping tells its keys apart, and their order is part of the
    Counts: two Counts listing the same values in a different order differ.
    """

    _counts: Dict[Value, int]
    _total: int

    def __init__(
        self, counts: Mapping[Value, int], total: Optional[int] = None
    ) -> None:
        """Initializes counts from a mapping of values to how often they occur.

        Args:
            counts (Mapping[Value, int]): How often every value occurs, in the
                order they are listed.
            total (Optional[int]): The number of values counted, or None for
                the sum of the counts. Defaults to None.

        Raises:
            ValueError: If a count is negative, or the total is below the sum of
                the counts.
        """
        self._counts = dict(counts)
        self._total = sum(self._counts.values()) if total is None else total

        if any(count < 0 for count in self._counts.values()):
            msg = "every count must be zero or more"
            raise ValueError(msg)

        if self._total < sum(self._counts.values()):
            msg = "the total must be at least the sum of the counts"
            raise ValueError(msg)

    @property
    def by_value(self) -> Dict[Value, int]:
        """How often every value occurs.

        Returns:
            Dict[Value, int]: The count per value, in the order given.
        """
        return dict(self._counts)

    @property
    def total(self) -> int:
        """The number of values counted.

        Returns:
            int: The total the shares are of.
        """
        return self._total

    def to_table(self) -> Table:
        """Converts the Counts to a table of values, counts and shares.

        Returns:
            Table: One row per value with its count and its share of the total,
                which is None when the total is zero; the share column carries
                the share unit.
        """
        rows: List[List[Value]] = [
            [value, count, None if self._total == 0 else count / self._total]
            for value, count in self._counts.items()
        ]

        return Table(["value", "count", "share"], rows, units={"share": Unit.Share})

    def to_polars(self) -> pl.DataFrame:
        """Converts the Counts to a Polars DataFrame of values, counts and shares.

        Returns:
            pl.DataFrame: One row per value with its count and its share.
        """
        return self.to_table().to_polars()

    def __eq__(self, other: object) -> bool:
        """Compares the Counts with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same counts in the same order and the
                same total, otherwise False.
        """
        if not isinstance(other, Counts):
            return NotImplemented

        return (
            list(self._counts.items()) == list(other._counts.items())
            and self._total == other._total
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Counts.

        Returns:
            str: The number of values listed and the total of the Counts.
        """
        return f"Counts({len(self._counts)} values of {self._total})"


#: A type alias for the value kinds an analytic can report.
ReportValue: TypeAlias = Union[
    "Value", Table, Plot, Measurement, Assessment, Distribution, Histogram, Counts
]

#: A type alias for one parameter or summary item: a value or a sequence of values.
Detail: TypeAlias = Union["Value", Sequence["Value"]]

InputsType = TypeVar("InputsType")

ResultType = TypeVar("ResultType", bound=ReportValue, covariant=True)

DerivedType = TypeVar("DerivedType")


class Analytic(ABC, Generic[InputsType, ResultType]):
    """One computation over inputs, reporting one value of the result type."""

    @abstractmethod
    def compute(self, inputs: InputsType, /) -> Union[ResultType, QueryError]:
        """Computes the value of the analytic.

        Args:
            inputs (InputsType): The inputs the analytic is placed over.

        Returns:
            Union[ResultType, QueryError]: The value, or the query engine's in-band
                failure standing in for it.
        """

    def title(self) -> Optional[str]:
        """Names the analytic in a typeset report.

        Returns:
            Optional[str]: The heading, or None to use the name in the group.
        """
        return None

    def description(self) -> Optional[str]:
        """Describes the analytic in a typeset report.

        Returns:
            Optional[str]: The text under the heading, or None for none.
        """
        return None

    def parameters(self) -> Mapping[str, Detail]:
        """Records what the analytic was configured with.

        Returns:
            Mapping[str, Detail]: The parameters by name; empty unless overridden.
        """
        return {}


class Derivation(ABC, Generic[InputsType, DerivedType]):
    """Shared work computed once per group, deriving the inputs of a nested one."""

    @abstractmethod
    def derive(self, inputs: InputsType, /) -> DerivedType:
        """Derives the inputs of the nested group.

        Args:
            inputs (InputsType): The inputs of the enclosing group.

        Returns:
            DerivedType: The derived inputs.
        """

    def parameters(self) -> Mapping[str, Detail]:
        """Records what the derivation was configured with.

        Returns:
            Mapping[str, Detail]: The parameters by name; empty unless overridden.
        """
        return {}

    def summarize(self, derived: DerivedType, /) -> Mapping[str, Detail]:
        """Records what the derivation produced.

        A summary that fails fails the derivation.

        Args:
            derived (DerivedType): What derive returned.

        Returns:
            Mapping[str, Detail]: The summary by name; empty unless overridden.
        """
        return {}
