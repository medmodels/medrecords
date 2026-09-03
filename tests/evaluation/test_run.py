import unittest
from datetime import timezone
from typing import Dict, List, Mapping, Optional, Union

import pytest
from graphrecords import QueryError
from graphrecords.types import Value

from medrecords.evaluation._run import OnFailure, ProgressArgs, ProgressHandler, Run
from medrecords.evaluation.analytic import Analytic, Derivation, Detail
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.report import Failure, InputEntry, Report
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum", "dolor")


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes_in_group([("lorem", {}), ("ipsum", {}), ("dolor", {})], "Sit")
        .add_edges([("lorem", "ipsum", {}), ("ipsum", "dolor", {})])
    )


def create_report(
    group: EvaluationGroup[MedRecord],
    on_failure: OnFailure = OnFailure.Record,
    on_progress: Optional[ProgressHandler] = None,
) -> Report:
    return Run(on_failure, on_progress).report("amet", None, group, create_medrecord())


class RaisingProgress:
    def __call__(self, args: ProgressArgs) -> None:
        msg = "laboris"
        raise RuntimeError(msg)


class NodeCount(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class Counting(Analytic[MedRecord]):
    def __init__(self) -> None:
        self.calls = 0

    def compute(self, medrecord: MedRecord) -> int:
        self.calls += 1

        return medrecord.node_count()


class Raising(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        msg = "consectetur"
        raise ValueError(msg)


class RaisingTitle(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()

    def title(self) -> Optional[str]:
        msg = "magna"
        raise ValueError(msg)


class InBand(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        return QueryError("adipiscing")


class Described(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.edge_count()

    def title(self) -> Optional[str]:
        return "elit"

    def description(self) -> Optional[str]:
        return "tempor"


class Parameterized(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()

    def parameters(self) -> Mapping[str, Detail]:
        return {"limit": 3, "groups": ("Sit", "Elit")}


class RaisingParameters(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()

    def parameters(self) -> Mapping[str, Detail]:
        msg = "eiusmod"
        raise ValueError(msg)


class FirstNode(Derivation[MedRecord, MedRecord]):
    def __init__(self) -> None:
        self.calls = 0

    def derive(self, medrecord: MedRecord) -> MedRecord:
        self.calls += 1

        return medrecord.keep_nodes(["lorem"])

    def parameters(self) -> Mapping[str, Detail]:
        return {"node": "lorem", "kept": ("lorem",)}

    def summarize(self, derived: MedRecord) -> Mapping[str, Detail]:
        return {"kept": derived.node_count()}


class RaisingSummary(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord

    def parameters(self) -> Mapping[str, Detail]:
        return {"seed": 7}

    def summarize(self, derived: MedRecord) -> Mapping[str, Detail]:
        msg = "tempor"
        raise ValueError(msg)


class RaisingDerivation(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        msg = "incididunt"
        raise ValueError(msg)


class RaisingDerivationParameters(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord

    def parameters(self) -> Mapping[str, Detail]:
        msg = "veniam"
        raise ValueError(msg)


class ByNode(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {name: medrecord.keep_nodes([name]) for name in NODE_NAMES}


class RaisingKeys(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        msg = "labore"
        raise ValueError(msg)


class NoKeys(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {}


class TestRun(unittest.TestCase):
    def test_report(self) -> None:
        progress: List[ProgressArgs] = []
        derivation = FirstNode()
        group = (
            EvaluationGroup[MedRecord]()
            .add_analytic("count", NodeCount())
            .add_analytic("described", Described())
            .add_analytic("parameterized", Parameterized())
            .add_group_over(
                "first",
                derivation,
                EvaluationGroup[MedRecord]()
                .add_analytic("count", NodeCount())
                .add_analytic(
                    "edges", Described(), title="consectetur", description="magna"
                )
                .add_group(
                    "nested",
                    EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                ),
            )
            .add_group_over_each(
                "nodes",
                ByNode(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
            .add_group_over_each(
                "none",
                NoKeys(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        )

        report = create_report(group, on_progress=progress.append)

        assert report.name == "amet"
        assert report.inputs == [InputEntry("medrecord", 3, 2)]
        assert [entry.name for entry in report.entries] == [
            "count",
            "described",
            "parameterized",
            "first",
            "nodes",
            "none",
        ]
        assert report.analytic("count").result == 3
        assert report.analytic("count").title == "count"
        assert report.analytic("described").title == "elit"
        assert report.analytic("described").description == "tempor"
        assert report.group("first").analytic("edges").title == "consectetur"
        assert report.group("first").analytic("edges").description == "magna"
        assert report.analytic("parameterized").parameters == {
            "limit": 3,
            "groups": ["Sit", "Elit"],
        }
        assert report.started_at.tzinfo is timezone.utc
        assert report.duration.total_seconds() > 0

        first = report.group("first")
        assert derivation.calls == 1
        assert first.inputs == [InputEntry("medrecord", 1, 0)]
        assert first.derivation is not None
        assert first.derivation.outcome is None
        assert first.derivation.parameters == {"node": "lorem", "kept": ["lorem"]}
        assert first.derivation.summary == {"kept": 1}
        assert first.analytic("count").result == 1
        assert first.analytic("edges").result == 0
        assert first.group("nested").inputs == [InputEntry("medrecord", 1, 0)]
        assert first.group("nested").analytic("count").result == 1
        assert first.group("nested").derivation is None

        keyed = report.group("nodes")
        assert keyed.inputs == [InputEntry("medrecord", 3, 2)]
        assert keyed.derivation is not None
        assert keyed.derivation.outcome is None
        assert [entry.name for entry in keyed.entries] == ["lorem", "ipsum", "dolor"]
        assert keyed.group("ipsum").inputs == [InputEntry("medrecord", 1, 0)]
        assert keyed.group("ipsum").derivation is None
        assert keyed.group("ipsum").analytic("count").result == 1
        assert report.group("none").entries == []
        assert report.group("none").derivation is not None

        assert [args["completed"] for args in progress] == list(range(1, 10))
        assert [args["path"] for args in progress] == [
            ("count",),
            ("described",),
            ("parameterized",),
            ("first", "count"),
            ("first", "edges"),
            ("first", "nested", "count"),
            ("nodes", "lorem", "count"),
            ("nodes", "ipsum", "count"),
            ("nodes", "dolor", "count"),
        ]
        assert progress[0]["entry"].result == 3

        empty = create_report(EvaluationGroup[MedRecord]())
        assert empty.entries == []
        assert empty.duration.total_seconds() > 0

    def test_invalid_report(self) -> None:
        group = (
            EvaluationGroup[MedRecord]()
            .add_analytic("raising", Raising())
            .add_analytic("in_band", InBand())
            .add_analytic("untitled", RaisingTitle())
            .add_analytic("unparameterized", RaisingParameters())
            .add_analytic("count", NodeCount())
            .add_group_over(
                "failing",
                RaisingDerivation(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
            .add_group_over(
                "unsummarized",
                RaisingSummary(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
            .add_group_over(
                "unparameterized_group",
                RaisingDerivationParameters(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
            .add_group_over_each(
                "failing_keys",
                RaisingKeys(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        )

        report = create_report(group)

        raising = report.analytic("raising").result
        assert isinstance(raising, Failure)
        assert raising.exception_type == "builtins.ValueError"
        assert raising.message == "consectetur"
        assert "ValueError: consectetur" in raising.traceback
        in_band = report.analytic("in_band").result
        assert isinstance(in_band, Failure)
        assert in_band.exception_type.endswith("QueryError")
        assert in_band.message == "adipiscing"
        untitled = report.analytic("untitled").result
        assert isinstance(untitled, Failure)
        assert untitled.message == "magna"
        assert report.analytic("untitled").duration.total_seconds() == 0
        unparameterized = report.analytic("unparameterized").result
        assert isinstance(unparameterized, Failure)
        assert unparameterized.message == "eiusmod"
        assert report.analytic("unparameterized").parameters == {}
        assert report.analytic("count").result == 3
        failing = report.group("failing")
        assert failing.derivation is not None
        assert isinstance(failing.derivation.outcome, Failure)
        assert failing.derivation.outcome.message == "incididunt"
        assert failing.entries == []
        assert failing.inputs == [InputEntry("medrecord", 3, 2)]
        unsummarized = report.group("unsummarized")
        assert unsummarized.derivation is not None
        assert isinstance(unsummarized.derivation.outcome, Failure)
        assert unsummarized.derivation.outcome.message == "tempor"
        assert unsummarized.derivation.parameters == {"seed": 7}
        assert unsummarized.derivation.summary == {}
        assert unsummarized.entries == []
        unparameterized_group = report.group("unparameterized_group")
        assert unparameterized_group.derivation is not None
        assert isinstance(unparameterized_group.derivation.outcome, Failure)
        assert unparameterized_group.derivation.outcome.message == "veniam"
        failing_keys = report.group("failing_keys")
        assert failing_keys.derivation is not None
        assert isinstance(failing_keys.derivation.outcome, Failure)
        assert failing_keys.entries == []
        assert failing_keys.inputs == [InputEntry("medrecord", 3, 2)]
        assert RaisingTitle().compute(create_medrecord()) == 3
        assert RaisingParameters().compute(create_medrecord()) == 3
        assert (
            RaisingDerivationParameters().derive(create_medrecord()).node_count() == 3
        )

        counting = Counting()
        strict = (
            EvaluationGroup[MedRecord]()
            .add_analytic("raising", Raising())
            .add_analytic("counting", counting)
        )

        assert create_report(strict).analytic("counting").result == 3
        assert counting.calls == 1

        with pytest.raises(ValueError, match="consectetur"):
            create_report(strict, on_failure=OnFailure.Raise)

        assert counting.calls == 1

        unsummarized_only = EvaluationGroup[MedRecord]().add_group_over(
            "unsummarized",
            RaisingSummary(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        with pytest.raises(ValueError, match="tempor"):
            create_report(unsummarized_only, on_failure=OnFailure.Raise)

        keyed_only = EvaluationGroup[MedRecord]().add_group_over_each(
            "failing_keys",
            RaisingKeys(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        with pytest.raises(ValueError, match="labore"):
            create_report(keyed_only, on_failure=OnFailure.Raise)

        with pytest.raises(RuntimeError, match="laboris"):
            create_report(
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                on_progress=RaisingProgress(),
            )


if __name__ == "__main__":
    unittest.main()
