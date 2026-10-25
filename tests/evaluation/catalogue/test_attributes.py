import math
import unittest

import pytest
from graphrecords import edges, nodes

from medrecords.evaluation.analytic import (
    Assessment,
    Bins,
    Counts,
    Histogram,
    Scale,
    Unit,
)
from medrecords.evaluation.catalogue.attributes import (
    AttributeCompleteness,
    AttributeCounts,
    AttributeDistribution,
    AttributeHistogram,
    AttributeMax,
    AttributeMean,
    AttributeMedian,
    AttributeMin,
    AttributeStd,
    AttributeSum,
    AttributeUniqueValues,
)
from medrecords.medrecord import MedRecord

CONSECTETUR = nodes().filter(nodes().in_group("Consectetur"))
ADIPISCING = edges().filter(edges().in_group("Adipiscing"))
VACANT = nodes().filter(nodes().in_group("Vacant"))


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes_in_group(
            [
                ("lorem", {"amet": 1, "sit": "dolor"}),
                ("ipsum", {"amet": 3, "sit": "dolor"}),
                ("dolor", {"amet": 5, "sit": "elit"}),
                ("sit", {"sit": "elit"}),
            ],
            "Consectetur",
        )
        .add_nodes([("elit", {"amet": 7})])
        .add_edges_in_group(
            [("lorem", "ipsum", {"amet": 2.5}), ("ipsum", "dolor", {})], "Adipiscing"
        )
        .add_group("Vacant")
    )


class TestAttributeAnalytic(unittest.TestCase):
    def test_parameters(self) -> None:
        assert AttributeMean("amet", ADIPISCING).parameters() == {"attribute": "amet"}


class TestAttributeMean(unittest.TestCase):
    def test_compute(self) -> None:
        assert AttributeMean("amet", CONSECTETUR).compute(create_medrecord()) == 3
        assert AttributeMean("amet", nodes()).compute(create_medrecord()) == 4
        assert AttributeMean("missing", nodes()).compute(create_medrecord()) is None

        dose = AttributeMean("amet", ADIPISCING).compute(create_medrecord())

        assert isinstance(dose, float)
        assert math.isclose(dose, 2.5)

    def test_title(self) -> None:
        assert AttributeMean("amet", nodes()).title() == "Mean amet"


class TestAttributeMedian(unittest.TestCase):
    def test_compute(self) -> None:
        assert AttributeMedian("amet", CONSECTETUR).compute(create_medrecord()) == 3

    def test_title(self) -> None:
        assert AttributeMedian("amet", nodes()).title() == "Median amet"


class TestAttributeStd(unittest.TestCase):
    def test_compute(self) -> None:
        deviation = AttributeStd("amet", CONSECTETUR).compute(create_medrecord())

        assert isinstance(deviation, float)
        assert math.isclose(deviation, 2.0)

    def test_title(self) -> None:
        assert AttributeStd("amet", nodes()).title() == "Standard deviation of amet"


class TestAttributeMin(unittest.TestCase):
    def test_compute(self) -> None:
        assert AttributeMin("amet", CONSECTETUR).compute(create_medrecord()) == 1

    def test_title(self) -> None:
        assert AttributeMin("amet", nodes()).title() == "Smallest amet"


class TestAttributeMax(unittest.TestCase):
    def test_compute(self) -> None:
        assert AttributeMax("amet", CONSECTETUR).compute(create_medrecord()) == 5

    def test_title(self) -> None:
        assert AttributeMax("amet", nodes()).title() == "Largest amet"


class TestAttributeSum(unittest.TestCase):
    def test_compute(self) -> None:
        assert AttributeSum("amet", CONSECTETUR).compute(create_medrecord()) == 9

    def test_title(self) -> None:
        assert AttributeSum("amet", nodes()).title() == "Sum of amet"


class TestAttributeDistribution(unittest.TestCase):
    def test_init(self) -> None:
        distribution = AttributeDistribution(
            "amet", CONSECTETUR, bins=Bins(count=4)
        ).compute(create_medrecord())

        assert distribution.bins == Bins(count=4)

    def test_compute(self) -> None:
        distribution = AttributeDistribution("amet", CONSECTETUR).compute(
            create_medrecord()
        )

        assert sorted(distribution.values) == [1.0, 3.0, 5.0]
        assert math.isclose(distribution.mean, 3.0)
        assert distribution.bins is None
        assert distribution.value_label == "amet"

    def test_invalid_compute(self) -> None:
        with pytest.raises(TypeError, match="expected float"):
            AttributeDistribution("sit", CONSECTETUR).compute(create_medrecord())

        with pytest.raises(ValueError, match="at least one value"):
            AttributeDistribution("missing", nodes()).compute(create_medrecord())

    def test_title(self) -> None:
        assert AttributeDistribution("amet", nodes()).title() == "Distribution of amet"


class TestAttributeHistogram(unittest.TestCase):
    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="at least two edges"):
            AttributeHistogram("amet", nodes(), [0.0])

        with pytest.raises(ValueError, match="must be finite"):
            AttributeHistogram("amet", nodes(), [0.0, math.inf])

        with pytest.raises(ValueError, match="must be increasing"):
            AttributeHistogram("amet", nodes(), [1.0, 0.0])

    def test_init(self) -> None:
        histogram = AttributeHistogram(
            "amet", CONSECTETUR, [1, 10, 100], scale=Scale.Logarithmic
        ).compute(create_medrecord())

        assert histogram.scale is Scale.Logarithmic
        assert histogram.counts == [3, 0]

    def test_compute(self) -> None:
        histogram = AttributeHistogram("amet", CONSECTETUR, [0.0, 2.0, 4.0]).compute(
            create_medrecord()
        )

        assert histogram.edges == [0.0, 2.0, 4.0]
        assert histogram.counts == [1, 1]
        assert histogram.below_count == 0
        assert histogram.above_count == 1
        assert histogram.statistics is not None
        assert math.isclose(histogram.statistics["mean"], 3.0)
        assert histogram.scale is Scale.Linear
        assert histogram.value_label == "amet"
        assert AttributeHistogram("missing", nodes(), [0.0, 1.0]).compute(
            create_medrecord()
        ) == Histogram([0.0, 1.0], [0], value_label="missing")

    def test_invalid_compute(self) -> None:
        with pytest.raises(TypeError, match="expected float"):
            AttributeHistogram("sit", CONSECTETUR, [0.0, 1.0]).compute(
                create_medrecord()
            )

    def test_title(self) -> None:
        assert AttributeHistogram("amet", nodes(), [0.0, 1.0]).title() == (
            "Distribution of amet"
        )

    def test_parameters(self) -> None:
        assert AttributeHistogram("amet", nodes(), [10, 20]).parameters() == {
            "attribute": "amet",
            "edges": [10, 20],
        }


class TestAttributeCounts(unittest.TestCase):
    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="limit of at least one, got 0"):
            AttributeCounts("sit", CONSECTETUR, 0)

    def test_compute(self) -> None:
        counts = AttributeCounts("sit", CONSECTETUR).compute(create_medrecord())

        assert counts.by_value == {"dolor": 2, "elit": 2}
        assert counts.total == 4
        assert counts.value_label == "sit"
        assert counts.remainder_label is None

        ranked = AttributeCounts("amet", nodes()).compute(
            create_medrecord().add_nodes([("nona", {"amet": 5}), ("deca", {"amet": 5})])
        )

        assert next(iter(ranked.by_value)) == 5
        assert list(ranked.by_value.values()) == [3, 1, 1, 1]

        limited = AttributeCounts("amet", CONSECTETUR, 1).compute(create_medrecord())

        assert len(limited.by_value) == 1
        assert list(limited.by_value.values()) == [1]
        assert limited.total == 3
        assert limited.remainder_label == "less frequent values"
        assert AttributeCounts("missing", nodes()).compute(create_medrecord()) == (
            Counts({}, value_label="missing")
        )

    def test_title(self) -> None:
        assert AttributeCounts("sit", nodes()).title() == "Values of sit"

    def test_description(self) -> None:
        assert AttributeCounts("sit", nodes()).description() == (
            "Shares are of the entries that carry sit."
        )

    def test_parameters(self) -> None:
        assert AttributeCounts("sit", nodes()).parameters() == {"attribute": "sit"}
        assert AttributeCounts("sit", CONSECTETUR, 3).parameters() == {
            "attribute": "sit",
            "limit": 3,
        }


class TestAttributeUniqueValues(unittest.TestCase):
    def test_compute(self) -> None:
        assert (
            AttributeUniqueValues("sit", CONSECTETUR).compute(create_medrecord()) == 2
        )
        assert AttributeUniqueValues("amet", nodes()).compute(create_medrecord()) == 4

    def test_title(self) -> None:
        assert (
            AttributeUniqueValues("sit", nodes()).title() == "Different values of sit"
        )


class TestAttributeCompleteness(unittest.TestCase):
    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match=r"between 0 and 1, got 1\.5"):
            AttributeCompleteness("amet", CONSECTETUR, 1.5)

    def test_compute(self) -> None:
        share = AttributeCompleteness("amet", CONSECTETUR).compute(create_medrecord())

        assert isinstance(share, float)
        assert math.isclose(share, 0.75)

        on_edges = AttributeCompleteness("amet", ADIPISCING).compute(create_medrecord())

        assert isinstance(on_edges, float)
        assert math.isclose(on_edges, 0.5)

        passed = AttributeCompleteness("amet", CONSECTETUR, 0.5).compute(
            create_medrecord()
        )
        failed = AttributeCompleteness("amet", CONSECTETUR, 0.8).compute(
            create_medrecord()
        )

        assert isinstance(passed, Assessment)
        assert isinstance(failed, Assessment)
        assert isinstance(passed.value, float)
        assert math.isclose(passed.value, 0.75)
        assert passed.requirement_label == "at least 50.0%"
        assert passed.unit is Unit.Share
        assert passed.passed
        assert not failed.passed
        assert failed.requirement_label == "at least 80.0%"
        assert failed.unit is Unit.Share

    def test_invalid_compute(self) -> None:
        with pytest.raises(ValueError, match="on no elements"):
            AttributeCompleteness("amet", VACANT).compute(create_medrecord())

    def test_title(self) -> None:
        assert AttributeCompleteness("amet", nodes()).title() == "Completeness of amet"

    def test_description(self) -> None:
        assert (
            AttributeCompleteness("amet", nodes()).description()
            == "The share of entries with a value of amet."
        )

    def test_parameters(self) -> None:
        assert AttributeCompleteness("amet", CONSECTETUR).parameters() == {
            "attribute": "amet"
        }
        assert AttributeCompleteness("amet", CONSECTETUR, 0.5).parameters() == {
            "attribute": "amet",
            "minimum": 0.5,
        }


if __name__ == "__main__":
    unittest.main()
