"""The run computing every entry of a group in order."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from time import perf_counter
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeAlias,
    TypedDict,
    Union,
)

from graphrecords import QueryError

from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
    KeyedAnalyticEntry,
    KeyedResult,
)
from medrecords.evaluation.report import Report

if TYPE_CHECKING:
    from graphrecords import Value

    from medrecords.evaluation.analytic import (
        Analytic,
        Derivation,
        DerivedType,
        Detail,
        EntryPath,
        InputsType,
        ReportValue,
    )
    from medrecords.evaluation.group import EvaluationGroup


class OnFailure(Enum):
    """Enumeration of what a run does when an analytic or a derivation fails."""

    Record = auto()
    Raise = auto()


class ProgressArguments(TypedDict):
    """Arguments for progress handling functions, filled after every analytic run.

    An analytic run across keyed inputs reports once per key, with the keyed
    result as what finished.
    """

    path: EntryPath
    finished: Union[AnalyticEntry, KeyedResult]
    completed: int


#: A type alias for a handling function called after every analytic finishes.
ProgressHandler: TypeAlias = Callable[[ProgressArguments], None]


class Run:
    """One run of an evaluation group, computing every analytic in turn."""

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
        parameters: Mapping[str, Detail],
        group: EvaluationGroup[InputsType],
        inputs: InputsType,
    ) -> Report:
        """Runs a group and collects its report.

        The group's analytics and nested groups run in definition order and
        its conclusions after them.

        Args:
            name (str): The name of the evaluation; the name of the report.
            description (Optional[str]): The text under the name of the report.
            parameters (Mapping[str, Detail]): What the evaluation was
                configured with.
            group (EvaluationGroup[InputsType]): The group to run.
            inputs (InputsType): What the analytics run on.

        Returns:
            Report: The report of the run.
        """
        started_at = datetime.now(timezone.utc)
        clock = perf_counter()
        root = GroupEntry(
            name, name, description, InputEntry._from_inputs(inputs), None, []
        )
        filled = group._filled(self, inputs, (), root)

        return Report(
            name,
            description,
            filled.inputs,
            filled.entries,
            started_at,
            timedelta(seconds=perf_counter() - clock),
            parameters=parameters,
        )

    def _analytic(
        self,
        analytic: Analytic[InputsType, ReportValue],
        inputs: InputsType,
        path: EntryPath,
        title: Optional[str],
        description: Optional[str],
    ) -> AnalyticEntry:
        """Computes an analytic, times it, and records what it reported.

        Args:
            analytic (Analytic[InputsType, ReportValue]): The analytic to compute.
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
        title, description, parameters, setup_error = self._described(
            analytic, name, title, description
        )

        if setup_error is None:
            result, error, duration = self._computed(analytic, inputs)
        else:
            result, error, duration = (
                Failure._from_exception(setup_error),
                setup_error,
                timedelta(),
            )

        entry = AnalyticEntry(name, title, description, parameters, duration, result)

        self._progress(path, entry)

        if error is not None:
            self._fail(error)

        return entry

    def _keyed_analytic(
        self,
        analytic: Analytic[InputsType, ReportValue],
        inputs_by_key: Mapping[Value, InputsType],
        path: EntryPath,
        title: Optional[str],
        description: Optional[str],
    ) -> KeyedAnalyticEntry:
        """Computes an analytic under every key and records what it reported.

        The title, description and parameters are resolved once; when that
        fails, every key records the failure and nothing is computed.

        Args:
            analytic (Analytic[InputsType, ReportValue]): The analytic to compute.
            inputs_by_key (Mapping[Value, InputsType]): What the analytic runs
                on, by key.
            path (EntryPath): The names from the root to the analytic.
            title (Optional[str]): The heading the analytic was placed under, or
                None for the one the analytic gives itself.
            description (Optional[str]): The text the analytic was placed with,
                or None for the one the analytic gives itself.

        Returns:
            KeyedAnalyticEntry: The entry of the analytic.
        """
        name = path[-1]
        title, description, parameters, setup_error = self._described(
            analytic, name, title, description
        )
        results: List[KeyedResult] = []

        for key, inputs in inputs_by_key.items():
            if setup_error is None:
                results.append(self._keyed_result(analytic, key, inputs, path))
            else:
                keyed = KeyedResult(
                    key, timedelta(), Failure._from_exception(setup_error)
                )
                results.append(keyed)
                self._progress(path, keyed)

        if setup_error is not None:
            self._fail(setup_error)

        return KeyedAnalyticEntry(name, title, description, parameters, results)

    def _keyed_result(
        self,
        analytic: Analytic[InputsType, ReportValue],
        key: Value,
        inputs: InputsType,
        path: EntryPath,
    ) -> KeyedResult:
        result, error, duration = self._computed(analytic, inputs)
        keyed = KeyedResult(key, duration, result)

        self._progress(path, keyed)

        if error is not None:
            self._fail(error)

        return keyed

    @staticmethod
    def _described(
        analytic: Analytic[InputsType, ReportValue],
        name: Value,
        title: Optional[str],
        description: Optional[str],
    ) -> Tuple[str, Optional[str], Dict[str, Detail], Optional[Exception]]:
        """Resolves the heading, text and parameters an analytic is recorded with.

        Args:
            analytic (Analytic[InputsType, ReportValue]): The analytic.
            name (Value): The name the analytic was placed under.
            title (Optional[str]): The heading it was placed under, or None for
                the one the analytic gives itself.
            description (Optional[str]): The text it was placed with, or None
                for the one the analytic gives itself.

        Returns:
            Tuple[str, Optional[str], Dict[str, Detail], Optional[Exception]]:
                The heading, the text, the parameters, and the exception the
                analytic raised while giving them, or None.
        """
        try:
            title = title or analytic.title() or str(name)
            description = description or analytic.description() or None
            parameters = dict(analytic.parameters())
        except Exception as error:
            return title or str(name), description, {}, error

        return title, description, parameters, None

    @staticmethod
    def _computed(
        analytic: Analytic[InputsType, ReportValue], inputs: InputsType
    ) -> Tuple[Union[ReportValue, Failure], Optional[Exception], timedelta]:
        """Computes an analytic and times it.

        A failure the query engine hands back in band counts as a failure like
        an exception.

        Args:
            analytic (Analytic[InputsType, ReportValue]): The analytic to compute.
            inputs (InputsType): What the analytic runs on.

        Returns:
            Tuple[Union[ReportValue, Failure], Optional[Exception], timedelta]:
                The result or the recorded failure, the exception behind a
                failure or None, and how long the computation took.
        """
        started = perf_counter()

        try:
            computed = analytic.compute(inputs)
        except Exception as error:
            duration = timedelta(seconds=perf_counter() - started)
            return Failure._from_exception(error), error, duration

        duration = timedelta(seconds=perf_counter() - started)

        if isinstance(computed, QueryError):
            return Failure._from_exception(computed), computed, duration

        return computed, None, duration

    def _derivation(
        self, derivation: Derivation[InputsType, DerivedType], inputs: InputsType
    ) -> Tuple[DerivationEntry, Union[DerivedType, Failure]]:
        """Runs a derivation, times it, and records what it produced.

        Args:
            derivation (Derivation[InputsType, DerivedType]): The derivation to
                run.
            inputs (InputsType): What the derivation runs on.

        Returns:
            Tuple[DerivationEntry, Union[DerivedType, Failure]]: The recorded
                run, and the derived inputs, or the failure the derivation
                ended with.
        """
        parameters: Dict[str, Detail] = {}
        started: Optional[float] = None

        try:
            parameters = dict(derivation.parameters())
            started = perf_counter()
            derived = derivation.derive(inputs)
            summary = dict(derivation.summarize(derived))
        except Exception as error:
            failure = Failure._from_exception(error)
            duration = (
                timedelta()
                if started is None
                else timedelta(seconds=perf_counter() - started)
            )
            self._fail(error)
            return DerivationEntry(parameters, {}, duration, failure), failure

        completed = DerivationEntry(
            parameters, summary, timedelta(seconds=perf_counter() - started), None
        )
        return completed, derived

    def _keyed_derivation(
        self,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        inputs: InputsType,
    ) -> Tuple[
        DerivationEntry, Union[Mapping[Value, DerivedType], Failure], Dict[Value, str]
    ]:
        """Runs a derivation by key and asks it for the titles of its keys.

        Titles that fail fail the derivation.

        Args:
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation to run.
            inputs (InputsType): What the derivation runs on.

        Returns:
            Tuple[DerivationEntry, Union[Mapping[Value, DerivedType], Failure],
                Dict[Value, str]]: The recorded run, the derived inputs by key
                or the failure the derivation ended with, and the title of every
                key that has one.
        """
        recorded, derived = self._derivation(derivation, inputs)

        if isinstance(derived, Failure):
            return recorded, derived, {}

        try:
            titles = dict(derivation.titles(inputs, derived))
        except Exception as error:
            failure = Failure._from_exception(error)
            self._fail(error)
            failed = DerivationEntry(
                recorded.parameters, {}, recorded.duration, failure
            )
            return failed, failure, {}

        return recorded, derived, titles

    def _keyed_derivations(
        self,
        derivation: Derivation[InputsType, Mapping[Value, DerivedType]],
        inputs_by_key: Mapping[Value, InputsType],
    ) -> Tuple[
        Dict[Value, DerivationEntry],
        Dict[Value, Mapping[Value, DerivedType]],
        Dict[Value, str],
    ]:
        """Runs a derivation by key under every key and collects the titles.

        A key whose derivation fails is recorded and left out of the derived
        inputs. A child key takes the first title any key's run gives it.

        Args:
            derivation (Derivation[InputsType, Mapping[Value, DerivedType]]): The
                derivation to run.
            inputs_by_key (Mapping[Value, InputsType]): What the derivation runs
                on, by key.

        Returns:
            Tuple[Dict[Value, DerivationEntry], Dict[Value, Mapping[Value,
                DerivedType]], Dict[Value, str]]: The derivation entries by
                key, the derived inputs of the keys that completed, and the
                title of every child key that has one.
        """
        derivations: Dict[Value, DerivationEntry] = {}
        derived: Dict[Value, Mapping[Value, DerivedType]] = {}
        titles: Dict[Value, str] = {}

        for key, inputs in inputs_by_key.items():
            entry, inner, inner_titles = self._keyed_derivation(derivation, inputs)
            derivations[key] = entry

            if not isinstance(inner, Failure):
                derived[key] = inner

            titles = {**inner_titles, **titles}

        return derivations, derived, titles

    def _derivations(
        self,
        derivation: Derivation[InputsType, DerivedType],
        inputs_by_key: Mapping[Value, InputsType],
    ) -> Tuple[Dict[Value, DerivationEntry], Dict[Value, DerivedType]]:
        """Runs a derivation under every key and records every run.

        A key whose derivation fails is recorded and left out of the derived
        inputs.

        Args:
            derivation (Derivation[InputsType, DerivedType]): The derivation to
                run.
            inputs_by_key (Mapping[Value, InputsType]): What the derivation runs
                on, by key.

        Returns:
            Tuple[Dict[Value, DerivationEntry], Dict[Value, DerivedType]]: The
                derivation entries by key, and the derived inputs of the keys
                that completed.
        """
        derivations: Dict[Value, DerivationEntry] = {}
        derived: Dict[Value, DerivedType] = {}

        for key, inputs in inputs_by_key.items():
            entry, inner = self._derivation(derivation, inputs)
            derivations[key] = entry

            if not isinstance(inner, Failure):
                derived[key] = inner

        return derivations, derived

    def _progress(
        self, path: EntryPath, finished: Union[AnalyticEntry, KeyedResult]
    ) -> None:
        self._completed += 1

        if self._on_progress is not None:
            self._on_progress(
                {"path": path, "finished": finished, "completed": self._completed}
            )

    def _fail(self, error: Exception) -> None:
        if self._on_failure is OnFailure.Raise:
            raise error
