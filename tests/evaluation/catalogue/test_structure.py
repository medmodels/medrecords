import unittest

from graphrecords import EdgeEndpointRole, edges, nodes

from medrecords.evaluation.catalogue.structure import (
    EdgesPerNode,
    ElementCount,
    GroupSizes,
)
from medrecords.medrecord import MedRecord

SIT = nodes().filter(nodes().in_group("Sit"))
ELIT = edges().filter(edges().in_group("Elit"))


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes_in_group([("lorem", {}), ("ipsum", {}), ("dolor", {})], "Sit")
        .add_nodes([("amet", {})])
        .add_edges_in_group([("lorem", "ipsum", {}), ("lorem", "dolor", {})], "Elit")
        .add_edges([("dolor", "amet", {})])
        .add_group("Vacant")
    )


class TestElementCount(unittest.TestCase):
    def test_compute(self) -> None:
        assert ElementCount(nodes()).compute(create_medrecord()) == 4
        assert ElementCount(SIT).compute(create_medrecord()) == 3
        assert ElementCount(edges()).compute(create_medrecord()) == 3
        assert ElementCount(ELIT).compute(create_medrecord()) == 2


class TestGroupSizes(unittest.TestCase):
    def test_compute(self) -> None:
        table = GroupSizes().compute(create_medrecord())

        assert table.headings == ["group", "nodes", "edges"]
        assert sorted(table.rows, key=str) == [
            ["Elit", 0, 2],
            ["Sit", 3, 0],
            ["Vacant", 0, 0],
        ]

    def test_title(self) -> None:
        assert GroupSizes().title() == "Group sizes"


class TestEdgesPerNode(unittest.TestCase):
    def test_compute(self) -> None:
        sources = EdgesPerNode(SIT, ELIT, EdgeEndpointRole.Source).compute(
            create_medrecord()
        )
        targets = EdgesPerNode(SIT, ELIT, EdgeEndpointRole.Target).compute(
            create_medrecord()
        )

        assert sorted(sources.values) == [0.0, 0.0, 2.0]
        assert sorted(targets.values) == [0.0, 1.0, 1.0]

    def test_description(self) -> None:
        assert (
            EdgesPerNode(SIT, ELIT, EdgeEndpointRole.Source).description()
            == "Nodes without any edge count as zero."
        )

    def test_parameters(self) -> None:
        assert EdgesPerNode(SIT, ELIT, EdgeEndpointRole.Source).parameters() == {
            "role": "source"
        }
        assert EdgesPerNode(SIT, ELIT, EdgeEndpointRole.Target).parameters() == {
            "role": "target"
        }


if __name__ == "__main__":
    unittest.main()
