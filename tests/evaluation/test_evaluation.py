import unittest
from typing import Dict, List, Mapping

import pytest
from graphrecords import Value

from medrecords.evaluation._run import OnFailure, ProgressArgs
from medrecords.evaluation.analytic import Analytic, Derivation
from medrecords.evaluation.evaluation import Evaluation
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.report import GroupEntry, InputEntry
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum")


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group([("lorem", {}), ("ipsum", {})], "Sit")


class NodeCount(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class FirstNode(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord.keep_nodes(["lorem"])


class ByNode(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {name: medrecord.keep_nodes([name]) for name in NODE_NAMES}


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

    def test_report(self) -> None:
        progress: List[ProgressArgs] = []
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
