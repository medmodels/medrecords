"""The JSON form of a report: its document types, decoder and value encoders."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeAlias,
    TypedDict,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from graphrecords import Identifier, Value

    from medrecords.evaluation.analytic import Cell, Detail

MemberType = TypeVar("MemberType", bound=Enum)

#: A type alias for anything a JSON file can hold.
Json: TypeAlias = Union[str, int, float, bool, List["Json"], Dict[str, "Json"], None]


class DateTimeDocument(TypedDict):
    """A datetime in its JSON form, in its parts and its offset from UTC in seconds."""

    kind: Literal["datetime"]
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    microsecond: int
    offset: Optional[int]


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


#: A type alias for a float in its JSON form: the number, or its text when JSON
#: cannot hold it.
FloatDocument: TypeAlias = Union[float, NonFiniteDocument]

#: A type alias for a value in its JSON form.
ValueDocument: TypeAlias = Union[
    str,
    int,
    FloatDocument,
    bool,
    DateTimeDocument,
    DurationDocument,
    None,
]

#: A type alias for one parameter or summary item in its JSON form.
DetailDocument: TypeAlias = Union[ValueDocument, List[ValueDocument]]


class PathDocument(TypedDict):
    """The path of an entry in a table cell, in its JSON form."""

    kind: Literal["path"]
    names: List[ValueDocument]


#: A type alias for one table cell in its JSON form.
CellDocument: TypeAlias = Union[ValueDocument, PathDocument]


class TableDocument(TypedDict):
    """A table in its JSON form."""

    kind: Literal["table"]
    headings: List[Identifier]
    rows: List[List[CellDocument]]
    units: List[Optional[str]]
    printed_rows: Optional[int]


class PlotDocument(TypedDict):
    """A plot in its JSON form."""

    kind: Literal["plot"]
    svg: str


class MeasurementDocument(TypedDict):
    """A measurement in its JSON form."""

    kind: Literal["measurement"]
    value: FloatDocument
    lower: Optional[FloatDocument]
    upper: Optional[FloatDocument]
    p_value: Optional[FloatDocument]
    unit: Optional[str]


class AssessmentDocument(TypedDict):
    """An assessment in its JSON form."""

    kind: Literal["assessment"]
    value: ValueDocument
    requirement_label: str
    passed: bool
    unit: Optional[str]


class BinsDocument(TypedDict):
    """The bin settings of a distribution in their JSON form."""

    count: Optional[int]
    scale: Optional[str]
    outside_share: Optional[float]


class StatisticsDocument(TypedDict):
    """The summary statistics of numeric values, in their JSON form."""

    count: int
    mean: FloatDocument
    standard_deviation: Optional[FloatDocument]
    minimum: FloatDocument
    lower_quartile: FloatDocument
    median: FloatDocument
    upper_quartile: FloatDocument
    maximum: FloatDocument


class DistributionHistogramDocument(TypedDict):
    """The histogram drawn of a distribution, in its JSON form."""

    edges: List[float]
    counts: List[int]
    below_count: int
    above_count: int
    scale: str
    whole_numbers: bool


class DistributionDocument(TypedDict):
    """A distribution in its JSON form."""

    kind: Literal["distribution"]
    values: List[float]
    bins: Optional[BinsDocument]
    value_label: Optional[str]
    count_label: Optional[str]
    arrangement: Optional[str]
    statistics: StatisticsDocument
    histogram: DistributionHistogramDocument


class HistogramDocument(TypedDict):
    """A histogram in its JSON form."""

    kind: Literal["histogram"]
    edges: List[float]
    counts: List[int]
    below_count: int
    above_count: int
    statistics: Optional[StatisticsDocument]
    scale: str
    whole_numbers: bool
    value_label: Optional[str]
    count_label: Optional[str]
    arrangement: Optional[str]


class CountDocument(TypedDict):
    """One value of a counts value with how often it occurs, in its JSON form."""

    value: ValueDocument
    count: int


class CountsDocument(TypedDict):
    """A counts value in its JSON form."""

    kind: Literal["counts"]
    counts: List[CountDocument]
    total: int
    value_label: Optional[str]
    count_label: Optional[str]
    remainder_label: Optional[str]
    arrangement: Optional[str]


class ScatterLabelDocument(TypedDict):
    """The label of one point of a scatter, in its JSON form."""

    index: int
    label: str


class ScatterDocument(TypedDict):
    """A scatter in its JSON form."""

    kind: Literal["scatter"]
    points: List[List[float]]
    x_label: str
    y_label: str
    x_scale: str
    y_scale: str
    labels: List[ScatterLabelDocument]
    diagonal: bool


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
    ScatterDocument,
    FailureDocument,
]


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
    layout: str
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
    layout: str
    derivations: List[KeyedDerivationDocument]
    entries: List[Union[KeyedAnalyticDocument, "KeyedGroupDocument"]]


class ReportDocument(TypedDict):
    """A whole report in its JSON form."""

    name: str
    description: Optional[str]
    parameters: Dict[str, DetailDocument]
    started_at: DateTimeDocument
    duration: float
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
        if isinstance(content, dict):
            document = JsonObject(content, path)

            if document.string("kind") == "float":
                return JsonObject._decoded_non_finite(document.string("value"), path)

        if isinstance(content, bool) or not isinstance(content, (int, float)):
            msg = f"expected a number at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_integer(content: Json, path: str) -> int:
        if not isinstance(content, int) or isinstance(content, bool):
            msg = f"expected an integer at {path}"
            raise ValueError(msg)

        return content

    def member(self, key: str, enumeration: Type[MemberType]) -> MemberType:
        """Reads a key as a member of an enumeration, by its value.

        Args:
            key (str): The key to read.
            enumeration (Type[MemberType]): The enumeration.

        Returns:
            MemberType: The member.
        """
        return JsonObject._decoded_member(
            self.content(key), f"{self._path}.{key}", enumeration
        )

    def optional_member(
        self, key: str, enumeration: Type[MemberType]
    ) -> Optional[MemberType]:
        """Reads a key as a member of an enumeration or null.

        Args:
            key (str): The key to read.
            enumeration (Type[MemberType]): The enumeration.

        Returns:
            Optional[MemberType]: The member, or None.
        """
        return None if self.content(key) is None else self.member(key, enumeration)

    @staticmethod
    def _decoded_member(
        content: Json, path: str, enumeration: Type[MemberType]
    ) -> MemberType:
        try:
            return enumeration(JsonObject._decoded_string(content, path))
        except ValueError as error:
            msg = f"expected a value of {enumeration.__name__} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_datetime(document: JsonObject) -> datetime:
        offset = document.optional_integer("offset")

        try:
            return datetime(
                document.integer("year"),
                document.integer("month"),
                document.integer("day"),
                document.integer("hour"),
                document.integer("minute"),
                document.integer("second"),
                document.integer("microsecond"),
                tzinfo=None if offset is None else timezone(timedelta(seconds=offset)),
            )
        except (OverflowError, ValueError) as error:
            msg = f"{error} at {document.path}"
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
            return JsonObject._decoded_datetime(document)

        if kind == "timedelta":
            return JsonObject._decoded_timedelta(document)

        if kind == "float":
            return JsonObject._decoded_non_finite(document.string("value"), path)

        msg = f"expected a value at {path}"
        raise ValueError(msg)

    @staticmethod
    def _decoded_cell(content: Json, path: str) -> Cell:
        if isinstance(content, dict) and content.get("kind") == "path":
            document = JsonObject(content, path)

            return tuple(
                JsonObject._decoded_value(name, f"{path}.names[{index}]")
                for index, name in enumerate(document.sequence("names"))
            )

        return JsonObject._decoded_value(content, path)

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


def encode_float(number: float) -> FloatDocument:
    """Converts a float to its JSON form.

    Args:
        number (float): The float to convert.

    Returns:
        FloatDocument: The float itself if it is finite, otherwise its text in
            a tagged object.
    """
    if not math.isfinite(number):
        return {"kind": "float", "value": str(number)}

    return number


def encode_value(value: Value) -> ValueDocument:
    """Converts a value to its JSON form.

    Args:
        value (Value): The value to convert.

    Returns:
        ValueDocument: The value itself if JSON holds its type, otherwise a
            tagged object.
    """
    if isinstance(value, datetime):
        return encode_datetime(value)

    if isinstance(value, timedelta):
        return {
            "kind": "timedelta",
            "days": value.days,
            "seconds": value.seconds,
            "microseconds": value.microseconds,
        }

    if isinstance(value, float):
        return encode_float(value)

    return value


def encode_datetime(value: datetime) -> DateTimeDocument:
    """Converts a datetime to its JSON form.

    Args:
        value (datetime): The datetime to convert.

    Returns:
        DateTimeDocument: The parts of the datetime and its offset from UTC.
    """
    offset = value.utcoffset()

    return {
        "kind": "datetime",
        "year": value.year,
        "month": value.month,
        "day": value.day,
        "hour": value.hour,
        "minute": value.minute,
        "second": value.second,
        "microsecond": value.microsecond,
        "offset": None if offset is None else int(offset.total_seconds()),
    }


def encode_cell(cell: Cell) -> CellDocument:
    """Converts a table cell to its JSON form.

    Args:
        cell (Cell): The cell to convert.

    Returns:
        CellDocument: The value in its JSON form, or the path as a tagged object.
    """
    if isinstance(cell, tuple):
        return {"kind": "path", "names": [encode_value(name) for name in cell]}

    return encode_value(cell)


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
