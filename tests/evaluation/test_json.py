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
    encode_cell,
    encode_datetime,
    encode_details,
    encode_float,
    encode_value,
)
from medrecords.evaluation.analytic import Arrangement, Scale

from ._fixtures import create_details

SINCE = datetime(2026, 9, 2, tzinfo=timezone.utc)
SINCE_DOCUMENT: Dict[str, Json] = {
    "kind": "datetime",
    "year": 2026,
    "month": 9,
    "day": 2,
    "hour": 0,
    "minute": 0,
    "second": 0,
    "microsecond": 0,
    "offset": 0,
}
WINDOW = timedelta(days=1, seconds=2, microseconds=3)
WINDOW_DOCUMENT: Dict[str, Json] = {
    "kind": "timedelta",
    "days": 1,
    "seconds": 2,
    "microseconds": 3,
}
INFINITY_DOCUMENT: Dict[str, Json] = {"kind": "float", "value": "inf"}


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

    def test_decoded_datetime(self) -> None:
        naive: Dict[str, Json] = {
            **SINCE_DOCUMENT,
            "hour": 10,
            "microsecond": 5,
            "offset": None,
        }
        shifted: Dict[str, Json] = {**SINCE_DOCUMENT, "offset": 19800}

        assert (
            JsonObject._decoded_datetime(JsonObject(SINCE_DOCUMENT, "report")) == SINCE
        )
        assert JsonObject._decoded_datetime(JsonObject(naive, "report")) == datetime(
            2026, 9, 2, 10, 0, 0, 5
        )
        assert JsonObject._decoded_datetime(JsonObject(shifted, "report")) == datetime(
            2026, 9, 2, tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

    def test_invalid_decoded_datetime(self) -> None:
        impossible: Dict[str, Json] = {**SINCE_DOCUMENT, "month": 13}

        with pytest.raises(
            ValueError, match=r"month must be in 1\.\.12.* at report\.started_at"
        ):
            JsonObject._decoded_datetime(JsonObject(impossible, "report.started_at"))

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

    def test_decoded_identifier(self) -> None:
        assert JsonObject._decoded_identifier("sit", "report") == "sit"
        assert JsonObject._decoded_identifier(2024, "report") == 2024

    def test_invalid_decoded_identifier(self) -> None:
        for content in (True, 1.5):
            with pytest.raises(ValueError, match=r"expected an identifier at report"):
                JsonObject._decoded_identifier(content, "report")

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

    def test_encode_datetime(self) -> None:
        assert encode_datetime(SINCE) == SINCE_DOCUMENT
        assert encode_datetime(datetime(2026, 9, 2, 10, 0, 0, 5)) == {
            **SINCE_DOCUMENT,
            "hour": 10,
            "microsecond": 5,
            "offset": None,
        }
        assert encode_datetime(
            datetime(2026, 9, 2, tzinfo=timezone(timedelta(hours=-5)))
        ) == {**SINCE_DOCUMENT, "offset": -18000}

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


if __name__ == "__main__":
    unittest.main()
