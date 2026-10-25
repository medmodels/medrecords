"""Entries: the records of what a run found."""

from __future__ import annotations

from enum import Enum
from traceback import format_exception
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Final,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeAlias,
    Union,
)

from medrecords.evaluation._json import (
    AnalyticDocument,
    DerivationDocument,
    FailureDocument,
    GroupDocument,
    InputDocument,
    Json,
    JsonObject,
    KeyedAnalyticDocument,
    KeyedGroupDocument,
    KeyedResultDocument,
    ResultDocument,
    copy_details,
    encode_arrangement,
    encode_cell,
    encode_details,
    encode_distribution,
    encode_float,
    encode_unit,
    encode_value,
)
from medrecords.evaluation.analytic import (
    Assessment,
    Counts,
    Distribution,
    Histogram,
    Measurement,
    Plot,
    Scatter,
    Table,
)
from medrecords.medrecord import MedRecord

if TYPE_CHECKING:
    from datetime import timedelta

    from graphrecords import Value

    from medrecords.evaluation.analytic import Detail, EntryPath, ReportValue

#: The name a bare MedRecord is recorded under in the inputs of a report.
_BARE_INPUT_NAME: Final[str] = "medrecord"


class Layout(Enum):
    """Enumeration of how a typeset report sets a group.

    A section has a heading of its own, numbered on the outer three levels and
    listed in the contents. An inline group has none: its entries join the
    group it sits in. An appendix group is set after the body, under a heading
    that reads its path, and a line where it stands names it with its page.
    """

    Section = "section"
    Inline = "inline"
    Appendix = "appendix"


#: How each kind of report value is read back from its JSON form.
_DECODERS: Final[Dict[str, Callable[[JsonObject], ReportValue]]] = {
    "table": JsonObject._table,
    "plot": JsonObject._plot,
    "measurement": JsonObject._measurement,
    "assessment": JsonObject._assessment,
    "distribution": JsonObject._distribution,
    "histogram": JsonObject._histogram,
    "counts": JsonObject._counts,
    "scatter": JsonObject._scatter,
}


def _decoded_result(content: Json, path: str) -> Union[ReportValue, Failure]:
    if not isinstance(content, dict):
        return JsonObject._decoded_value(content, path)

    document = JsonObject(content, path)
    kind = document.string("kind")

    if kind == "failure":
        return Failure._from_document(document)

    decoder = _DECODERS.get(kind)

    if decoder is None:
        return JsonObject._decoded_value(content, path)

    return decoder(document)


def _encode_result(result: Union[ReportValue, Failure]) -> ResultDocument:
    if isinstance(result, Table):
        return {
            "kind": "table",
            "headings": result.headings,
            "rows": [[encode_cell(cell) for cell in row] for row in result.rows],
            "units": [
                encode_unit(result.units.get(heading)) for heading in result.headings
            ],
        }

    if isinstance(result, Plot):
        return {"kind": "plot", "svg": result.svg}

    if isinstance(result, Measurement):
        return {
            "kind": "measurement",
            "value": encode_float(result.value),
            "lower": None if result.lower is None else encode_float(result.lower),
            "upper": None if result.upper is None else encode_float(result.upper),
            "p_value": None if result.p_value is None else encode_float(result.p_value),
            "unit": encode_unit(result.unit),
        }

    if isinstance(result, Assessment):
        return {
            "kind": "assessment",
            "value": encode_value(result.value),
            "requirement_label": result.requirement_label,
            "passed": result.passed,
            "unit": encode_unit(result.unit),
        }

    if isinstance(result, Distribution):
        return encode_distribution(result, result.histogram())

    if isinstance(result, Histogram):
        return {
            "kind": "histogram",
            "edges": result.edges,
            "counts": result.counts,
            "below_count": result.below_count,
            "above_count": result.above_count,
            "statistics": result.statistics,
            "scale": result.scale.value,
            "value_label": result.value_label,
            "count_label": result.count_label,
            "arrangement": encode_arrangement(result.arrangement),
        }

    if isinstance(result, Counts):
        return {
            "kind": "counts",
            "counts": [
                {"value": encode_value(value), "count": count}
                for value, count in result.by_value.items()
            ],
            "total": result.total,
            "value_label": result.value_label,
            "count_label": result.count_label,
            "remainder_label": result.remainder_label,
            "arrangement": encode_arrangement(result.arrangement),
        }

    if isinstance(result, Scatter):
        return {
            "kind": "scatter",
            "points": [[x, y] for x, y in result.points],
            "x_label": result.x_label,
            "y_label": result.y_label,
            "x_scale": result.x_scale.value,
            "y_scale": result.y_scale.value,
            "labels": [
                {"index": index, "label": label}
                for index, label in result.labels.items()
            ],
            "diagonal": result.diagonal,
        }

    if isinstance(result, Failure):
        return result._to_document()

    return encode_value(result)


def _encode_keyed_result(
    key: Value, duration: timedelta, result: ResultDocument
) -> KeyedResultDocument:
    return {
        "key": encode_value(key),
        "duration": duration.total_seconds(),
        "result": result,
    }


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
        exception_type = type(error)

        return cls(
            f"{exception_type.__module__}.{exception_type.__qualname__}",
            str(error),
            "".join(format_exception(exception_type, error, error.__traceback__)),
        )

    @classmethod
    def _from_document(cls, document: JsonObject) -> Failure:
        return cls(
            document.string("exception_type"),
            document.string("message"),
            document.string("traceback"),
        )

    def _to_document(self) -> FailureDocument:
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
    """The name and size of one MedRecord found in the inputs of a group."""

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
        return f"{name}.{key}" if name else key

    @classmethod
    def _from_document(cls, document: JsonObject) -> InputEntry:
        return cls(
            document.string("name"),
            document.integer("node_count"),
            document.integer("edge_count"),
        )

    def _to_document(self) -> InputDocument:
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
    _failure: Optional[Failure]

    def __init__(
        self,
        parameters: Mapping[str, Detail],
        summary: Mapping[str, Detail],
        duration: timedelta,
        failure: Optional[Failure],
    ) -> None:
        """Initializes a derivation entry.

        Args:
            parameters (Mapping[str, Detail]): What the derivation was configured
                with.
            summary (Mapping[str, Detail]): What the derivation produced.
            duration (timedelta): How long the derivation took.
            failure (Optional[Failure]): The failure it ended with, or None if
                it completed.
        """
        self._parameters = copy_details(parameters)
        self._summary = copy_details(summary)
        self._duration = duration
        self._failure = failure

    @classmethod
    def _from_document(cls, document: JsonObject) -> DerivationEntry:
        parameters = document._details("parameters")
        summary = document._details("summary")
        duration = JsonObject._decoded_duration(
            document.number("duration"), f"{document.path}.duration"
        )
        failure = document.optional_document("failure")

        if failure is None:
            return cls(parameters, summary, duration, None)

        if failure.string("kind") == "failure":
            return cls(parameters, summary, duration, Failure._from_document(failure))

        msg = f"expected a failure at {failure.path}"
        raise ValueError(msg)

    def _to_document(self) -> DerivationDocument:
        failure = self._failure
        return {
            "parameters": encode_details(self._parameters),
            "summary": encode_details(self._summary),
            "duration": self._duration.total_seconds(),
            "failure": None if failure is None else failure._to_document(),
        }

    @property
    def parameters(self) -> Dict[str, Detail]:
        """What the derivation was configured with.

        Returns:
            Dict[str, Detail]: The parameters by name.
        """
        return copy_details(self._parameters)

    @property
    def summary(self) -> Dict[str, Detail]:
        """What the derivation produced.

        Returns:
            Dict[str, Detail]: The summary by name.
        """
        return copy_details(self._summary)

    @property
    def duration(self) -> timedelta:
        """How long the derivation took.

        Returns:
            timedelta: The duration of the derivation.
        """
        return self._duration

    @property
    def failure(self) -> Optional[Failure]:
        """How the derivation ended.

        Returns:
            Optional[Failure]: The failure, or None if the derivation completed.
        """
        return self._failure

    def __eq__(self, other: object) -> bool:
        """Compares the DerivationEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same parameters, summary, duration and
                failure, otherwise False.
        """
        if not isinstance(other, DerivationEntry):
            return NotImplemented

        return (
            self._parameters == other._parameters
            and self._summary == other._summary
            and self._duration == other._duration
            and self._failure == other._failure
        )

    def __repr__(self) -> str:
        """Returns the string representation of the DerivationEntry.

        Returns:
            str: How the derivation ended and how long it took.
        """
        ending = "completed" if self._failure is None else "failed"
        return f"DerivationEntry({ending} in {self._duration})"


class AnalyticEntry:
    """The recorded run of one analytic."""

    _name: Value
    _title: str
    _description: Optional[str]
    _parameters: Dict[str, Detail]
    _duration: timedelta
    _result: Union[ReportValue, Failure]

    def __init__(
        self,
        name: Value,
        title: str,
        description: Optional[str],
        parameters: Mapping[str, Detail],
        duration: timedelta,
        result: Union[ReportValue, Failure],
    ) -> None:
        """Initializes an analytic entry.

        Args:
            name (Value): The name the analytic was placed under.
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
        self._parameters = copy_details(parameters)
        self._duration = duration
        self._result = result

    @classmethod
    def _from_document(cls, document: JsonObject) -> AnalyticEntry:
        return cls(
            JsonObject._decoded_value(
                document.content("name"), f"{document.path}.name"
            ),
            document.string("title"),
            document.optional_string("description"),
            document._details("parameters"),
            JsonObject._decoded_duration(
                document.number("duration"), f"{document.path}.duration"
            ),
            _decoded_result(document.content("result"), f"{document.path}.result"),
        )

    def _to_document(self) -> AnalyticDocument:
        return {
            "kind": "analytic",
            "name": encode_value(self._name),
            "title": self._title,
            "description": self._description,
            "parameters": encode_details(self._parameters),
            "duration": self._duration.total_seconds(),
            "result": _encode_result(self._result),
        }

    @property
    def name(self) -> Value:
        """The name the analytic was placed under.

        Returns:
            Value: The name in the group.
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
        return copy_details(self._parameters)

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
    """The recorded run of a group: its entries in definition order."""

    _name: Value
    _title: str
    _description: Optional[str]
    _inputs: List[InputEntry]
    _derivation: Optional[DerivationEntry]
    _entries: List[Entry]
    _layout: Layout

    def __init__(
        self,
        name: Value,
        title: str,
        description: Optional[str],
        inputs: Sequence[InputEntry],
        derivation: Optional[DerivationEntry],
        entries: Sequence[Entry],
        *,
        layout: Layout = Layout.Section,
    ) -> None:
        """Initializes a group entry.

        Args:
            name (Value): The name the group was placed under.
            title (str): The heading of the group in a typeset report.
            description (Optional[str]): The text under the heading, if any.
            inputs (Sequence[InputEntry]): The sizes of the MedRecords the group
                ran on.
            derivation (Optional[DerivationEntry]): The recorded derivation that
                bound the inputs, or None.
            entries (Sequence[Entry]): The entries of the group, in definition
                order.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.
        """
        self._name = name
        self._title = title
        self._description = description
        self._inputs = list(inputs)
        self._derivation = derivation
        self._entries = list(entries)
        self._layout = layout

    @classmethod
    def _from_document(cls, document: JsonObject) -> GroupEntry:
        derivation = document.optional_document("derivation")
        return cls(
            JsonObject._decoded_value(
                document.content("name"), f"{document.path}.name"
            ),
            document.string("title"),
            document.optional_string("description"),
            cls._inputs_from_document(document),
            None if derivation is None else DerivationEntry._from_document(derivation),
            cls._entries_from_document(document),
            layout=document.member("layout", Layout),
        )

    @staticmethod
    def _inputs_from_document(document: JsonObject) -> List[InputEntry]:
        return [
            InputEntry._from_document(
                JsonObject(item, f"{document.path}.inputs[{index}]")
            )
            for index, item in enumerate(document.sequence("inputs"))
        ]

    @staticmethod
    def _entries_from_document(document: JsonObject) -> List[Entry]:
        entries: List[Entry] = []

        for index, item in enumerate(document.sequence("entries")):
            entry = JsonObject(item, f"{document.path}.entries[{index}]")
            kind = entry.string("kind")

            if kind == "analytic":
                entries.append(AnalyticEntry._from_document(entry))
            elif kind == "group":
                entries.append(GroupEntry._from_document(entry))
            elif kind == "keyed_analytic":
                entries.append(KeyedAnalyticEntry._from_document(entry))
            elif kind == "keyed_group":
                entries.append(KeyedGroupEntry._from_document(entry))
            else:
                msg = f"expected an entry at {entry.path}"
                raise ValueError(msg)

        return entries

    def _with_entries(self, entries: Sequence[Entry]) -> GroupEntry:
        return GroupEntry(
            self._name,
            self._title,
            self._description,
            self._inputs,
            self._derivation,
            entries,
            layout=self._layout,
        )

    def _to_document(self) -> GroupDocument:
        derivation = self._derivation
        return {
            "kind": "group",
            "name": encode_value(self._name),
            "title": self._title,
            "description": self._description,
            "layout": self._layout.value,
            "inputs": [entry._to_document() for entry in self._inputs],
            "derivation": None if derivation is None else derivation._to_document(),
            "entries": [entry._to_document() for entry in self._entries],
        }

    @property
    def name(self) -> Value:
        """The name the group was placed under.

        Returns:
            Value: The name in the group.
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
    def layout(self) -> Layout:
        """How a typeset report sets the group.

        Returns:
            Layout: The layout.
        """
        return self._layout

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

    def group(self, name: Value) -> GroupEntry:
        """Views the entry of the group placed under the name.

        Args:
            name (Value): The name in the group.

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

    def analytic(self, name: Value) -> AnalyticEntry:
        """Views the entry of the analytic placed under the name.

        Args:
            name (Value): The name in the group.

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
        """Walks every analytic computed once below this group, depth first.

        Analytics computed across keys are reached through keyed_analytics.

        Yields:
            Tuple[EntryPath, AnalyticEntry]: The path from this group and the
                entry.
        """
        for entry in self._entries:
            if isinstance(entry, AnalyticEntry):
                yield (entry._name,), entry
            elif isinstance(entry, GroupEntry):
                for path, analytic in entry.analytics():
                    yield (entry._name, *path), analytic

    def keyed_group(self, name: Value) -> KeyedGroupEntry:
        """Views the entry of the group placed across keyed inputs under the name.

        Args:
            name (Value): The name in the group.

        Returns:
            KeyedGroupEntry: The group's entry.

        Raises:
            KeyError: If no group placed across keyed inputs has the name.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedGroupEntry) and entry._name == name:
                return entry

        msg = f"cannot find keyed group {name!r}"
        raise KeyError(msg)

    def keyed_analytic(self, name: Value) -> KeyedAnalyticEntry:
        """Views the entry of the analytic run across keyed inputs under the name.

        Args:
            name (Value): The name in the group.

        Returns:
            KeyedAnalyticEntry: The analytic's entry.

        Raises:
            KeyError: If no analytic run across keyed inputs has the name.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedAnalyticEntry) and entry._name == name:
                return entry

        msg = f"cannot find keyed analytic {name!r}"
        raise KeyError(msg)

    def keyed_analytics(self) -> Iterator[Tuple[EntryPath, KeyedAnalyticEntry]]:
        """Walks every analytic run across keyed inputs below this group, in order.

        Yields:
            Tuple[EntryPath, KeyedAnalyticEntry]: The path from this group and
                the entry.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedAnalyticEntry):
                yield (entry._name,), entry
            elif isinstance(entry, (GroupEntry, KeyedGroupEntry)):
                for path, keyed in entry.keyed_analytics():
                    yield (entry._name, *path), keyed

    def __eq__(self, other: object) -> bool:
        """Compares the GroupEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name, title, description, layout,
                inputs, derivation and entries, otherwise False.
        """
        if not isinstance(other, GroupEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._title == other._title
            and self._description == other._description
            and self._layout == other._layout
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


class KeyedResult:
    """What one analytic reported under one key of a group run across keys."""

    _key: Value
    _duration: timedelta
    _result: Union[ReportValue, Failure]

    def __init__(
        self, key: Value, duration: timedelta, result: Union[ReportValue, Failure]
    ) -> None:
        """Initializes a keyed result.

        Args:
            key (Value): The key the inputs were derived under.
            duration (timedelta): How long the analytic took under the key.
            result (Union[ReportValue, Failure]): The value the analytic
                reported, or the failure it ended with.
        """
        self._key = key
        self._duration = duration
        self._result = result

    @classmethod
    def _from_document(cls, document: JsonObject) -> KeyedResult:
        return cls(
            JsonObject._decoded_value(document.content("key"), f"{document.path}.key"),
            JsonObject._decoded_duration(
                document.number("duration"), f"{document.path}.duration"
            ),
            _decoded_result(document.content("result"), f"{document.path}.result"),
        )

    def _to_document(self) -> KeyedResultDocument:
        return _encode_keyed_result(
            self._key, self._duration, _encode_result(self._result)
        )

    @property
    def key(self) -> Value:
        """The key the inputs were derived under.

        Returns:
            Value: The key.
        """
        return self._key

    @property
    def duration(self) -> timedelta:
        """How long the analytic took under the key.

        Returns:
            timedelta: The duration of the run.
        """
        return self._duration

    @property
    def result(self) -> Union[ReportValue, Failure]:
        """What the analytic left behind under the key.

        Returns:
            Union[ReportValue, Failure]: The value it reported, or the failure it
                ended with.
        """
        return self._result

    def __eq__(self, other: object) -> bool:
        """Compares the KeyedResult with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same key, duration and result, otherwise
                False.
        """
        if not isinstance(other, KeyedResult):
            return NotImplemented

        return (
            self._key == other._key
            and self._duration == other._duration
            and self._result == other._result
        )

    def __repr__(self) -> str:
        """Returns the string representation of the KeyedResult.

        Returns:
            str: The key and what the analytic left behind.
        """
        return f"KeyedResult({self._key!r}, {self._result!r})"


class KeyedAnalyticEntry:
    """The recorded run of one analytic across keyed inputs: one result per key."""

    _name: Value
    _title: str
    _description: Optional[str]
    _parameters: Dict[str, Detail]
    _results: List[KeyedResult]

    def __init__(
        self,
        name: Value,
        title: str,
        description: Optional[str],
        parameters: Mapping[str, Detail],
        results: Sequence[KeyedResult],
    ) -> None:
        """Initializes an entry of an analytic run across keyed inputs.

        Args:
            name (Value): The name the analytic was placed under.
            title (str): The heading the analytic is typeset with.
            description (Optional[str]): The text under the heading, or None.
            parameters (Mapping[str, Detail]): What the analytic was configured
                with.
            results (Sequence[KeyedResult]): What the analytic reported under
                every key, in key order.
        """
        self._name = name
        self._title = title
        self._description = description
        self._parameters = copy_details(parameters)
        self._results = list(results)

    @classmethod
    def _from_document(cls, document: JsonObject) -> KeyedAnalyticEntry:
        return cls(
            JsonObject._decoded_value(
                document.content("name"), f"{document.path}.name"
            ),
            document.string("title"),
            document.optional_string("description"),
            document._details("parameters"),
            [
                KeyedResult._from_document(
                    JsonObject(item, f"{document.path}.results[{index}]")
                )
                for index, item in enumerate(document.sequence("results"))
            ],
        )

    def _to_document(self) -> KeyedAnalyticDocument:
        """Converts the entry to its JSON form.

        The histograms of the distributions among the results are written over
        shared bin edges, so that a typeset report draws them on one axis,
        unless the distributions declare different scales or outside shares.

        Returns:
            KeyedAnalyticDocument: The JSON object holding the entry.
        """
        distributions = {
            index: keyed._result
            for index, keyed in enumerate(self._results)
            if isinstance(keyed._result, Distribution)
        }
        histograms = (
            dict(
                zip(
                    distributions,
                    Distribution.shared_histograms(list(distributions.values())),
                    strict=True,
                )
            )
            if distributions and Distribution._agreeing(list(distributions.values()))
            else {}
        )
        results = [
            _encode_keyed_result(
                keyed._key,
                keyed._duration,
                encode_distribution(distributions[index], histograms[index]),
            )
            if index in histograms
            else keyed._to_document()
            for index, keyed in enumerate(self._results)
        ]

        return {
            "kind": "keyed_analytic",
            "name": encode_value(self._name),
            "title": self._title,
            "description": self._description,
            "parameters": encode_details(self._parameters),
            "results": results,
        }

    @property
    def name(self) -> Value:
        """The name the analytic was placed under.

        Returns:
            Value: The name in the group.
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
        return copy_details(self._parameters)

    @property
    def results(self) -> List[KeyedResult]:
        """What the analytic reported under every key.

        Returns:
            List[KeyedResult]: One result per key, in key order.
        """
        return list(self._results)

    @property
    def keys(self) -> List[Value]:
        """The keys the analytic ran under.

        Returns:
            List[Value]: The keys, in key order.
        """
        return [keyed._key for keyed in self._results]

    def result(self, key: Value) -> Union[ReportValue, Failure]:
        """Views what the analytic reported under one key.

        Args:
            key (Value): The key the inputs were derived under.

        Returns:
            Union[ReportValue, Failure]: The value it reported under the key, or
                the failure it ended with.

        Raises:
            KeyError: If the analytic did not run under the key.
        """
        for keyed in self._results:
            if keyed._key == key:
                return keyed._result

        msg = f"cannot find key {key!r}"
        raise KeyError(msg)

    def __eq__(self, other: object) -> bool:
        """Compares the KeyedAnalyticEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name, title, description,
                parameters and results, otherwise False.
        """
        if not isinstance(other, KeyedAnalyticEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._title == other._title
            and self._description == other._description
            and self._parameters == other._parameters
            and self._results == other._results
        )

    def __repr__(self) -> str:
        """Returns the string representation of the KeyedAnalyticEntry.

        Returns:
            str: The name and the keys the analytic ran under.
        """
        return f"KeyedAnalyticEntry({self._name!r}, keys={self.keys!r})"


class KeyedGroupEntry:
    """The recorded run of a group across keyed inputs: its entries in definition order.

    A group placed over a derivation holds one derivation entry per key; a group
    placed over the same inputs holds none.
    """

    _name: Value
    _title: str
    _description: Optional[str]
    _inputs: List[InputEntry]
    _derivations: Dict[Value, DerivationEntry]
    _entries: List[KeyedEntry]
    _layout: Layout

    def __init__(
        self,
        name: Value,
        title: str,
        description: Optional[str],
        inputs: Sequence[InputEntry],
        derivations: Mapping[Value, DerivationEntry],
        entries: Sequence[KeyedEntry],
        *,
        layout: Layout = Layout.Section,
    ) -> None:
        """Initializes an entry of a group run across keyed inputs.

        Args:
            name (Value): The name the group was placed under.
            title (str): The heading of the group in a typeset report.
            description (Optional[str]): The text under the heading, if any.
            inputs (Sequence[InputEntry]): The sizes of the MedRecords the group
                ran on, under every key.
            derivations (Mapping[Value, DerivationEntry]): The recorded
                derivation that bound the group's inputs, by key.
            entries (Sequence[KeyedEntry]): The entries of the group, in
                definition order.
            layout (Layout): How a typeset report sets the group. Defaults to
                Layout.Section.
        """
        self._name = name
        self._title = title
        self._description = description
        self._inputs = list(inputs)
        self._derivations = dict(derivations)
        self._entries = list(entries)
        self._layout = layout

    @classmethod
    def _from_document(cls, document: JsonObject) -> KeyedGroupEntry:
        return cls(
            JsonObject._decoded_value(
                document.content("name"), f"{document.path}.name"
            ),
            document.string("title"),
            document.optional_string("description"),
            GroupEntry._inputs_from_document(document),
            cls._derivations_from_document(document),
            cls._entries_from_document(document),
            layout=document.member("layout", Layout),
        )

    @staticmethod
    def _derivations_from_document(
        document: JsonObject,
    ) -> Dict[Value, DerivationEntry]:
        derivations: Dict[Value, DerivationEntry] = {}

        for index, item in enumerate(document.sequence("derivations")):
            keyed = JsonObject(item, f"{document.path}.derivations[{index}]")
            key = JsonObject._decoded_value(keyed.content("key"), f"{keyed.path}.key")
            derivations[key] = DerivationEntry._from_document(
                keyed.document("derivation")
            )

        return derivations

    @staticmethod
    def _entries_from_document(document: JsonObject) -> List[KeyedEntry]:
        entries: List[KeyedEntry] = []

        for index, item in enumerate(document.sequence("entries")):
            entry = JsonObject(item, f"{document.path}.entries[{index}]")
            kind = entry.string("kind")

            if kind == "keyed_analytic":
                entries.append(KeyedAnalyticEntry._from_document(entry))
            elif kind == "keyed_group":
                entries.append(KeyedGroupEntry._from_document(entry))
            else:
                msg = f"expected a keyed analytic or a keyed group at {entry.path}"
                raise ValueError(msg)

        return entries

    def _to_document(self) -> KeyedGroupDocument:
        return {
            "kind": "keyed_group",
            "name": encode_value(self._name),
            "title": self._title,
            "description": self._description,
            "layout": self._layout.value,
            "inputs": [entry._to_document() for entry in self._inputs],
            "derivations": [
                {"key": encode_value(key), "derivation": derivation._to_document()}
                for key, derivation in self._derivations.items()
            ],
            "entries": [entry._to_document() for entry in self._entries],
        }

    @property
    def name(self) -> Value:
        """The name the group was placed under.

        Returns:
            Value: The name in the group.
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
    def layout(self) -> Layout:
        """How a typeset report sets the group.

        Returns:
            Layout: The layout.
        """
        return self._layout

    @property
    def inputs(self) -> List[InputEntry]:
        """The sizes of the MedRecords the group ran on, under every key.

        Returns:
            List[InputEntry]: One entry per MedRecord found in the inputs.
        """
        return list(self._inputs)

    @property
    def derivations(self) -> Dict[Value, DerivationEntry]:
        """The recorded derivation that bound the group's inputs, by key.

        Returns:
            Dict[Value, DerivationEntry]: The derivation entries by key, or an
                empty mapping if the group ran on the inputs of its parent.
        """
        return dict(self._derivations)

    @property
    def entries(self) -> List[KeyedEntry]:
        """The entries of the group.

        Returns:
            List[KeyedEntry]: Every entry, in definition order.
        """
        return list(self._entries)

    def keyed_group(self, name: Value) -> KeyedGroupEntry:
        """Views the entry of the group placed under the name.

        Args:
            name (Value): The name in the group.

        Returns:
            KeyedGroupEntry: The group's entry.

        Raises:
            KeyError: If no group was placed under the name.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedGroupEntry) and entry._name == name:
                return entry

        msg = f"cannot find keyed group {name!r}"
        raise KeyError(msg)

    def keyed_analytic(self, name: Value) -> KeyedAnalyticEntry:
        """Views the entry of the analytic placed under the name.

        Args:
            name (Value): The name in the group.

        Returns:
            KeyedAnalyticEntry: The analytic's entry.

        Raises:
            KeyError: If no analytic was placed under the name.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedAnalyticEntry) and entry._name == name:
                return entry

        msg = f"cannot find keyed analytic {name!r}"
        raise KeyError(msg)

    def keyed_analytics(self) -> Iterator[Tuple[EntryPath, KeyedAnalyticEntry]]:
        """Walks every keyed analytic entry below this group, depth first.

        Yields:
            Tuple[EntryPath, KeyedAnalyticEntry]: The path from this group and
                the entry.
        """
        for entry in self._entries:
            if isinstance(entry, KeyedAnalyticEntry):
                yield (entry._name,), entry
            else:
                for path, keyed in entry.keyed_analytics():
                    yield (entry._name, *path), keyed

    def __eq__(self, other: object) -> bool:
        """Compares the KeyedGroupEntry with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same name, title, description, layout,
                inputs, derivations and entries, otherwise False.
        """
        if not isinstance(other, KeyedGroupEntry):
            return NotImplemented

        return (
            self._name == other._name
            and self._title == other._title
            and self._description == other._description
            and self._layout == other._layout
            and self._inputs == other._inputs
            and self._derivations == other._derivations
            and self._entries == other._entries
        )

    def __repr__(self) -> str:
        """Returns the string representation of the KeyedGroupEntry.

        Returns:
            str: The name and the number of entries the group holds.
        """
        return f"KeyedGroupEntry({self._name!r}, entries={len(self._entries)})"


#: A type alias for one entry of a group run across keyed inputs.
KeyedEntry: TypeAlias = Union[KeyedAnalyticEntry, KeyedGroupEntry]

#: A type alias for one entry of a report tree.
Entry: TypeAlias = Union[AnalyticEntry, GroupEntry, KeyedAnalyticEntry, KeyedGroupEntry]
