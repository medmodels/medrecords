"""The run computing every entry of a group in order."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from time import perf_counter
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Optional,
    TypeAlias,
    TypedDict,
    Union,
)

from graphrecords import QueryError

from medrecords.evaluation.report import (
    AnalyticEntry,
    Failure,
    InputEntry,
    Report,
)

if TYPE_CHECKING:
    from medrecords.evaluation.analytic import (
        Analytic,
        Detail,
        InputsType,
        ReportValue,
    )
    from medrecords.evaluation.group import EvaluationGroup
    from medrecords.evaluation.report import EntryPath


class OnFailure(Enum):
    """Enumeration of what a run does when an analytic or a derivation fails."""

    Record = auto()
    Raise = auto()


class ProgressArgs(TypedDict):
    """Arguments for progress handling functions, filled after every analytic."""

    path: EntryPath
    entry: AnalyticEntry
    completed: int


#: A type alias for a handling function called after every analytic finishes.
ProgressHandler: TypeAlias = Callable[[ProgressArgs], None]


class Run:
    """One run of an evaluation group, computing every analytic in turn.

    The run holds what every entry needs while the group is walked: the failure
    policy, the progress handling function and how many analytics are done.
    """

    _on_failure: OnFailure
    _on_progress: Optional[ProgressHandler]
    _completed: int

    def __init__(
        self, on_failure: OnFailure, on_progress: Optional[ProgressHandler]
    ) -> None:
        """Initializes a run.

        Args:
            on_failure (OnFailure): Whether a failing analytic or derivation is
                recorded or ends the run.
            on_progress (Optional[ProgressHandler]): Called after every analytic
                finishes. An exception it raises ends the run, whatever the
                failure policy is.
        """
        self._on_failure = on_failure
        self._on_progress = on_progress
        self._completed = 0

    def report(
        self,
        name: str,
        description: Optional[str],
        group: EvaluationGroup[InputsType],
        inputs: InputsType,
    ) -> Report:
        """Runs a group from top to bottom and collects its report.

        Args:
            name (str): The name of the evaluation; the name of the report.
            description (Optional[str]): The text under the name of the report.
            group (EvaluationGroup[InputsType]): The group to run.
            inputs (InputsType): What the analytics run on.

        Returns:
            Report: The report of the run.
        """
        started_at = datetime.now(timezone.utc)
        clock = perf_counter()
        entries = group._entries(self, inputs, ())
        return Report(
            name,
            description,
            InputEntry._from_inputs(inputs),
            entries,
            started_at,
            timedelta(seconds=perf_counter() - clock),
        )

    def _analytic(
        self,
        analytic: Analytic[InputsType],
        inputs: InputsType,
        path: EntryPath,
        title: Optional[str],
        description: Optional[str],
    ) -> AnalyticEntry:
        """Computes an analytic, times it, and records what it reported.

        Args:
            analytic (Analytic[InputsType]): The analytic to compute.
            inputs (InputsType): What the analytic runs on.
            path (EntryPath): The names from the root to the analytic.
            title (Optional[str]): The heading the analytic was placed under, or
                None for the one the analytic gives itself.
            description (Optional[str]): The text the analytic was placed with,
                or None for the one the analytic gives itself.

        Returns:
            AnalyticEntry: The entry of the analytic.
        """
        name = path[-1]
        parameters: Dict[str, Detail] = {}
        result: Union[ReportValue, Failure]
        error: Optional[Exception] = None
        started: Optional[float] = None

        try:
            title = title or analytic.title() or name
            description = description or analytic.description() or None
            parameters = dict(analytic.parameters())
            started = perf_counter()
            computed = analytic.compute(inputs)

            if isinstance(computed, QueryError):
                result = Failure._from_exception(computed)
                error = computed
            else:
                result = computed
        except Exception as exception:
            result = Failure._from_exception(exception)
            error = exception

        duration = (
            timedelta()
            if started is None
            else timedelta(seconds=perf_counter() - started)
        )
        entry = AnalyticEntry(
            name, title or name, description, parameters, duration, result
        )

        self._progress(path, entry)

        if error is not None:
            self._fail(error)

        return entry

    def _progress(self, path: EntryPath, entry: AnalyticEntry) -> None:
        """Counts a finished analytic and tells the progress handling function.

        Args:
            path (EntryPath): The names from the root to the analytic.
            entry (AnalyticEntry): The entry the analytic filled in.
        """
        self._completed += 1

        if self._on_progress is not None:
            self._on_progress(
                {"path": path, "entry": entry, "completed": self._completed}
            )

    def _fail(self, error: Exception) -> None:
        """Raises the error under OnFailure.Raise, and records it otherwise.

        Args:
            error (Exception): The exception an analytic or derivation raised or
                handed back.
        """
        if self._on_failure is OnFailure.Raise:
            raise error
