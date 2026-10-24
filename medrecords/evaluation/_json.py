"""The JSON form of a report: its document types, decoder and value encoders."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeAlias,
    TypedDict,
    Union,
)

from medrecords.evaluation.analytic import (
    Counts,
    Distribution,
    Histogram,
    Table,
    Unit,
)

if TYPE_CHECKING:
    from graphrecords import Identifier, Value

    from medrecords.evaluation.analytic import Detail, Statistics

#: A type alias for anything a JSON file can hold.
Json: TypeAlias = Union[str, int, float, bool, List["Json"], Dict[str, "Json"], None]


class DateTimeDocument(TypedDict):
    """A datetime in its JSON form."""

    kind: Literal["datetime"]
    value: str


class DurationDocument(TypedDict):
    """A duration in its JSON form, in the parts a duration is built from."""

    kind: Literal["timedelta"]
    days: int
    seconds: int
    microseconds: int


class NonFiniteDocument(TypedDict):
    """A number JSON cannot hold, as its text."""

    kind: Literal["float"]
    value: str


#: A type alias for a value in its JSON form.
ValueDocument: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    DateTimeDocument,
    DurationDocument,
    NonFiniteDocument,
    None,
]

#: A type alias for one parameter or summary item in its JSON form.
DetailDocument: TypeAlias = Union[ValueDocument, List[ValueDocument]]


class TableDocument(TypedDict):
    """A table in its JSON form."""

    kind: Literal["table"]
    headings: List[Identifier]
    rows: List[List[ValueDocument]]
    units: List[Optional[str]]


class PlotDocument(TypedDict):
    """A plot in its JSON form."""

    kind: Literal["plot"]
    svg: str


class MeasurementDocument(TypedDict):
    """A measurement in its JSON form."""

    kind: Literal["measurement"]
    value: float
    lower: Optional[float]
    upper: Optional[float]
    p_value: Optional[float]
    unit: Optional[str]


class AssessmentDocument(TypedDict):
    """An assessment in its JSON form."""

    kind: Literal["assessment"]
    value: ValueDocument
    requirement_label: str
    passed: bool
    unit: Optional[str]


class BinsDocument(TypedDict):
    """The bins of a distribution's histogram in their JSON form."""

    edges: List[float]
    counts: List[int]


class DistributionDocument(TypedDict):
    """A distribution in its JSON form."""

    kind: Literal["distribution"]
    values: List[float]
    bin_count: Optional[int]
    statistics: Statistics
    histogram: BinsDocument


class HistogramDocument(TypedDict):
    """A histogram in its JSON form."""

    kind: Literal["histogram"]
    edges: List[float]
    counts: List[int]
    below_count: int
    above_count: int
    statistics: Optional[Statistics]


class CountDocument(TypedDict):
    """One value of a counts value with how often it occurs, in its JSON form."""

    value: ValueDocument
    count: int


class CountsDocument(TypedDict):
    """A counts value in its JSON form."""

    kind: Literal["counts"]
    counts: List[CountDocument]
    total: int


class FailureDocument(TypedDict):
    """A failure in its JSON form."""

    kind: Literal["failure"]
    exception_type: str
    message: str
    traceback: str


#: A type alias for what an analytic left behind, in its JSON form.
ResultDocument: TypeAlias = Union[
    ValueDocument,
    TableDocument,
    PlotDocument,
    MeasurementDocument,
    AssessmentDocument,
    DistributionDocument,
    HistogramDocument,
    CountsDocument,
    FailureDocument,
]


class InputDocument(TypedDict):
    """The size of one input MedRecord in its JSON form."""

    name: str
    node_count: int
    edge_count: int


class DerivationDocument(TypedDict):
    """The run of a derivation in its JSON form."""

    parameters: Dict[str, DetailDocument]
    summary: Dict[str, DetailDocument]
    duration: float
    failure: Optional[FailureDocument]


class AnalyticDocument(TypedDict):
    """The run of one analytic in its JSON form."""

    kind: Literal["analytic"]
    name: ValueDocument
    title: str
    description: Optional[str]
    parameters: Dict[str, DetailDocument]
    duration: float
    result: ResultDocument


class GroupDocument(TypedDict):
    """The run of one group in its JSON form."""

    kind: Literal["group"]
    name: ValueDocument
    title: str
    description: Optional[str]
    inputs: List[InputDocument]
    derivation: Optional[DerivationDocument]
    entries: List[
        Union[
            AnalyticDocument,
            "GroupDocument",
            "KeyedAnalyticDocument",
            "KeyedGroupDocument",
        ]
    ]


class KeyedResultDocument(TypedDict):
    """The result of one analytic under one key, in its JSON form."""

    key: ValueDocument
    duration: float
    result: ResultDocument


class KeyedAnalyticDocument(TypedDict):
    """The run of one analytic across keyed inputs, in its JSON form."""

    kind: Literal["keyed_analytic"]
    name: ValueDocument
    title: str
    description: Optional[str]
    parameters: Dict[str, DetailDocument]
    results: List[KeyedResultDocument]


class KeyedDerivationDocument(TypedDict):
    """The run of a derivation under one key, in its JSON form."""

    key: ValueDocument
    derivation: DerivationDocument


class KeyedGroupDocument(TypedDict):
    """The run of one group across keyed inputs, in its JSON form."""

    kind: Literal["keyed_group"]
    name: ValueDocument
    title: str
    description: Optional[str]
    inputs: List[InputDocument]
    derivations: List[KeyedDerivationDocument]
    entries: List[Union[KeyedAnalyticDocument, "KeyedGroupDocument"]]


class ReportDocument(TypedDict):
    """A whole report in its JSON form."""

    name: str
    description: Optional[str]
    started_at: str
    duration: float
    inputs: List[InputDocument]
    entries: List[
        Union[
            AnalyticDocument,
            GroupDocument,
            KeyedAnalyticDocument,
            KeyedGroupDocument,
        ]
    ]


class JsonObject:
    """A JSON object being read back, with where it sits in the file."""

    _content: Dict[str, Json]
    _path: str

    def __init__(self, content: Json, path: str) -> None:
        """Initializes a JSON object being read.

        Args:
            content (Json): What the file held.
            path (str): Where it sits in the file.

        Raises:
            ValueError: If the content is not an object.
        """
        if not isinstance(content, dict):
            msg = f"expected an object at {path}"
            raise ValueError(msg)

        self._content = content
        self._path = path

    @property
    def path(self) -> str:
        """Where the object sits in the file.

        Returns:
            str: The path.
        """
        return self._path

    def items(self) -> List[Tuple[str, Json]]:
        """Reads every key and content of the object.

        Returns:
            List[Tuple[str, Json]]: The pairs, in file order.
        """
        return list(self._content.items())

    def content(self, key: str) -> Json:
        """Reads what a key holds.

        Args:
            key (str): The key to read.

        Returns:
            Json: What the key holds.

        Raises:
            ValueError: If the key is missing.
        """
        if key not in self._content:
            msg = f"expected {key!r} at {self._path}"
            raise ValueError(msg)

        return self._content[key]

    def string(self, key: str) -> str:
        """Reads a key as a string.

        Args:
            key (str): The key to read.

        Returns:
            str: The string.
        """
        return JsonObject._decoded_string(self.content(key), f"{self._path}.{key}")

    def optional_string(self, key: str) -> Optional[str]:
        """Reads a key as a string or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[str]: The string, or None.
        """
        content = self.content(key)

        if content is None:
            return None

        return JsonObject._decoded_string(content, f"{self._path}.{key}")

    def boolean(self, key: str) -> bool:
        """Reads a key as a boolean.

        Args:
            key (str): The key to read.

        Returns:
            bool: The boolean.

        Raises:
            ValueError: If the key does not hold a boolean.
        """
        content = self.content(key)

        if not isinstance(content, bool):
            msg = f"expected a boolean at {self._path}.{key}"
            raise ValueError(msg)

        return content

    def number(self, key: str) -> float:
        """Reads a key as a number.

        Args:
            key (str): The key to read.

        Returns:
            float: The number.
        """
        return JsonObject._decoded_number(self.content(key), f"{self._path}.{key}")

    def optional_number(self, key: str) -> Optional[float]:
        """Reads a key as a number or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[float]: The number, or None.
        """
        content = self.content(key)

        if content is None:
            return None

        return JsonObject._decoded_number(content, f"{self._path}.{key}")

    def integer(self, key: str) -> int:
        """Reads a key as an integer.

        Args:
            key (str): The key to read.

        Returns:
            int: The integer.
        """
        return JsonObject._decoded_integer(self.content(key), f"{self._path}.{key}")

    def sequence(self, key: str) -> List[Json]:
        """Reads a key as an array.

        Args:
            key (str): The key to read.

        Returns:
            List[Json]: What the array holds.
        """
        return JsonObject._decoded_sequence(self.content(key), f"{self._path}.{key}")

    def document(self, key: str) -> JsonObject:
        """Reads a key as an object.

        Args:
            key (str): The key to read.

        Returns:
            JsonObject: The object.
        """
        return JsonObject(self.content(key), f"{self._path}.{key}")

    def optional_integer(self, key: str) -> Optional[int]:
        """Reads a key as an integer or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[int]: The integer, or None.
        """
        return None if self.content(key) is None else self.integer(key)

    def optional_document(self, key: str) -> Optional[JsonObject]:
        """Reads a key as an object or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[JsonObject]: The object, or None.
        """
        content = self.content(key)

        if content is None:
            return None

        return JsonObject(content, f"{self._path}.{key}")

    @staticmethod
    def _decoded_string(content: Json, path: str) -> str:
        if not isinstance(content, str):
            msg = f"expected a string at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_identifier(content: Json, path: str) -> Identifier:
        if isinstance(content, bool) or not isinstance(content, (str, int)):
            msg = f"expected an identifier at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_number(content: Json, path: str) -> float:
        if isinstance(content, bool) or not isinstance(content, (int, float)):
            msg = f"expected a number at {path}"
            raise ValueError(msg)

        return float(content)

    @staticmethod
    def _decoded_integer(content: Json, path: str) -> int:
        if not isinstance(content, int) or isinstance(content, bool):
            msg = f"expected an integer at {path}"
            raise ValueError(msg)

        return content

    def optional_unit(self, key: str) -> Optional[Unit]:
        """Reads a key as a unit or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[Unit]: The unit, or None.
        """
        content = self.content(key)

        if content is None:
            return None

        return JsonObject._decoded_unit(content, f"{self._path}.{key}")

    @staticmethod
    def _decoded_datetime(text: str, path: str) -> datetime:
        try:
            return datetime.fromisoformat(text)
        except ValueError as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_duration(seconds: float, path: str) -> timedelta:
        try:
            return timedelta(seconds=seconds)
        except (OverflowError, ValueError) as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_timedelta(document: JsonObject) -> timedelta:
        try:
            return timedelta(
                days=document.integer("days"),
                seconds=document.integer("seconds"),
                microseconds=document.integer("microseconds"),
            )
        except (OverflowError, ValueError) as error:
            msg = f"{error} at {document.path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_non_finite(text: str, path: str) -> float:
        try:
            return float(text)
        except ValueError as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_sequence(content: Json, path: str) -> List[Json]:
        if not isinstance(content, list):
            msg = f"expected an array at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_value(content: Json, path: str) -> Value:
        if content is None or isinstance(content, (str, bool, int, float)):
            return content

        document = JsonObject(content, path)
        kind = document.string("kind")

        if kind == "datetime":
            return JsonObject._decoded_datetime(document.string("value"), path)

        if kind == "timedelta":
            return JsonObject._decoded_timedelta(document)

        if kind == "float":
            return JsonObject._decoded_non_finite(document.string("value"), path)

        msg = f"expected a value at {path}"
        raise ValueError(msg)

    @staticmethod
    def _decoded_unit(content: Json, path: str) -> Unit:
        try:
            return Unit(JsonObject._decoded_string(content, path))
        except ValueError as error:
            msg = f"expected a unit at {path}"
            raise ValueError(msg) from error

    def _table(self) -> Table:
        headings = [
            JsonObject._decoded_identifier(heading, f"{self._path}.headings[{index}]")
            for index, heading in enumerate(self.sequence("headings"))
        ]
        rows = [
            [
                JsonObject._decoded_value(cell, f"{self._path}.rows")
                for cell in JsonObject._decoded_sequence(row, f"{self._path}.rows")
            ]
            for row in self.sequence("rows")
        ]

        units = [
            None
            if content is None
            else JsonObject._decoded_unit(content, f"{self._path}.units[{index}]")
            for index, content in enumerate(self.sequence("units"))
        ]

        if len(units) != len(headings):
            msg = f"expected one unit per heading at {self._path}.units"
            raise ValueError(msg)

        try:
            return Table(
                headings,
                rows,
                units={
                    heading: unit
                    for heading, unit in zip(headings, units, strict=True)
                    if unit is not None
                },
            )
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    def _distribution(self) -> Distribution:
        values = [
            JsonObject._decoded_number(value, f"{self._path}.values")
            for value in self.sequence("values")
        ]
        bin_count = self.optional_integer("bin_count")

        try:
            return Distribution(values, bin_count)
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    def _histogram(self) -> Histogram:
        edges = [
            JsonObject._decoded_number(edge, f"{self._path}.edges")
            for edge in self.sequence("edges")
        ]
        counts = [
            JsonObject._decoded_integer(count, f"{self._path}.counts")
            for count in self.sequence("counts")
        ]
        statistics = self.optional_document("statistics")

        try:
            return Histogram(
                edges,
                counts,
                below_count=self.integer("below_count"),
                above_count=self.integer("above_count"),
                statistics=None if statistics is None else statistics._statistics(),
            )
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    def _statistics(self) -> Statistics:
        return {
            "count": self.integer("count"),
            "mean": self.number("mean"),
            "standard_deviation": self.number("standard_deviation"),
            "minimum": self.number("minimum"),
            "lower_quartile": self.number("lower_quartile"),
            "median": self.number("median"),
            "upper_quartile": self.number("upper_quartile"),
            "maximum": self.number("maximum"),
        }

    def _counts(self) -> Counts:
        counts: Dict[Value, int] = {}

        for index, item in enumerate(self.sequence("counts")):
            document = JsonObject(item, f"{self._path}.counts[{index}]")
            value = JsonObject._decoded_value(
                document.content("value"), f"{document.path}.value"
            )
            counts[value] = document.integer("count")

        try:
            return Counts(counts, self.integer("total"))
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    def _details(self, key: str) -> Dict[str, Detail]:
        details = self.document(key)
        decoded: Dict[str, Detail] = {}

        for name, content in details.items():
            path = f"{details.path}.{name}"

            if isinstance(content, list):
                decoded[name] = [
                    JsonObject._decoded_value(item, f"{path}[{index}]")
                    for index, item in enumerate(content)
                ]
            else:
                decoded[name] = JsonObject._decoded_value(content, path)

        return decoded


def copy_details(details: Mapping[str, Detail]) -> Dict[str, Detail]:
    """Copies parameters or a summary, so that no caller shares what is recorded.

    Args:
        details (Mapping[str, Detail]): The details by name.

    Returns:
        Dict[str, Detail]: The details, every sequence as a fresh list.
    """
    return {
        name: list(detail)
        if isinstance(detail, Sequence) and not isinstance(detail, str)
        else detail
        for name, detail in details.items()
    }


def encode_value(value: Value) -> ValueDocument:
    """Converts a value to its JSON form.

    Args:
        value (Value): The value to convert.

    Returns:
        ValueDocument: The value itself if JSON holds its type, otherwise a
            tagged object.
    """
    if isinstance(value, datetime):
        return {"kind": "datetime", "value": value.isoformat()}

    if isinstance(value, timedelta):
        return {
            "kind": "timedelta",
            "days": value.days,
            "seconds": value.seconds,
            "microseconds": value.microseconds,
        }

    if isinstance(value, float) and not math.isfinite(value):
        return {"kind": "float", "value": str(value)}

    return value


def encode_details(details: Mapping[str, Detail]) -> Dict[str, DetailDocument]:
    """Converts parameters or a summary to their JSON form.

    Args:
        details (Mapping[str, Detail]): The details by name.

    Returns:
        Dict[str, DetailDocument]: The details in their JSON form, by name.
    """
    return {
        name: encode_value(detail)
        if isinstance(detail, str) or not isinstance(detail, Sequence)
        else [encode_value(item) for item in detail]
        for name, detail in details.items()
    }


def encode_unit(unit: Optional[Unit]) -> Optional[str]:
    """Converts a unit to its JSON form.

    Args:
        unit (Optional[Unit]): The unit, or None.

    Returns:
        Optional[str]: The value of the unit, or None.
    """
    return None if unit is None else unit.value


def encode_distribution(
    distribution: Distribution, histogram: Histogram
) -> DistributionDocument:
    """Converts a distribution to its JSON form, with the histogram given.

    Args:
        distribution (Distribution): The distribution to convert.
        histogram (Histogram): The histogram to write, which is the
            distribution's own or one over edges shared with others.

    Returns:
        DistributionDocument: The JSON form of the distribution.
    """
    return {
        "kind": "distribution",
        "values": distribution.values,
        "bin_count": distribution.bin_count,
        "statistics": distribution.statistics,
        "histogram": {"edges": histogram.edges, "counts": histogram.counts},
    }
