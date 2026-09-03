import unittest
from datetime import datetime

import pytest
from graphrecords import EdgeEndpointRole, edges, nodes

from medrecords.evaluation.catalogue.quality import (
    AttributeOrder,
    AttributeRange,
    AttributeUniqueness,
    UnlinkedNodes,
)
from medrecords.medrecord import MedRecord

SIT = nodes().filter(nodes().in_group("Sit"))
ELIT = nodes().filter(nodes().in_group("Elit"))
CONSECTETUR = edges().filter(edges().in_group("Consectetur"))


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes_in_group(
            [
                (
                    "lorem",
                    {
                        "amet": 1,
                        "id": "a",
                        "start": datetime(2020, 1, 1),
                        "end": datetime(2021, 1, 1),
                    },
                ),
                (
                    "ipsum",
                    {
                        "amet": 3,
                        "id": "a",
                        "start": datetime(2021, 1, 1),
                        "end": datetime(2020, 6, 1),
                    },
                ),
                ("dolor", {"amet": 30, "id": "b", "start": datetime(2020, 1, 1)}),
                ("sit", {}),
            ],
            "Sit",
        )
        .add_nodes_in_group([("a", {}), ("b", {}), ("c", {})], "Elit")
        .add_edges_in_group(
            [
                (
                    "lorem",
                    "a",
                    {"start": datetime(2020, 1, 1), "end": datetime(2019, 1, 1)},
                ),
                (
                    "ipsum",
                    "b",
                    {"start": datetime(2020, 1, 1), "end": datetime(2021, 1, 1)},
                ),
            ],
            "Consectetur",
        )
    )


class TestAttributeRange(unittest.TestCase):
    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="needs a minimum or a maximum"):
            AttributeRange("amet", SIT)

    def test_compute(self) -> None:
        medrecord = create_medrecord()

        assert AttributeRange("amet", SIT, minimum=2).compute(medrecord).value == 1
        assert AttributeRange("amet", SIT, maximum=10).compute(medrecord).value == 1
        assert AttributeRange("amet", SIT, 0, 10).compute(medrecord).value == 1
        assert AttributeRange("amet", SIT, 0, 40).compute(medrecord).passed
        assert (
            AttributeRange("amet", SIT, 0, 10).compute(medrecord).requirement_label
            == "none allowed"
        )

    def test_title(self) -> None:
        assert (
            AttributeRange("amet", SIT, 0, 10).title()
            == "Values of amet outside the range"
        )

    def test_parameters(self) -> None:
        assert AttributeRange("amet", SIT, minimum=0).parameters() == {
            "attribute": "amet",
            "minimum": 0,
        }
        assert AttributeRange("amet", SIT, 0, 10).parameters() == {
            "attribute": "amet",
            "minimum": 0,
            "maximum": 10,
        }


class TestAttributeUniqueness(unittest.TestCase):
    def test_compute(self) -> None:
        shared = AttributeUniqueness("id", SIT).compute(create_medrecord())
        unique = AttributeUniqueness("amet", SIT).compute(create_medrecord())

        assert shared.value == 2
        assert not shared.passed
        assert unique.value == 0
        assert unique.passed

    def test_title(self) -> None:
        assert (
            AttributeUniqueness("id", SIT).title() == "Elements sharing a value of id"
        )


class TestAttributeOrder(unittest.TestCase):
    def test_compute(self) -> None:
        on_nodes = AttributeOrder("start", "end", SIT).compute(create_medrecord())
        on_edges = AttributeOrder("start", "end", CONSECTETUR).compute(
            create_medrecord()
        )

        assert on_nodes.value == 1
        assert not on_nodes.passed
        assert on_edges.value == 1
        assert on_nodes.requirement_label == "none allowed"

    def test_title(self) -> None:
        assert AttributeOrder("start", "end", SIT).title() == "Order of start and end"

    def test_description(self) -> None:
        assert (
            AttributeOrder("start", "end", SIT).description()
            == "Elements lacking either attribute are left out."
        )

    def test_parameters(self) -> None:
        assert AttributeOrder("start", "end", CONSECTETUR).parameters() == {
            "earlier": "start",
            "later": "end",
        }


class TestUnlinkedNodes(unittest.TestCase):
    def test_compute(self) -> None:
        targets = UnlinkedNodes(ELIT, CONSECTETUR, EdgeEndpointRole.Target).compute(
            create_medrecord()
        )
        sources = UnlinkedNodes(SIT, CONSECTETUR, EdgeEndpointRole.Source).compute(
            create_medrecord()
        )

        assert targets.value == 1
        assert not targets.passed
        assert sources.value == 2
        assert targets.requirement_label == "none allowed"

    def test_parameters(self) -> None:
        assert UnlinkedNodes(
            ELIT, CONSECTETUR, EdgeEndpointRole.Target
        ).parameters() == {"role": "target"}


if __name__ == "__main__":
    unittest.main()
