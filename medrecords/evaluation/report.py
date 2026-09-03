"""Report classes holding what a run found, and their JSON form."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from traceback import format_exception
from typing import (
    TYPE_CHECKING,
    Dict,
    Final,
    Iterator,
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
    overload,
)

from medrecords.evaluation.analytic import (
    Assessment,
    Distribution,
    Measurement,
    Plot,
    Table,
)
from medrecords.medrecord import MedRecord

if TYPE_CHECKING:
    import os

    from graphrecords.types import Value

    from medrecords.evaluation.analytic import Bin, Detail, ReportValue

KindType = TypeVar(
    "KindType",
    bound=Union[
        str,
        int,
        float,
        bool,
        datetime,
        timedelta,
        Table,
        Plot,
        Measurement,
        Assessment,
        Distribution,
    ],
)

#: A type alias for the names leading from the report root to an entry.
EntryPath: TypeAlias = Tuple[str, ...]

#: A type alias for anything a JSON file can hold.
_Json: TypeAlias = Union[str, int, float, bool, List["_Json"], Dict[str, "_Json"], None]


class _DateTimeDocument(TypedDict):
    """A datetime in its JSON form."""

    kind: Literal["datetime"]
    value: str


class _DurationDocument(TypedDict):
    """A duration in its JSON form, in the parts a duration is built from."""

    kind: Literal["timedelta"]
    days: int
    seconds: int
    microseconds: int


class _NonFiniteDocument(TypedDict):
    """A number JSON cannot hold, as its text."""

    kind: Literal["float"]
    value: str


#: A type alias for a value in its JSON form.
_ValueDocument: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    _DateTimeDocument,
    _DurationDocument,
    _NonFiniteDocument,
    None,
]

#: A type alias for one parameter or summary item in its JSON form.
_DetailDocument: TypeAlias = Union[_ValueDocument, List[_ValueDocument]]


class _TableDocument(TypedDict):
    """A table in its JSON form."""

    kind: Literal["table"]
    headings: List[str]
    rows: List[List[_ValueDocument]]


class _PlotDocument(TypedDict):
    """A plot in its JSON form."""

    kind: Literal["plot"]
    svg: str


class _MeasurementDocument(TypedDict):
    """A measurement in its JSON form."""

    kind: Literal["measurement"]
    value: float
    lower: Optional[float]
    upper: Optional[float]
    p_value: Optional[float]


class _AssessmentDocument(TypedDict):
    """An assessment in its JSON form."""

    kind: Literal["assessment"]
    value: _ValueDocument
    requirement_label: str
    passed: bool


class _SummaryDocument(TypedDict):
    """The summary statistics of a distribution in their JSON form."""

    count: int
    mean: float
    std: float
    minimum: float
    lower_quartile: float
    median: float
    upper_quartile: float
    maximum: float


class _DistributionDocument(TypedDict):
    """A distribution in its JSON form."""

    kind: Literal["distribution"]
    values: List[float]
    bins: Optional[int]
    summary: _SummaryDocument
    histogram: List[Bin]


class _FailureDocument(TypedDict):
    """A failure in its JSON form."""

    kind: Literal["failure"]
    exception_type: str
    message: str
    traceback: str


#: A type alias for what an analytic left behind, in its JSON form.
_ResultDocument: TypeAlias = Union[
    _ValueDocument,
    _TableDocument,
    _PlotDocument,
    _MeasurementDocument,
    _AssessmentDocument,
    _DistributionDocument,
    _FailureDocument,
]


class _InputDocument(TypedDict):
    """The size of one input MedRecord in its JSON form."""

    name: str
    node_count: int
    edge_count: int


class _DerivationDocument(TypedDict):
    """The run of a derivation in its JSON form."""

    parameters: Dict[str, _DetailDocument]
    summary: Dict[str, _DetailDocument]
    duration: float
    outcome: Optional[_FailureDocument]


class _AnalyticDocument(TypedDict):
    """The run of one analytic in its JSON form."""

    kind: Literal["analytic"]
    name: str
    title: str
    description: Optional[str]
    parameters: Dict[str, _DetailDocument]
    duration: float
    result: _ResultDocument


class _GroupDocument(TypedDict):
    """The run of one group in its JSON form."""

    kind: Literal["group"]
    name: str
    title: str
    description: Optional[str]
    inputs: List[_InputDocument]
    derivation: Optional[_DerivationDocument]
    entries: List[Union[_AnalyticDocument, "_GroupDocument"]]


class _ReportDocument(TypedDict):
    """A whole report in its JSON form."""

    name: str
    description: Optional[str]
    started_at: str
    duration: float
    inputs: List[_InputDocument]
    entries: List[Union[_AnalyticDocument, _GroupDocument]]


#: The name a bare MedRecord is recorded under in the inputs of a report.
_BARE_INPUT_NAME: Final[str] = "medrecord"


class _Document:
    """A JSON object being read back, with where it sits in the file."""

    _content: Dict[str, _Json]
    _path: str

    def __init__(self, content: _Json, path: str) -> None:
        """Reads a JSON object.

        Args:
            content (_Json): What the file held.
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

    def items(self) -> List[Tuple[str, _Json]]:
        """Reads every key and content of the object.

        Returns:
            List[Tuple[str, _Json]]: The pairs, in file order.
        """
        return list(self._content.items())

    def content(self, key: str) -> _Json:
        """Reads what a key holds.

        Args:
            key (str): The key to read.

        Returns:
            _Json: What the key holds.

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
        return _Document._decoded_string(self.content(key), f"{self._path}.{key}")

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

        return _Document._decoded_string(content, f"{self._path}.{key}")

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
        return _Document._decoded_number(self.content(key), f"{self._path}.{key}")

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

        return _Document._decoded_number(content, f"{self._path}.{key}")

    def integer(self, key: str) -> int:
        """Reads a key as an integer.

        Args:
            key (str): The key to read.

        Returns:
            int: The integer.

        Raises:
            ValueError: If the key does not hold an integer.
        """
        content = self.content(key)

        if not isinstance(content, int) or isinstance(content, bool):
            msg = f"expected an integer at {self._path}.{key}"
            raise ValueError(msg)

        return content

    def sequence(self, key: str) -> List[_Json]:
        """Reads a key as an array.

        Args:
            key (str): The key to read.

        Returns:
            List[_Json]: What the array holds.
        """
        return _Document._decoded_sequence(self.content(key), f"{self._path}.{key}")

    def document(self, key: str) -> _Document:
        """Reads a key as an object.

        Args:
            key (str): The key to read.

        Returns:
            _Document: The object.
        """
        return _Document(self.content(key), f"{self._path}.{key}")

    def optional_document(self, key: str) -> Optional[_Document]:
        """Reads a key as an object or null.

        Args:
            key (str): The key to read.

        Returns:
            Optional[_Document]: The object, or None.
        """
        content = self.content(key)

        if content is None:
            return None

        return _Document(content, f"{self._path}.{key}")

    @staticmethod
    def _decoded_string(content: _Json, path: str) -> str:
        """Reads a string back.

        Args:
            content (_Json): What the file held.
            path (str): Where it sits in the file.

        Returns:
            str: The string.

        Raises:
            ValueError: If the content is not a string.
        """
        if not isinstance(content, str):
            msg = f"expected a string at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_number(content: _Json, path: str) -> float:
        """Reads a number back.

        Args:
            content (_Json): What the file held.
            path (str): Where it sits in the file.

        Returns:
            float: The number.

        Raises:
            ValueError: If the content is not a number.
        """
        if isinstance(content, bool) or not isinstance(content, (int, float)):
            msg = f"expected a number at {path}"
            raise ValueError(msg)

        return float(content)

    @staticmethod
    def _decoded_moment(text: str, path: str) -> datetime:
        """Reads a timestamp back from its text.

        Args:
            text (str): The timestamp in ISO 8601.
            path (str): Where it sits in the file.

        Returns:
            datetime: The timestamp.

        Raises:
            ValueError: If the text is not a timestamp.
        """
        try:
            return datetime.fromisoformat(text)
        except ValueError as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_duration(seconds: float, path: str) -> timedelta:
        """Reads a duration back from its seconds.

        Args:
            seconds (float): How many seconds the duration holds.
            path (str): Where it sits in the file.

        Returns:
            timedelta: The duration.

        Raises:
            ValueError: If no duration is that long.
        """
        try:
            return timedelta(seconds=seconds)
        except (OverflowError, ValueError) as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_parts(document: _Document) -> timedelta:
        """Reads a duration back from its parts.

        Args:
            document (_Document): The object holding the parts.

        Returns:
            timedelta: The duration.

        Raises:
            ValueError: If no duration is that long.
        """
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
        """Reads a number JSON cannot hold back from its text.

        Args:
            text (str): The number as text.
            path (str): Where it sits in the file.

        Returns:
            float: The number.

        Raises:
            ValueError: If the text is not a number.
        """
        try:
            return float(text)
        except ValueError as error:
            msg = f"{error} at {path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_sequence(content: _Json, path: str) -> List[_Json]:
        """Reads an array back.

        Args:
            content (_Json): What the file held.
            path (str): Where it sits in the file.

        Returns:
            List[_Json]: What the array holds.

        Raises:
            ValueError: If the content is not an array.
        """
        if not isinstance(content, list):
            msg = f"expected an array at {path}"
            raise ValueError(msg)

        return content

    @staticmethod
    def _decoded_value(content: _Json, path: str) -> Value:
        """Reads a value back from its JSON form.

        Args:
            content (_Json): The JSON form of the value.
            path (str): Where the value sits in the file.

        Returns:
            Value: The value.

        Raises:
            ValueError: If the content is not a value.
        """
        if content is None or isinstance(content, (str, bool, int, float)):
            return content

        document = _Document(content, path)
        kind = document.string("kind")

        if kind == "datetime":
            return _Document._decoded_moment(document.string("value"), path)

        if kind == "timedelta":
            return _Document._decoded_parts(document)

        if kind == "float":
            return _Document._decoded_non_finite(document.string("value"), path)

        msg = f"expected a value at {path}"
        raise ValueError(msg)

    def _table(self) -> Table:
        """Reads the object as a table.

        Returns:
            Table: The table.

        Raises:
            ValueError: If a heading is empty, two headings are the same, or a
                row does not hold one value per heading.
        """
        headings = [
            _Document._decoded_string(heading, f"{self._path}.headings")
            for heading in self.sequence("headings")
        ]
        rows = [
            [
                _Document._decoded_value(cell, f"{self._path}.rows")
                for cell in _Document._decoded_sequence(row, f"{self._path}.rows")
            ]
            for row in self.sequence("rows")
        ]

        try:
            return Table(headings, rows)
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    def _distribution(self) -> Distribution:
        """Reads the object as a distribution.

        The summary and the histogram are computed again from the values.

        Returns:
            Distribution: The distribution.

        Raises:
            ValueError: If it holds no values, or asks for fewer than one bin.
        """
        values = [
            _Document._decoded_number(value, f"{self._path}.values")
            for value in self.sequence("values")
        ]
        bins = None if self.content("bins") is None else self.integer("bins")

        try:
            return Distribution(values, bins)
        except ValueError as error:
            msg = f"{error} at {self._path}"
            raise ValueError(msg) from error

    @staticmethod
    def _decoded_result(content: _Json, path: str) -> Union[ReportValue, Failure]:
        """Reads a result back from its JSON form.

        Args:
            content (_Json): The JSON form of the result.
            path (str): Where the result sits in the file.

        Returns:
            Union[ReportValue, Failure]: The result.
        """
        if not isinstance(content, dict):
            return _Document._decoded_value(content, path)

        document = _Document(content, path)
        kind = document.string("kind")

        if kind == "table":
            return document._table()

        if kind == "plot":
            return Plot(document.string("svg"))

        if kind == "measurement":
            return Measurement(
                document.number("value"),
                document.optional_number("lower"),
                document.optional_number("upper"),
                document.optional_number("p_value"),
            )

        if kind == "assessment":
            return Assessment(
                _Document._decoded_value(document.content("value"), f"{path}.value"),
                document.string("requirement_label"),
                passed=document.boolean("passed"),
            )

        if kind == "distribution":
            return document._distribution()

        if kind == "failure":
            return Failure._from_document(document)

        return _Document._decoded_value(content, path)

    def _details(self, key: str) -> Dict[str, Detail]:
        """Reads a key as parameters or a summary.

        Args:
            key (str): The key they sit under.

        Returns:
            Dict[str, Detail]: The details by name.
        """
        details = self.document(key)
        return {
            name: [
                _Document._decoded_value(item, f"{details.path}.{name}")
                for item in _Document._decoded_sequence(
                    content, f"{details.path}.{name}"
                )
            ]
            if isinstance(content, list)
            else _Document._decoded_value(content, f"{details.path}.{name}")
            for name, content in details.items()
        }


def _copied_details(details: Mapping[str, Detail]) -> Dict[str, Detail]:
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


def _encode_value(value: Value) -> _ValueDocument:
    """Converts a value to its JSON form.

    Args:
        value (Value): The value to convert.

    Returns:
        _ValueDocument: The value itself if JSON holds its type, otherwise a
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


def _encode_details(details: Mapping[str, Detail]) -> Dict[str, _DetailDocument]:
    """Converts parameters or a summary to their JSON form.

    Args:
        details (Mapping[str, Detail]): The details by name.

    Returns:
        Dict[str, _DetailDocument]: The details in their JSON form, by name.
    """
    return {
        name: _encode_value(detail)
        if isinstance(detail, str) or not isinstance(detail, Sequence)
        else [_encode_value(item) for item in detail]
        for name, detail in details.items()
    }


def _encode_result(result: Union[ReportValue, Failure]) -> _ResultDocument:
    """Converts a result to its JSON form.

    Args:
        result (Union[ReportValue, Failure]): The result to convert.

    Returns:
        _ResultDocument: The JSON form of the result.
    """
    if isinstance(result, Table):
        return {
            "kind": "table",
            "headings": result.headings,
            "rows": [[_encode_value(cell) for cell in row] for row in result.rows],
        }

    if isinstance(result, Plot):
        return {"kind": "plot", "svg": result.svg}

    if isinstance(result, Measurement):
        return {
            "kind": "measurement",
            "value": result.value,
            "lower": result.lower,
            "upper": result.upper,
            "p_value": result.p_value,
        }

    if isinstance(result, Assessment):
        return {
            "kind": "assessment",
            "value": _encode_value(result.value),
            "requirement_label": result.requirement_label,
            "passed": result.passed,
        }

    if isinstance(result, Distribution):
        return {
            "kind": "distribution",
            "values": result.values,
            "bins": result.bins,
            "summary": {
                "count": result.count,
                "mean": result.mean,
                "std": result.std,
                "minimum": result.minimum,
                "lower_quartile": result.lower_quartile,
                "median": result.median,
                "upper_quartile": result.upper_quartile,
                "maximum": result.maximum,
            },
            "histogram": result.histogram(),
        }

    if isinstance(result, Failure):
        return result._to_document()

    return _encode_value(result)


class Failure:
    """What a failed analytic or derivation raised, or handed back in band."""

    _exception_type: str
    _message: str
    _traceback: str

    def __init__(self, exception_type: str, message: str, traceback: str) -> None:
        """Initializes a failure.

        Args:
            exception_type (str): The qualified name of the exception class.
            message (str): The message of the exception.
            traceback (str): The formatted traceback.
        """
        self._exception_type = exception_type
        self._message = message
        self._traceback = traceback

    @classmethod
    def _from_exception(cls, error: BaseException) -> Failure:
        """Records an exception.

        Args:
            error (BaseException): The exception to record.

        Returns:
            Failure: The exception's qualified type name, message and traceback.
        """
        exception_type = type(error)

        return cls(
            f"{exception_type.__module__}.{exception_type.__qualname__}",
            str(error),
            "".join(format_exception(exception_type, error, error.__traceback__)),
        )

    @classmethod
    def _from_document(cls, document: _Document) -> Failure:
        """Reads a failure back from its JSON form.

        Args:
            document (_Document): The JSON object holding the failure.

        Returns:
            Failure: The failure the document holds.
        """
        return cls(
            document.string("exception_type"),
            document.string("message"),
            document.string("traceback"),
        )

    def _to_document(self) -> _FailureDocument:
        """Converts the failure to its JSON form.

        Returns:
            _FailureDocument: The JSON object holding the failure.
        """
        return {
            "kind": "failure",
            "exception_type": self._exception_type,
            "message": self._message,
            "traceback": self._traceback,
        }

    @property
    def exception_type(self) -> str:
        """The qualified name of the exception class.

        Returns:
            str: The module and qualified name of the exception class.
        """
        return self._exception_type

    @property
    def message(self) -> str:
        """The message of the exception.

        Returns:
            str: The message of the exception.
        """
        return self._message

    @property
    def traceback(self) -> str:
        """The formatted traceback of the exception.

        Returns:
            str: The formatted traceback.
        """
        return self._traceback

    def __eq__(self, other: object) -> bool:
        """Compares the Failure with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same exception type, message and
                traceback, otherwise False.
        """
        if not isinstance(other, Failure):
            return NotImplemented

        return (
            self._exception_type == other._exception_type
            and self._message == other._message
            and self._traceback == other._traceback
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Failure.

        Returns:
            str: The exception type and message of the Failure.
        """
        return f"Failure({self._exception_type}: {self._message})"


class InputEntry:
    """The name and size of one MedRecord found in the inputs of a group.

    A bare MedRecord is named ``medrecord``; a MedRecord inside a mapping or a
    sequence is named by its keys joined with dots (``synthetics.a``).
    """

    _name: str
    _node_count: int
    _edge_count: int

    def __init__(self, name: str, node_count: int, edge_count: int) -> None:
        """Initializes an input entry.

        Args:
            name (str): The name the MedRecord was found under.
            node_count (int): The number of nodes of the MedRecord.
            edge_count (int): The number of edges of the MedRecord.
        """
        self._name = name
        self._node_count = node_count
        self._edge_count = edge_count

    @classmethod
    def _from_inputs(cls, inputs: object, name: str = "") -> List[InputEntry]:
        """Records every MedRecord found in the inputs of a group.

        Args:
            inputs (object): The inputs to search.
            name (str): The name the inputs were found under. Defaults to "".

        Returns:
            List[InputEntry]: One entry per MedRecord, in the order found.
        """
        if isinstance(inputs, MedRecord):
            return [
                cls(name or _BARE_INPUT_NAME, inputs.node_count(), inputs.edge_count())
            ]

        if isinstance(inputs, Mapping):
            return [
                entry
                for key, item in inputs.items()
                for entry in cls._from_inputs(item, cls._join(name, str(key)))
            ]

        if isinstance(inputs, Sequence) and not isinstance(inputs, (str, bytes)):
            return [
                entry
                for position, item in enumerate(inputs)
                for entry in cls._from_inputs(item, cls._join(name, str(position)))
            ]

        return []

    @staticmethod
    def _join(name: str, key: str) -> str:
        """Joins the name of a container with the key found inside it.

        Args:
            name (str): The name of the container, or "" for the inputs themselves.
            key (str): The key found inside the container.

        Returns:
            str: The joined name.
        """
        return f"{name}.{key}" if name else key

    @classmethod
    def _from_document(cls, document: _Document) -> InputEntry:
        """Reads an input entry back from its JSON form.

        Args:
            document (_Document): The JSON object holding the entry.

        Returns:
            InputEntry: The entry the document holds.
        """
        return cls(
            document.string("name"),
            document.integer("node_count"),
            document.integer("edge_count"),
        )

    def _to_document(self) -> _InputDocument:
        """Converts the entry to its JSON form.

        Returns:
            _InputDocument: The JSON object holding the entry.
        """
        return {
            "name": self._name,
            "node_count": self._node_count,
            "edge_count": self._edge_count,
        }

    @property
    def name(self) -> str:
        """The name the MedRecord was found under.

        Returns:
            str: The name of the input.
        """
        return self._name

    @property
    def node_count(self) -> int:
        """The number of nodes of the MedRecord.

        Returns:
            int: The number of nodes.
        """
        return self._node_count

    @property
    def edge_count(self) -> int:
        """The number of edges of the MedRecord.

        Returns:
            int: The number of edges.
        """
        return self._edge_count

    def __eq__(self, other: object) -> bool:
        """Compares the InputEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name and sizes, otherwise False.
        """
        if not isinstance(other, InputEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._node_count == other._node_count
            and self._edge_count == other._edge_count
        )

    def __repr__(self) -> str:
        """Returns the string representation of the InputEntry.

        Returns:
            str: The name and the sizes of the MedRecord.
        """
        return (
            f"InputEntry({self._name!r}, node_count={self._node_count}, "
            f"edge_count={self._edge_count})"
        )


class DerivationEntry:
    """The recorded run of the derivation that bound a group's inputs."""

    _parameters: Dict[str, Detail]
    _summary: Dict[str, Detail]
    _duration: timedelta
    _outcome: Optional[Failure]

    def __init__(
        self,
        parameters: Mapping[str, Detail],
        summary: Mapping[str, Detail],
        duration: timedelta,
        outcome: Optional[Failure],
    ) -> None:
        """Initializes a derivation entry.

        Args:
            parameters (Mapping[str, Detail]): What the derivation was configured
                with.
            summary (Mapping[str, Detail]): What the derivation produced.
            duration (timedelta): How long the derivation took.
            outcome (Optional[Failure]): The failure it ended with, or None if
                it completed.
        """
        self._parameters = _copied_details(parameters)
        self._summary = _copied_details(summary)
        self._duration = duration
        self._outcome = outcome

    @classmethod
    def _from_document(cls, document: _Document) -> DerivationEntry:
        """Reads a derivation entry back from its JSON form.

        Args:
            document (_Document): The JSON object holding the entry.

        Returns:
            DerivationEntry: The entry the document holds.

        Raises:
            ValueError: If the outcome is neither null nor a failure.
        """
        parameters = document._details("parameters")
        summary = document._details("summary")
        duration = document._decoded_duration(
            document.number("duration"), document.path
        )
        outcome = document.optional_document("outcome")

        if outcome is None:
            return cls(parameters, summary, duration, None)

        if outcome.string("kind") == "failure":
            return cls(parameters, summary, duration, Failure._from_document(outcome))

        msg = f"expected a failure at {outcome.path}"
        raise ValueError(msg)

    def _to_document(self) -> _DerivationDocument:
        """Converts the entry to its JSON form.

        Returns:
            _DerivationDocument: The JSON object holding the entry.
        """
        outcome = self._outcome
        return {
            "parameters": _encode_details(self._parameters),
            "summary": _encode_details(self._summary),
            "duration": self._duration.total_seconds(),
            "outcome": None if outcome is None else outcome._to_document(),
        }

    @property
    def parameters(self) -> Dict[str, Detail]:
        """What the derivation was configured with.

        Returns:
            Dict[str, Detail]: The parameters by name.
        """
        return _copied_details(self._parameters)

    @property
    def summary(self) -> Dict[str, Detail]:
        """What the derivation produced.

        Returns:
            Dict[str, Detail]: The summary by name.
        """
        return _copied_details(self._summary)

    @property
    def duration(self) -> timedelta:
        """How long the derivation took.

        Returns:
            timedelta: The duration of the derivation.
        """
        return self._duration

    @property
    def outcome(self) -> Optional[Failure]:
        """How the derivation ended.

        Returns:
            Optional[Failure]: The failure, or None if the derivation completed.
        """
        return self._outcome

    def __eq__(self, other: object) -> bool:
        """Compares the DerivationEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same parameters, summary, duration and
                outcome, otherwise False.
        """
        if not isinstance(other, DerivationEntry):
            return NotImplemented

        return (
            self._parameters == other._parameters
            and self._summary == other._summary
            and self._duration == other._duration
            and self._outcome == other._outcome
        )

    def __repr__(self) -> str:
        """Returns the string representation of the DerivationEntry.

        Returns:
            str: How the derivation ended and how long it took.
        """
        outcome = "completed" if self._outcome is None else "failed"
        return f"DerivationEntry({outcome} in {self._duration})"


class AnalyticEntry:
    """The recorded run of one analytic."""

    _name: str
    _title: str
    _description: Optional[str]
    _parameters: Dict[str, Detail]
    _duration: timedelta
    _result: Union[ReportValue, Failure]

    def __init__(
        self,
        name: str,
        title: str,
        description: Optional[str],
        parameters: Mapping[str, Detail],
        duration: timedelta,
        result: Union[ReportValue, Failure],
    ) -> None:
        """Initializes an analytic entry.

        Args:
            name (str): The name the analytic was placed under.
            title (str): The heading the analytic is typeset with.
            description (Optional[str]): The text under the heading, or None.
            parameters (Mapping[str, Detail]): What the analytic was configured
                with.
            duration (timedelta): How long the analytic took.
            result (Union[ReportValue, Failure]): The value the analytic
                reported, or the failure it ended with.
        """
        self._name = name
        self._title = title
        self._description = description
        self._parameters = _copied_details(parameters)
        self._duration = duration
        self._result = result

    @classmethod
    def _from_document(cls, document: _Document) -> AnalyticEntry:
        """Reads an analytic entry back from its JSON form.

        Args:
            document (_Document): The JSON object holding the entry.

        Returns:
            AnalyticEntry: The entry the document holds.
        """
        return cls(
            document.string("name"),
            document.string("title"),
            document.optional_string("description"),
            document._details("parameters"),
            _Document._decoded_duration(document.number("duration"), document.path),
            _Document._decoded_result(
                document.content("result"), f"{document.path}.result"
            ),
        )

    def _to_document(self) -> _AnalyticDocument:
        """Converts the entry to its JSON form.

        Returns:
            _AnalyticDocument: The JSON object holding the entry.
        """
        return {
            "kind": "analytic",
            "name": self._name,
            "title": self._title,
            "description": self._description,
            "parameters": _encode_details(self._parameters),
            "duration": self._duration.total_seconds(),
            "result": _encode_result(self._result),
        }

    @property
    def name(self) -> str:
        """The name the analytic was placed under.

        Returns:
            str: The name in the group.
        """
        return self._name

    @property
    def title(self) -> str:
        """The heading the analytic is typeset with.

        Returns:
            str: The title of the entry.
        """
        return self._title

    @property
    def description(self) -> Optional[str]:
        """The text typeset under the heading.

        Returns:
            Optional[str]: The description, or None.
        """
        return self._description

    @property
    def parameters(self) -> Dict[str, Detail]:
        """What the analytic was configured with.

        Returns:
            Dict[str, Detail]: The parameters by name.
        """
        return _copied_details(self._parameters)

    @property
    def duration(self) -> timedelta:
        """How long the analytic took.

        Returns:
            timedelta: The duration of the analytic.
        """
        return self._duration

    @property
    def result(self) -> Union[ReportValue, Failure]:
        """What the analytic left behind.

        Returns:
            Union[ReportValue, Failure]: The value it reported, or the failure it
                ended with.
        """
        return self._result

    @overload
    def value(self, kind: Type[bool], /) -> bool: ...

    @overload
    def value(self, kind: Type[int], /) -> int: ...

    @overload
    def value(self, kind: Type[float], /) -> float: ...

    @overload
    def value(self, kind: Type[KindType], /) -> KindType: ...

    def value(self, kind: Type[KindType], /) -> Union[float, KindType]:
        """Reads the result as the given kind.

        An integer result is read as a number, the way ``read`` does. A boolean
        result is neither an integer nor a number.

        Args:
            kind (Type[KindType]): str, int, float, bool, datetime, timedelta,
                Table, Plot, Measurement, Assessment or Distribution.

        Returns:
            Union[float, KindType]: The result, as a number when a number was
                asked for.

        Raises:
            TypeError: If the result is not of that kind, or is a failure.
        """
        result = self._result

        if kind is float and isinstance(result, int) and not isinstance(result, bool):
            return float(result)

        if isinstance(result, kind) and (kind is bool or not isinstance(result, bool)):
            return result

        msg = f"cannot read {self._name!r} as {kind.__name__}: it holds {result!r}"
        raise TypeError(msg)

    def __eq__(self, other: object) -> bool:
        """Compares the AnalyticEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name, title, description,
                parameters, duration and result, otherwise False.
        """
        if not isinstance(other, AnalyticEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._title == other._title
            and self._description == other._description
            and self._parameters == other._parameters
            and self._duration == other._duration
            and self._result == other._result
        )

    def __repr__(self) -> str:
        """Returns the string representation of the AnalyticEntry.

        Returns:
            str: The name and what the analytic left behind.
        """
        return f"AnalyticEntry({self._name!r}, {self._result!r})"


class GroupEntry:
    """The recorded run of a group: its entries in definition order.

    ``inputs`` holds the sizes of the MedRecords the group's analytics ran on.
    ``derivation`` is present when a derivation bound those inputs. A group under
    a key carries its own inputs and no derivation; the group holding the keys
    carries the derivation.
    """

    _name: str
    _title: str
    _description: Optional[str]
    _inputs: List[InputEntry]
    _derivation: Optional[DerivationEntry]
    _entries: List[Entry]

    def __init__(
        self,
        name: str,
        title: str,
        description: Optional[str],
        inputs: Sequence[InputEntry],
        derivation: Optional[DerivationEntry],
        entries: Sequence[Entry],
    ) -> None:
        """Initializes a group entry.

        Args:
            name (str): The name the group was placed under.
            title (str): The heading of the group in a typeset report.
            description (Optional[str]): The text under the heading, if any.
            inputs (Sequence[InputEntry]): The sizes of the MedRecords the group
                ran on.
            derivation (Optional[DerivationEntry]): The recorded derivation that
                bound the inputs, or None.
            entries (Sequence[Entry]): The entries of the group, in definition
                order.
        """
        self._name = name
        self._title = title
        self._description = description
        self._inputs = list(inputs)
        self._derivation = derivation
        self._entries = list(entries)

    @classmethod
    def _from_document(cls, document: _Document) -> GroupEntry:
        """Reads a group entry back from its JSON form.

        Args:
            document (_Document): The JSON object holding the entry.

        Returns:
            GroupEntry: The entry the document holds.
        """
        derivation = document.optional_document("derivation")
        return cls(
            document.string("name"),
            document.string("title"),
            document.optional_string("description"),
            cls._inputs_from_document(document),
            None if derivation is None else DerivationEntry._from_document(derivation),
            cls._entries_from_document(document),
        )

    @staticmethod
    def _inputs_from_document(document: _Document) -> List[InputEntry]:
        """Reads the input entries of a group back from its JSON form.

        Args:
            document (_Document): The JSON object holding the group.

        Returns:
            List[InputEntry]: The input entries, in order.
        """
        return [
            InputEntry._from_document(_Document(item, f"{document.path}.inputs"))
            for item in document.sequence("inputs")
        ]

    @staticmethod
    def _entries_from_document(document: _Document) -> List[Entry]:
        """Reads the entries of a group back from its JSON form.

        Args:
            document (_Document): The JSON object holding the group.

        Returns:
            List[Entry]: The entries, in order.

        Raises:
            ValueError: If an entry is neither an analytic nor a group.
        """
        entries: List[Entry] = []

        for item in document.sequence("entries"):
            entry = _Document(item, f"{document.path}.entries")
            kind = entry.string("kind")

            if kind == "analytic":
                entries.append(AnalyticEntry._from_document(entry))
            elif kind == "group":
                entries.append(GroupEntry._from_document(entry))
            else:
                msg = f"expected an analytic or a group at {entry.path}"
                raise ValueError(msg)

        return entries

    def _to_document(self) -> _GroupDocument:
        """Converts the entry to its JSON form.

        Returns:
            _GroupDocument: The JSON object holding the entry.
        """
        derivation = self._derivation
        return {
            "kind": "group",
            "name": self._name,
            "title": self._title,
            "description": self._description,
            "inputs": [entry._to_document() for entry in self._inputs],
            "derivation": None if derivation is None else derivation._to_document(),
            "entries": [entry._to_document() for entry in self._entries],
        }

    @property
    def name(self) -> str:
        """The name the group was placed under.

        Returns:
            str: The name in the group.
        """
        return self._name

    @property
    def title(self) -> str:
        """The heading of the group in a typeset report.

        Returns:
            str: The title.
        """
        return self._title

    @property
    def description(self) -> Optional[str]:
        """The text under the heading.

        Returns:
            Optional[str]: The description, or None for none.
        """
        return self._description

    @property
    def inputs(self) -> List[InputEntry]:
        """The sizes of the MedRecords the group ran on.

        Returns:
            List[InputEntry]: One entry per MedRecord found in the inputs.
        """
        return list(self._inputs)

    @property
    def derivation(self) -> Optional[DerivationEntry]:
        """The recorded derivation that bound the group's inputs.

        Returns:
            Optional[DerivationEntry]: The derivation entry, or None if the group
                ran on the inputs of its parent.
        """
        return self._derivation

    @property
    def entries(self) -> List[Entry]:
        """The entries of the group.

        Returns:
            List[Entry]: Every entry, in definition order.
        """
        return list(self._entries)

    def group(self, name: str) -> GroupEntry:
        """Views the entry of the group placed under the name.

        Args:
            name (str): The name in the group.

        Returns:
            GroupEntry: The group's entry.

        Raises:
            KeyError: If no group was placed under the name.
        """
        for entry in self._entries:
            if isinstance(entry, GroupEntry) and entry._name == name:
                return entry

        msg = f"cannot find group {name!r}"
        raise KeyError(msg)

    def analytic(self, name: str) -> AnalyticEntry:
        """Views the entry of the analytic placed under the name.

        Args:
            name (str): The name in the group.

        Returns:
            AnalyticEntry: The analytic's entry.

        Raises:
            KeyError: If no analytic was placed under the name.
        """
        for entry in self._entries:
            if isinstance(entry, AnalyticEntry) and entry._name == name:
                return entry

        msg = f"cannot find analytic {name!r}"
        raise KeyError(msg)

    def analytics(self) -> Iterator[Tuple[EntryPath, AnalyticEntry]]:
        """Walks every analytic entry below this group, depth first, in order.

        Yields:
            Tuple[EntryPath, AnalyticEntry]: The path from this group and the
                entry.
        """
        for entry in self._entries:
            if isinstance(entry, AnalyticEntry):
                yield (entry._name,), entry
            else:
                for path, analytic in entry.analytics():
                    yield (entry._name, *path), analytic

    def __eq__(self, other: object) -> bool:
        """Compares the GroupEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name, inputs, derivation and entries,
                otherwise False.
        """
        if not isinstance(other, GroupEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._title == other._title
            and self._description == other._description
            and self._inputs == other._inputs
            and self._derivation == other._derivation
            and self._entries == other._entries
        )

    def __repr__(self) -> str:
        """Returns the string representation of the GroupEntry.

        Returns:
            str: The name and the number of entries the group holds.
        """
        return f"GroupEntry({self._name!r}, entries={len(self._entries)})"


#: A type alias for one entry of a report tree.
Entry: TypeAlias = Union[AnalyticEntry, GroupEntry]


class Report:
    """The report of one run: the entries of its root group, timed."""

    _root: GroupEntry
    _started_at: datetime
    _duration: timedelta

    def __init__(
        self,
        name: str,
        description: Optional[str],
        inputs: Sequence[InputEntry],
        entries: Sequence[Entry],
        started_at: datetime,
        duration: timedelta,
    ) -> None:
        """Initializes a report.

        Args:
            name (str): The name of the evaluation that ran.
            description (Optional[str]): The text under the name, if any.
            inputs (Sequence[InputEntry]): The sizes of the MedRecords the run
                was started with.
            entries (Sequence[Entry]): The entries of the root group, in
                definition order.
            started_at (datetime): When the run started.
            duration (timedelta): How long the run took.
        """
        self._root = GroupEntry(name, name, description, inputs, None, entries)
        self._started_at = started_at
        self._duration = duration

    @classmethod
    def from_json(cls, path: Union[str, os.PathLike[str]]) -> Report:
        """Reads a report from a JSON file written by to_json.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the file to read.

        Returns:
            Report: The report the file holds.
        """
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls._from_document(_Document(content, "report"))

    @classmethod
    def _from_document(cls, document: _Document) -> Report:
        """Reads a report back from its JSON form.

        Args:
            document (_Document): The JSON object holding the report.

        Returns:
            Report: The report the document holds.
        """
        return cls(
            document.string("name"),
            document.optional_string("description"),
            GroupEntry._inputs_from_document(document),
            GroupEntry._entries_from_document(document),
            _Document._decoded_moment(document.string("started_at"), "report"),
            _Document._decoded_duration(document.number("duration"), "report"),
        )

    def to_json(self, path: Union[str, os.PathLike[str]]) -> None:
        """Writes the report to a JSON file.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the file to write.
        """
        Path(path).write_text(self._to_json(), encoding="utf-8")

    def _to_json(self) -> str:
        """Converts the report to JSON text.

        Returns:
            str: The JSON document holding the report.
        """
        return json.dumps(self._to_document(), indent=2, allow_nan=False)

    def _to_document(self) -> _ReportDocument:
        """Converts the report to its JSON form.

        Returns:
            _ReportDocument: The JSON object holding the report.
        """
        return {
            "name": self.name,
            "description": self.description,
            "started_at": self._started_at.isoformat(),
            "duration": self._duration.total_seconds(),
            "inputs": [entry._to_document() for entry in self.inputs],
            "entries": [entry._to_document() for entry in self.entries],
        }

    @property
    def name(self) -> str:
        """The name of the evaluation that ran.

        Returns:
            str: The name of the report.
        """
        return self._root.name

    @property
    def description(self) -> Optional[str]:
        """The text under the name of the report.

        Returns:
            Optional[str]: The description, or None for none.
        """
        return self._root.description

    @property
    def inputs(self) -> List[InputEntry]:
        """The sizes of the MedRecords the run was started with.

        Returns:
            List[InputEntry]: One entry per MedRecord found in the inputs.
        """
        return self._root.inputs

    @property
    def entries(self) -> List[Entry]:
        """The entries of the root group.

        Returns:
            List[Entry]: The entries, in definition order.
        """
        return self._root.entries

    @property
    def started_at(self) -> datetime:
        """When the run started.

        Returns:
            datetime: The start of the run, in UTC when a run recorded it.
        """
        return self._started_at

    @property
    def duration(self) -> timedelta:
        """How long the run took.

        Returns:
            timedelta: From the start of the run to the end of its last entry.
        """
        return self._duration

    def group(self, name: str) -> GroupEntry:
        """Reads a group of the root group by name.

        Args:
            name (str): The name the group was added under.

        Returns:
            GroupEntry: The entry of the group.
        """
        return self._root.group(name)

    def analytic(self, name: str) -> AnalyticEntry:
        """Reads an analytic of the root group by name.

        Args:
            name (str): The name the analytic was added under.

        Returns:
            AnalyticEntry: The entry of the analytic.
        """
        return self._root.analytic(name)

    def analytics(self) -> Iterator[Tuple[EntryPath, AnalyticEntry]]:
        """Walks every analytic of the report, depth first.

        Returns:
            Iterator[Tuple[EntryPath, AnalyticEntry]]: The path from the root to
                every analytic, and its entry, in definition order.
        """
        return self._root.analytics()

    def __eq__(self, other: object) -> bool:
        """Compares the Report with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same entries, inputs, start and duration,
                otherwise False.
        """
        if not isinstance(other, Report):
            return NotImplemented

        return (
            self._root == other._root
            and self._started_at == other._started_at
            and self._duration == other._duration
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Report.

        Returns:
            str: The name and the number of entries the report holds.
        """
        return f"Report({self.name!r}, entries={len(self.entries)})"
