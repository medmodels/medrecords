import unittest
from typing import Dict, List, Mapping, Optional

import pytest
from graphrecords import Value

from medrecords.evaluation._run import OnFailure, ProgressArguments, Run
from medrecords.evaluation.analytic import (
    Analytic,
    Derivation,
)
from medrecords.evaluation.entry import (
    Failure,
    InputEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    Layout,
)
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.placement import (
    GroupPlacement,
    InGroup,
    KeyedGroupPlacement,
    NoResultError,
    Placement,
)
from medrecords.evaluation.report import Report
from medrecords.medrecord import MedRecord

NODE_NAMES = ("lorem", "ipsum")


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group([("lorem", {}), ("ipsum", {})], "Sit")


def create_report(
    group: EvaluationGroup[MedRecord],
    on_failure: OnFailure = OnFailure.Record,
    progress: Optional[List[ProgressArguments]] = None,
) -> Report:
    return Run(on_failure, None if progress is None else progress.append).report(
        "amet", None, {}, group, create_medrecord()
    )


class NodeCount(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class Raising(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        msg = "consectetur"
        raise ValueError(msg)


class RaisingOnIpsum(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        if medrecord.node_indices() == ["ipsum"]:
            msg = "adipiscing"
            raise ValueError(msg)

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


class ByPosition(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {
            position: medrecord.keep_nodes([name])
            for position, name in enumerate(NODE_NAMES)
        }


class Twice(Derivation[MedRecord, Mapping[Value, MedRecord]]):
    def derive(self, medrecord: MedRecord) -> Dict[Value, MedRecord]:
        return {0: medrecord, 1: medrecord}


class TitledNodes(ByNode):
    def titles(
        self, medrecord: MedRecord, derived: Mapping[Value, MedRecord], /
    ) -> Mapping[Value, str]:
        return {"lorem": f"Lorem of {medrecord.node_count()}", "dolor": "Dolor"}


class TitledTwice(Twice):
    def titles(
        self, medrecord: MedRecord, derived: Mapping[Value, MedRecord], /
    ) -> Mapping[Value, str]:
        return {0: f"First of {medrecord.node_indices()[0]}"}


class RaisingTitles(Twice):
    def titles(
        self, medrecord: MedRecord, derived: Mapping[Value, MedRecord], /
    ) -> Mapping[Value, str]:
        msg = "elit"
        raise ValueError(msg)


class Paths(Analytic[Findings[InGroup], str]):
    def __init__(self, count: Placement[InGroup, object]) -> None:
        self._count = count

    def compute(self, findings: Findings[InGroup]) -> str:
        return " / ".join(str(name) for name in findings.path(self._count))


class IntNames(Analytic[Findings[InGroup], str]):
    def compute(self, findings: Findings[InGroup]) -> str:
        return ", ".join(
            "/".join(str(name) for name in path) for path, _ in findings.each(int)
        )


class Doubled(Analytic[Findings[InGroup], int]):
    def __init__(self, count: Placement[InGroup, int]) -> None:
        self._count = count

    def compute(self, findings: Findings[InGroup]) -> int:
        return 2 * findings[self._count]


class Summed(Analytic[Findings[InGroup], int]):
    def __init__(self, counts: Placement[InGroup, Mapping[Value, int]]) -> None:
        self._counts = counts

    def compute(self, findings: Findings[InGroup]) -> int:
        return sum(findings[self._counts].values())


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
        assert nested.layout is Layout.Section
        assert (
            create_report(
                group.add_group(
                    "nested", EvaluationGroup[MedRecord](), layout=Layout.Inline
                )
            )
            .group("nested")
            .layout
            is Layout.Inline
        )

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
        assert (
            create_report(
                group.add_group_over(
                    "first",
                    FirstNode(),
                    EvaluationGroup[MedRecord](),
                    layout=Layout.Appendix,
                )
            )
            .group("first")
            .layout
            is Layout.Appendix
        )

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
        assert isinstance(failing.derivation.failure, Failure)
        assert failing.derivation.failure.message == "consectetur"

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

        positioned = create_report(
            EvaluationGroup[MedRecord]().add_group_over_each(
                "positions",
                ByPosition(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        ).group("positions")

        assert [entry.name for entry in positioned.entries] == [0, 1]
        assert positioned.group(1).title == "1"
        assert positioned.group(1).analytic("count").result == 1
        assert positioned.layout is Layout.Section
        assert positioned.group(1).layout is Layout.Section

        titled = create_report(
            EvaluationGroup[MedRecord]().add_group_over_each(
                "nodes",
                TitledNodes(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                layout=Layout.Appendix,
            )
        ).group("nodes")

        assert titled.layout is Layout.Appendix
        assert [entry.title for entry in titled.entries] == ["Lorem of 2", "ipsum"]
        assert titled.group("lorem").layout is Layout.Section

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
        assert isinstance(failing.derivation.failure, Failure)
        assert failing.derivation.failure.message == "adipiscing"

        untitled = create_report(
            EvaluationGroup[MedRecord]().add_group_over_each(
                "nodes",
                RaisingTitles(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        ).group("nodes")

        assert untitled.entries == []
        assert untitled.derivation is not None
        assert untitled.derivation.summary == {}
        assert isinstance(untitled.derivation.failure, Failure)
        assert untitled.derivation.failure.message == "elit"

        with pytest.raises(ValueError, match="elit"):
            create_report(
                EvaluationGroup[MedRecord]().add_group_over_each(
                    "nodes", RaisingTitles(), EvaluationGroup[MedRecord]()
                ),
                OnFailure.Raise,
            )

    def test_add_group_across(self) -> None:
        group = EvaluationGroup[MedRecord]()

        added = group.add_group_across(
            "nodes",
            ByNode(),
            EvaluationGroup[MedRecord]()
            .add_analytic("count", NodeCount())
            .add_group(
                "nested",
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                layout=Layout.Inline,
            )
            .add_group_over(
                "first",
                FirstNode(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                layout=Layout.Appendix,
            )
            .add_group_over_each(
                "positions",
                TitledTwice(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                layout=Layout.Inline,
            )
            .add_group_across(
                "again",
                Twice(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            ),
            layout=Layout.Inline,
        )

        assert create_report(group).entries == []
        across = create_report(added).group("nodes")
        assert across.layout is Layout.Inline
        assert across.inputs == [InputEntry("lorem", 1, 0), InputEntry("ipsum", 1, 0)]
        assert across.derivation is not None
        assert [type(entry) for entry in across.entries] == [
            KeyedAnalyticEntry,
            KeyedGroupEntry,
            KeyedGroupEntry,
            KeyedGroupEntry,
            KeyedGroupEntry,
        ]
        count = across.keyed_analytic("count")
        assert count.keys == ["lorem", "ipsum"]
        assert count.result("lorem") == 1
        assert count.result("ipsum") == 1
        nested = across.keyed_group("nested")
        assert nested.inputs == [InputEntry("lorem", 1, 0), InputEntry("ipsum", 1, 0)]
        assert nested.derivations == {}
        assert nested.layout is Layout.Inline
        assert nested.keyed_analytic("count").keys == ["lorem", "ipsum"]
        first = across.keyed_group("first")
        assert first.layout is Layout.Appendix
        assert first.inputs == [InputEntry("lorem", 1, 0)]
        assert list(first.derivations) == ["lorem", "ipsum"]
        assert first.derivations["lorem"].failure is None
        assert isinstance(first.derivations["ipsum"].failure, Failure)
        assert first.keyed_analytic("count").keys == ["lorem"]
        assert first.keyed_analytic("count").result("lorem") == 1
        positions = across.keyed_group("positions")
        assert list(positions.derivations) == ["lorem", "ipsum"]
        assert [entry.name for entry in positions.entries] == [0, 1]
        assert positions.layout is Layout.Inline
        assert positions.keyed_group(0).title == "First of lorem"
        assert positions.keyed_group(1).title == "1"
        assert positions.keyed_group(0).layout is Layout.Section
        assert positions.keyed_group(0).derivations == {}
        assert positions.keyed_group(0).inputs == [
            InputEntry("lorem", 1, 0),
            InputEntry("ipsum", 1, 0),
        ]
        assert positions.keyed_group(1).keyed_analytic("count").keys == [
            "lorem",
            "ipsum",
        ]
        again = across.keyed_group("again")
        assert [entry.name for entry in again.entries] == [0, 1]
        assert again.layout is Layout.Section
        assert again.keyed_group(1).keyed_analytic("count").result("ipsum") == 1

        titled = create_report(
            group.add_group_across(
                "nodes", ByNode(), EvaluationGroup[MedRecord](), title="Sit"
            )
        ).group("nodes")

        assert titled.title == "Sit"
        assert titled.entries == []

    def test_invalid_add_group_across(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_group_across("count", ByNode(), EvaluationGroup[MedRecord]())

        failing = create_report(
            EvaluationGroup[MedRecord]().add_group_across(
                "nodes",
                RaisingNodes(),
                EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
            )
        ).group("nodes")

        assert failing.inputs == [InputEntry("medrecord", 2, 0)]
        assert failing.entries == []
        assert failing.derivation is not None
        assert isinstance(failing.derivation.failure, Failure)
        assert failing.derivation.failure.message == "adipiscing"

        untitled = create_report(
            EvaluationGroup[MedRecord]().add_group_across(
                "nodes",
                ByNode(),
                EvaluationGroup[MedRecord]().add_group_over_each(
                    "inner",
                    RaisingTitles(),
                    EvaluationGroup[MedRecord]().add_analytic("count", NodeCount()),
                ),
            )
        ).group("nodes")
        inner = untitled.keyed_group("inner")

        assert inner.entries == []
        assert [
            derivation.failure.message
            for derivation in inner.derivations.values()
            if derivation.failure is not None
        ] == ["elit", "elit"]

    def test_add_conclusion(self) -> None:
        group, count = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )
        nested = nested.add_conclusion("doubled", Doubled(inner))
        across, across_count = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )
        across = across.add_conclusion("doubled", Doubled(across_count))
        progress: List[ProgressArguments] = []

        added = group.add_conclusion("names", IntNames())
        added, nested_placement = added.place_group("nested", nested)
        added, nodes = added.place_group_across("nodes", ByNode(), across)
        added, doubled = added.place_conclusion(
            "doubled", Doubled(count), title="Sit", description="dolor"
        )
        added = (
            added.add_conclusion("nested doubled", Doubled(nested_placement[inner]))
            .add_conclusion("summed", Summed(nodes[across_count]))
            .add_conclusion("quadrupled", Doubled(doubled))
        )

        assert [entry.name for entry in create_report(group).entries] == ["count"]
        report = create_report(added, progress=progress)
        assert [entry.name for entry in report.entries] == [
            "count",
            "names",
            "nested",
            "nodes",
            "doubled",
            "nested doubled",
            "summed",
            "quadrupled",
        ]
        assert report.analytic("names").result == (
            "count, nested/count, nested/doubled, nodes/count/lorem, "
            "nodes/count/ipsum, nodes/doubled/lorem, nodes/doubled/ipsum"
        )
        assert report.analytic("doubled").result == 4
        assert report.analytic("doubled").title == "Sit"
        assert report.analytic("doubled").description == "dolor"
        assert report.analytic("nested doubled").result == 4
        assert report.analytic("summed").result == 2
        assert report.analytic("quadrupled").result == 8
        assert report.group("nested").analytic("doubled").result == 4
        keyed = report.group("nodes").keyed_analytic("doubled")
        assert keyed.result("lorem") == 2
        assert keyed.result("ipsum") == 2
        assert [args["path"] for args in progress] == [
            ("count",),
            ("nested", "count"),
            ("nested", "doubled"),
            ("nodes", "count"),
            ("nodes", "count"),
            ("nodes", "doubled"),
            ("nodes", "doubled"),
            ("names",),
            ("doubled",),
            ("nested doubled",),
            ("summed",),
            ("quadrupled",),
        ]

        located, located_count = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )
        located = located.add_conclusion("names", IntNames()).add_conclusion(
            "path", Paths(located_count)
        )
        placed = create_report(
            EvaluationGroup[MedRecord]()
            .add_group("outer", located)
            .add_group_across("nodes", ByNode(), located)
        )

        assert placed.group("outer").analytic("names").result == "outer/count"
        assert placed.group("outer").analytic("path").result == "outer / count"
        assert placed.group("nodes").keyed_analytic("names").result("lorem") == (
            "nodes/count"
        )
        assert placed.group("nodes").keyed_analytic("path").result("ipsum") == (
            "nodes / count"
        )

    def test_invalid_add_conclusion(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        with pytest.raises(ValueError, match="name 'count' is already taken"):
            group.add_conclusion("count", IntNames())

        failing, raising = EvaluationGroup[MedRecord]().place_analytic(
            "raising", Raising()
        )
        failed = create_report(
            failing.add_conclusion("doubled", Doubled(raising))
        ).analytic("doubled")

        assert isinstance(failed.result, Failure)
        assert failed.result.exception_type.endswith("NoResultError")
        assert failed.result.message == "raising failed: consectetur"

        with pytest.raises(ValueError, match="consectetur"):
            create_report(
                failing.add_conclusion("doubled", Doubled(raising)), OnFailure.Raise
            )

        _, foreign = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        misplaced = create_report(
            group.add_conclusion("doubled", Doubled(foreign))
        ).analytic("doubled")

        assert isinstance(misplaced.result, Failure)
        assert misplaced.result.message == (
            "Placement('count') was not placed in this group"
        )

        with pytest.raises(NoResultError, match="was not placed in this group"):
            create_report(
                group.add_conclusion("doubled", Doubled(foreign)), OnFailure.Raise
            )

        across, partial = EvaluationGroup[MedRecord]().place_analytic(
            "partial", RaisingOnIpsum()
        )
        keyed, nodes = EvaluationGroup[MedRecord]().place_group_across(
            "nodes", ByNode(), across
        )
        summed = create_report(
            keyed.add_conclusion("summed", Summed(nodes[partial]))
        ).analytic("summed")

        assert isinstance(summed.result, Failure)
        assert summed.result.message == ("nodes / partial / ipsum failed: adipiscing")

    def test_place_analytic(self) -> None:
        group, count = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount(), title="Sit", description="dolor"
        )

        assert count == Placement((group._members[0]._step,))
        report = create_report(group.add_conclusion("doubled", Doubled(count)))
        assert report.analytic("count").title == "Sit"
        assert report.analytic("count").description == "dolor"
        assert report.analytic("doubled").result == 4

    def test_place_group(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        group, placement = EvaluationGroup[MedRecord]().place_group(
            "nested", nested, title="Sit", description="dolor", layout=Layout.Inline
        )

        assert isinstance(placement, GroupPlacement)
        assert placement[inner] == Placement((group._members[0]._step, *inner._steps))
        report = create_report(
            group.add_conclusion("doubled", Doubled(placement[inner]))
        )
        assert report.group("nested").title == "Sit"
        assert report.group("nested").description == "dolor"
        assert report.group("nested").layout is Layout.Inline
        assert report.analytic("doubled").result == 4

    def test_place_group_over(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        group, placement = EvaluationGroup[MedRecord]().place_group_over(
            "first",
            FirstNode(),
            nested,
            title="Sit",
            description="dolor",
            layout=Layout.Inline,
        )

        assert type(placement) is GroupPlacement
        report = create_report(
            group.add_conclusion("doubled", Doubled(placement[inner]))
        )
        assert report.group("first").title == "Sit"
        assert report.group("first").description == "dolor"
        assert report.group("first").layout is Layout.Inline
        assert report.analytic("doubled").result == 2

    def test_place_group_over_each(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        group, placement = EvaluationGroup[MedRecord]().place_group_over_each(
            "nodes",
            ByNode(),
            nested,
            title="Sit",
            description="dolor",
            layout=Layout.Inline,
        )

        assert type(placement) is KeyedGroupPlacement
        report = create_report(group.add_conclusion("summed", Summed(placement[inner])))
        assert report.group("nodes").title == "Sit"
        assert report.group("nodes").description == "dolor"
        assert report.group("nodes").layout is Layout.Inline
        assert report.analytic("summed").result == 2

    def test_place_group_across(self) -> None:
        nested, inner = EvaluationGroup[MedRecord]().place_analytic(
            "count", NodeCount()
        )

        group, placement = EvaluationGroup[MedRecord]().place_group_across(
            "nodes",
            ByNode(),
            nested,
            title="Sit",
            description="dolor",
            layout=Layout.Inline,
        )

        assert type(placement) is KeyedGroupPlacement
        report = create_report(group.add_conclusion("summed", Summed(placement[inner])))
        assert report.group("nodes").title == "Sit"
        assert report.group("nodes").description == "dolor"
        assert report.group("nodes").layout is Layout.Inline
        assert report.analytic("summed").result == 2

    def test_place_conclusion(self) -> None:
        group, count = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())

        group, doubled = group.place_conclusion(
            "doubled", Doubled(count), title="Sit", description="dolor"
        )

        assert doubled == Placement((group._members[1]._step,))
        report = create_report(group.add_conclusion("quadrupled", Doubled(doubled)))
        assert report.analytic("doubled").title == "Sit"
        assert report.analytic("doubled").description == "dolor"
        assert report.analytic("quadrupled").result == 8

    def test_repr(self) -> None:
        group = EvaluationGroup[MedRecord]().add_analytic("count", NodeCount())

        assert repr(group) == "EvaluationGroup(members=1)"


if __name__ == "__main__":
    unittest.main()
