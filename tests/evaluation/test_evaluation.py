import unittest
from typing import Dict, List, Mapping

import pytest
from graphrecords import Value

from medrecords.evaluation._run import OnFailure, ProgressArguments
from medrecords.evaluation.analytic import (
    Analytic,
    Derivation,
)
from medrecords.evaluation.entry import GroupEntry, InputEntry
from medrecords.evaluation.evaluation import Evaluation
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.placement import (
    AtRoot,
    GroupPlacement,
    KeyedGroupPlacement,
    Placement,
)
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum")


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group([("lorem", {}), ("ipsum", {})], "Sit")


class NodeCount(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class FirstNode(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord.keep_nodes(["lorem"])


class ByNode(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {name: medrecord.keep_nodes([name]) for name in NODE_NAMES}


class IntNames(Analytic[Findings[AtRoot], str]):
    def compute(self, findings: Findings[AtRoot]) -> str:
        return ", ".join(
            "/".join(str(name) for name in path) for path, _ in findings.each(int)
        )


class Doubled(Analytic[Findings[AtRoot], int]):
    def __init__(self, count: Placement[AtRoot, int]) -> None:
        self._count = count

    def compute(self, findings: Findings[AtRoot]) -> int:
        return 2 * findings[self._count]


class TestEvaluation(unittest.TestCase):
    def test_init(self) -> None:
        report = Evaluation[MedRecord]("amet").report(create_medrecord())

        assert report.name == "amet"
        assert report.description is None
        assert report.entries == []

        described = Evaluation[MedRecord]("amet", description="lorem")

        assert described.report(create_medrecord()).description == "lorem"

    def test_add_analytic(self) -> None:
        evaluation = Evaluation[MedRecord]("amet")

        added = evaluation.add_analytic("count", NodeCount())

        assert evaluation.report(create_medrecord()).entries == []
        assert added.report(create_medrecord()).analytic("count").result == 2

        titled = (
            Evaluation[MedRecord]("amet")
            .add_analytic("count", NodeCount(), title="Sit", description="dolor")
            .report(create_medrecord())
            .analytic("count")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"

    def test_invalid_add_analytic(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_analytic("count", NodeCount())

    def test_add_group(self) -> None:
        evaluation = Evaluation[MedRecord]("amet")

        added = evaluation.add_group(
            "nested", EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())
        )

        assert evaluation.report(create_medrecord()).entries == []
        assert (
            added.report(create_medrecord()).group("nested").analytic("count").result
            == 2
        )

        titled = (
            Evaluation[MedRecord]("amet")
            .add_group(
                "Sit", EvaluationGroup[MedRecord](), title="Sit", description="dolor"
            )
            .report(create_medrecord())
            .group("Sit")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"

    def test_invalid_add_group(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_group("count", EvaluationGroup[MedRecord]())

    def test_add_group_over(self) -> None:
        evaluation = Evaluation[MedRecord]("amet")

        added = evaluation.add_group_over(
            "first",
            FirstNode(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        assert evaluation.report(create_medrecord()).entries == []
        first = added.report(create_medrecord()).group("first")
        assert first.inputs == [InputEntry("medrecord", 1, 0)]
        assert first.analytic("count").result == 1

        titled = (
            Evaluation[MedRecord]("amet")
            .add_group_over(
                "Sit",
                FirstNode(),
                EvaluationGroup[MedRecord](),
                title="Sit",
                description="dolor",
            )
            .report(create_medrecord())
            .group("Sit")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"

    def test_invalid_add_group_over(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_group_over(
                "count", FirstNode(), EvaluationGroup[MedRecord]()
            )

    def test_add_group_over_each(self) -> None:
        evaluation = Evaluation[MedRecord]("amet")

        added = evaluation.add_group_over_each(
            "nodes",
            ByNode(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        assert evaluation.report(create_medrecord()).entries == []
        keyed = added.report(create_medrecord()).group("nodes")
        assert [entry.name for entry in keyed.entries] == ["lorem", "ipsum"]
        assert keyed.group("ipsum").analytic("count").result == 1

        titled = (
            Evaluation[MedRecord]("amet")
            .add_group_over_each(
                "Sit",
                ByNode(),
                EvaluationGroup[MedRecord](),
                title="Sit",
                description="dolor",
            )
            .report(create_medrecord())
            .group("Sit")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"
        assert all(
            entry.title == entry.name
            for entry in titled.entries
            if isinstance(entry, GroupEntry)
        )

    def test_invalid_add_group_over_each(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_group_over_each(
                "count", ByNode(), EvaluationGroup[MedRecord]()
            )

    def test_add_group_across(self) -> None:
        evaluation = Evaluation[MedRecord]("amet")

        added = evaluation.add_group_across(
            "nodes",
            ByNode(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        assert evaluation.report(create_medrecord()).entries == []
        across = added.report(create_medrecord()).group("nodes")
        assert across.keyed_analytic("count").keys == ["lorem", "ipsum"]
        assert across.keyed_analytic("count").result("ipsum") == 1

        titled = (
            Evaluation[MedRecord]("amet")
            .add_group_across(
                "Sit",
                ByNode(),
                EvaluationGroup[MedRecord](),
                title="Sit",
                description="dolor",
            )
            .report(create_medrecord())
            .group("Sit")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"

    def test_invalid_add_group_across(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_group_across("count", ByNode(), EvaluationGroup[MedRecord]())

    def test_add_conclusion(self) -> None:
        evaluation, count = Evaluation[MedRecord]("amet").place_analytic(
            "count", NodeCount()
        )

        added = evaluation.add_conclusion("doubled", Doubled(count))

        assert [
            entry.name for entry in evaluation.report(create_medrecord()).entries
        ] == ["count"]
        assert added.report(create_medrecord()).analytic("doubled").result == 4

        titled = (
            Evaluation[MedRecord]("amet")
            .add_conclusion("names", IntNames(), title="Sit", description="dolor")
            .add_analytic("count", NodeCount())
            .report(create_medrecord())
            .analytic("names")
        )

        assert titled.title == "Sit"
        assert titled.description == "dolor"
        assert titled.result == "count"

    def test_invalid_add_conclusion(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            evaluation.add_conclusion("count", IntNames())

    def test_place_analytic(self) -> None:
        evaluation, count = Evaluation[MedRecord]("amet").place_analytic(
            "count", NodeCount(), title="Sit", description="dolor"
        )

        assert count == Placement((evaluation._group._members[0]._step,))
        report = evaluation.report(create_medrecord())
        assert report.analytic("count").title == "Sit"
        assert report.analytic("count").description == "dolor"
        assert report.findings[count] == 2

    def test_place_group(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        evaluation, placement = Evaluation[MedRecord]("amet").place_group(
            "nested", nested, title="Sit", description="dolor"
        )

        assert isinstance(placement, GroupPlacement)
        report = evaluation.report(create_medrecord())
        assert report.group("nested").title == "Sit"
        assert report.group("nested").description == "dolor"
        assert report.findings[placement[inner]] == 2

    def test_place_group_over(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        evaluation, placement = Evaluation[MedRecord]("amet").place_group_over(
            "first", FirstNode(), nested, title="Sit", description="dolor"
        )

        assert type(placement) is GroupPlacement
        report = evaluation.report(create_medrecord())
        assert report.group("first").title == "Sit"
        assert report.group("first").description == "dolor"
        assert report.findings[placement[inner]] == 1

    def test_place_group_over_each(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        evaluation, placement = Evaluation[MedRecord]("amet").place_group_over_each(
            "nodes", ByNode(), nested, title="Sit", description="dolor"
        )

        assert type(placement) is KeyedGroupPlacement
        report = evaluation.report(create_medrecord())
        assert report.group("nodes").title == "Sit"
        assert report.group("nodes").description == "dolor"
        assert report.findings[placement[inner]] == {"lorem": 1, "ipsum": 1}

    def test_place_group_across(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        evaluation, placement = Evaluation[MedRecord]("amet").place_group_across(
            "nodes", ByNode(), nested, title="Sit", description="dolor"
        )

        assert type(placement) is KeyedGroupPlacement
        report = evaluation.report(create_medrecord())
        assert report.group("nodes").title == "Sit"
        assert report.group("nodes").description == "dolor"
        assert report.findings[placement[inner]] == {"lorem": 1, "ipsum": 1}

    def test_place_conclusion(self) -> None:
        evaluation, count = Evaluation[MedRecord]("amet").place_analytic(
            "count", NodeCount()
        )

        evaluation, doubled = evaluation.place_conclusion(
            "doubled", Doubled(count), title="Sit", description="dolor"
        )

        assert doubled == Placement((evaluation._group._members[1]._step,))
        report = evaluation.add_conclusion("quadrupled", Doubled(doubled)).report(
            create_medrecord()
        )
        assert report.analytic("doubled").title == "Sit"
        assert report.analytic("doubled").description == "dolor"
        assert report.analytic("quadrupled").result == 8
        assert report.findings[doubled] == 4

    def test_report(self) -> None:
        progress: List[ProgressArguments] = []
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        report = evaluation.report(
            create_medrecord(),
            on_failure=OnFailure.Raise,
            on_progress=progress.append,
        )

        assert report.name == "amet"
        assert report.inputs == [InputEntry("medrecord", 2, 0)]
        assert report.analytic("count").result == 2
        assert [args["path"] for args in progress] == [("count",)]

    def test_repr(self) -> None:
        evaluation = Evaluation[MedRecord]("amet").add_analytic("count", NodeCount())

        assert repr(evaluation) == "Evaluation('amet', members=1)"


if __name__ == "__main__":
    unittest.main()
