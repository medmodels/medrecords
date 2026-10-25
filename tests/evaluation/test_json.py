import math
import re
import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest

from medrecords.evaluation._json import (
    Json,
    JsonObject,
    copy_details,
    encode_arrangement,
    encode_cell,
    encode_details,
    encode_distribution,
    encode_float,
    encode_unit,
    encode_value,
)
from medrecords.evaluation.analytic import (
    Arrangement,
    Assessment,
    Bins,
    Counts,
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

from ._fixtures import create_details

SINCE = datetime(2026, 9, 2, tzinfo=timezone.utc)
SINCE_DOCUMENT: Dict[str, Json] = {
    "kind": "datetime",
    "value": "2026-09-02T00:00:00+00:00",
}
WINDOW = timedelta(days=1, seconds=2, microseconds=3)
WINDOW_DOCUMENT: Dict[str, Json] = {
    "kind": "timedelta",
    "days": 1,
    "seconds": 2,
    "microseconds": 3,
}
INFINITY_DOCUMENT: Dict[str, Json] = {"kind": "float", "value": "inf"}


def create_statistics() -> Statistics:
    return {
        "count": 2,
        "mean": 1.5,
        "standard_deviation": 0.5,
        "minimum": 1.0,
        "lower_quartile": 1.25,
        "median": 1.5,
        "upper_quartile": 1.75,
        "maximum": 2.0,
    }


def create_statistics_document() -> Dict[str, Json]:
    return {
        "count": 2,
        "mean": 1.5,
        "standard_deviation": 0.5,
        "minimum": 1.0,
        "lower_quartile": 1.25,
        "median": 1.5,
        "upper_quartile": 1.75,
        "maximum": 2.0,
    }


def create_table_document() -> Dict[str, Json]:
    return {"headings": ["a"], "rows": [[1]], "units": [None]}


def create_histogram_document() -> Dict[str, Json]:
    return {
        "edges": [0.0, 1.0],
        "counts": [3],
        "below_count": 1,
        "above_count": 2,
        "statistics": None,
        "scale": "linear",
        "value_label": None,
        "count_label": None,
        "arrangement": None,
    }


def create_distribution_document() -> Dict[str, Json]:
    return {
        "values": [1.0, 2.0],
        "bins": None,
        "value_label": None,
        "count_label": None,
        "arrangement": None,
    }


def create_counts_document() -> Dict[str, Json]:
    return {
        "counts": [{"value": "sit", "count": 2}],
        "total": 2,
        "value_label": None,
        "count_label": None,
        "remainder_label": None,
        "arrangement": None,
    }


def create_scatter_document() -> Dict[str, Json]:
    return {
        "points": [[0.1, 0.2], [0.5, 0.4]],
        "x_label": "real",
        "y_label": "synthetic",
        "x_scale": "logarithmic",
        "y_scale": "linear",
        "labels": [{"index": 1, "label": "lorem"}],
        "diagonal": True,
    }


class TestJsonObject(unittest.TestCase):
    def test_init(self) -> None:
        assert JsonObject({"amet": 1}, "report").path == "report"

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="expected an object at report"):
            JsonObject([1], "report")

    def test_items(self) -> None:
        assert JsonObject({"amet": 1, "elit": None}, "report").items() == [
            ("amet", 1),
            ("elit", None),
        ]

    def test_content(self) -> None:
        assert JsonObject({"amet": 1}, "report").content("amet") == 1

    def test_invalid_content(self) -> None:
        with pytest.raises(ValueError, match="expected 'amet' at report"):
            JsonObject({}, "report").content("amet")

    def test_string(self) -> None:
        assert JsonObject({"amet": "sit"}, "report").string("amet") == "sit"

    def test_invalid_string(self) -> None:
        with pytest.raises(ValueError, match=r"expected a string at report.amet"):
            JsonObject({"amet": 1}, "report").string("amet")

    def test_optional_string(self) -> None:
        assert JsonObject({"amet": None}, "report").optional_string("amet") is None
        assert JsonObject({"amet": "sit"}, "report").optional_string("amet") == "sit"

    def test_boolean(self) -> None:
        assert JsonObject({"amet": True}, "report").boolean("amet") is True

    def test_invalid_boolean(self) -> None:
        with pytest.raises(ValueError, match=r"expected a boolean at report.amet"):
            JsonObject({"amet": 1}, "report").boolean("amet")

    def test_number(self) -> None:
        assert math.isclose(JsonObject({"amet": 1}, "report").number("amet"), 1.0)
        assert math.isclose(JsonObject({"amet": 1.5}, "report").number("amet"), 1.5)
        assert (
            JsonObject({"amet": INFINITY_DOCUMENT}, "report").number("amet") == math.inf
        )
        assert math.isnan(
            JsonObject({"amet": {"kind": "float", "value": "nan"}}, "report").number(
                "amet"
            )
        )

    def test_invalid_number(self) -> None:
        truth = True

        with pytest.raises(ValueError, match=r"expected a number at report.amet"):
            JsonObject({"amet": truth}, "report").number("amet")
        with pytest.raises(ValueError, match=r"expected a number at report.amet"):
            JsonObject({"amet": SINCE_DOCUMENT}, "report").number("amet")

    def test_optional_number(self) -> None:
        assert JsonObject({"amet": None}, "report").optional_number("amet") is None
        assert JsonObject({"amet": 2}, "report").optional_number("amet") == 2

    def test_integer(self) -> None:
        assert JsonObject({"amet": 1}, "report").integer("amet") == 1

    def test_invalid_integer(self) -> None:
        with pytest.raises(ValueError, match=r"expected an integer at report.amet"):
            JsonObject({"amet": 1.5}, "report").integer("amet")

    def test_optional_integer(self) -> None:
        assert JsonObject({"amet": None}, "report").optional_integer("amet") is None
        assert JsonObject({"amet": 2}, "report").optional_integer("amet") == 2

    def test_sequence(self) -> None:
        assert JsonObject({"amet": [1, 2]}, "report").sequence("amet") == [1, 2]

    def test_invalid_sequence(self) -> None:
        with pytest.raises(ValueError, match=r"expected an array at report.amet"):
            JsonObject({"amet": 1}, "report").sequence("amet")

    def test_document(self) -> None:
        assert JsonObject({"amet": {"sit": 1}}, "report").document("amet").path == (
            "report.amet"
        )

    def test_optional_document(self) -> None:
        assert JsonObject({"amet": None}, "report").optional_document("amet") is None

        nested = JsonObject({"amet": {"sit": 1}}, "report").optional_document("amet")

        assert nested is not None
        assert nested.path == "report.amet"

    def test_member(self) -> None:
        assert JsonObject({"amet": "logarithmic"}, "report").member("amet", Scale) is (
            Scale.Logarithmic
        )

    def test_invalid_member(self) -> None:
        with pytest.raises(
            ValueError, match=re.escape("expected a value of Scale at report.amet")
        ):
            JsonObject({"amet": "lorem"}, "report").member("amet", Scale)

        with pytest.raises(
            ValueError,
            match=re.escape("expected a value of Arrangement at report.amet"),
        ):
            JsonObject({"amet": 1}, "report").member("amet", Arrangement)

        with pytest.raises(ValueError, match=re.escape("expected 'amet' at report")):
            JsonObject({}, "report").member("amet", Scale)

    def test_optional_member(self) -> None:
        assert (
            JsonObject({"amet": None}, "report").optional_member("amet", Scale) is None
        )
        assert JsonObject({"amet": "panels"}, "report").optional_member(
            "amet", Arrangement
        ) is (Arrangement.Panels)

    def test_optional_unit(self) -> None:
        assert JsonObject({"amet": None}, "report").optional_unit("amet") is None
        assert JsonObject({"amet": "share"}, "report").optional_unit("amet") is (
            Unit.Share
        )
        assert JsonObject({"amet": "points"}, "report").optional_unit("amet") is (
            Unit.Points
        )

    def test_invalid_optional_unit(self) -> None:
        with pytest.raises(ValueError, match=r"expected a unit at report.amet"):
            JsonObject({"amet": "lorem"}, "report").optional_unit("amet")

        with pytest.raises(ValueError, match=r"expected a unit at report.amet"):
            JsonObject({"amet": 1}, "report").optional_unit("amet")

    def test_decoded_datetime(self) -> None:
        assert JsonObject._decoded_datetime(SINCE.isoformat(), "report") == SINCE

    def test_invalid_decoded_datetime(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape("Invalid isoformat string: 'lorem' at report.started_at"),
        ):
            JsonObject._decoded_datetime("lorem", "report.started_at")

    def test_decoded_duration(self) -> None:
        assert JsonObject._decoded_duration(1.5, "report") == timedelta(seconds=1.5)

    def test_invalid_decoded_duration(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape(
                "cannot convert float infinity to integer at report.duration"
            ),
        ):
            JsonObject._decoded_duration(math.inf, "report.duration")

        with pytest.raises(
            ValueError,
            match=re.escape(
                "Python int too large to convert to C int at report.duration"
            ),
        ):
            JsonObject._decoded_duration(1e30, "report.duration")

    def test_decoded_timedelta(self) -> None:
        document = JsonObject(WINDOW_DOCUMENT, "report")

        assert JsonObject._decoded_timedelta(document) == WINDOW

    def test_invalid_decoded_timedelta(self) -> None:
        oversized: Dict[str, Json] = {**WINDOW_DOCUMENT, "days": 10**9}
        fractional: Dict[str, Json] = {**WINDOW_DOCUMENT, "days": 1.5}

        with pytest.raises(
            ValueError, match=re.escape("must have magnitude <= 999999999 at report")
        ):
            JsonObject._decoded_timedelta(JsonObject(oversized, "report"))

        with pytest.raises(
            ValueError, match=re.escape("expected an integer at report.days")
        ):
            JsonObject._decoded_timedelta(JsonObject(fractional, "report"))

    def test_decoded_non_finite(self) -> None:
        assert JsonObject._decoded_non_finite("inf", "report") == math.inf
        assert JsonObject._decoded_non_finite("-inf", "report") == -math.inf
        assert math.isnan(JsonObject._decoded_non_finite("nan", "report"))

    def test_invalid_decoded_non_finite(self) -> None:
        with pytest.raises(
            ValueError,
            match=re.escape("could not convert string to float: 'lorem' at report"),
        ):
            JsonObject._decoded_non_finite("lorem", "report")

    def test_decoded_value(self) -> None:
        truth = True

        assert JsonObject._decoded_value(None, "report") is None
        assert JsonObject._decoded_value("sit", "report") == "sit"
        assert JsonObject._decoded_value(1, "report") == 1
        assert JsonObject._decoded_value(truth, "report") is True
        assert JsonObject._decoded_value(SINCE_DOCUMENT, "report") == SINCE
        assert JsonObject._decoded_value(WINDOW_DOCUMENT, "report") == WINDOW
        assert JsonObject._decoded_value(INFINITY_DOCUMENT, "report") == math.inf

    def test_invalid_decoded_value(self) -> None:
        unknown: Dict[str, Json] = {"kind": "lorem"}

        with pytest.raises(ValueError, match=re.escape("expected a value at report")):
            JsonObject._decoded_value(unknown, "report")

        with pytest.raises(ValueError, match=re.escape("expected an object at report")):
            JsonObject._decoded_value([1], "report")

    def test_decoded_cell(self) -> None:
        path: Dict[str, Json] = {"kind": "path", "names": ["sit", 1, SINCE_DOCUMENT]}

        assert JsonObject._decoded_cell(path, "report") == ("sit", 1, SINCE)
        assert JsonObject._decoded_cell("sit", "report") == "sit"
        assert JsonObject._decoded_cell(SINCE_DOCUMENT, "report") == SINCE

    def test_invalid_decoded_cell(self) -> None:
        nameless: Dict[str, Json] = {"kind": "path"}
        unknown: Dict[str, Json] = {"kind": "path", "names": [{"kind": "lorem"}]}

        with pytest.raises(ValueError, match=re.escape("expected 'names' at report")):
            JsonObject._decoded_cell(nameless, "report")

        with pytest.raises(
            ValueError, match=re.escape("expected a value at report.names[0]")
        ):
            JsonObject._decoded_cell(unknown, "report")

    def test_table(self) -> None:
        document: Dict[str, Json] = {
            "headings": ["a", 2024],
            "rows": [[1, "sit"], [{"kind": "path", "names": ["elit", 2]}, None]],
            "units": [None, "share"],
        }

        assert JsonObject(document, "report")._table() == Table(
            ["a", 2024], [[1, "sit"], [("elit", 2), None]], units={2024: Unit.Share}
        )

    def test_invalid_table(self) -> None:
        unlabelled: Dict[str, Json] = {**create_table_document(), "headings": [1.5]}
        flat: Dict[str, Json] = {**create_table_document(), "rows": [1]}
        wide: Dict[str, Json] = {**create_table_document(), "rows": [[1, 2]]}
        unitless: Dict[str, Json] = {**create_table_document(), "units": ["lorem"]}
        uneven: Dict[str, Json] = {**create_table_document(), "units": []}

        with pytest.raises(
            ValueError, match=re.escape("expected an identifier at report.headings[0]")
        ):
            JsonObject(unlabelled, "report")._table()

        with pytest.raises(
            ValueError, match=re.escape("expected an array at report.rows")
        ):
            JsonObject(flat, "report")._table()

        with pytest.raises(
            ValueError,
            match=re.escape("every row must hold one cell per heading at report"),
        ):
            JsonObject(wide, "report")._table()

        with pytest.raises(
            ValueError, match=re.escape("expected a unit at report.units[0]")
        ):
            JsonObject(unitless, "report")._table()

        with pytest.raises(
            ValueError,
            match=re.escape("expected one unit per heading at report.units"),
        ):
            JsonObject(uneven, "report")._table()

    def test_plot(self) -> None:
        assert JsonObject({"svg": "<svg/>"}, "report")._plot() == Plot("<svg/>")

    def test_measurement(self) -> None:
        document: Dict[str, Json] = {
            "value": 0.5,
            "lower": None,
            "upper": INFINITY_DOCUMENT,
            "p_value": None,
            "unit": "share",
        }

        assert JsonObject(document, "report")._measurement() == Measurement(
            0.5, upper=math.inf, unit=Unit.Share
        )

    def test_assessment(self) -> None:
        document: Dict[str, Json] = {
            "value": SINCE_DOCUMENT,
            "requirement_label": "after 2026",
            "passed": True,
            "unit": None,
        }

        assert JsonObject(document, "report")._assessment() == Assessment(
            SINCE, "after 2026", passed=True
        )

    def test_distribution(self) -> None:
        described: Dict[str, Json] = {
            **create_distribution_document(),
            "bins": {"count": 4, "scale": "logarithmic", "outside_share": 0.01},
            "value_label": "age",
            "count_label": "patients",
            "arrangement": "overlay",
        }

        assert JsonObject(
            create_distribution_document(), "report"
        )._distribution() == Distribution([1.0, 2.0])
        assert JsonObject(described, "report")._distribution() == Distribution(
            [1.0, 2.0],
            bins=Bins(count=4, scale=Scale.Logarithmic, outside_share=0.01),
            value_label="age",
            count_label="patients",
            arrangement=Arrangement.Overlay,
        )

    def test_invalid_distribution(self) -> None:
        empty: Dict[str, Json] = {**create_distribution_document(), "values": []}
        unarranged: Dict[str, Json] = {
            **create_distribution_document(),
            "arrangement": "lorem",
        }

        with pytest.raises(
            ValueError,
            match=re.escape("a distribution must hold at least one value at report"),
        ):
            JsonObject(empty, "report")._distribution()

        with pytest.raises(
            ValueError,
            match=re.escape("expected a value of Arrangement at report.arrangement"),
        ):
            JsonObject(unarranged, "report")._distribution()

    def test_bins(self) -> None:
        unset: Dict[str, Json] = {"count": None, "scale": None, "outside_share": None}

        assert JsonObject(unset, "report")._bins() == Bins()

    def test_invalid_bins(self) -> None:
        binless: Dict[str, Json] = {"count": 0, "scale": None, "outside_share": None}

        with pytest.raises(
            ValueError, match=re.escape("a histogram needs at least one bin at report")
        ):
            JsonObject(binless, "report")._bins()

    def test_histogram(self) -> None:
        described: Dict[str, Json] = {
            **create_histogram_document(),
            "statistics": create_statistics_document(),
        }

        assert JsonObject(create_histogram_document(), "report")._histogram() == (
            Histogram([0.0, 1.0], [3], below_count=1, above_count=2)
        )
        assert JsonObject(described, "report")._histogram() == Histogram(
            [0.0, 1.0],
            [3],
            below_count=1,
            above_count=2,
            statistics=create_statistics(),
        )

        labelled: Dict[str, Json] = {
            **create_histogram_document(),
            "edges": [1.0, 10.0],
            "scale": "logarithmic",
            "value_label": "dose",
            "count_label": "prescriptions",
            "arrangement": "panels",
        }

        assert JsonObject(labelled, "report")._histogram() == Histogram(
            [1.0, 10.0],
            [3],
            below_count=1,
            above_count=2,
            scale=Scale.Logarithmic,
            value_label="dose",
            count_label="prescriptions",
            arrangement=Arrangement.Panels,
        )

    def test_invalid_histogram(self) -> None:
        decreasing: Dict[str, Json] = {
            **create_histogram_document(),
            "edges": [1.0, 0.0],
        }
        fractional: Dict[str, Json] = {**create_histogram_document(), "counts": [1.5]}
        unscaled: Dict[str, Json] = {**create_histogram_document(), "scale": "lorem"}

        with pytest.raises(
            ValueError,
            match=re.escape("the edges of a histogram must be increasing at report"),
        ):
            JsonObject(decreasing, "report")._histogram()

        with pytest.raises(
            ValueError, match=re.escape("expected an integer at report.counts")
        ):
            JsonObject(fractional, "report")._histogram()

        with pytest.raises(
            ValueError, match=re.escape("expected a value of Scale at report.scale")
        ):
            JsonObject(unscaled, "report")._histogram()

    def test_statistics(self) -> None:
        document = JsonObject(create_statistics_document(), "report")

        assert document._statistics() == create_statistics()

    def test_counts(self) -> None:
        document: Dict[str, Json] = {
            **create_counts_document(),
            "counts": [
                {"value": "sit", "count": 2},
                {"value": SINCE_DOCUMENT, "count": 1},
            ],
            "total": 4,
            "value_label": "diagnosis",
            "count_label": "patients",
            "remainder_label": "rarer",
            "arrangement": "overlay",
        }

        assert JsonObject(document, "report")._counts() == Counts(
            {"sit": 2, SINCE: 1},
            4,
            value_label="diagnosis",
            count_label="patients",
            remainder_label="rarer",
            arrangement=Arrangement.Overlay,
        )
        assert JsonObject(create_counts_document(), "report")._counts() == Counts(
            {"sit": 2}
        )

    def test_invalid_counts(self) -> None:
        unvalued: Dict[str, Json] = {
            **create_counts_document(),
            "counts": [{"count": 1}],
            "total": 1,
        }
        exceeded: Dict[str, Json] = {**create_counts_document(), "total": 1}

        with pytest.raises(
            ValueError, match=re.escape("expected 'value' at report.counts[0]")
        ):
            JsonObject(unvalued, "report")._counts()

        with pytest.raises(
            ValueError,
            match=re.escape(
                "the total must be at least the sum of the counts at report"
            ),
        ):
            JsonObject(exceeded, "report")._counts()

    def test_scatter(self) -> None:
        assert JsonObject(create_scatter_document(), "report")._scatter() == Scatter(
            [(0.1, 0.2), (0.5, 0.4)],
            x_label="real",
            y_label="synthetic",
            x_scale=Scale.Logarithmic,
            labels={1: "lorem"},
            diagonal=True,
        )

    def test_invalid_scatter(self) -> None:
        short: Dict[str, Json] = {**create_scatter_document(), "points": [[0.1]]}
        unlabelled: Dict[str, Json] = {
            **create_scatter_document(),
            "labels": [{"index": 2, "label": "lorem"}],
        }
        unscaled: Dict[str, Json] = {**create_scatter_document(), "y_scale": 1}

        with pytest.raises(
            ValueError, match=re.escape("expected two coordinates at report.points[0]")
        ):
            JsonObject(short, "report")._scatter()

        with pytest.raises(
            ValueError,
            match=re.escape("names the point 2, which the scatter does not have"),
        ):
            JsonObject(unlabelled, "report")._scatter()

        with pytest.raises(
            ValueError, match=re.escape("expected a value of Scale at report.y_scale")
        ):
            JsonObject(unscaled, "report")._scatter()

    def test_details(self) -> None:
        document: Dict[str, Json] = {
            "parameters": {
                "limit": 3,
                "groups": ["sit", "elit"],
                "since": SINCE_DOCUMENT,
                "window": WINDOW_DOCUMENT,
                "label": None,
            }
        }

        assert JsonObject(document, "report")._details("parameters") == {
            "limit": 3,
            "groups": ["sit", "elit"],
            "since": SINCE,
            "window": WINDOW,
            "label": None,
        }

    def test_invalid_details(self) -> None:
        unknown: Dict[str, Json] = {"parameters": {"limit": {"kind": "lorem"}}}
        unknown_item: Dict[str, Json] = {"parameters": {"groups": [{"kind": "lorem"}]}}

        with pytest.raises(
            ValueError, match=re.escape("expected a value at report.parameters.limit")
        ):
            JsonObject(unknown, "report")._details("parameters")

        with pytest.raises(
            ValueError,
            match=re.escape("expected a value at report.parameters.groups[0]"),
        ):
            JsonObject(unknown_item, "report")._details("parameters")


class TestCodec(unittest.TestCase):
    def test_copy_details(self) -> None:
        details = create_details()

        copied = copy_details(details)

        assert copied == details
        assert copied["groups"] is not details["groups"]
        assert copied["limit"] is details["limit"]

    def test_encode_float(self) -> None:
        assert encode_float(1.5) == pytest.approx(1.5)
        assert encode_float(math.inf) == INFINITY_DOCUMENT
        assert encode_float(math.nan) == {"kind": "float", "value": "nan"}

    def test_encode_value(self) -> None:
        assert encode_value(None) is None
        assert encode_value("sit") == "sit"
        assert encode_value(2) == 2
        assert encode_value(SINCE) == SINCE_DOCUMENT
        assert encode_value(WINDOW) == WINDOW_DOCUMENT
        assert encode_value(math.inf) == INFINITY_DOCUMENT

    def test_encode_cell(self) -> None:
        assert encode_cell(("sit", SINCE)) == {
            "kind": "path",
            "names": ["sit", SINCE_DOCUMENT],
        }
        assert encode_cell(math.inf) == INFINITY_DOCUMENT
        assert encode_cell("sit") == "sit"

    def test_encode_details(self) -> None:
        assert encode_details(create_details()) == {
            "limit": 3,
            "groups": ["sit", "elit"],
            "since": SINCE_DOCUMENT,
            "window": {"kind": "timedelta", "days": 1, "seconds": 0, "microseconds": 0},
            "label": None,
        }

    def test_encode_unit(self) -> None:
        assert encode_unit(None) is None
        assert encode_unit(Unit.Share) == "share"
        assert encode_unit(Unit.Points) == "points"

    def test_encode_arrangement(self) -> None:
        assert encode_arrangement(None) is None
        assert encode_arrangement(Arrangement.Overlay) == "overlay"
        assert encode_arrangement(Arrangement.Panels) == "panels"

    def test_encode_distribution(self) -> None:
        distribution = Distribution([1.0, 2.0, 3.0])

        assert encode_distribution(distribution, Histogram([0.0, 5.0], [3])) == {
            "kind": "distribution",
            "values": [1.0, 2.0, 3.0],
            "bins": None,
            "value_label": None,
            "count_label": None,
            "arrangement": None,
            "statistics": distribution.statistics,
            "histogram": {
                "edges": [0.0, 5.0],
                "counts": [3],
                "below_count": 0,
                "above_count": 0,
                "scale": "linear",
            },
        }

        described = Distribution(
            [1.0, 20.0],
            bins=Bins(count=3, scale=Scale.Logarithmic, outside_share=0.0),
            value_label="dose",
            count_label="prescriptions",
            arrangement=Arrangement.Panels,
        )
        histogram = Histogram(
            [2.0, 10.0], [0], below_count=1, above_count=1, scale=Scale.Logarithmic
        )

        assert encode_distribution(described, histogram) == {
            "kind": "distribution",
            "values": [1.0, 20.0],
            "bins": {"count": 3, "scale": "logarithmic", "outside_share": 0.0},
            "value_label": "dose",
            "count_label": "prescriptions",
            "arrangement": "panels",
            "statistics": described.statistics,
            "histogram": {
                "edges": [2.0, 10.0],
                "counts": [0],
                "below_count": 1,
                "above_count": 1,
                "scale": "logarithmic",
            },
        }


if __name__ == "__main__":
    unittest.main()
