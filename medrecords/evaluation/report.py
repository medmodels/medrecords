"""The report of a run: what it found, read by name or through placements."""

from __future__ import annotations

import json
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from medrecords.evaluation._json import (
    JsonObject,
    ReportDocument,
    copy_details,
    encode_details,
)
from medrecords.evaluation.entry import (
    AnalyticEntry,
    Entry,
    GroupEntry,
    InputEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
)
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.placement import _UNKEYED

if TYPE_CHECKING:
    import os
    from datetime import datetime, timedelta

    from graphrecords import Value

    from medrecords.evaluation.analytic import Detail, EntryPath
    from medrecords.evaluation.placement import AtRoot


class Report:
    """The report of one run: the entries of its root group, timed."""

    _name: str
    _parameters: Dict[str, Detail]
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
        *,
        parameters: Optional[Mapping[str, Detail]] = None,
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
            parameters (Optional[Mapping[str, Detail]]): What the evaluation was
                configured with. Defaults to None.
        """
        self._name = name
        self._parameters = {} if parameters is None else copy_details(parameters)
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
        return cls._from_document(JsonObject(content, "report"))

    @classmethod
    def _from_document(cls, document: JsonObject) -> Report:
        return cls(
            document.string("name"),
            document.optional_string("description"),
            GroupEntry._inputs_from_document(document),
            GroupEntry._entries_from_document(document),
            JsonObject._decoded_datetime(
                document.string("started_at"), "report.started_at"
            ),
            JsonObject._decoded_duration(
                document.number("duration"), "report.duration"
            ),
            parameters=document._details("parameters"),
        )

    def to_json(self, path: Union[str, os.PathLike[str]]) -> None:
        """Writes the report to a JSON file.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the file to write.
        """
        Path(path).write_text(self._to_json(), encoding="utf-8")

    def _to_json(self) -> str:
        return json.dumps(self._to_document(), indent=2, allow_nan=False)

    def _to_document(self) -> ReportDocument:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": encode_details(self._parameters),
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
        return self._name

    @property
    def description(self) -> Optional[str]:
        """The text under the name of the report.

        Returns:
            Optional[str]: The description, or None for none.
        """
        return self._root.description

    @property
    def parameters(self) -> Dict[str, Detail]:
        """What the evaluation was configured with.

        Returns:
            Dict[str, Detail]: The parameters by name.
        """
        return copy_details(self._parameters)

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

    def group(self, name: Value) -> GroupEntry:
        """Reads a group of the root group by name.

        Args:
            name (Value): The name the group was added under.

        Returns:
            GroupEntry: The entry of the group.
        """
        return self._root.group(name)

    def analytic(self, name: Value) -> AnalyticEntry:
        """Reads an analytic of the root group by name.

        Args:
            name (Value): The name the analytic was added under.

        Returns:
            AnalyticEntry: The entry of the analytic.
        """
        return self._root.analytic(name)

    def analytics(self) -> Iterator[Tuple[EntryPath, AnalyticEntry]]:
        """Walks every analytic of the report computed once, depth first.

        Analytics computed across keys are reached through keyed_analytics.

        Returns:
            Iterator[Tuple[EntryPath, AnalyticEntry]]: The path from the root to
                every analytic, and its entry, in definition order.
        """
        return self._root.analytics()

    def keyed_group(self, name: Value) -> KeyedGroupEntry:
        """Reads a group run across keyed inputs of the root group by name.

        Args:
            name (Value): The name the group was added under.

        Returns:
            KeyedGroupEntry: The entry of the group.
        """
        return self._root.keyed_group(name)

    def keyed_analytic(self, name: Value) -> KeyedAnalyticEntry:
        """Reads an analytic run across keyed inputs of the root group by name.

        Args:
            name (Value): The name the analytic was added under.

        Returns:
            KeyedAnalyticEntry: The entry of the analytic.
        """
        return self._root.keyed_analytic(name)

    def keyed_analytics(self) -> Iterator[Tuple[EntryPath, KeyedAnalyticEntry]]:
        """Walks every analytic run across keyed inputs of the report, depth first.

        Returns:
            Iterator[Tuple[EntryPath, KeyedAnalyticEntry]]: The path from the
                root to every such analytic, and its entry, in definition order.
        """
        return self._root.keyed_analytics()

    @property
    def findings(self) -> Findings[AtRoot]:
        """The findings of the report, read through the evaluation's placements.

        A report answers to placements by their names, since it does not hold
        the evaluation that made them; a placement from another evaluation with
        the same names reads the same entry.

        Returns:
            Findings[AtRoot]: The findings of the root group.
        """
        return Findings(self._root.entries, None, _UNKEYED, ())

    def __eq__(self, other: object) -> bool:
        """Compares the Report with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same entries, inputs, parameters, start
                and duration, otherwise False.
        """
        if not isinstance(other, Report):
            return NotImplemented

        return (
            self._root == other._root
            and self._parameters == other._parameters
            and self._started_at == other._started_at
            and self._duration == other._duration
        )

    def __repr__(self) -> str:
        """Returns the string representation of the Report.

        Returns:
            str: The name and the number of entries the report holds.
        """
        return f"Report({self.name!r}, entries={len(self.entries)})"
