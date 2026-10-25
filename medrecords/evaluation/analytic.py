"""Analytic and derivation base classes and the values they report."""

from __future__ import annotations

import math
import sys
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from io import BytesIO
from itertools import pairwise
from numbers import Integral
from statistics import NormalDist, mean, stdev
from typing import (
    TYPE_CHECKING,
    BinaryIO,
    Dict,
    Final,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeAlias,
    TypeVar,
    Union,
)

import polars as pl

from medrecords.evaluation._json import (
    JsonObject,
    encode_cell,
    encode_float,
    encode_value,
)

if TYPE_CHECKING:
    from graphrecords import Identifier, QueryError, Value

    from medrecords.evaluation._json import (
        AssessmentDocument,
        BinsDocument,
        CountsDocument,
        DistributionDocument,
        HistogramDocument,
        MeasurementDocument,
        PlotDocument,
        ScatterDocument,
        StatisticsDocument,
        TableDocument,
    )


class Unit(Enum):
    """Enumeration of what a number measures, beyond what its type says.

    A typeset report prints a share as percent and points as percentage points;
    the numbers themselves stay fractions. Durations and datetimes carry no unit.
    """

    Share = "share"
    Points = "points"


class Scale(Enum):
    """Enumeration of how a chart spaces a value axis.

    A linear axis spaces equal differences evenly. A logarithmic axis spaces
    equal ratios evenly and holds positive values only; a histogram on one
    counts every value below its first edge, zero and negative values among
    them, below the edges.
    """

    Linear = "linear"
    Logarithmic = "logarithmic"


class Arrangement(Enum):
    """Enumeration of how a typeset report draws the results of several keys.

    Overlaid results share one chart; results in panels get one chart each,
    side by side on a shared axis.
    """

    Overlay = "overlay"
    Panels = "panels"


#: A type alias for the names leading from the report root to an entry.
EntryPath: TypeAlias = Tuple["Value", ...]

#: A type alias for one cell of a table: a value, or an entry of the report named
#: by its path.
Cell: TypeAlias = Union["Value", EntryPath]


class Table:
    """A tabular report value: headings and rows of cells.

    A cell is a value or the path of an entry of the report, which a typeset
    report prints as a reference to that entry. A column may declare the unit of
    its numbers; the cells stay as given. A table may say how many of its rows a
    typeset report prints; every row stays in the table.
    """

    _headings: List[Identifier]
    _rows: List[List[Cell]]
    _units: Dict[Identifier, Unit]
    _printed_rows: Optional[int]

    def __init__(
        self,
        headings: Iterable[Identifier],
        rows: Iterable[Iterable[Cell]],
        *,
        units: Optional[Mapping[Identifier, Unit]] = None,
        printed_rows: Optional[int] = None,
    ) -> None:
        """Initializes a table from its headings and rows.

        Args:
            headings (Iterable[Identifier]): One heading per position in a row.
            rows (Iterable[Iterable[Cell]]): The rows, each as long as the
                headings.
            units (Optional[Mapping[Identifier, Unit]]): The unit of the numbers
                of a column, by heading, for the columns that have one. Defaults
                to None.
            printed_rows (Optional[int]): How many rows, from the first, a
                typeset report prints, with a line saying how many follow, or
                None for every row. Defaults to None.

        Raises:
            ValueError: If a heading repeats, a row does not hold one value per
                heading, a unit names a heading the table does not have, or the
                printed rows are fewer than zero.
        """
        self._headings = list(headings)
        self._rows = [list(row) for row in rows]
        self._units = {} if units is None else dict(units)
        self._printed_rows = printed_rows

        if len(set(self._headings)) != len(self._headings):
            msg = "every heading must be different"
            raise ValueError(msg)

        for row in self._rows:
            if len(row) != len(self._headings):
                msg = "every row must hold one cell per heading"
                raise ValueError(msg)

        for heading in self._units:
            if heading not in self._headings:
                msg = f"a unit names the heading {heading!r}, which the table does not have"
                raise ValueError(msg)

        if printed_rows is not None and printed_rows < 0:
            msg = "a table cannot print fewer than zero rows"
            raise ValueError(msg)

    @classmethod
    def from_polars(
        cls,
        dataframe: pl.DataFrame,
        *,
        units: Optional[Mapping[Identifier, Unit]] = None,
        printed_rows: Optional[int] = None,
    ) -> Table:
        """Converts a Polars DataFrame to a table, one heading per column.

        A DataFrame with an unnamed column, or with two columns of the same
        name, is rejected the way a table rejects such headings.

        Args:
            dataframe (pl.DataFrame): The DataFrame to convert.
            units (Optional[Mapping[Identifier, Unit]]): The unit of the numbers
                of a column, by column name, for the columns that have one.
                Defaults to None.
            printed_rows (Optional[int]): How many rows, from the first, a
                typeset report prints, or None for every row. Defaults to None.

        Returns:
            Table: The DataFrame as a table.

        Raises:
            TypeError: If a cell holds something a table cannot report, such as
                a date, a list or a decimal.
        """
        rows: List[List[Cell]] = []

        for row in dataframe.iter_rows():
            values: List[Cell] = []

            for heading, cell in zip(dataframe.columns, row, strict=True):
                if cell is not None and not isinstance(
                    cell, (str, int, float, datetime, timedelta)
                ):
                    msg = f"column {heading!r} holds {cell!r}, which a table cannot report"
                    raise TypeError(msg)

                values.append(cell)

            rows.append(values)
        return cls(dataframe.columns, rows, units=units, printed_rows=printed_rows)

    def to_polars(self) -> pl.DataFrame:
        """Converts the table to a Polars DataFrame, one column per heading.

        An integer heading becomes the text of the number, because a column
        name is a string. A path cell becomes its names joined with " / ". A
        column holding both integers and floats holds floats, since both are
        numbers; a column holding values of more than one other kind is rejected
        by Polars.

        Returns:
            pl.DataFrame: The table as a DataFrame.
        """
        return pl.DataFrame(
            {
                str(heading): self._column(
                    [self._flattened(row[position]) for row in self._rows]
                )
                for position, heading in enumerate(self._headings)
            }
        )

    @staticmethod
    def _column(values: List[Value]) -> List[Value]:
        if not any(isinstance(value, float) for value in values):
            return values

        return [
            float(value)
            if isinstance(value, int) and not isinstance(value, bool)
            else value
            for value in values
        ]

    @staticmethod
    def _flattened(cell: Cell) -> Value:
        if isinstance(cell, tuple):
            return " / ".join(str(name) for name in cell)

        return cell

    @property
    def headings(self) -> List[Identifier]:
        """The headings of the Table.

        Returns:
            List[Identifier]: One heading per position in a row.
        """
        return list(self._headings)

    @property
    def rows(self) -> List[List[Cell]]:
        """The rows of the Table.

        Returns:
            List[List[Cell]]: Every row, in order.
        """
        return [list(row) for row in self._rows]

    @property
    def units(self) -> Dict[Identifier, Unit]:
        """The units of the columns that declare one.

        Returns:
            Dict[Identifier, Unit]: The unit by heading.
        """
        return dict(self._units)

    @property
    def printed_rows(self) -> Optional[int]:
        """How many rows, from the first, a typeset report prints.

        Returns:
            Optional[int]: The number of printed rows, or None for every row.
        """
        return self._printed_rows

    def _to_document(self) -> TableDocument:
        return {
            "kind": "table",
            "headings": list(self._headings),
            "rows": [[encode_cell(cell) for cell in row] for row in self._rows],
            "units": [
                self._units[heading].value if heading in self._units else None
                for heading in self._headings
            ],
            "printed_rows": self._printed_rows,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Table:
        path = document.path
        headings = [
            JsonObject._decoded_identifier(heading, f"{path}.headings[{index}]")
            for index, heading in enumerate(document.sequence("headings"))
        ]
        rows = [
            [
                JsonObject._decoded_cell(cell, f"{path}.rows")
                for cell in JsonObject._decoded_sequence(row, f"{path}.rows")
            ]
            for row in document.sequence("rows")
        ]
        units = [
            None
            if content is None
            else JsonObject._decoded_member(content, f"{path}.units[{index}]", Unit)
            for index, content in enumerate(document.sequence("units"))
        ]

        if len(units) != len(headings):
            msg = f"expected one unit per heading at {path}.units"
            raise ValueError(msg)

        try:
            return cls(
                headings,
                rows,
                units={
                    heading: unit
                    for heading, unit in zip(headings, units, strict=True)
                    if unit is not None
                },
                printed_rows=document.optional_integer("printed_rows"),
            )
        except ValueError as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Table with another by headings, rows, units and printed rows.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same headings, rows, units and printed
                rows, otherwise False.
        """
        if not isinstance(other, Table):
            return NotImplemented

        return (
            self._headings == other._headings
            and self._rows == other._rows
            and self._units == other._units
            and self._printed_rows == other._printed_rows
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Table.

        Returns:
            str: The headings and rows of the Table, and its units and printed
                rows when it declares them.
        """
        parts = [f"headings={self._headings!r}", f"rows={self._rows!r}"]

        if self._units:
            parts.append(f"units={self._units!r}")

        if self._printed_rows is not None:
            parts.append(f"printed_rows={self._printed_rows!r}")

        return f"Table({', '.join(parts)})"


class Figure(Protocol):
    """Protocol for figures that save themselves as SVG."""

    def savefig(
        self,
        file: BinaryIO,
        /,
        *,
        format: str,
        bbox_inches: Literal["tight"],
        metadata: Dict[str, Optional[str]],
    ) -> None:
        """Saves the figure.

        Args:
            file (BinaryIO): Where the figure is written to.
            format (str): The image format.
            bbox_inches (Literal["tight"]): How the bounding box is chosen.
            metadata (Dict[str, Optional[str]]): The metadata to write, by key;
                None leaves a key out.
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

        The SVG carries no date, so the same figure always gives the same plot.

        Args:
            figure (Figure): The figure to save, such as a matplotlib figure or a
                seaborn grid.

        Returns:
            Plot: The figure as a plot.
        """
        buffer = BytesIO()
        figure.savefig(
            buffer, format="svg", bbox_inches="tight", metadata={"Date": None}
        )
        return cls(buffer.getvalue().decode())

    @property
    def svg(self) -> str:
        """The plot as SVG text.

        Returns:
            str: The SVG text.
        """
        return self._svg

    def _to_document(self) -> PlotDocument:
        return {"kind": "plot", "svg": self._svg}

    @classmethod
    def _from_document(cls, document: JsonObject) -> Plot:
        return cls(document.string("svg"))

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

    def _to_document(self) -> MeasurementDocument:
        return {
            "kind": "measurement",
            "value": encode_float(self._value),
            "lower": None if self._lower is None else encode_float(self._lower),
            "upper": None if self._upper is None else encode_float(self._upper),
            "p_value": None if self._p_value is None else encode_float(self._p_value),
            "unit": None if self._unit is None else self._unit.value,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Measurement:
        return cls(
            document.number("value"),
            document.optional_number("lower"),
            document.optional_number("upper"),
            document.optional_number("p_value"),
            unit=document.optional_member("unit", Unit),
        )

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
            requirement_label (str): The condition the value must meet, printed
                after "required:", such as "at least 99.0%".
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

    def _to_document(self) -> AssessmentDocument:
        return {
            "kind": "assessment",
            "value": encode_value(self._value),
            "requirement_label": self._requirement_label,
            "passed": self._passed,
            "unit": None if self._unit is None else self._unit.value,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Assessment:
        return cls(
            JsonObject._decoded_value(
                document.content("value"), f"{document.path}.value"
            ),
            document.string("requirement_label"),
            passed=document.boolean("passed"),
            unit=document.optional_member("unit", Unit),
        )

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


class Bin:
    """One bin of a histogram: its edges and how many values it holds."""

    _lower: float
    _upper: float
    _count: int

    def __init__(self, lower: float, upper: float, count: int) -> None:
        """Initializes a bin.

        Args:
            lower (float): The lower edge.
            upper (float): The upper edge.
            count (int): How many values the bin holds.
        """
        self._lower = lower
        self._upper = upper
        self._count = count

    @property
    def lower(self) -> float:
        """The lower edge of the Bin.

        Returns:
            float: The lower edge.
        """
        return self._lower

    @property
    def upper(self) -> float:
        """The upper edge of the Bin.

        Returns:
            float: The upper edge.
        """
        return self._upper

    @property
    def count(self) -> int:
        """How many values the Bin holds.

        Returns:
            int: The count.
        """
        return self._count

    def __eq__(self, other: object) -> bool:
        """Compares the Bin with another one by its edges and count.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both have the same edges and count, otherwise False.
        """
        if not isinstance(other, Bin):
            return NotImplemented

        return (
            self._lower == other._lower
            and self._upper == other._upper
            and self._count == other._count
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Bin.

        Returns:
            str: The edges and count of the Bin.
        """
        return (
            f"Bin(lower={self._lower!r}, upper={self._upper!r}, count={self._count!r})"
        )


class Statistics:
    """The summary statistics of numeric values."""

    _count: int
    _mean: float
    _standard_deviation: Optional[float]
    _minimum: float
    _lower_quartile: float
    _median: float
    _upper_quartile: float
    _maximum: float

    def __init__(
        self,
        *,
        count: int,
        mean: float,
        standard_deviation: Optional[float],
        minimum: float,
        lower_quartile: float,
        median: float,
        upper_quartile: float,
        maximum: float,
    ) -> None:
        """Initializes summary statistics.

        Args:
            count (int): The number of values.
            mean (float): The arithmetic mean.
            standard_deviation (Optional[float]): The standard deviation over
                one degree less, or None for a single value.
            minimum (float): The smallest value.
            lower_quartile (float): The value a quarter of the values lie below.
            median (float): The value half of the values lie below.
            upper_quartile (float): The value three quarters of the values lie
                below.
            maximum (float): The largest value.
        """
        self._count = count
        self._mean = mean
        self._standard_deviation = standard_deviation
        self._minimum = minimum
        self._lower_quartile = lower_quartile
        self._median = median
        self._upper_quartile = upper_quartile
        self._maximum = maximum

    @property
    def count(self) -> int:
        """The number of values.

        Returns:
            int: The count.
        """
        return self._count

    @property
    def mean(self) -> float:
        """The arithmetic mean of the values.

        Returns:
            float: The mean.
        """
        return self._mean

    @property
    def standard_deviation(self) -> Optional[float]:
        """The standard deviation of the values, over one degree less.

        Returns:
            Optional[float]: The standard deviation, or None for a single value.
        """
        return self._standard_deviation

    @property
    def minimum(self) -> float:
        """The smallest value.

        Returns:
            float: The minimum.
        """
        return self._minimum

    @property
    def lower_quartile(self) -> float:
        """The value a quarter of the values lie below.

        Returns:
            float: The lower quartile.
        """
        return self._lower_quartile

    @property
    def median(self) -> float:
        """The value half of the values lie below.

        Returns:
            float: The median.
        """
        return self._median

    @property
    def upper_quartile(self) -> float:
        """The value three quarters of the values lie below.

        Returns:
            float: The upper quartile.
        """
        return self._upper_quartile

    @property
    def maximum(self) -> float:
        """The largest value.

        Returns:
            float: The maximum.
        """
        return self._maximum

    def _to_document(self) -> StatisticsDocument:
        return {
            "count": self._count,
            "mean": encode_float(self._mean),
            "standard_deviation": None
            if self._standard_deviation is None
            else encode_float(self._standard_deviation),
            "minimum": encode_float(self._minimum),
            "lower_quartile": encode_float(self._lower_quartile),
            "median": encode_float(self._median),
            "upper_quartile": encode_float(self._upper_quartile),
            "maximum": encode_float(self._maximum),
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Statistics:
        return cls(
            count=document.integer("count"),
            mean=document.number("mean"),
            standard_deviation=document.optional_number("standard_deviation"),
            minimum=document.number("minimum"),
            lower_quartile=document.number("lower_quartile"),
            median=document.number("median"),
            upper_quartile=document.number("upper_quartile"),
            maximum=document.number("maximum"),
        )

    def __eq__(self, other: object) -> bool:
        """Compares the Statistics with another one by every number.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same numbers, otherwise False.
        """
        if not isinstance(other, Statistics):
            return NotImplemented

        return (
            self._count == other._count
            and self._mean == other._mean
            and self._standard_deviation == other._standard_deviation
            and self._minimum == other._minimum
            and self._lower_quartile == other._lower_quartile
            and self._median == other._median
            and self._upper_quartile == other._upper_quartile
            and self._maximum == other._maximum
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Statistics.

        Returns:
            str: The count, mean and standard deviation.
        """
        return (
            f"Statistics(count={self._count!r}, mean={self._mean!r}, "
            f"standard_deviation={self._standard_deviation!r})"
        )


#: The share of each distribution's values a shared histogram may leave below its
#: first edge, and again above its last, unless the bins ask for another share.
_OUTSIDE_SHARE: Final[float] = 0.005

#: A bar counts as visible from this share of its distribution's tallest bar on.
_VISIBLE_SHARE: Final[float] = 0.02

#: A distribution shown on fewer visible bars than this is crowded.
_FEWEST_VISIBLE_BARS: Final[int] = 5

#: A distribution with more of its values than this share in one bar is crowded.
_MOST_IN_ONE_BAR: Final[float] = 0.4

#: Whole numbers get one bin each while their range spans at most this many
#: numbers per bin asked for.
_WHOLE_NUMBERS_PER_BIN: Final[int] = 4

#: The factor between the edges of logarithmic whole number bins; every power of
#: it is odd, so every edge lies halfway between whole numbers.
_WHOLE_NUMBER_RATIO: Final[int] = 3

#: The leading digits of the round numbers the outer edges of logarithmic bins fall on.
_ROUND_STEPS: Final[Tuple[int, ...]] = (1, 2, 5)

#: Whole numbers are binned as such only below this magnitude, where the points
#: halfway between them are still floats.
_LARGEST_WHOLE_NUMBER: Final[float] = 2.0**52


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


class Bins:
    """How the histogram of a distribution chooses its bins.

    Every setting left unset is chosen by the binning rule of
    Distribution.shared_histograms.
    """

    _count: Optional[int]
    _scale: Optional[Scale]
    _outside_share: Optional[float]

    def __init__(
        self,
        *,
        count: Optional[int] = None,
        scale: Optional[Scale] = None,
        outside_share: Optional[float] = None,
    ) -> None:
        """Initializes bin settings.

        Args:
            count (Optional[int]): The number of bins to aim for, or None to
                choose it. Defaults to None.
            scale (Optional[Scale]): The scale of the value axis, or None to
                choose it from the values. Defaults to None.
            outside_share (Optional[float]): The share of each distribution's
                values the axis may leave below its first edge, and again above
                its last, or None for 0.5 percent. Defaults to None.

        Raises:
            ValueError: If fewer than one bin is asked for, or the outside share
                is not at least 0 and below 0.5.
        """
        if count is not None and count < 1:
            msg = "a histogram needs at least one bin"
            raise ValueError(msg)

        if outside_share is not None and not 0 <= outside_share < 0.5:
            msg = f"expected an outside share from 0 to below 0.5, got {outside_share}"
            raise ValueError(msg)

        self._count = count
        self._scale = scale
        self._outside_share = outside_share

    @property
    def count(self) -> Optional[int]:
        """The number of bins to aim for.

        Returns:
            Optional[int]: The number of bins, or None to choose it.
        """
        return self._count

    @property
    def scale(self) -> Optional[Scale]:
        """The scale of the value axis.

        Returns:
            Optional[Scale]: The scale, or None to choose it from the values.
        """
        return self._scale

    @property
    def outside_share(self) -> Optional[float]:
        """The share of each distribution's values the axis may leave out per side.

        Returns:
            Optional[float]: The share, or None for 0.5 percent.
        """
        return self._outside_share

    def describe(self) -> str:
        """Puts the settings that are set in words, for the parameters of a report.

        Returns:
            str: The settings, or "chosen from the values" when none is set.
        """
        parts: List[str] = []

        if self._count is not None:
            parts.append(
                f"about {self._count} bars, or one per value for integers that span "
                f"at most {_WHOLE_NUMBERS_PER_BIN * self._count} numbers"
            )

        if self._scale is not None:
            parts.append(f"{self._scale.value} scale")

        if self._outside_share is not None:
            parts.append(
                f"at most {(Decimal(repr(self._outside_share)) * 100).normalize():f}% "
                "of the values outside the axis at each end"
            )

        if not parts:
            return "chosen from the values"

        return "; ".join(parts)

    def _to_document(self) -> BinsDocument:
        return {
            "count": self._count,
            "scale": None if self._scale is None else self._scale.value,
            "outside_share": self._outside_share,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Bins:
        try:
            return cls(
                count=document.optional_integer("count"),
                scale=document.optional_member("scale", Scale),
                outside_share=document.optional_number("outside_share"),
            )
        except ValueError as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Bins with another one by their settings.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same settings, otherwise False.
        """
        if not isinstance(other, Bins):
            return NotImplemented

        return (
            self._count == other._count
            and self._scale == other._scale
            and self._outside_share == other._outside_share
        )

    def __hash__(self) -> int:
        """Hashes the Bins by their settings.

        Returns:
            int: The hash.
        """
        return hash((self._count, self._scale, self._outside_share))

    def __repr__(self) -> str:
        """Returns the string representation of the Bins.

        Returns:
            str: The settings of the Bins.
        """
        return (
            f"Bins(count={self._count!r}, scale={self._scale!r}, "
            f"outside_share={self._outside_share!r})"
        )


class Distribution:
    """The values of a numeric distribution and their summary statistics."""

    _values: List[float]
    _bins: Optional[Bins]
    _value_label: Optional[str]
    _count_label: Optional[str]
    _arrangement: Optional[Arrangement]

    def __init__(
        self,
        values: Iterable[float],
        *,
        bins: Optional[Bins] = None,
        value_label: Optional[str] = None,
        count_label: Optional[str] = None,
        arrangement: Optional[Arrangement] = None,
    ) -> None:
        """Initializes a distribution from its values.

        Args:
            values (Iterable[float]): The values, at least one, all finite.
            bins (Optional[Bins]): How its histogram chooses its bins, or None
                to choose every setting. Defaults to None.
            value_label (Optional[str]): What the values measure, as the value
                axis names it, such as "age in years", or None for no axis
                caption. Defaults to None.
            count_label (Optional[str]): What one value is, in the plural, as
                the share axis and the legend name it, such as "patients", or
                None for "values". Defaults to None.
            arrangement (Optional[Arrangement]): How a typeset report draws the
                distributions of several keys, or None to choose it. Defaults to
                None.

        Raises:
            ValueError: If there is no value, or a value is not finite.
        """
        self._values = list(values)
        self._bins = bins
        self._value_label = value_label
        self._count_label = count_label
        self._arrangement = arrangement

        if not self._values:
            msg = "a distribution must hold at least one value"
            raise ValueError(msg)

        if not all(math.isfinite(value) for value in self._values):
            msg = "every value of a distribution must be finite"
            raise ValueError(msg)

    @property
    def values(self) -> List[float]:
        """The values of the Distribution.

        Returns:
            List[float]: Every value, in the order given.
        """
        return list(self._values)

    @property
    def whole_numbers(self) -> bool:
        """Whether every value is an integer.

        Returns:
            bool: True if every value was given as an integer, otherwise False.
        """
        return all(isinstance(value, Integral) for value in self._values)

    @property
    def bins(self) -> Optional[Bins]:
        """How the histogram of the Distribution chooses its bins.

        Returns:
            Optional[Bins]: The bin settings, or None to choose every setting.
        """
        return self._bins

    @property
    def value_label(self) -> Optional[str]:
        """What the values measure.

        Returns:
            Optional[str]: The caption of the value axis, or None.
        """
        return self._value_label

    @property
    def count_label(self) -> Optional[str]:
        """What one value is, in the plural.

        Returns:
            Optional[str]: The noun of the share axis and the legend, or None.
        """
        return self._count_label

    @property
    def arrangement(self) -> Optional[Arrangement]:
        """How a typeset report draws the distributions of several keys.

        Returns:
            Optional[Arrangement]: The arrangement, or None to choose it.
        """
        return self._arrangement

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
    def standard_deviation(self) -> Optional[float]:
        """The standard deviation of the values, over one degree less.

        Returns:
            Optional[float]: The standard deviation, or None for a single value.
        """
        if len(self._values) == 1:
            return None

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

        return Statistics(
            count=len(ordered),
            mean=mean(ordered),
            standard_deviation=self.standard_deviation,
            minimum=ordered[0],
            lower_quartile=self._interpolated(ordered, 0.25),
            median=self._interpolated(ordered, 0.5),
            upper_quartile=self._interpolated(ordered, 0.75),
            maximum=ordered[-1],
        )

    def histogram(self, bins: Optional[Bins] = None) -> Histogram:
        """Counts the values in the bins the binning rule chooses.

        Args:
            bins (Optional[Bins]): Settings that override the ones the
                Distribution was given, or None for those. Defaults to None.

        Returns:
            Histogram: The counts per bin, the counts outside the edges, and the
                statistics and labels of the values.
        """
        return Distribution.shared_histograms([self], bins)[0]

    @classmethod
    def shared_histograms(
        cls, distributions: Sequence[Distribution], bins: Optional[Bins] = None
    ) -> List[Histogram]:
        """Counts the values of several distributions in the same bins.

        Each distribution keeps at most the outside share of its values below
        the first edge and the same share above the last; whole numbers keep
        their minimum. Whole numbers get one bin per number while the range
        spans at most four times the bin count of them; beyond that, bins of a
        rounded whole width with zero in a bar one wide of its own, or,
        on a logarithmic axis, bins that each end three times as far from zero
        as the one before. Other values get bins of a rounded width, 1, 2 or 5
        times a power of ten, or, on a logarithmic axis, bins of one ratio
        between outer edges at 1, 2 or 5 times a power of ten, over the
        positive values. Unless a scale is declared, the axis is linear unless
        the linear picture crowds one of the distributions, showing it on fewer
        than five bars that reach 2 percent of its tallest bar or putting more
        than 40 percent of its values into one bar, and the logarithmic picture
        puts less of the worst distribution's values into one bar, or as much
        on more visible bars.

        Every setting the bins argument leaves unset comes from the
        distributions: the largest bin count one was given, or Sturges' rule
        on the largest distribution if none was given one; the scale and the
        outside share they declare, or the rule's choice and 0.5 percent.

        Args:
            distributions (Sequence[Distribution]): The distributions, at least
                one.
            bins (Optional[Bins]): Settings that override the ones the
                distributions were given, or None for those. Defaults to None.

        Returns:
            List[Histogram]: One histogram per distribution, in the order given,
                over the shared edges and scale, each with its own outside
                counts, statistics and labels.

        Raises:
            ValueError: If there is no distribution, or the distributions
                declare different scales or outside shares that the bins
                argument does not override.
        """
        if not distributions:
            msg = "shared histograms need at least one distribution"
            raise ValueError(msg)

        asked = Bins() if bins is None else bins
        conflict = cls._conflict(distributions, asked)

        if conflict is not None:
            raise ValueError(conflict)

        declared = [
            distribution._bins
            for distribution in distributions
            if distribution._bins is not None
        ]
        scales = {setting._scale for setting in declared if setting._scale is not None}
        shares = {
            setting._outside_share
            for setting in declared
            if setting._outside_share is not None
        }
        largest = max(len(distribution._values) for distribution in distributions)
        given = [setting._count for setting in declared if setting._count is not None]
        count = asked._count or max(given, default=math.ceil(math.log2(largest)) + 1)
        scale = asked._scale or next(iter(scales), None)
        outside_share = asked._outside_share

        if outside_share is None:
            outside_share = next(iter(shares), _OUTSIDE_SHARE)

        ordered = [sorted(distribution._values) for distribution in distributions]
        whole = all(distribution.whole_numbers for distribution in distributions)
        edges, chosen = cls._shared_edges(
            ordered, count, scale, outside_share, whole=whole
        )

        return [
            Histogram._from_distribution(distribution, edges, chosen)
            for distribution in distributions
        ]

    @staticmethod
    def _conflict(distributions: Sequence[Distribution], asked: Bins) -> Optional[str]:
        declared = [
            distribution._bins
            for distribution in distributions
            if distribution._bins is not None
        ]
        scales = {setting._scale for setting in declared if setting._scale is not None}
        shares = {
            setting._outside_share
            for setting in declared
            if setting._outside_share is not None
        }

        if asked._scale is None and len(scales) > 1:
            return "the distributions declare different scales"

        if asked._outside_share is None and len(shares) > 1:
            return "the distributions declare different outside shares"

        return None

    @classmethod
    def _shared_edges(
        cls,
        ordered: Sequence[Sequence[float]],
        count: int,
        scale: Optional[Scale],
        outside_share: float,
        *,
        whole: bool,
    ) -> Tuple[List[float], Scale]:
        """Chooses the edges and the scale shared histograms are counted over.

        Args:
            ordered (Sequence[Sequence[float]]): The values of every
                distribution, sorted, at least one each.
            count (int): The number of bins to aim for.
            scale (Optional[Scale]): The declared scale, or None to choose one.
            outside_share (float): The share of each distribution's values the
                axis may leave out on each side.
            whole (bool): Whether every value is an integer.

        Returns:
            Tuple[List[float], Scale]: The edges, from the lowest to the
                highest, and the scale they are drawn on.
        """
        if whole and all(
            abs(value) < _LARGEST_WHOLE_NUMBER for values in ordered for value in values
        ):
            low = min(values[0] for values in ordered)
            high = max(cls._high_value(values, outside_share) for values in ordered)
            logarithmic = cls._logarithmic_whole_number_edges(low, high)

            if high - low + 1 <= _WHOLE_NUMBERS_PER_BIN * count:
                if scale is Scale.Logarithmic and logarithmic is not None:
                    return logarithmic, Scale.Logarithmic

                return cls._whole_number_edges(low, high), Scale.Linear

            linear = cls._wide_whole_number_edges(low, high, count)
        else:
            low = min(cls._low_value(values, outside_share) for values in ordered)
            high = max(cls._high_value(values, outside_share) for values in ordered)
            linear = cls._linear_edges(low, high, count)
            logarithmic = cls._logarithmic_edges(ordered, count, outside_share)

        if scale is Scale.Linear or logarithmic is None:
            return linear, Scale.Linear

        if scale is Scale.Logarithmic:
            return logarithmic, Scale.Logarithmic

        linear_bars, linear_share = cls._crowding(ordered, linear)

        if linear_bars >= _FEWEST_VISIBLE_BARS and linear_share <= _MOST_IN_ONE_BAR:
            return linear, Scale.Linear

        logarithmic_bars, logarithmic_share = cls._crowding(ordered, logarithmic)

        if (logarithmic_share, -logarithmic_bars) < (linear_share, -linear_bars):
            return logarithmic, Scale.Logarithmic

        return linear, Scale.Linear

    @staticmethod
    def _low_value(ordered: Sequence[float], outside_share: float) -> float:
        """Finds the value the axis starts at for one distribution.

        Args:
            ordered (Sequence[float]): The values, sorted, at least one.
            outside_share (float): The share of values that may lie below it.

        Returns:
            float: The value at the position of the outside share.
        """
        return ordered[math.floor(outside_share * (len(ordered) - 1))]

    @staticmethod
    def _high_value(ordered: Sequence[float], outside_share: float) -> float:
        """Finds the value the axis ends at for one distribution.

        Args:
            ordered (Sequence[float]): The values, sorted, at least one.
            outside_share (float): The share of values that may lie above it.

        Returns:
            float: The value at the position of one less the outside share.
        """
        return ordered[math.ceil((1 - outside_share) * (len(ordered) - 1))]

    @staticmethod
    def _whole_number_edges(low: float, high: float) -> List[float]:
        """Chooses one bin per whole number.

        Args:
            low (float): The smallest whole number.
            high (float): The largest whole number.

        Returns:
            List[float]: The edges halfway between the whole numbers.
        """
        return [number - 0.5 for number in range(int(low), int(high) + 2)]

    @staticmethod
    def _wide_whole_number_edges(low: float, high: float, count: int) -> List[float]:
        """Chooses bins of one rounded whole width, of at least two numbers each.

        With the range at zero or above, zero gets a bin of its own.

        Args:
            low (float): The smallest whole number.
            high (float): The largest whole number the axis holds.
            count (int): The number of bins to aim for.

        Returns:
            List[float]: The edges halfway between whole numbers.
        """
        if low < 0:
            width = max(2, int(_rounded_width((high - low + 1) / count)))
            first = math.floor(low / width) * width - 0.5
        else:
            start = max(low, 1)
            width = max(2, int(_rounded_width((high - start + 1) / count)))
            first = math.floor((start - 1) / width) * width + 0.5

        edges = [first]

        while edges[-1] < high + 0.5:
            edges.append(edges[-1] + width)

        if low == 0:
            return [-0.5, *edges]

        return edges

    @staticmethod
    def _logarithmic_whole_number_edges(
        low: float, high: float
    ) -> Optional[List[float]]:
        """Chooses whole number bins that each end three times as far from zero.

        Args:
            low (float): The smallest whole number.
            high (float): The largest whole number the axis holds.

        Returns:
            Optional[List[float]]: The edges, halfway between whole numbers, or
                None when a number lies below zero or one bin cannot be made.
        """
        if low < 0:
            return None

        start = max(low, 1) - 0.5
        first = 0.5

        while first * _WHOLE_NUMBER_RATIO <= start:
            first *= _WHOLE_NUMBER_RATIO

        edges = [first]

        while edges[-1] < high + 0.5:
            edges.append(edges[-1] * _WHOLE_NUMBER_RATIO)

        return edges if len(edges) > 1 else None

    @staticmethod
    def _linear_edges(low: float, high: float, count: int) -> List[float]:
        """Chooses edges of one rounded width over a range.

        Args:
            low (float): The value the axis starts at.
            high (float): The value the axis ends at.
            count (int): The number of bins to aim for.

        Returns:
            List[float]: The edges, from the lowest to the highest; one bin
                around a single value.
        """
        if low == high:
            span = abs(low) / 10
            width = _rounded_width(span) if span > 0 else Fraction(1)

            return [float(Fraction(low) - width / 2), float(Fraction(low) + width / 2)]

        width = _rounded_width((high - low) / count)
        start = Fraction(low) // width * width
        edges = [float(start)]

        while edges[-1] <= high:
            edges.append(float(start + len(edges) * width))

        return edges

    @classmethod
    def _logarithmic_edges(
        cls, ordered: Sequence[Sequence[float]], count: int, outside_share: float
    ) -> Optional[List[float]]:
        """Chooses edges of one ratio between round outer edges over positive values.

        The outer edges are 1, 2 or 5 times a power of ten: the largest at or
        below the lowest held positive value and the smallest at or above the
        highest held value. Between them every bin spans the same ratio, with
        about the bin count of bins per decade the held values span, or per
        decade when they span less than one.

        Args:
            ordered (Sequence[Sequence[float]]): The values of every
                distribution, sorted.
            count (int): The number of bins to aim for.
            outside_share (float): The share of each distribution's values
                the axis may leave out on each side.

        Returns:
            Optional[List[float]]: The edges, or None when the positive values
                hold fewer than two different values or the axis would hold a
                single value.
        """
        positives = [[value for value in values if value > 0] for values in ordered]
        present = [values for values in positives if values]

        if not present or min(values[0] for values in present) == max(
            values[-1] for values in present
        ):
            return None

        low = min(cls._low_value(values, outside_share) for values in present)
        high = max(cls._high_value(values, outside_share) for values in ordered)

        if high <= low:
            return None

        first = max(number for number in cls._round_numbers(low) if number <= low)
        last = min(number for number in cls._round_numbers(high) if number >= high)
        start = math.log10(float(first))
        decades = math.log10(float(last)) - start
        bin_count = max(1, round(count * decades / max(math.log10(high / low), 1)))
        inner = [
            10 ** (start + step * decades / bin_count) for step in range(1, bin_count)
        ]

        return [float(first), *inner, float(last)]

    @staticmethod
    def _round_numbers(value: float) -> List[Fraction]:
        """Lists the numbers 1, 2 and 5 times a power of ten around a value.

        Args:
            value (float): A positive value.

        Returns:
            List[Fraction]: The round numbers from a tenth of the value's power
                of ten to five times ten times it, exactly.
        """
        exponent = math.floor(math.log10(value))

        return [
            step * Fraction(10) ** power
            for power in range(exponent - 1, exponent + 2)
            for step in _ROUND_STEPS
        ]

    @staticmethod
    def _crowding(
        ordered: Sequence[Sequence[float]], edges: Sequence[float]
    ) -> Tuple[int, float]:
        """Measures how crowded the distributions look on a set of edges.

        A distribution's drawn bars are its bins and an end bar on each side
        that holds values; a bar is visible when it holds at least 2 percent of
        what the distribution's tallest bar holds.

        Args:
            ordered (Sequence[Sequence[float]]): The values of every
                distribution, sorted, at least one each.
            edges (Sequence[float]): The edges.

        Returns:
            Tuple[int, float]: The fewest visible bars of a distribution, and
                the largest share of a distribution's values in one bar.
        """
        fewest = sys.maxsize
        most = 0.0

        for values in ordered:
            counts, below, above = Histogram._counted(values, edges)
            bars = [count for count in (below, *counts, above) if count > 0]
            tallest = max(bars)
            visible = sum(1 for count in bars if count >= _VISIBLE_SHARE * tallest)
            fewest = min(fewest, visible)
            most = max(most, tallest / len(values))

        return fewest, most

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

    def _to_document(
        self, histogram: Optional[Histogram] = None
    ) -> DistributionDocument:
        drawn = self.histogram() if histogram is None else histogram

        return {
            "kind": "distribution",
            "values": list(self._values),
            "bins": None if self._bins is None else self._bins._to_document(),
            "value_label": self._value_label,
            "count_label": self._count_label,
            "arrangement": None
            if self._arrangement is None
            else self._arrangement.value,
            "statistics": self.statistics._to_document(),
            "histogram": {
                "edges": drawn.edges,
                "counts": drawn.counts,
                "below_count": drawn.below_count,
                "above_count": drawn.above_count,
                "scale": drawn.scale.value,
                "whole_numbers": drawn.whole_numbers,
            },
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Distribution:
        values = [
            JsonObject._decoded_number(value, f"{document.path}.values")
            for value in document.sequence("values")
        ]
        bins = document.optional_document("bins")

        try:
            return cls(
                values,
                bins=None if bins is None else Bins._from_document(bins),
                value_label=document.optional_string("value_label"),
                count_label=document.optional_string("count_label"),
                arrangement=document.optional_member("arrangement", Arrangement),
            )
        except ValueError as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Distribution with another one by its values and settings.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same values in the same order, the same
                bin settings, labels and arrangement, otherwise False.
        """
        if not isinstance(other, Distribution):
            return NotImplemented

        return (
            self._values == other._values
            and self._bins == other._bins
            and self._value_label == other._value_label
            and self._count_label == other._count_label
            and self._arrangement == other._arrangement
        )

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
    statistics describe every value, the ones outside the edges included; a
    histogram that counts values but carries no statistics withholds them.
    """

    _edges: List[float]
    _counts: List[int]
    _below_count: int
    _above_count: int
    _statistics: Optional[Statistics]
    _scale: Scale
    _whole_numbers: bool
    _value_label: Optional[str]
    _count_label: Optional[str]
    _arrangement: Optional[Arrangement]

    def __init__(
        self,
        edges: Iterable[float],
        counts: Iterable[int],
        *,
        below_count: int = 0,
        above_count: int = 0,
        statistics: Optional[Statistics] = None,
        scale: Scale = Scale.Linear,
        whole_numbers: bool = False,
        value_label: Optional[str] = None,
        count_label: Optional[str] = None,
        arrangement: Optional[Arrangement] = None,
    ) -> None:
        """Initializes a histogram from its edges and counts.

        Args:
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing; above zero on a logarithmic scale.
            counts (Iterable[int]): One count per bin, so one fewer than the
                edges.
            below_count (int): How many values lay below the first edge.
                Defaults to 0.
            above_count (int): How many values lay above the last edge.
                Defaults to 0.
            statistics (Optional[Statistics]): The statistics of every value
                counted, or None when there is no value or they are withheld.
                Defaults to None.
            scale (Scale): How the value axis is spaced. Defaults to
                Scale.Linear.
            whole_numbers (bool): Whether every counted value is an integer.
                Defaults to False.
            value_label (Optional[str]): What the values measure, as the value
                axis names it, such as "days", or None for no axis caption.
                Defaults to None.
            count_label (Optional[str]): What one counted value is, in the
                plural, as the share axis and the legend name it, such as
                "intervals", or None for "values". Defaults to None.
            arrangement (Optional[Arrangement]): How a typeset report draws the
                histograms of several keys, or None to choose it. Defaults to
                None.

        Raises:
            ValueError: If the counts are not one per bin, a count is negative,
                or the scale is logarithmic and the first edge is not above
                zero.
        """
        self._edges = self._checked_edges(edges)
        self._counts = list(counts)
        self._below_count = below_count
        self._above_count = above_count
        self._statistics = statistics
        self._scale = scale
        self._whole_numbers = whole_numbers
        self._value_label = value_label
        self._count_label = count_label
        self._arrangement = arrangement

        if len(self._counts) != len(self._edges) - 1:
            msg = "a histogram needs one count per bin"
            raise ValueError(msg)

        if any(count < 0 for count in (*self._counts, below_count, above_count)):
            msg = "every count of a histogram must be zero or more"
            raise ValueError(msg)

        if scale is Scale.Logarithmic and self._edges[0] <= 0:
            msg = "the edges of a logarithmic histogram must be above zero"
            raise ValueError(msg)

    @classmethod
    def from_values(
        cls,
        values: Iterable[float],
        edges: Iterable[float],
        *,
        scale: Scale = Scale.Linear,
        value_label: Optional[str] = None,
        count_label: Optional[str] = None,
        arrangement: Optional[Arrangement] = None,
    ) -> Histogram:
        """Counts values into bins over given edges.

        Args:
            values (Iterable[float]): The values to count, all finite.
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing; above zero on a logarithmic scale.
            scale (Scale): How the value axis is spaced. Defaults to
                Scale.Linear.
            value_label (Optional[str]): What the values measure, or None for
                no axis caption. Defaults to None.
            count_label (Optional[str]): What one value is, in the plural, or
                None for "values". Defaults to None.
            arrangement (Optional[Arrangement]): How a typeset report draws the
                histograms of several keys, or None to choose it. Defaults to
                None.

        Returns:
            Histogram: The counts per bin, the counts outside the edges, and the
                statistics of the values, or none when there is no value.
        """
        materialized = list(values)

        if not materialized:
            bounds = cls._checked_edges(edges)

            return cls(
                bounds,
                [0] * (len(bounds) - 1),
                scale=scale,
                value_label=value_label,
                count_label=count_label,
                arrangement=arrangement,
            )

        distribution = Distribution(
            materialized,
            value_label=value_label,
            count_label=count_label,
            arrangement=arrangement,
        )

        return cls._from_distribution(distribution, edges, scale)

    @classmethod
    def _from_distribution(
        cls, distribution: Distribution, edges: Iterable[float], scale: Scale
    ) -> Histogram:
        """Counts the values of a distribution into bins over given edges.

        Args:
            distribution (Distribution): The values to count, with their
                statistics and labels.
            edges (Iterable[float]): The bin edges, at least two, finite and
                increasing.
            scale (Scale): How the value axis is spaced.

        Returns:
            Histogram: The counts per bin, the counts outside the edges, and the
                statistics and labels of the distribution.
        """
        bounds = cls._checked_edges(edges)
        counts, below_count, above_count = cls._counted(
            sorted(distribution._values), bounds
        )

        return cls(
            bounds,
            counts,
            below_count=below_count,
            above_count=above_count,
            statistics=distribution.statistics,
            scale=scale,
            whole_numbers=distribution.whole_numbers,
            value_label=distribution._value_label,
            count_label=distribution._count_label,
            arrangement=distribution._arrangement,
        )

    @staticmethod
    def _counted(
        ordered: Sequence[float], edges: Sequence[float]
    ) -> Tuple[List[int], int, int]:
        """Counts sorted values into bins over edges.

        Args:
            ordered (Sequence[float]): The values, sorted.
            edges (Sequence[float]): The bin edges, at least two, increasing.

        Returns:
            Tuple[List[int], int, int]: The count per bin, the count below the
                first edge and the count above the last.
        """
        positions = [bisect_left(ordered, edge) for edge in edges[:-1]]
        positions.append(bisect_right(ordered, edges[-1]))
        counts = [upper - lower for lower, upper in pairwise(positions)]

        return counts, positions[0], len(ordered) - positions[-1]

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
        return self._statistics

    @property
    def scale(self) -> Scale:
        """How the value axis of the Histogram is spaced.

        Returns:
            Scale: The scale.
        """
        return self._scale

    @property
    def whole_numbers(self) -> bool:
        """Whether every counted value is an integer.

        Returns:
            bool: True if every counted value is an integer, otherwise False.
        """
        return self._whole_numbers

    @property
    def value_label(self) -> Optional[str]:
        """What the values measure.

        Returns:
            Optional[str]: The caption of the value axis, or None.
        """
        return self._value_label

    @property
    def count_label(self) -> Optional[str]:
        """What one counted value is, in the plural.

        Returns:
            Optional[str]: The noun of the share axis and the legend, or None.
        """
        return self._count_label

    @property
    def arrangement(self) -> Optional[Arrangement]:
        """How a typeset report draws the histograms of several keys.

        Returns:
            Optional[Arrangement]: The arrangement, or None to choose it.
        """
        return self._arrangement

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
            Bin(lower, upper, count)
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

    def _to_document(self) -> HistogramDocument:
        return {
            "kind": "histogram",
            "edges": list(self._edges),
            "counts": list(self._counts),
            "below_count": self._below_count,
            "above_count": self._above_count,
            "statistics": None
            if self._statistics is None
            else self._statistics._to_document(),
            "scale": self._scale.value,
            "whole_numbers": self._whole_numbers,
            "value_label": self._value_label,
            "count_label": self._count_label,
            "arrangement": None
            if self._arrangement is None
            else self._arrangement.value,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Histogram:
        edges = [
            JsonObject._decoded_number(edge, f"{document.path}.edges")
            for edge in document.sequence("edges")
        ]
        counts = [
            JsonObject._decoded_integer(count, f"{document.path}.counts")
            for count in document.sequence("counts")
        ]
        statistics = document.optional_document("statistics")

        try:
            return cls(
                edges,
                counts,
                below_count=document.integer("below_count"),
                above_count=document.integer("above_count"),
                statistics=None
                if statistics is None
                else Statistics._from_document(statistics),
                scale=document.member("scale", Scale),
                whole_numbers=document.boolean("whole_numbers"),
                value_label=document.optional_string("value_label"),
                count_label=document.optional_string("count_label"),
                arrangement=document.optional_member("arrangement", Arrangement),
            )
        except ValueError as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Histogram with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same edges, counts, outside counts,
                statistics, scale, whole numbers flag, labels and arrangement,
                otherwise False.
        """
        if not isinstance(other, Histogram):
            return NotImplemented

        return (
            self._edges == other._edges
            and self._counts == other._counts
            and self._below_count == other._below_count
            and self._above_count == other._above_count
            and self._statistics == other._statistics
            and self._scale == other._scale
            and self._whole_numbers == other._whole_numbers
            and self._value_label == other._value_label
            and self._count_label == other._count_label
            and self._arrangement == other._arrangement
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
    counts when only the most frequent values are listed; the values left out
    are the remainder. Values are told apart the way a mapping tells its keys
    apart, and their order is part of the Counts: two Counts listing the same
    values in a different order differ.
    """

    _counts: Dict[Value, int]
    _total: int
    _value_label: Optional[str]
    _count_label: Optional[str]
    _remainder_label: Optional[str]
    _arrangement: Optional[Arrangement]

    def __init__(
        self,
        counts: Mapping[Value, int],
        total: Optional[int] = None,
        *,
        value_label: Optional[str] = None,
        count_label: Optional[str] = None,
        remainder_label: Optional[str] = None,
        arrangement: Optional[Arrangement] = None,
    ) -> None:
        """Initializes counts from a mapping of values to how often they occur.

        Args:
            counts (Mapping[Value, int]): How often every value occurs, in the
                order they are listed.
            total (Optional[int]): The number of values counted, or None for
                the sum of the counts. Defaults to None.
            value_label (Optional[str]): What the values are, as the category
                axis names them, such as "diagnosis", or None for no caption.
                Defaults to None.
            count_label (Optional[str]): What one counted value is, in the
                plural, as the share axis and the legend name it, such as
                "patients", or None for "values". Defaults to None.
            remainder_label (Optional[str]): What the values left out of the
                listing are called in its last row, or None for "other values".
                Defaults to None.
            arrangement (Optional[Arrangement]): How a typeset report draws the
                counts of several keys, or None to choose it. Defaults to None.

        Raises:
            ValueError: If a count is negative, or the total is below the sum of
                the counts.
        """
        self._counts = dict(counts)
        self._total = sum(self._counts.values()) if total is None else total
        self._value_label = value_label
        self._count_label = count_label
        self._remainder_label = remainder_label
        self._arrangement = arrangement

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

    @property
    def value_label(self) -> Optional[str]:
        """What the values are.

        Returns:
            Optional[str]: The caption of the category axis, or None.
        """
        return self._value_label

    @property
    def count_label(self) -> Optional[str]:
        """What one counted value is, in the plural.

        Returns:
            Optional[str]: The noun of the share axis and the legend, or None.
        """
        return self._count_label

    @property
    def remainder_label(self) -> Optional[str]:
        """What the values left out of the listing are called.

        Returns:
            Optional[str]: The label of the remainder, or None.
        """
        return self._remainder_label

    @property
    def arrangement(self) -> Optional[Arrangement]:
        """How a typeset report draws the counts of several keys.

        Returns:
            Optional[Arrangement]: The arrangement, or None to choose it.
        """
        return self._arrangement

    def to_table(self) -> Table:
        """Converts the Counts to a table of values, counts and shares.

        Returns:
            Table: One row per value with its count and its share of the total,
                which is None when the total is zero; the share column carries
                the share unit.
        """
        rows: List[List[Cell]] = [
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

    def _to_document(self) -> CountsDocument:
        return {
            "kind": "counts",
            "counts": [
                {"value": encode_value(value), "count": count}
                for value, count in self._counts.items()
            ],
            "total": self._total,
            "value_label": self._value_label,
            "count_label": self._count_label,
            "remainder_label": self._remainder_label,
            "arrangement": None
            if self._arrangement is None
            else self._arrangement.value,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Counts:
        counts: Dict[Value, int] = {}

        for index, item in enumerate(document.sequence("counts")):
            counted = JsonObject(item, f"{document.path}.counts[{index}]")
            value = JsonObject._decoded_value(
                counted.content("value"), f"{counted.path}.value"
            )
            counts[value] = counted.integer("count")

        try:
            return cls(
                counts,
                document.integer("total"),
                value_label=document.optional_string("value_label"),
                count_label=document.optional_string("count_label"),
                remainder_label=document.optional_string("remainder_label"),
                arrangement=document.optional_member("arrangement", Arrangement),
            )
        except ValueError as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Counts with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same counts in the same order, the same
                total, labels and arrangement, otherwise False.
        """
        if not isinstance(other, Counts):
            return NotImplemented

        return (
            list(self._counts.items()) == list(other._counts.items())
            and self._total == other._total
            and self._value_label == other._value_label
            and self._count_label == other._count_label
            and self._remainder_label == other._remainder_label
            and self._arrangement == other._arrangement
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Counts.

        Returns:
            str: The number of values listed and the total of the Counts.
        """
        return f"Counts({len(self._counts)} values of {self._total})"


class Scatter:
    """Points in a plane, each a pair of numbers, some of them labelled."""

    _points: List[Tuple[float, float]]
    _x_label: str
    _y_label: str
    _x_scale: Scale
    _y_scale: Scale
    _labels: Dict[int, str]
    _diagonal: bool

    def __init__(
        self,
        points: Sequence[Tuple[float, float]],
        *,
        x_label: str,
        y_label: str,
        x_scale: Scale = Scale.Linear,
        y_scale: Scale = Scale.Linear,
        labels: Optional[Mapping[int, str]] = None,
        diagonal: bool = False,
    ) -> None:
        """Initializes a scatter from its points.

        Args:
            points (Sequence[Tuple[float, float]]): The points, each as its
                position on the horizontal and on the vertical axis, all
                finite.
            x_label (str): What the horizontal axis measures.
            y_label (str): What the vertical axis measures.
            x_scale (Scale): How the horizontal axis is spaced. Defaults to
                Scale.Linear.
            y_scale (Scale): How the vertical axis is spaced. Defaults to
                Scale.Linear.
            labels (Optional[Mapping[int, str]]): The text printed beside a
                point, by the point's position in the points, for the points
                that have one. Defaults to None.
            diagonal (bool): Whether the line where both coordinates are equal
                is drawn. Defaults to False.

        Raises:
            ValueError: If a coordinate is not finite, or a label names a
                position the points do not have.
        """
        self._points = [(float(x), float(y)) for x, y in points]
        self._x_label = x_label
        self._y_label = y_label
        self._x_scale = x_scale
        self._y_scale = y_scale
        self._labels = {} if labels is None else dict(labels)
        self._diagonal = diagonal

        if not all(math.isfinite(x) and math.isfinite(y) for x, y in self._points):
            msg = "every coordinate of a scatter must be finite"
            raise ValueError(msg)

        for index in self._labels:
            if not 0 <= index < len(self._points):
                msg = (
                    f"a label names the point {index}, which the scatter does not have"
                )
                raise ValueError(msg)

    @property
    def points(self) -> List[Tuple[float, float]]:
        """The points of the Scatter.

        Returns:
            List[Tuple[float, float]]: Every point, in the order given.
        """
        return list(self._points)

    @property
    def x_label(self) -> str:
        """What the horizontal axis measures.

        Returns:
            str: The caption of the horizontal axis.
        """
        return self._x_label

    @property
    def y_label(self) -> str:
        """What the vertical axis measures.

        Returns:
            str: The caption of the vertical axis.
        """
        return self._y_label

    @property
    def x_scale(self) -> Scale:
        """How the horizontal axis is spaced.

        Returns:
            Scale: The scale of the horizontal axis.
        """
        return self._x_scale

    @property
    def y_scale(self) -> Scale:
        """How the vertical axis is spaced.

        Returns:
            Scale: The scale of the vertical axis.
        """
        return self._y_scale

    @property
    def labels(self) -> Dict[int, str]:
        """The text printed beside the labelled points.

        Returns:
            Dict[int, str]: The label by the point's position in the points.
        """
        return dict(self._labels)

    @property
    def diagonal(self) -> bool:
        """Whether the line where both coordinates are equal is drawn.

        Returns:
            bool: True if the line is drawn, otherwise False.
        """
        return self._diagonal

    def to_polars(self) -> pl.DataFrame:
        """Converts the points to a Polars DataFrame.

        Returns:
            pl.DataFrame: One row per point with its two coordinates and its
                label, which is None for a point without one.
        """
        return pl.DataFrame(
            {
                "x": [x for x, _ in self._points],
                "y": [y for _, y in self._points],
                "label": [
                    self._labels.get(index) for index in range(len(self._points))
                ],
            },
            schema={"x": pl.Float64, "y": pl.Float64, "label": pl.String},
        )

    def _to_document(self) -> ScatterDocument:
        return {
            "kind": "scatter",
            "points": [[x, y] for x, y in self._points],
            "x_label": self._x_label,
            "y_label": self._y_label,
            "x_scale": self._x_scale.value,
            "y_scale": self._y_scale.value,
            "labels": [
                {"index": index, "label": label}
                for index, label in self._labels.items()
            ],
            "diagonal": self._diagonal,
        }

    @classmethod
    def _from_document(cls, document: JsonObject) -> Scatter:
        points: List[Tuple[float, float]] = []

        for index, item in enumerate(document.sequence("points")):
            path = f"{document.path}.points[{index}]"
            coordinates = JsonObject._decoded_sequence(item, path)

            if len(coordinates) != 2:
                msg = f"expected two coordinates at {path}"
                raise ValueError(msg)

            points.append(
                (
                    JsonObject._decoded_number(coordinates[0], path),
                    JsonObject._decoded_number(coordinates[1], path),
                )
            )

        labels: Dict[int, str] = {}

        for index, item in enumerate(document.sequence("labels")):
            label = JsonObject(item, f"{document.path}.labels[{index}]")
            labels[label.integer("index")] = label.string("label")

        try:
            return cls(
                points,
                x_label=document.string("x_label"),
                y_label=document.string("y_label"),
                x_scale=document.member("x_scale", Scale),
                y_scale=document.member("y_scale", Scale),
                labels=labels,
                diagonal=document.boolean("diagonal"),
            )
        except ValueError as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    def __eq__(self, other: object) -> bool:
        """Compares the Scatter with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same points in the same order, the same
                axis labels and scales, the same point labels and the same
                diagonal, otherwise False.
        """
        if not isinstance(other, Scatter):
            return NotImplemented

        return (
            self._points == other._points
            and self._x_label == other._x_label
            and self._y_label == other._y_label
            and self._x_scale == other._x_scale
            and self._y_scale == other._y_scale
            and self._labels == other._labels
            and self._diagonal == other._diagonal
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Scatter.

        Returns:
            str: The number of points and labels of the Scatter.
        """
        return f"Scatter({len(self._points)} points, {len(self._labels)} labelled)"


#: A type alias for the value kinds an analytic can report.
ReportValue: TypeAlias = Union[
    "Value",
    Table,
    Plot,
    Measurement,
    Assessment,
    Distribution,
    Histogram,
    Counts,
    Scatter,
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

    def titles(
        self, inputs: InputsType, derived: DerivedType, /
    ) -> Mapping[Value, str]:
        """Names the keys of what the derivation derives, for the groups per key.

        A run calls it once after every derive whose keys head a group of their
        own, as a group placed over each key has. A key without a title is
        headed by itself; a title for a key that was not derived is ignored.
        Titles that fail fail the derivation.

        Args:
            inputs (InputsType): The inputs the derivation ran on.
            derived (DerivedType): What derive returned.

        Returns:
            Mapping[Value, str]: The heading by key; empty unless overridden.
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
