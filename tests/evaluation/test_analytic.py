import math
import unittest
from datetime import date, datetime, timedelta
from typing import BinaryIO, Dict, Literal, Mapping, Optional, Union

import polars as pl
import pytest
from graphrecords import QueryError, nodes
from graphrecords.types import Value

from medrecords.evaluation.analytic import (
    Analytic,
    Assessment,
    Derivation,
    Detail,
    Distribution,
    Measurement,
    Plot,
    Table,
)
from medrecords.medrecord import MedRecord


def create_medrecord() -> MedRecord:
    return MedRecord().add_nodes_in_group(
        [("lorem", {"amet": 30}), ("ipsum", {"amet": 50}), ("dolor", {"amet": 70})],
        "Sit",
    )


def create_distribution() -> Distribution:
    return Distribution([4, 1, 3, 2, 10])


class AmetCount(Analytic[MedRecord]):
    def compute(self, medrecord: MedRecord) -> Union[Value, QueryError]:
        return medrecord.nodes().filter(nodes().in_group("Sit")).count().evaluate()


class Described(Analytic[MedRecord]):
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

    def parameters(self) -> Mapping[str, Detail]:
        return {"seed": 7}

    def summarize(self, derived: Dict[str, int]) -> Mapping[str, Detail]:
        return {"nodes": derived["nodes"]}


class SavingFigure:
    def __init__(self) -> None:
        self.format = ""
        self.bbox_inches = ""

    def savefig(
        self, target: BinaryIO, *, format: str, bbox_inches: Literal["tight"]
    ) -> None:
        self.format = format
        self.bbox_inches = bbox_inches
        target.write(b"<svg/>")


class TestTable(unittest.TestCase):
    def test_init(self) -> None:
        table = Table(["amet", "elit"], [[1, "sed"], [None, 2.5]])

        assert table.headings == ["amet", "elit"]
        assert table.rows == [[1, "sed"], [None, 2.5]]

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="one value per heading"):
            Table(["amet"], [[1, 2]])

        with pytest.raises(ValueError, match="every heading must be different"):
            Table(["amet", "amet"], [[1, 2]])

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

    def test_headings(self) -> None:
        table = Table(["amet"], [[1]])

        table.headings.append("elit")

        assert table.headings == ["amet"]

    def test_rows(self) -> None:
        table = Table(["amet"], [[1]])

        table.rows.append([2])
        table.rows[0].append(3)

        assert table.rows == [[1]]

    def test_eq(self) -> None:
        table = Table(["amet"], [[1], [2]])

        assert table == Table(["amet"], [[1], [2]])
        assert table != Table(["amet"], [[1]])
        assert table != Table(["elit"], [[1], [2]])
        assert table != "amet"

    def test_repr(self) -> None:
        assert repr(Table(["amet"], [[1]])) == "Table(headings=['amet'], rows=[[1]])"


class TestPlot(unittest.TestCase):
    def test_init(self) -> None:
        assert Plot("<svg/>").svg == "<svg/>"

    def test_from_figure(self) -> None:
        figure = SavingFigure()

        plot = Plot.from_figure(figure)

        assert plot == Plot("<svg/>")
        assert figure.format == "svg"
        assert figure.bbox_inches == "tight"

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

    def test_from_proportion(self) -> None:
        estimate = Measurement.from_proportion(5, 10)

        assert math.isclose(estimate.value, 0.5)
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

    def test_eq(self) -> None:
        assert Measurement(1.0, lower=0.5) == Measurement(1.0, lower=0.5)
        assert Measurement(1.0, lower=0.5) != Measurement(1.0, upper=0.5)
        assert Measurement(1.0) != "sit"

    def test_repr(self) -> None:
        assert (
            repr(Measurement(1.0, p_value=0.5))
            == "Measurement(1.0, lower=None, upper=None, p_value=0.5)"
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

    def test_eq(self) -> None:
        assessment = Assessment(3, "at least 5", passed=False)

        assert assessment == Assessment(3, "at least 5", passed=False)
        assert assessment != Assessment(4, "at least 5", passed=False)
        assert assessment != Assessment(3, "at most 5", passed=False)
        assert assessment != Assessment(3, "at least 5", passed=True)
        assert assessment != 3

    def test_repr(self) -> None:
        assert (
            repr(Assessment(3, "at least 5", passed=False))
            == "Assessment(3, 'at least 5', passed=False)"
        )


class TestDistribution(unittest.TestCase):
    def test_init(self) -> None:
        distribution = create_distribution()

        assert distribution.values == [4.0, 1.0, 3.0, 2.0, 10.0]
        assert distribution.count == 5
        assert distribution.bins is None
        assert Distribution([1.0, 2.0], 4).bins == 4

        distribution.values.append(0.0)

        assert distribution.count == 5

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            Distribution([])

        with pytest.raises(ValueError, match="must be finite"):
            Distribution([1.0, math.nan])

        with pytest.raises(ValueError, match="at least one bin"):
            Distribution([1.0], 0)

    def test_mean(self) -> None:
        assert math.isclose(create_distribution().mean, 4.0)

    def test_std(self) -> None:
        assert math.isclose(create_distribution().std, math.sqrt(12.5))
        assert math.isclose(Distribution([2.0]).std, 0.0)

    def test_minimum(self) -> None:
        assert math.isclose(create_distribution().minimum, 1.0)

    def test_lower_quartile(self) -> None:
        assert math.isclose(create_distribution().lower_quartile, 2.0)
        assert math.isclose(Distribution([1.0, 2.0]).lower_quartile, 1.25)
        assert math.isclose(Distribution([1e308, -1e308]).lower_quartile, -5e307)

    def test_median(self) -> None:
        assert math.isclose(create_distribution().median, 3.0)
        assert math.isclose(Distribution([1.0, 2.0]).median, 1.5)

    def test_upper_quartile(self) -> None:
        assert math.isclose(create_distribution().upper_quartile, 4.0)
        assert math.isclose(Distribution([1.0, 2.0]).upper_quartile, 1.75)
        assert math.isclose(Distribution([1e308, -1e308]).upper_quartile, 5e307)

    def test_maximum(self) -> None:
        assert math.isclose(create_distribution().maximum, 10.0)

    def test_histogram(self) -> None:
        assert create_distribution().histogram(3) == [
            {"lower": 0.0, "upper": 5.0, "count": 4},
            {"lower": 5.0, "upper": 10.0, "count": 0},
            {"lower": 10.0, "upper": 15.0, "count": 1},
        ]
        assert create_distribution().histogram() == [
            {"lower": 0.0, "upper": 5.0, "count": 4},
            {"lower": 5.0, "upper": 10.0, "count": 0},
            {"lower": 10.0, "upper": 15.0, "count": 1},
        ]
        assert create_distribution().histogram(10) == [
            {"lower": 1.0, "upper": 2.0, "count": 1},
            {"lower": 2.0, "upper": 3.0, "count": 1},
            {"lower": 3.0, "upper": 4.0, "count": 1},
            {"lower": 4.0, "upper": 5.0, "count": 1},
            {"lower": 5.0, "upper": 6.0, "count": 0},
            {"lower": 6.0, "upper": 7.0, "count": 0},
            {"lower": 7.0, "upper": 8.0, "count": 0},
            {"lower": 8.0, "upper": 9.0, "count": 0},
            {"lower": 9.0, "upper": 10.0, "count": 0},
            {"lower": 10.0, "upper": 11.0, "count": 1},
        ]
        assert Distribution([0.15, 0.2, 0.31]).histogram(2) == [
            {"lower": 0.1, "upper": 0.2, "count": 1},
            {"lower": 0.2, "upper": 0.3, "count": 1},
            {"lower": 0.3, "upper": 0.4, "count": 1},
        ]
        assert Distribution([12.0, 30.0]).histogram(1) == [
            {"lower": 0.0, "upper": 20.0, "count": 1},
            {"lower": 20.0, "upper": 40.0, "count": 1},
        ]
        assert Distribution([0.0, 10.0]).histogram(1) == [
            {"lower": 0.0, "upper": 10.0, "count": 1},
            {"lower": 10.0, "upper": 20.0, "count": 1},
        ]
        assert len(Distribution([1.0]).histogram()) == 1
        assert Distribution([2.0, 2.0]).histogram(5) == [
            {"lower": 2.0, "upper": 2.0, "count": 2}
        ]
        assert Distribution([-1e-17, 0.25, 0.5, 1.0]).histogram()[0]["count"] == 1
        assert Distribution([999999.9999999, 2000000.0]).histogram()[0]["count"] == 1
        assert Distribution([1e308, -1e308]).histogram() == [
            {"lower": -1e308, "upper": 1e308, "count": 2}
        ]
        assert Distribution([-30408.723007846016, -30408.72300784601]).histogram() == [
            {"lower": -30408.723007846016, "upper": -30408.72300784601, "count": 1},
            {"lower": -30408.72300784601, "upper": -30408.723007846005, "count": 1},
        ]
        assert Distribution([1e10, 1e10 + 1e-6]).histogram() == [
            {"lower": 1e10, "upper": 1e10 + 1e-6, "count": 2}
        ]
        assert Distribution([0.0, 5e-324]).histogram() == [
            {"lower": 0.0, "upper": 5e-324, "count": 2}
        ]
        assert Distribution([0.7, 0.8, 0.9], 3).histogram() == Distribution(
            [0.7, 0.8, 0.9]
        ).histogram(3)
        assert Distribution([0.7, 0.8, 0.9]).histogram(3) == [
            {"lower": 0.7, "upper": 0.8, "count": 1},
            {"lower": 0.8, "upper": 0.9, "count": 1},
            {"lower": 0.9, "upper": 1.0, "count": 1},
        ]

    def test_invalid_histogram(self) -> None:
        with pytest.raises(ValueError, match="at least one bin"):
            create_distribution().histogram(0)

    def test_eq(self) -> None:
        assert create_distribution() == Distribution([4, 1, 3, 2, 10])
        assert create_distribution() != Distribution([1, 2, 3, 4, 10])
        assert create_distribution() != Distribution([4, 1, 3, 2, 10], 4)
        assert create_distribution() != [4, 1, 3, 2, 10]

    def test_repr(self) -> None:
        assert repr(create_distribution()) == "Distribution(5 values)"


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

    def test_summarize(self) -> None:
        assert FirstNode().summarize(create_medrecord()) == {}
        assert Summarized().summarize({"nodes": 3}) == {"nodes": 3}


if __name__ == "__main__":
    unittest.main()
