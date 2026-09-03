import unittest
from typing import Dict, Mapping

import pytest
from graphrecords import Value

from medrecords.evaluation._run import OnFailure, Run
from medrecords.evaluation.analytic import Analytic, Derivation
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.report import Failure, InputEntry, Report
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum")


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group([("lorem", {}), ("ipsum", {})], "Sit")


def create_report(group: EvaluationGroup[MedRecord]) -> Report:
    return Run(OnFailure.Record, None).report("amet", None, group, create_medrecord())


class NodeCount(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class FirstNode(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord.keep_nodes(["lorem"])


class RaisingNode(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        msg = "consectetur"
        raise ValueError(msg)


class RaisingNodes(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        msg = "adipiscing"
        raise ValueError(msg)


class ByNode(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {name: medrecord.keep_nodes([name]) for name in NODE_NAMES}


class TestGroup(unittest.TestCase):
    def test_init(self) -> None:
        assert create_report(EvaluationGroup[MedRecord]()).entries == []

    def test_add_analytic(self) -> None:
        group = EvaluationGroup[MedRecord]()

        added = group.add_analytic("count", NodeCount())

        assert create_report(group).entries == []
        assert create_report(added).analytic("count").result == 2

        titled = create_report(
            group.add_analytic("count", NodeCount(), title="Sit", description="dolor")
        ).analytic("count")

        assert titled.title == "Sit"
        assert titled.description == "dolor"

    def test_invalid_add_analytic(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_analytic("count", NodeCount())

    def test_add_group(self) -> None:
        group = EvaluationGroup[MedRecord]()

        added = group.add_group(
            "nested", EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())
        )

        assert create_report(group).entries == []
        nested = create_report(added).group("nested")
        assert nested.inputs == [InputEntry("medrecord", 2, 0)]
        assert nested.derivation is None
        assert nested.analytic("count").result == 2

    def test_invalid_add_group(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_group("count", EvaluationGroup[MedRecord]())

    def test_add_group_over(self) -> None:
        group = EvaluationGroup[MedRecord]()

        added = group.add_group_over(
            "first",
            FirstNode(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        assert create_report(group).entries == []
        first = create_report(added).group("first")
        assert first.inputs == [InputEntry("medrecord", 1, 0)]
        assert first.derivation is not None
        assert first.analytic("count").result == 1

    def test_invalid_add_group_over(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_group_over("count", FirstNode(), EvaluationGroup[MedRecord]())

        failing = create_report(
            EvaluationGroup[MedRecord]().add_group_over(
                "first",
                RaisingNode(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        ).group("first")

        assert failing.inputs == [InputEntry("medrecord", 2, 0)]
        assert failing.entries == []
        assert failing.derivation is not None
        assert isinstance(failing.derivation.outcome, Failure)
        assert failing.derivation.outcome.message == "consectetur"

    def test_add_group_over_each(self) -> None:
        group = EvaluationGroup[MedRecord]()

        added = group.add_group_over_each(
            "nodes",
            ByNode(),
            EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
        )

        assert create_report(group).entries == []
        keyed = create_report(added).group("nodes")
        assert [entry.name for entry in keyed.entries] == ["lorem", "ipsum"]
        assert keyed.derivation is not None
        assert keyed.group("lorem").inputs == [InputEntry("medrecord", 1, 0)]
        assert keyed.group("lorem").analytic("count").result == 1

    def test_invalid_add_group_over_each(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_group_over_each("count", ByNode(), EvaluationGroup[MedRecord]())

        failing = create_report(
            EvaluationGroup[MedRecord]().add_group_over_each(
                "nodes",
                RaisingNodes(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        ).group("nodes")

        assert failing.inputs == [InputEntry("medrecord", 2, 0)]
        assert failing.entries == []
        assert failing.derivation is not None
        assert isinstance(failing.derivation.outcome, Failure)
        assert failing.derivation.outcome.message == "adipiscing"

    def test_repr(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        assert repr(group) == "EvaluationGroup(members=1)"


if __name__ == "__main__":
    unittest.main()
