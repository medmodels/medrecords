"""Analytic and derivation base classes and the values they report."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from fractions import Fraction
from io import BytesIO
from itertools import pairwise
from statistics import NormalDist, mean, median, stdev
from typing import (
    TYPE_CHECKING,
    BinaryIO,
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
    from graphrecords import QueryError
    from graphrecords.types import Value


class Table:
    """A tabular report value: headings and rows of values."""

    _headings: List[str]
    _rows: List[List[Value]]

    def __init__(
        self, headings: Iterable[str], rows: Iterable[Iterable[Value]]
    ) -> None:
        """Initializes a table from its headings and rows.

        Args:
            headings (Iterable[str]): One heading per position in a row.
            rows (Iterable[Iterable[Value]]): The rows, each as long as the headings.

        Raises:
            ValueError: If a heading repeats, or a row does not hold one value
                per heading.
        """
        self._headings = list(headings)
        self._rows = [list(row) for row in rows]

        if len(set(self._headings)) != len(self._headings):
            msg = "every heading must be different"
            raise ValueError(msg)

        for row in self._rows:
            if len(row) != len(self._headings):
                msg = "every row must hold one value per heading"
                raise ValueError(msg)

    @classmethod
    def from_polars(cls, dataframe: pl.DataFrame) -> Table:
        """Converts a Polars DataFrame to a table, one heading per column.

        A DataFrame with an unnamed column, or with two columns of the same
        name, is rejected the way a table rejects such headings.

        Args:
            dataframe (pl.DataFrame): The DataFrame to convert.

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
        return cls(dataframe.columns, rows)

    def to_polars(self) -> pl.DataFrame:
        """Converts the table to a Polars DataFrame, one column per heading.

        A column holding values of more than one kind is rejected by Polars.

        Returns:
            pl.DataFrame: The table as a DataFrame.
        """
        return pl.DataFrame(
            {
                heading: [row[position] for row in self._rows]
                for position, heading in enumerate(self._headings)
            }
        )

    @property
    def headings(self) -> List[str]:
        """The headings of the Table.

        Returns:
            List[str]: One heading per position in a row.
        """
        return list(self._headings)

    @property
    def rows(self) -> List[List[Value]]:
        """The rows of the Table.

        Returns:
            List[List[Value]]: Every row, in order.
        """
        return [list(row) for row in self._rows]

    def __eq__(self, other: object) -> bool:
        """Compares the Table with another one by its headings and rows.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same headings and rows, otherwise False.
        """
        if not isinstance(other, Table):
            return NotImplemented

        return self._headings == other._headings and self._rows == other._rows

    def __repr__(self) -> str:
        """Returns the string representation of the Table.

        Returns:
            str: The headings and rows of the Table.
        """
        return f"Table(headings={self._headings!r}, rows={self._rows!r})"


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

    def __init__(
        self,
        value: float,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
        p_value: Optional[float] = None,
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
        """
        self._value = float(value)
        self._lower = None if lower is None else float(lower)
        self._upper = None if upper is None else float(upper)
        self._p_value = None if p_value is None else float(p_value)

    @classmethod
    def from_proportion(
        cls, successes: int, total: int, confidence: float = 0.95
    ) -> Measurement:
        """Estimates a share with a Wilson score interval.

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
        return cls(share, lower=max(0.0, centre - half), upper=min(1.0, centre + half))

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

    def __eq__(self, other: object) -> bool:
        """Compares the Measurement with another one by its numbers.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same numbers, otherwise False.
        """
        if not isinstance(other, Measurement):
            return NotImplemented

        return (
            self._value == other._value
            and self._lower == other._lower
            and self._upper == other._upper
            and self._p_value == other._p_value
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Measurement.

        Returns:
            str: The numbers of the Measurement.
        """
        return (
            f"Measurement({self._value!r}, lower={self._lower!r}, "
            f"upper={self._upper!r}, p_value={self._p_value!r})"
        )


class Assessment:
    """A value checked against a requirement, with the verdict of the check."""

    _value: Value
    _requirement_label: str
    _passed: bool

    def __init__(self, value: Value, requirement_label: str, *, passed: bool) -> None:
        """Initializes an assessment.

        Args:
            value (Value): The value that was found.
            requirement_label (str): What was required of the value, in words
                that follow "passed" or "failed", such as "at least 0.99".
            passed (bool): Whether the value met the requirement.
        """
        self._value = value
        self._requirement_label = requirement_label
        self._passed = passed

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

    def __eq__(self, other: object) -> bool:
        """Compares the Assessment with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same value, requirement label and verdict,
                otherwise False.
        """
        if not isinstance(other, Assessment):
            return NotImplemented

        return (
            self._value == other._value
            and self._requirement_label == other._requirement_label
            and self._passed == other._passed
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Assessment.

        Returns:
            str: The value, requirement label and verdict of the Assessment.
        """
        return f"Assessment({self._value!r}, {self._requirement_label!r}, passed={self._passed!r})"


class Bin(TypedDict):
    """One bin of a histogram."""

    lower: float
    upper: float
    count: int


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
    _bins: Optional[int]

    def __init__(self, values: Iterable[float], bins: Optional[int] = None) -> None:
        """Initializes a distribution from its values.

        Args:
            values (Iterable[float]): The values, at least one, all finite.
            bins (Optional[int]): The number of bins its histogram aims for, or
                None for Sturges' rule. Defaults to None.

        Raises:
            ValueError: If there is no value, a value is not finite, or fewer
                than one bin is asked for.
        """
        self._values = [float(value) for value in values]
        self._bins = bins

        if not self._values:
            msg = "a distribution must hold at least one value"
            raise ValueError(msg)

        if not all(math.isfinite(value) for value in self._values):
            msg = "every value of a distribution must be finite"
            raise ValueError(msg)

        if bins is not None and bins < 1:
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
    def bins(self) -> Optional[int]:
        """The number of bins the histogram of the Distribution aims for.

        Returns:
            Optional[int]: The number of bins, or None for Sturges' rule.
        """
        return self._bins

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
    def std(self) -> float:
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
        return median(self._values)

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

    def histogram(self, bins: Optional[int] = None) -> List[Bin]:
        """Counts the values in bins of equal, rounded width.

        Args:
            bins (Optional[int]): The number of bins to aim for, or None for the
                number the Distribution was given, or Sturges' rule if it was
                given none. Defaults to None.

        Returns:
            List[Bin]: The bins, from the lowest edge to the highest.

        Raises:
            ValueError: If fewer than one bin is asked for.
        """
        asked = self._bins if bins is None else bins
        count = math.ceil(math.log2(len(self._values))) + 1 if asked is None else asked

        if count < 1:
            msg = "a histogram needs at least one bin"
            raise ValueError(msg)

        minimum = self.minimum
        maximum = self.maximum
        span = (maximum - minimum) / count

        if span == 0 or not math.isfinite(span):
            return [{"lower": minimum, "upper": maximum, "count": len(self._values)}]

        width = _rounded_width(span)

        if all(value.is_integer() for value in self._values):
            width = max(width, Fraction(1))

        start = Fraction(minimum) // width * width
        edges = [float(start)]

        while edges[-1] <= maximum:
            edges.append(float(start + len(edges) * width))

        if any(lower == upper for lower, upper in pairwise(edges)):
            return [{"lower": minimum, "upper": maximum, "count": len(self._values)}]

        counted: List[Bin] = [
            {
                "lower": lower,
                "upper": upper,
                "count": sum(1 for value in self._values if lower <= value < upper),
            }
            for lower, upper in pairwise(edges)
        ]

        if counted[0]["count"] == 0:
            return counted[1:]

        return counted

    def _quantile(self, fraction: float) -> float:
        """Interpolates the value the given fraction of the values lie below.

        Args:
            fraction (float): The fraction, between 0 and 1.

        Returns:
            float: The interpolated quantile.
        """
        ordered = sorted(self._values)
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

        return self._values == other._values and self._bins == other._bins

    def __repr__(self) -> str:
        """Returns the string representation of the Distribution.

        Returns:
            str: The number of values of the Distribution.
        """
        return f"Distribution({len(self._values)} values)"


#: A type alias for the value kinds an analytic can report.
ReportValue: TypeAlias = Union[
    "Value", Table, Plot, Measurement, Assessment, Distribution
]

#: A type alias for one parameter or summary item: a value or a sequence of values.
Detail: TypeAlias = Union["Value", Sequence["Value"]]

InputsType = TypeVar("InputsType")

DerivedType = TypeVar("DerivedType")


class Analytic(ABC, Generic[InputsType]):
    """One computation over inputs, reporting one value."""

    @abstractmethod
    def compute(self, inputs: InputsType, /) -> Union[ReportValue, QueryError]:
        """Computes the value of the analytic.

        Args:
            inputs (InputsType): The inputs the analytic is placed over.

        Returns:
            Union[ReportValue, QueryError]: The value, or the query engine's in-band
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
