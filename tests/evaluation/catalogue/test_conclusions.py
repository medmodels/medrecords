import math
import unittest
from typing import Dict, Mapping

from graphrecords import Value

from medrecords.evaluation._run import OnFailure, Run
from medrecords.evaluation.analytic import Analytic, Assessment, Derivation, Table
from medrecords.evaluation.catalogue.conclusions import (
    AnalyticsFailed,
    ChecksFailed,
    ChecksRun,
    FailedAnalytics,
    FailedChecks,
    KeyedMean,
    KeyedTable,
    Mean,
)
from medrecords.evaluation.entry import Failure
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.report import Report
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum")


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group([("lorem", {}), ("ipsum", {})], "Sit")


def create_report(group: EvaluationGroup[MedRecord]) -> Report:
    return Run(OnFailure.Record, None).report(
        "amet", None, {}, group, create_medrecord()
    )


class NodeCount(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class Score(Analytic[MedRecord, float]):
    def __init__(self, score: float) -> None:
        self._score = score

    def compute(self, medrecord: MedRecord) -> float:
        return self._score


class NodeScore(Analytic[MedRecord, float]):
    def compute(self, medrecord: MedRecord) -> float:
        return 0.5 if medrecord.contains_node("lorem") else 1.0


class AtLeast(Analytic[MedRecord, Assessment]):
    def __init__(self, minimum: int) -> None:
        self._minimum = minimum

    def compute(self, medrecord: MedRecord) -> Assessment:
        count = medrecord.node_count()

        return Assessment(
            count, f"at least {self._minimum}", passed=count >= self._minimum
        )


class Raising(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        msg = "consectetur"
        raise ValueError(msg)


class ByNode(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {name: medrecord.keep_nodes([name]) for name in NODE_NAMES}


def create_group() -> EvaluationGroup[MedRecord]:
    return (
        EvaluationGroup[MedRecord]()
        .add_analytic("passing", AtLeast(1))
        .add_analytic("failing", AtLeast(3))
        .add_analytic("raising", Raising())
        .add_group_across(
            "nodes",
            ByNode(),
            EvaluationGroup[MedRecord]()
            .add_analytic("passing", AtLeast(1))
            .add_analytic("failing", AtLeast(2)),
        )
    )


class TestChecksRun(unittest.TestCase):
    def test_compute(self) -> None:
        report = create_report(create_group().add_conclusion("run", ChecksRun()))

        assert report.analytic("run").result == 6

    def test_title(self) -> None:
        assert ChecksRun().title() == "Checks run"


class TestChecksFailed(unittest.TestCase):
    def test_compute(self) -> None:
        report = create_report(create_group().add_conclusion("failed", ChecksFailed()))

        assert report.analytic("failed").result == 3

    def test_title(self) -> None:
        assert ChecksFailed().title() == "Checks failed"


class TestFailedChecks(unittest.TestCase):
    def test_compute(self) -> None:
        report = create_report(create_group().add_conclusion("failed", FailedChecks()))

        assert report.analytic("failed").result == Table(
            ["check", "value", "required"],
            [
                [("failing",), 2, "at least 3"],
                [("nodes", "failing", "lorem"), 1, "at least 2"],
                [("nodes", "failing", "ipsum"), 1, "at least 2"],
            ],
        )

    def test_title(self) -> None:
        assert FailedChecks().title() == "Failed checks"


class TestAnalyticsFailed(unittest.TestCase):
    def test_compute(self) -> None:
        report = create_report(
            create_group().add_conclusion("broken", AnalyticsFailed())
        )

        assert report.analytic("broken").result == 1

    def test_title(self) -> None:
        assert AnalyticsFailed().title() == "Entries not computed"


class TestFailedAnalytics(unittest.TestCase):
    def test_compute(self) -> None:
        report = create_report(
            create_group().add_conclusion("broken", FailedAnalytics())
        )

        assert report.analytic("broken").result == Table(
            ["entry", "exception type", "message"],
            [[("raising",), "builtins.ValueError", "consectetur"]],
        )

    def test_title(self) -> None:
        assert FailedAnalytics().title() == "Entries not computed, with their errors"


class TestMean(unittest.TestCase):
    def test_compute(self) -> None:
        group, first = EvaluationGroup[MedRecord]().place_analytic("first", Score(0.5))
        group, second = group.place_analytic("second", Score(1.0))
        group, count = group.place_analytic("count", NodeCount())
        group, raising = group.place_analytic("raising", Raising())

        report = create_report(
            group.add_conclusion("mean", Mean([first, second, count])).add_conclusion(
                "broken", Mean([first, raising])
            )
        )

        mean = report.analytic("mean").result
        assert isinstance(mean, float)
        assert math.isclose(mean, 7 / 6)
        broken = report.analytic("broken").result
        assert isinstance(broken, Failure)
        assert broken.message == "raising failed: consectetur"

    def test_title(self) -> None:
        assert Mean([]).title() == "Mean"


class TestKeyedMean(unittest.TestCase):
    def test_compute(self) -> None:
        nested, score = EvaluationGroup[MedRecord]().place_analytic(
            "score", NodeScore()
        )
        nested, raising = nested.place_analytic("raising", Raising())
        group, nodes = EvaluationGroup[MedRecord]().place_group_across(
            "nodes", ByNode(), nested
        )

        report = create_report(
            group.add_conclusion("mean", KeyedMean(nodes[score])).add_conclusion(
                "broken", KeyedMean(nodes[raising])
            )
        )

        mean = report.analytic("mean").result
        assert isinstance(mean, float)
        assert math.isclose(mean, 0.75)
        broken = report.analytic("broken").result
        assert isinstance(broken, Failure)
        assert broken.message == "nodes / raising / lorem failed: consectetur"

    def test_title(self) -> None:
        nested, score = EvaluationGroup[MedRecord]().place_analytic(
            "score", NodeScore()
        )
        _, nodes = EvaluationGroup[MedRecord]().place_group_across(
            "nodes", ByNode(), nested
        )

        assert KeyedMean(nodes[score]).title() == "Mean"


class TestKeyedTable(unittest.TestCase):
    def test_compute(self) -> None:
        nested, count = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )
        group, nodes = EvaluationGroup[MedRecord]().place_group_across(
            "nodes", ByNode(), nested
        )

        report = create_report(
            group.add_conclusion("sizes", KeyedTable(nodes[count], "node", "count"))
        )

        assert report.analytic("sizes").result == Table(
            ["node", "count"], [["lorem", 1], ["ipsum", 1]]
        )


if __name__ == "__main__":
    unittest.main()
