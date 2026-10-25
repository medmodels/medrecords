import math
import re
import unittest
from datetime import date, datetime, timedelta
from typing import BinaryIO, Dict, Literal, Mapping, Optional, Union

import polars as pl
import pytest
from graphrecords import QueryError, nodes
from graphrecords.types import Value

from medrecords.evaluation.analytic import (
    Analytic,
    Arrangement,
    Assessment,
    Bins,
    Counts,
    Derivation,
    Detail,
    Distribution,
    Histogram,
    Measurement,
    Plot,
    Scale,
    Scatter,
    Statistics,
    Table,
    Unit,
)
from medrecords.medrecord import MedRecord


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group(
        [("lorem", {"amet": 30}), ("ipsum", {"amet": 50}), ("dolor", {"amet": 70})],
        "Sit",
    )


def create_distribution() -> Distribution:
    return Distribution([4, 1, 3, 2, 10])


def create_statistics() -> Statistics:
    return {
        "count": 5,
        "mean": 4.0,
        "standard_deviation": math.sqrt(12.5),
        "minimum": 1.0,
        "lower_quartile": 2.0,
        "median": 3.0,
        "upper_quartile": 4.0,
        "maximum": 10.0,
    }


def create_histogram() -> Histogram:
    return Histogram(
        [0.0, 5.0, 10.0],
        [4, 1],
        below_count=1,
        above_count=2,
        statistics=create_statistics(),
    )


def create_counts() -> Counts:
    return Counts({"dolor": 2, "elit": 1, None: 1}, 5)


def create_scatter() -> Scatter:
    return Scatter(
        [(0.1, 0.2), (0.5, 0.4), (1.0, 0.9)],
        x_label="share of real patients",
        y_label="share of synthetic patients",
        x_scale=Scale.Logarithmic,
        y_scale=Scale.Logarithmic,
        labels={1: "lorem"},
        diagonal=True,
    )


class AmetCount(Analytic[MedRecord, Value]):
    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        return medrecord.nodes().filter(nodes().in_group("Sit")).count().evaluate()


class Described(Analytic[MedRecord, int]):
    def __init__(self, limit: int) -> None:
        self._limit = limit

    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()

    def title(self) -> Optional[str]:
        return "consectetur"

    def description(self) -> Optional[str]:
        return "adipiscing"

    def parameters(self) -> Mapping[str, Detail]:
        return {"limit": self._limit, "groups": ["Sit", "Elit"]}


class FirstNode(Derivation[MedRecord, MedRecord]):
    def derive(self, medrecord: MedRecord) -> MedRecord:
        return medrecord.keep_nodes(["lorem"])


class Summarized(Derivation[MedRecord, Dict[str, int]]):
    def derive(self, medrecord: MedRecord) -> Dict[str, int]:
        return {"nodes": medrecord.node_count()}

    def titles(
        self, medrecord: MedRecord, derived: Dict[str, int], /
    ) -> Mapping[Value, str]:
        return {"nodes": f"{derived['nodes']} of {medrecord.node_count()} nodes"}

    def parameters(self) -> Mapping[str, Detail]:
        return {"seed": 7}

    def summarize(self, derived: Dict[str, int]) -> Mapping[str, Detail]:
        return {"nodes": derived["nodes"]}


class SavingFigure:
    def __init__(self) -> None:
        self.format = ""
        self.bbox_inches = ""
        self.metadata: Dict[str, Optional[str]] = {}

    def savefig(
        self,
        target: BinaryIO,
        *,
        format: str,
        bbox_inches: Literal["tight"],
        metadata: Dict[str, Optional[str]],
    ) -> None:
        self.format = format
        self.bbox_inches = bbox_inches
        self.metadata = metadata
        target.write(b"<svg/>")


class TestTable(unittest.TestCase):
    def test_init(self) -> None:
        table = Table(["amet", "elit"], [[1, "sed"], [None, 2.5]])

        assert table.headings == ["amet", "elit"]
        assert table.rows == [[1, "sed"], [None, 2.5]]
        assert Table(["entry"], [[("sit", 1)]]).rows == [[("sit", 1)]]
        assert table.units == {}
        assert Table(["amet"], [[0.5]], units={"amet": Unit.Share}).units == {
            "amet": Unit.Share
        }
        assert Table(["amet", 2024], [[1, 0.5]], units={2024: Unit.Share}).units == {
            2024: Unit.Share
        }

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="one cell per heading"):
            Table(["amet"], [[1, 2]])

        with pytest.raises(ValueError, match="every heading must be different"):
            Table(["amet", "amet"], [[1, 2]])

        with pytest.raises(ValueError, match="names the heading 'elit', which"):
            Table(["amet"], [[1]], units={"elit": Unit.Share})

    def test_from_polars(self) -> None:
        dataframe = pl.DataFrame(
            {
                "amet": [1, 2],
                "elit": ["sed", None],
                "dolor": [1.5, 2.5],
                "sit": [True, False],
                "consectetur": [datetime(2026, 9, 2), None],
                "adipiscing": [timedelta(seconds=1), timedelta(days=1)],
            }
        )

        table = Table.from_polars(dataframe)

        assert table.headings == [
            "amet",
            "elit",
            "dolor",
            "sit",
            "consectetur",
            "adipiscing",
        ]
        assert table.rows == [
            [1, "sed", 1.5, True, datetime(2026, 9, 2), timedelta(seconds=1)],
            [2, None, 2.5, False, None, timedelta(days=1)],
        ]
        assert Table.from_polars(table.to_polars()) == table
        assert Table.from_polars(pl.DataFrame({"amet": []})) == Table(["amet"], [])
        assert Table.from_polars(
            pl.DataFrame({"amet": [0.5]}), units={"amet": Unit.Share}
        ) == Table(["amet"], [[0.5]], units={"amet": Unit.Share})

    def test_invalid_from_polars(self) -> None:
        with pytest.raises(TypeError, match=r"column 'amet' holds datetime\.date"):
            Table.from_polars(pl.DataFrame({"amet": [date(2026, 9, 2)]}))

        with pytest.raises(TypeError, match=r"column 'amet' holds \[1\]"):
            Table.from_polars(pl.DataFrame({"amet": [[1]]}))

    def test_invalid_to_polars(self) -> None:
        with pytest.raises(TypeError, match="unexpected value"):
            Table(["amet"], [[1], ["sed"]]).to_polars()

    def test_to_polars(self) -> None:
        dataframe = Table(["amet", "elit"], [[1, "sed"], [2, None]]).to_polars()

        assert dataframe.columns == ["amet", "elit"]
        assert dataframe["amet"].to_list() == [1, 2]
        assert dataframe["elit"].to_list() == ["sed", None]
        assert Table([2024, "amet"], [[1, 2]]).to_polars().columns == ["2024", "amet"]
        assert Table(["entry"], [[("sit", 1)], ["elit"]]).to_polars()[
            "entry"
        ].to_list() == ["sit / 1", "elit"]

    def test_to_polars_holds_integers_beside_floats_as_floats(self) -> None:
        dataframe = Table(["amet", "elit"], [[1, True], [0.5, False]]).to_polars()

        assert dataframe["amet"].to_list() == [1.0, 0.5]
        assert dataframe["amet"].dtype == pl.Float64
        assert dataframe["elit"].to_list() == [True, False]

    def test_headings(self) -> None:
        table = Table(["amet"], [[1]])

        table.headings.append("elit")

        assert table.headings == ["amet"]

    def test_rows(self) -> None:
        table = Table(["amet"], [[1]])

        table.rows.append([2])
        table.rows[0].append(3)

        assert table.rows == [[1]]

    def test_units(self) -> None:
        table = Table(["amet", "elit"], [[0.5, 0.1]], units={"elit": Unit.Points})

        table.units["amet"] = Unit.Share

        assert table.units == {"elit": Unit.Points}

    def test_eq(self) -> None:
        table = Table(["amet"], [[1], [2]])

        assert table == Table(["amet"], [[1], [2]])
        assert table != Table(["amet"], [[1]])
        assert table != Table(["elit"], [[1], [2]])
        assert table != Table(["amet"], [[1], [2]], units={"amet": Unit.Share})
        assert table != "amet"

    def test_repr(self) -> None:
        assert repr(Table(["amet"], [[1]])) == "Table(headings=['amet'], rows=[[1]])"
        assert repr(Table(["amet"], [[1]], units={"amet": Unit.Share})) == (
            "Table(headings=['amet'], rows=[[1]], units={'amet': <Unit.Share: 'share'>})"
        )


class TestPlot(unittest.TestCase):
    def test_init(self) -> None:
        assert Plot("<svg/>").svg == "<svg/>"

    def test_from_figure(self) -> None:
        figure = SavingFigure()

        plot = Plot.from_figure(figure)

        assert plot == Plot("<svg/>")
        assert figure.format == "svg"
        assert figure.bbox_inches == "tight"
        assert figure.metadata == {"Date": None}

    def test_eq(self) -> None:
        assert Plot("<svg/>") == Plot("<svg/>")
        assert Plot("<svg/>") != Plot("<svg></svg>")
        assert Plot("<svg/>") != "<svg/>"

    def test_repr(self) -> None:
        assert repr(Plot("<svg/>")) == "Plot(6 characters of SVG)"


class TestMeasurement(unittest.TestCase):
    def test_init(self) -> None:
        measurement = Measurement(0.87, lower=0.82, upper=0.91, p_value=0.003)

        assert math.isclose(measurement.value, 0.87)
        assert measurement.lower is not None
        assert math.isclose(measurement.lower, 0.82)
        assert measurement.upper is not None
        assert math.isclose(measurement.upper, 0.91)
        assert measurement.p_value is not None
        assert math.isclose(measurement.p_value, 0.003)

        bare = Measurement(3)

        assert bare.value == 3
        assert bare.lower is None
        assert bare.upper is None
        assert bare.p_value is None
        assert bare.unit is None
        assert Measurement(0.5, unit=Unit.Share).unit is Unit.Share

    def test_from_proportion(self) -> None:
        estimate = Measurement.from_proportion(5, 10)

        assert math.isclose(estimate.value, 0.5)
        assert estimate.unit is Unit.Share
        assert estimate.lower is not None
        assert estimate.upper is not None
        assert math.isclose(estimate.lower, 0.2366, abs_tol=1e-3)
        assert math.isclose(estimate.upper, 0.7634, abs_tol=1e-3)
        assert estimate.p_value is None

        none = Measurement.from_proportion(0, 1)
        every = Measurement.from_proportion(1, 1)

        assert math.isclose(none.value, 0.0)
        assert none.lower is not None
        assert math.isclose(none.lower, 0.0)
        assert math.isclose(every.value, 1.0)
        assert every.upper is not None
        assert math.isclose(every.upper, 1.0)

        wider = Measurement.from_proportion(5, 10, confidence=0.99)

        assert wider.lower is not None
        assert wider.lower < 0.2366

    def test_invalid_from_proportion(self) -> None:
        with pytest.raises(ValueError, match="at least one trial"):
            Measurement.from_proportion(0, 0)

        with pytest.raises(ValueError, match="between 0 and 1 successes, got 2"):
            Measurement.from_proportion(2, 1)

        with pytest.raises(ValueError, match="between 0 and 1 successes, got -1"):
            Measurement.from_proportion(-1, 1)

        with pytest.raises(ValueError, match="confidence level between 0 and 1"):
            Measurement.from_proportion(1, 2, confidence=1.0)

    def test_unit(self) -> None:
        assert Measurement(1.0).unit is None
        assert Measurement(0.5, unit=Unit.Points).unit is Unit.Points

    def test_eq(self) -> None:
        assert Measurement(1.0, lower=0.5) == Measurement(1.0, lower=0.5)
        assert Measurement(1.0, lower=0.5) != Measurement(1.0, upper=0.5)
        assert Measurement(1.0) != Measurement(1.0, unit=Unit.Share)
        assert Measurement(1.0) != "sit"

    def test_repr(self) -> None:
        assert (
            repr(Measurement(1.0, p_value=0.5))
            == "Measurement(1.0, lower=None, upper=None, p_value=0.5)"
        )
        assert repr(Measurement(0.5, unit=Unit.Share)) == (
            "Measurement(0.5, lower=None, upper=None, p_value=None, "
            "unit=<Unit.Share: 'share'>)"
        )


class TestAssessment(unittest.TestCase):
    def test_init(self) -> None:
        assessment = Assessment(3, "at least 5", passed=False)

        assert assessment.value == 3
        assert assessment.requirement_label == "at least 5"
        assert not assessment.passed

        dated = Assessment(datetime(2026, 9, 2), "after 2026-01-01", passed=True)

        assert dated.value == datetime(2026, 9, 2)
        assert dated.passed
        assert dated.unit is None

    def test_unit(self) -> None:
        assert Assessment(3, "at least 5", passed=False).unit is None
        assert Assessment(0.5, "at least 50.0%", passed=True, unit=Unit.Share).unit is (
            Unit.Share
        )

    def test_eq(self) -> None:
        assessment = Assessment(3, "at least 5", passed=False)

        assert assessment == Assessment(3, "at least 5", passed=False)
        assert assessment != Assessment(4, "at least 5", passed=False)
        assert assessment != Assessment(3, "at most 5", passed=False)
        assert assessment != Assessment(3, "at least 5", passed=True)
        assert assessment != Assessment(3, "at least 5", passed=False, unit=Unit.Share)
        assert assessment != 3

    def test_repr(self) -> None:
        assert (
            repr(Assessment(3, "at least 5", passed=False))
            == "Assessment(3, 'at least 5', passed=False)"
        )
        assert repr(
            Assessment(0.5, "at least 50.0%", passed=True, unit=Unit.Share)
        ) == (
            "Assessment(0.5, 'at least 50.0%', passed=True, unit=<Unit.Share: 'share'>)"
        )


class TestBins(unittest.TestCase):
    def test_init(self) -> None:
        bins = Bins(count=30, scale=Scale.Logarithmic, outside_share=0.01)

        assert bins.count == 30
        assert bins.scale is Scale.Logarithmic
        assert math.isclose(bins.outside_share or 0.0, 0.01)
        assert Bins().count is None
        assert Bins().scale is None
        assert Bins().outside_share is None
        assert Bins(outside_share=0.0) != Bins()

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="at least one bin"):
            Bins(count=0)

        with pytest.raises(
            ValueError, match=re.escape("outside share from 0 to below 0.5")
        ):
            Bins(outside_share=0.5)

        with pytest.raises(
            ValueError, match=re.escape("outside share from 0 to below 0.5")
        ):
            Bins(outside_share=-0.1)

    def test_count(self) -> None:
        assert Bins(count=4).count == 4

    def test_scale(self) -> None:
        assert Bins(scale=Scale.Linear).scale is Scale.Linear

    def test_outside_share(self) -> None:
        assert math.isclose(Bins(outside_share=0.1).outside_share or 0.0, 0.1)

    def test_describe(self) -> None:
        assert Bins().describe() == "chosen from the values"
        assert Bins(count=30).describe() == (
            "about 30 bars, or one per value for values without decimals that span "
            "at most 120 numbers"
        )
        assert Bins(
            count=4, scale=Scale.Logarithmic, outside_share=0.01
        ).describe() == (
            "about 4 bars, or one per value for values without decimals that span "
            "at most 16 numbers; logarithmic scale; at most 1.0% of the values "
            "outside the axis at each end"
        )

    def test_eq(self) -> None:
        assert Bins(count=4) == Bins(count=4)
        assert Bins(count=4) != Bins(count=5)
        assert Bins(count=4) != Bins(count=4, scale=Scale.Linear)
        assert Bins(count=4) != Bins(count=4, outside_share=0.1)
        assert Bins(count=4) != 4

    def test_hash(self) -> None:
        assert hash(Bins(count=4)) == hash(Bins(count=4))
        assert len({Bins(), Bins(), Bins(count=2)}) == 2

    def test_repr(self) -> None:
        assert repr(Bins(count=4, scale=Scale.Linear)) == (
            "Bins(count=4, scale=<Scale.Linear: 'linear'>, outside_share=None)"
        )


class TestDistribution(unittest.TestCase):
    def test_init(self) -> None:
        distribution = create_distribution()

        assert distribution.values == [4.0, 1.0, 3.0, 2.0, 10.0]
        assert distribution.count == 5
        assert distribution.bins is None
        assert distribution.value_label is None
        assert distribution.count_label is None
        assert distribution.arrangement is None

        distribution.values.append(0.0)

        assert distribution.count == 5

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            Distribution([])

        with pytest.raises(ValueError, match="must be finite"):
            Distribution([1.0, math.nan])

    def test_bins(self) -> None:
        assert Distribution([1.0], bins=Bins(count=4)).bins == Bins(count=4)

    def test_value_label(self) -> None:
        assert Distribution([1.0], value_label="age").value_label == "age"

    def test_count_label(self) -> None:
        assert Distribution([1.0], count_label="patients").count_label == "patients"

    def test_arrangement(self) -> None:
        assert (
            Distribution([1.0], arrangement=Arrangement.Panels).arrangement
            is Arrangement.Panels
        )

    def test_mean(self) -> None:
        assert math.isclose(create_distribution().mean, 4.0)

    def test_std(self) -> None:
        assert math.isclose(create_distribution().standard_deviation, math.sqrt(12.5))
        assert math.isclose(Distribution([2.0]).standard_deviation, 0.0)

    def test_minimum(self) -> None:
        assert math.isclose(create_distribution().minimum, 1.0)

    def test_lower_quartile(self) -> None:
        assert math.isclose(create_distribution().lower_quartile, 2.0)
        assert math.isclose(Distribution([1.0, 2.0]).lower_quartile, 1.25)

    def test_median(self) -> None:
        assert math.isclose(create_distribution().median, 3.0)
        assert math.isclose(Distribution([1.0, 2.0]).median, 1.5)

    def test_upper_quartile(self) -> None:
        assert math.isclose(create_distribution().upper_quartile, 4.0)
        assert math.isclose(Distribution([1.0, 2.0]).upper_quartile, 1.75)

    def test_maximum(self) -> None:
        assert math.isclose(create_distribution().maximum, 10.0)

    def test_statistics(self) -> None:
        statistics = create_distribution().statistics

        assert statistics == create_statistics()
        assert statistics["count"] == 5
        assert math.isclose(statistics["standard_deviation"], math.sqrt(12.5))

    def test_histogram(self) -> None:
        histogram = create_distribution().histogram()

        assert histogram.edges == [
            0.5,
            1.5,
            2.5,
            3.5,
            4.5,
            5.5,
            6.5,
            7.5,
            8.5,
            9.5,
            10.5,
        ]
        assert histogram.counts == [1, 1, 1, 1, 0, 0, 0, 0, 0, 1]
        assert histogram.scale is Scale.Linear
        assert histogram.statistics == create_statistics()
        assert create_distribution().histogram(Bins(count=2)).edges == [
            0.5,
            1.5,
            4.5,
            13.5,
        ]

        labelled = Distribution(
            [1.0],
            value_label="age",
            count_label="patients",
            arrangement=Arrangement.Overlay,
        ).histogram()

        assert labelled.value_label == "age"
        assert labelled.count_label == "patients"
        assert labelled.arrangement is Arrangement.Overlay

    def test_shared_histograms(self) -> None:
        assert [
            histogram.counts
            for histogram in Distribution.shared_histograms(
                [Distribution([1.0, 2.0]), Distribution([2.0, 3.0])]
            )
        ] == [[1, 1, 0], [0, 1, 1]]
        assert Distribution.shared_histograms([create_distribution()]) == [
            create_distribution().histogram()
        ]

        logarithmic = Bins(scale=Scale.Logarithmic)
        assert Distribution.shared_histograms(
            [Distribution([1.0, 2.0, 3.0, 9.0], bins=logarithmic)]
        )[0].edges == [0.5, 1.5, 4.5, 13.5]
        assert Distribution.shared_histograms(
            [Distribution([0.0, 0.0], bins=logarithmic)]
        )[0].edges == [-0.5, 0.5]

        counted = Distribution.shared_histograms(
            [Distribution(range(21))], Bins(count=2)
        )[0]

        assert counted.scale is Scale.Logarithmic
        assert counted.edges == [0.5, 1.5, 4.5, 13.5, 40.5]
        assert counted.counts == [1, 3, 9, 7]
        assert counted.below_count == 1

        wide = Distribution.shared_histograms(
            [Distribution(range(21))], Bins(count=2, scale=Scale.Linear)
        )[0]

        assert wide.scale is Scale.Linear
        assert wide.edges == [-0.5, 0.5, 10.5, 20.5]
        assert wide.counts == [1, 10, 10]
        assert wide.below_count == 0
        assert Distribution.shared_histograms(
            [Distribution(range(1, 21))], Bins(count=2, scale=Scale.Linear)
        )[0].edges == [0.5, 10.5, 20.5]
        assert Distribution.shared_histograms(
            [Distribution(range(-10, 11))], Bins(count=2)
        )[0].edges == [-20.5, -0.5, 19.5]
        assert Distribution.shared_histograms(
            [Distribution(range(37, 200))], Bins(count=2, scale=Scale.Logarithmic)
        )[0].edges == [13.5, 40.5, 121.5, 364.5]
        assert Distribution.shared_histograms(
            [Distribution([value + 0.5 for value in range(10)])], Bins(count=5)
        )[0].edges == [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]

        tailed = Distribution(
            [0.1, 0.2, 0.5, 1.5, 3.3, 10.5, 40.5, 100.5, 900.5, 5000.5]
        ).histogram()

        assert tailed.scale is Scale.Logarithmic
        assert [round(edge, 9) for edge in tailed.edges] == [
            0.1,
            1.0,
            10.0,
            100.0,
            1000.0,
            10000.0,
        ]
        assert tailed.counts == [3, 2, 2, 2, 1]
        assert Distribution(
            [-1000.5, -10.5, -1.5, -0.5, 0.5, 1.5, 10.5, 1000.5]
        ).histogram().edges == [-2000.0, -1000.0, 0.0, 1000.0, 2000.0]
        assert Distribution([1.5, 2.5, 3.5]).histogram(
            Bins(count=2, scale=Scale.Logarithmic)
        ).edges == [1.0, 5.0]
        assert (
            Distribution([-1.5, -2.5]).histogram(Bins(scale=Scale.Logarithmic)).scale
            is Scale.Linear
        )
        assert (
            Distribution([-1.5, 0.5, 0.5])
            .histogram(Bins(scale=Scale.Logarithmic))
            .scale
            is Scale.Linear
        )
        assert Distribution([1.5] * 999 + [1000.5, 0.1]).histogram().edges == [1.4, 1.6]
        assert Distribution([2.5]).histogram().edges == [2.25, 2.75]
        assert Distribution([-0.5] + [0.0] * 500 + [0.5]).histogram().edges == [
            -0.5,
            0.5,
        ]

        trimmed = Distribution([0.5, 0.25, *[1.5] * 1000, 9.5])

        assert trimmed.histogram().edges == [1.4, 1.6]
        assert trimmed.histogram().below_count == 2
        assert trimmed.histogram().above_count == 1
        assert (
            Distribution(trimmed.values, bins=Bins(outside_share=0.0))
            .histogram()
            .below_count
            == 0
        )
        assert Distribution.shared_histograms(
            [
                Distribution([1.0, 2.0], bins=Bins(count=1)),
                Distribution([1.0, 2.0], bins=Bins(count=8)),
            ],
            Bins(outside_share=0.0),
        )[0].edges == [0.5, 1.5, 2.5]
        assert (
            Distribution.shared_histograms(
                [
                    Distribution([1.5], bins=Bins(scale=Scale.Linear)),
                    Distribution([2.5], bins=Bins(scale=Scale.Logarithmic)),
                ],
                Bins(scale=Scale.Linear),
            )[0].scale
            is Scale.Linear
        )
        assert Distribution.shared_histograms(
            [
                Distribution([1.5], bins=Bins(outside_share=0.0)),
                Distribution([2.5], bins=Bins(outside_share=0.1)),
            ],
            Bins(outside_share=0.0),
        )[0].edges == [1.0, 2.0, 3.0]

    def test_invalid_shared_histograms(self) -> None:
        with pytest.raises(ValueError, match="at least one distribution"):
            Distribution.shared_histograms([])

        with pytest.raises(ValueError, match="declare different scales"):
            Distribution.shared_histograms(
                [
                    Distribution([1.5], bins=Bins(scale=Scale.Linear)),
                    Distribution([2.5], bins=Bins(scale=Scale.Logarithmic)),
                ]
            )

        with pytest.raises(ValueError, match="declare different outside shares"):
            Distribution.shared_histograms(
                [
                    Distribution([1.5], bins=Bins(outside_share=0.0)),
                    Distribution([2.5], bins=Bins(outside_share=0.1)),
                ]
            )

    def test_agreeing(self) -> None:
        linear = Distribution([1.0], bins=Bins(scale=Scale.Linear))
        logarithmic = Distribution([1.0], bins=Bins(scale=Scale.Logarithmic))
        trimmed = Distribution([1.0], bins=Bins(outside_share=0.1))
        untrimmed = Distribution([1.0], bins=Bins(outside_share=0.0))

        assert Distribution._agreeing([linear, linear, Distribution([2.0])])
        assert Distribution._agreeing([trimmed, Distribution([2.0], bins=Bins())])
        assert not Distribution._agreeing([linear, logarithmic])
        assert not Distribution._agreeing([trimmed, untrimmed])

    def test_eq(self) -> None:
        assert create_distribution() == Distribution([4, 1, 3, 2, 10])
        assert create_distribution() != Distribution([1, 2, 3, 4, 10])
        assert create_distribution() != Distribution(
            [4, 1, 3, 2, 10], bins=Bins(count=4)
        )
        assert create_distribution() != Distribution([4, 1, 3, 2, 10], value_label="a")
        assert create_distribution() != Distribution([4, 1, 3, 2, 10], count_label="a")
        assert create_distribution() != Distribution(
            [4, 1, 3, 2, 10], arrangement=Arrangement.Panels
        )
        assert create_distribution() != [4, 1, 3, 2, 10]

    def test_repr(self) -> None:
        assert repr(create_distribution()) == "Distribution(5 values)"


class TestHistogram(unittest.TestCase):
    def test_init(self) -> None:
        histogram = create_histogram()

        assert histogram.edges == [0.0, 5.0, 10.0]
        assert histogram.counts == [4, 1]
        assert histogram.below_count == 1
        assert histogram.above_count == 2
        assert histogram.statistics == create_statistics()
        assert Histogram([0, 1], [0]).statistics is None
        assert Histogram([0, 1], [0]).count == 0
        assert Histogram([0, 1], [0]).edges == [0.0, 1.0]
        assert histogram.scale is Scale.Linear
        assert histogram.value_label is None
        assert histogram.count_label is None
        assert histogram.arrangement is None

        histogram.edges.append(15.0)
        histogram.counts.append(0)

        assert histogram.edges == [0.0, 5.0, 10.0]
        assert histogram.counts == [4, 1]

        statistics = create_statistics()
        statistics["count"] = 9
        histogram = Histogram([0.0, 1.0], [1], statistics=statistics)
        statistics["count"] = 1

        assert histogram.statistics is not None
        assert histogram.statistics["count"] == 9

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="at least two edges"):
            Histogram([1.0], [])

        with pytest.raises(
            ValueError, match="every edge of a histogram must be finite"
        ):
            Histogram([0.0, math.inf], [1])

        with pytest.raises(ValueError, match="edges of a histogram must be increasing"):
            Histogram([0.0, 5.0, 5.0], [1, 1])

        with pytest.raises(ValueError, match="one count per bin"):
            Histogram([0.0, 5.0, 10.0], [1])

        with pytest.raises(ValueError, match="must be zero or more"):
            Histogram([0.0, 5.0], [-1])

        with pytest.raises(ValueError, match="must be zero or more"):
            Histogram([0.0, 5.0], [1], below_count=-1)

        with pytest.raises(ValueError, match="must be zero or more"):
            Histogram([0.0, 5.0], [1], above_count=-1)

        with pytest.raises(ValueError, match="logarithmic histogram must be above"):
            Histogram([0.0, 5.0], [1], scale=Scale.Logarithmic)

    def test_from_values(self) -> None:
        assert Histogram.from_values([4, 1, 3, 2, 10], [0.0, 5.0, 10.0]) == Histogram(
            [0.0, 5.0, 10.0], [4, 1], statistics=create_statistics()
        )
        assert Histogram.from_values([4, 1, 3, 2, 10], [2.0, 4.0]) == Histogram(
            [2.0, 4.0],
            [3],
            below_count=1,
            above_count=1,
            statistics=create_statistics(),
        )
        assert Histogram.from_values([0.0, 5.0, 10.0], [0.0, 5.0, 10.0]).counts == [
            1,
            2,
        ]
        assert Histogram.from_values([], [0.0, 5.0, 10.0]) == Histogram(
            [0.0, 5.0, 10.0], [0, 0]
        )
        assert Histogram.from_values(
            [2.0, 20.0],
            [1.0, 10.0, 100.0],
            scale=Scale.Logarithmic,
            value_label="dose in mg",
            count_label="prescriptions",
            arrangement=Arrangement.Panels,
        ) == Histogram(
            [1.0, 10.0, 100.0],
            [1, 1],
            statistics=Distribution([2.0, 20.0]).statistics,
            scale=Scale.Logarithmic,
            value_label="dose in mg",
            count_label="prescriptions",
            arrangement=Arrangement.Panels,
        )
        assert Histogram.from_values(
            [], [1.0, 10.0], scale=Scale.Logarithmic, value_label="dose in mg"
        ) == Histogram(
            [1.0, 10.0], [0], scale=Scale.Logarithmic, value_label="dose in mg"
        )

    def test_invalid_from_values(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            Histogram.from_values([math.nan], [0.0, 1.0])

        with pytest.raises(ValueError, match="at least two edges"):
            Histogram.from_values([1.0], [0.0])

        with pytest.raises(ValueError, match="at least two edges"):
            Histogram.from_values([], [])

    def test_edges(self) -> None:
        assert create_histogram().edges == [0.0, 5.0, 10.0]

    def test_counts(self) -> None:
        assert create_histogram().counts == [4, 1]

    def test_below_count(self) -> None:
        assert create_histogram().below_count == 1

    def test_above_count(self) -> None:
        assert create_histogram().above_count == 2

    def test_statistics(self) -> None:
        assert create_histogram().statistics == create_statistics()
        assert Histogram([0.0, 1.0], [0]).statistics is None

    def test_scale(self) -> None:
        assert (
            Histogram([1.0, 2.0], [1], scale=Scale.Logarithmic).scale
            is Scale.Logarithmic
        )

    def test_value_label(self) -> None:
        assert Histogram([1.0, 2.0], [1], value_label="days").value_label == "days"

    def test_count_label(self) -> None:
        assert (
            Histogram([1.0, 2.0], [1], count_label="intervals").count_label
            == "intervals"
        )

    def test_arrangement(self) -> None:
        assert (
            Histogram([1.0, 2.0], [1], arrangement=Arrangement.Overlay).arrangement
            is Arrangement.Overlay
        )

    def test_count(self) -> None:
        assert create_histogram().count == 8

    def test_bins(self) -> None:
        assert create_histogram().bins == [
            {"lower": 0.0, "upper": 5.0, "count": 4},
            {"lower": 5.0, "upper": 10.0, "count": 1},
        ]

    def test_to_polars(self) -> None:
        dataframe = create_histogram().to_polars()

        assert dataframe.columns == ["lower", "upper", "count"]
        assert dataframe.rows() == [(0.0, 5.0, 4), (5.0, 10.0, 1)]

    def test_eq(self) -> None:
        histogram = create_histogram()

        assert histogram == create_histogram()
        assert histogram != Histogram(
            [0.0, 5.0, 11.0],
            [4, 1],
            below_count=1,
            above_count=2,
            statistics=create_statistics(),
        )
        assert histogram != Histogram(
            [0.0, 5.0, 10.0],
            [4, 2],
            below_count=1,
            above_count=2,
            statistics=create_statistics(),
        )
        assert histogram != Histogram(
            [0.0, 5.0, 10.0],
            [4, 1],
            below_count=0,
            above_count=2,
            statistics=create_statistics(),
        )
        assert histogram != Histogram(
            [0.0, 5.0, 10.0],
            [4, 1],
            below_count=1,
            above_count=0,
            statistics=create_statistics(),
        )
        assert histogram != Histogram(
            [0.0, 5.0, 10.0], [4, 1], below_count=1, above_count=2
        )
        assert Histogram([1.0, 2.0], [1]) != Histogram(
            [1.0, 2.0], [1], scale=Scale.Logarithmic
        )
        assert Histogram([1.0, 2.0], [1]) != Histogram(
            [1.0, 2.0], [1], value_label="days"
        )
        assert Histogram([1.0, 2.0], [1]) != Histogram(
            [1.0, 2.0], [1], count_label="intervals"
        )
        assert Histogram([1.0, 2.0], [1]) != Histogram(
            [1.0, 2.0], [1], arrangement=Arrangement.Panels
        )
        assert histogram != [4, 1]

    def test_repr(self) -> None:
        assert repr(create_histogram()) == "Histogram(2 bins, 8 values)"


class TestCounts(unittest.TestCase):
    def test_init(self) -> None:
        counts = create_counts()

        assert counts.by_value == {"dolor": 2, "elit": 1, None: 1}
        assert counts.total == 5
        assert Counts({"dolor": 2}).total == 2
        assert Counts({}).total == 0
        assert counts.value_label is None
        assert counts.count_label is None
        assert counts.remainder_label is None
        assert counts.arrangement is None

        counts.by_value["sit"] = 3

        assert counts.by_value == {"dolor": 2, "elit": 1, None: 1}

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="every count must be zero or more"):
            Counts({"dolor": -1})

        with pytest.raises(ValueError, match="at least the sum of the counts"):
            Counts({"dolor": 2, "elit": 1}, 2)

    def test_by_value(self) -> None:
        assert create_counts().by_value == {"dolor": 2, "elit": 1, None: 1}

    def test_total(self) -> None:
        assert create_counts().total == 5

    def test_value_label(self) -> None:
        assert Counts({}, value_label="diagnosis").value_label == "diagnosis"

    def test_count_label(self) -> None:
        assert Counts({}, count_label="patients").count_label == "patients"

    def test_remainder_label(self) -> None:
        assert Counts({}, remainder_label="rarer").remainder_label == "rarer"

    def test_arrangement(self) -> None:
        assert (
            Counts({}, arrangement=Arrangement.Panels).arrangement is Arrangement.Panels
        )

    def test_to_table(self) -> None:
        assert create_counts().to_table() == Table(
            ["value", "count", "share"],
            [["dolor", 2, 0.4], ["elit", 1, 0.2], [None, 1, 0.2]],
            units={"share": Unit.Share},
        )
        assert Counts({"dolor": 0}).to_table() == Table(
            ["value", "count", "share"],
            [["dolor", 0, None]],
            units={"share": Unit.Share},
        )

    def test_to_polars(self) -> None:
        dataframe = create_counts().to_polars()

        assert dataframe.columns == ["value", "count", "share"]
        assert dataframe.rows() == [("dolor", 2, 0.4), ("elit", 1, 0.2), (None, 1, 0.2)]

    def test_eq(self) -> None:
        counts = create_counts()

        assert counts == Counts({"dolor": 2, "elit": 1, None: 1}, 5)
        assert counts != Counts({"elit": 1, "dolor": 2, None: 1}, 5)
        assert counts != Counts({"dolor": 2, "elit": 1, None: 1}, 6)
        assert counts != Counts({"dolor": 2, "elit": 1}, 5)
        assert Counts({}) != Counts({}, value_label="diagnosis")
        assert Counts({}) != Counts({}, count_label="patients")
        assert Counts({}) != Counts({}, remainder_label="rarer")
        assert Counts({}) != Counts({}, arrangement=Arrangement.Overlay)
        assert counts != {"dolor": 2, "elit": 1, None: 1}

    def test_repr(self) -> None:
        assert repr(create_counts()) == "Counts(3 values of 5)"


class TestScatter(unittest.TestCase):
    def test_init(self) -> None:
        scatter = create_scatter()

        assert scatter.points == [(0.1, 0.2), (0.5, 0.4), (1.0, 0.9)]
        assert scatter.x_label == "share of real patients"
        assert scatter.y_label == "share of synthetic patients"
        assert scatter.x_scale is Scale.Logarithmic
        assert scatter.y_scale is Scale.Logarithmic
        assert scatter.labels == {1: "lorem"}
        assert scatter.diagonal is True

        bare = Scatter([(1, 2)], x_label="x", y_label="y")

        assert bare.points == [(1.0, 2.0)]
        assert bare.x_scale is Scale.Linear
        assert bare.y_scale is Scale.Linear
        assert bare.labels == {}
        assert bare.diagonal is False

        scatter.points.append((2.0, 2.0))
        scatter.labels[0] = "ipsum"

        assert len(scatter.points) == 3
        assert scatter.labels == {1: "lorem"}

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="every coordinate of a scatter"):
            Scatter([(math.nan, 1.0)], x_label="x", y_label="y")

        with pytest.raises(ValueError, match="every coordinate of a scatter"):
            Scatter([(1.0, math.inf)], x_label="x", y_label="y")

        with pytest.raises(ValueError, match="names the point 1, which"):
            Scatter([(1.0, 1.0)], x_label="x", y_label="y", labels={1: "lorem"})

        with pytest.raises(ValueError, match="names the point -1, which"):
            Scatter([(1.0, 1.0)], x_label="x", y_label="y", labels={-1: "lorem"})

    def test_points(self) -> None:
        assert create_scatter().points[0] == (0.1, 0.2)

    def test_x_label(self) -> None:
        assert create_scatter().x_label == "share of real patients"

    def test_y_label(self) -> None:
        assert create_scatter().y_label == "share of synthetic patients"

    def test_x_scale(self) -> None:
        assert create_scatter().x_scale is Scale.Logarithmic

    def test_y_scale(self) -> None:
        assert create_scatter().y_scale is Scale.Logarithmic

    def test_labels(self) -> None:
        assert create_scatter().labels == {1: "lorem"}

    def test_to_polars(self) -> None:
        dataframe = create_scatter().to_polars()

        assert dataframe.columns == ["x", "y", "label"]
        assert dataframe.rows() == [
            (0.1, 0.2, None),
            (0.5, 0.4, "lorem"),
            (1.0, 0.9, None),
        ]
        assert Scatter([], x_label="x", y_label="y").to_polars().schema == {
            "x": pl.Float64,
            "y": pl.Float64,
            "label": pl.String,
        }

    def test_eq(self) -> None:
        scatter = create_scatter()

        assert scatter == create_scatter()
        assert scatter != Scatter(
            [(0.1, 0.2)],
            x_label="share of real patients",
            y_label="share of synthetic patients",
            x_scale=Scale.Logarithmic,
            y_scale=Scale.Logarithmic,
            diagonal=True,
        )
        assert Scatter([], x_label="x", y_label="y") != Scatter(
            [], x_label="a", y_label="y"
        )
        assert Scatter([], x_label="x", y_label="y") != Scatter(
            [], x_label="x", y_label="y", diagonal=True
        )
        assert Scatter([], x_label="x", y_label="y") != Scatter(
            [], x_label="x", y_label="a"
        )
        assert Scatter([], x_label="x", y_label="y") != Scatter(
            [], x_label="x", y_label="y", x_scale=Scale.Logarithmic
        )
        assert Scatter([], x_label="x", y_label="y") != Scatter(
            [], x_label="x", y_label="y", y_scale=Scale.Logarithmic
        )
        assert Scatter([(1.0, 1.0)], x_label="x", y_label="y") != Scatter(
            [(1.0, 1.0)], x_label="x", y_label="y", labels={0: "lorem"}
        )
        assert scatter != [(0.1, 0.2)]

    def test_repr(self) -> None:
        assert repr(create_scatter()) == "Scatter(3 points, 1 labelled)"


class TestAnalytic(unittest.TestCase):
    def test_compute(self) -> None:
        assert AmetCount().compute(create_medrecord()) == 3
        assert Described(2).compute(create_medrecord()) == 3

    def test_title(self) -> None:
        assert AmetCount().title() is None
        assert Described(2).title() == "consectetur"

    def test_description(self) -> None:
        assert AmetCount().description() is None
        assert Described(2).description() == "adipiscing"

    def test_parameters(self) -> None:
        assert AmetCount().parameters() == {}
        assert Described(2).parameters() == {"limit": 2, "groups": ["Sit", "Elit"]}


class TestDerivation(unittest.TestCase):
    def test_derive(self) -> None:
        assert FirstNode().derive(create_medrecord()).node_indices() == ["lorem"]
        assert Summarized().derive(create_medrecord()) == {"nodes": 3}

    def test_parameters(self) -> None:
        assert FirstNode().parameters() == {}
        assert Summarized().parameters() == {"seed": 7}

    def test_titles(self) -> None:
        assert FirstNode().titles(create_medrecord(), create_medrecord()) == {}
        assert Summarized().titles(create_medrecord(), {"nodes": 1}) == {
            "nodes": "1 of 3 nodes"
        }

    def test_summarize(self) -> None:
        assert FirstNode().summarize(create_medrecord()) == {}
        assert Summarized().summarize({"nodes": 3}) == {"nodes": 3}


if __name__ == "__main__":
    unittest.main()
