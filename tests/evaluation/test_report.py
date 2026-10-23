import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from medrecords.evaluation.analytic import (
    Assessment,
    Counts,
    Distribution,
    Histogram,
    Measurement,
    Table,
    Unit,
)
from medrecords.evaluation.entry import DerivationEntry, GroupEntry, InputEntry
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.placement import (
    Placement,
    _Shape,
    _Step,
)
from medrecords.evaluation.report import Report

from ._fixtures import (
    create_analytic_entry,
    create_details,
    create_failure,
    create_group_entry,
    create_keyed_analytic_entry,
    create_keyed_group_entry,
    create_keyed_result,
    create_plot,
    create_report,
    create_rich_report,
    write_json,
)


class TestReport(unittest.TestCase):
    def test_init(self) -> None:
        report = create_report()

        assert report.name == "lorem"
        assert report.description is None
        assert report.started_at == datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
        assert report.duration == timedelta(seconds=2)
        assert report.inputs == [InputEntry("medrecord", 3, 2)]
        assert [entry.name for entry in report.entries] == ["amet", "sit", "across"]
        assert report.analytic("amet").result == 1
        assert [path for path, _ in report.analytics()] == [
            ("amet",),
            ("sit", "amet"),
            ("sit", "elit", "consectetur"),
        ]
        assert (
            report.group("sit").group("elit").analytic("consectetur").result == "dolor"
        )
        assert [path for path, _ in report.keyed_analytics()] == [
            ("across", "amet"),
            ("across", "sit", "amet"),
            ("across", "sit", "elit", "consectetur"),
        ]

    def test_to_json(self) -> None:
        report = create_rich_report()

        document = json.loads(report._to_json())
        entries = document["entries"]
        assert entries[0]["result"] == "sed"
        assert entries[24]["result"] == {
            "kind": "histogram",
            "edges": [0.0, 5.0, 10.0],
            "counts": [4, 1],
            "below_count": 0,
            "above_count": 0,
            "statistics": Distribution([4, 1, 3, 2, 10]).statistics,
        }
        assert entries[27]["result"] == {
            "kind": "histogram",
            "edges": [0.0, 1.0],
            "counts": [3],
            "below_count": 1,
            "above_count": 2,
            "statistics": None,
        }
        assert entries[28]["result"] == {
            "kind": "table",
            "headings": ["value", "share"],
            "rows": [["sit", 0.75]],
            "units": [None, "share"],
        }
        assert entries[29]["result"] == {
            "kind": "measurement",
            "value": 0.5,
            "lower": 0.4,
            "upper": None,
            "p_value": None,
            "unit": "share",
        }
        assert entries[30]["result"] == {
            "kind": "assessment",
            "value": 0.75,
            "requirement_label": "at least 50.0%",
            "passed": True,
            "unit": "points",
        }
        assert entries[25]["result"] == {
            "kind": "counts",
            "counts": [
                {"value": "sit", "count": 2},
                {
                    "value": {"kind": "datetime", "value": "2026-09-02T00:00:00+00:00"},
                    "count": 1,
                },
            ],
            "total": 4,
        }
        assert entries[26]["result"]["statistics"] is None
        assert entries[20]["name"] == 2023
        assert entries[21]["kind"] == "keyed_analytic"
        assert entries[21]["results"][1]["key"] == {
            "kind": "datetime",
            "value": "2026-09-02T00:00:00+00:00",
        }
        assert [keyed["result"]["histogram"] for keyed in entries[21]["results"]] == [
            {"edges": [0.0, 5.0, 10.0], "counts": [3, 0]},
            {"edges": [0.0, 5.0, 10.0], "counts": [0, 2]},
        ]
        assert entries[22]["results"][0]["result"]["histogram"] == {
            "edges": [1.0, 2.0, 3.0],
            "counts": [1, 1],
        }
        assert entries[22]["results"][1]["result"]["kind"] == "failure"
        assert entries[23]["kind"] == "keyed_group"
        assert entries[23]["derivations"][1]["key"] == "synthetic"
        assert entries[23]["derivations"][1]["derivation"]["failure"]["kind"] == (
            "failure"
        )
        assert entries[23]["entries"][1]["kind"] == "keyed_group"
        assert entries[18]["result"] == {
            "kind": "measurement",
            "value": 1.0,
            "lower": None,
            "upper": None,
            "p_value": None,
            "unit": None,
        }
        assert entries[19]["result"]["value"] == {
            "kind": "datetime",
            "value": "2026-09-02T00:00:00+00:00",
        }
        assert entries[7]["result"] == {"kind": "float", "value": "inf"}
        assert entries[8]["result"]["rows"][1][0] == {
            "kind": "datetime",
            "value": "2026-09-02T00:00:00+00:00",
        }
        assert entries[8]["result"]["units"] == [None, None, None, None, None]
        assert entries[9]["result"]["kind"] == "failure"
        assert entries[10]["derivation"]["failure"]["kind"] == "failure"
        assert entries[11]["derivation"]["parameters"] == {"node": "lorem"}
        assert entries[11]["derivation"]["summary"] == {"kept": 1}
        assert entries[12]["result"] == {"kind": "plot", "svg": create_plot().svg}
        assert entries[13]["result"] == {
            "kind": "measurement",
            "value": 0.87,
            "lower": 0.82,
            "upper": 0.91,
            "p_value": 0.003,
            "unit": None,
        }
        assert entries[14]["result"] == {
            "kind": "assessment",
            "value": 3,
            "requirement_label": "at least 5",
            "passed": False,
            "unit": None,
        }
        assert entries[15]["result"]["values"] == [4.0, 1.0, 3.0, 2.0, 10.0]
        assert entries[15]["result"]["bin_count"] is None
        assert entries[15]["result"]["statistics"]["count"] == 5
        assert math.isclose(entries[15]["result"]["statistics"]["median"], 3.0)
        assert entries[15]["result"]["histogram"] == {
            "edges": [0.0, 5.0, 10.0, 15.0],
            "counts": [4, 0, 1],
        }
        assert entries[16]["parameters"] == {
            "limit": 3,
            "groups": ["sit", "elit"],
            "since": {"kind": "datetime", "value": "2026-09-02T00:00:00+00:00"},
            "window": {
                "kind": "timedelta",
                "days": 1,
                "seconds": 0,
                "microseconds": 0,
            },
            "label": None,
        }
        assert entries[17]["derivation"]["summary"] == {"kept": [1, 2]}

        report = Report(
            "lorem",
            None,
            [],
            [create_analytic_entry("nan", result=math.nan)],
            datetime.now(timezone.utc),
            timedelta(),
        )

        document = json.loads(report._to_json())

        assert document["entries"][0]["result"] == {"kind": "float", "value": "nan"}

    def test_from_json(self) -> None:
        report = create_report()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report.to_json(path)
            loaded = Report.from_json(path)

        assert loaded == report

        rich = Report(
            "lorem",
            "ipsum",
            [InputEntry("medrecord", 3, 2)],
            [
                create_analytic_entry("plot", result=create_plot()),
                create_analytic_entry("table", result=Table(["a"], [[1], [None]])),
                create_analytic_entry(
                    "shares",
                    result=Table(
                        ["value", "share"],
                        [["sit", 0.75]],
                        units={"share": Unit.Share},
                    ),
                ),
                create_analytic_entry(
                    "measurement", result=Measurement(0.5, 0.4, 0.6, 0.01)
                ),
                create_analytic_entry(
                    "share", result=Measurement(0.5, 0.4, 0.6, unit=Unit.Share)
                ),
                create_analytic_entry(
                    "complete",
                    result=Assessment(
                        0.75, "at least 50.0%", passed=True, unit=Unit.Points
                    ),
                ),
                create_analytic_entry(
                    "assessment",
                    result=Assessment(
                        datetime(2026, 9, 2, tzinfo=timezone.utc),
                        "after 2026",
                        passed=True,
                    ),
                ),
                create_analytic_entry("distribution", result=Distribution([1.0, 2.0])),
                create_analytic_entry("failure", result=create_failure()),
                create_analytic_entry("infinity", result=math.inf),
                create_analytic_entry("window", result=timedelta(days=1)),
                create_analytic_entry("detailed", parameters=create_details()),
                GroupEntry(
                    "derived",
                    "Derived",
                    "sit",
                    [InputEntry("medrecord", 1, 0)],
                    DerivationEntry(
                        {"node": "lorem"}, {"kept": [1, 2]}, timedelta(seconds=1), None
                    ),
                    [create_analytic_entry("inner")],
                ),
                GroupEntry(
                    "failed",
                    "Failed",
                    None,
                    [],
                    DerivationEntry({}, {}, timedelta(), create_failure()),
                    [],
                ),
                GroupEntry(
                    2023,
                    "2023",
                    None,
                    [],
                    None,
                    [create_analytic_entry(datetime(2026, 9, 2, tzinfo=timezone.utc))],
                ),
                create_keyed_analytic_entry(
                    "shared",
                    results=[
                        create_keyed_result(result=Distribution([1.0, 2.0])),
                        create_keyed_result(2024, result=Distribution([3.0])),
                    ],
                ),
                create_keyed_analytic_entry(
                    "tables",
                    results=[
                        create_keyed_result(result=Table(["a"], [[1]])),
                        create_keyed_result("synthetic", result=create_failure()),
                    ],
                ),
                create_keyed_group_entry(),
                create_analytic_entry(
                    "histogram",
                    result=Histogram.from_values([4, 1, 3, 2, 10], [2.0, 4.0]),
                ),
                create_analytic_entry("empty", result=Histogram([0.0, 1.0], [0])),
                create_analytic_entry(
                    "counts",
                    result=Counts(
                        {
                            "sit": 2,
                            datetime(2026, 9, 2, tzinfo=timezone.utc): 1,
                            None: 1,
                        },
                        5,
                    ),
                ),
                create_keyed_analytic_entry(
                    "histograms",
                    results=[
                        create_keyed_result(
                            result=Histogram.from_values([1.0, 2.0], [0.0, 5.0])
                        ),
                        create_keyed_result("synthetic", result=Counts({"sit": 1})),
                    ],
                ),
            ],
            datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
            timedelta(seconds=2),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            rich.to_json(path)
            loaded = Report.from_json(path)

        assert loaded == rich
        assert loaded.analytic("shares").result == Table(
            ["value", "share"], [["sit", 0.75]], units={"share": Unit.Share}
        )
        assert loaded.analytic("share").result == Measurement(
            0.5, 0.4, 0.6, unit=Unit.Share
        )
        assert loaded.analytic("complete").result == Assessment(
            0.75, "at least 50.0%", passed=True, unit=Unit.Points
        )
        assert loaded.analytic("histogram").result == Histogram(
            [2.0, 4.0],
            [3],
            below_count=1,
            above_count=1,
            statistics=Distribution([4, 1, 3, 2, 10]).statistics,
        )
        assert loaded.keyed_group("sit").derivations == (
            create_keyed_group_entry().derivations
        )
        assert loaded.analytic("counts").result == Counts(
            {"sit": 2, datetime(2026, 9, 2, tzinfo=timezone.utc): 1, None: 1}, 5
        )
        assert loaded.group(2023).analytic(
            datetime(2026, 9, 2, tzinfo=timezone.utc)
        ).name == datetime(2026, 9, 2, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            create_rich_report().to_json(path)

            assert Report.from_json(path) == create_rich_report()

    def test_invalid_from_json(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            pytest.raises(ValueError, match="expected an object at report"),
        ):
            Report.from_json(write_json(directory, []))

    def test_keyed_group(self) -> None:
        report = Report(
            "lorem", None, [], [create_keyed_group_entry()], datetime.now(), timedelta()
        )

        assert report.keyed_group("sit") == create_keyed_group_entry()

    def test_keyed_analytic(self) -> None:
        report = Report(
            "lorem",
            None,
            [],
            [create_keyed_analytic_entry()],
            datetime.now(),
            timedelta(),
        )

        assert report.keyed_analytic("amet") == create_keyed_analytic_entry()

    def test_keyed_analytics(self) -> None:
        assert [path for path, _ in create_report().keyed_analytics()] == [
            ("across", "amet"),
            ("across", "sit", "amet"),
            ("across", "sit", "elit", "consectetur"),
        ]

    def test_eq(self) -> None:
        report = create_report()

        assert report == create_report()
        assert report != Report(
            "lorem",
            None,
            [InputEntry("medrecord", 3, 2)],
            report.entries,
            report.started_at,
            timedelta(),
        )
        assert report != Report(
            "lorem",
            None,
            [InputEntry("medrecord", 3, 2)],
            report.entries,
            datetime.now(timezone.utc),
            report.duration,
        )
        assert report != create_group_entry()

        twin = GroupEntry("lorem", "lorem", None, report.inputs, None, report.entries)

        assert report != twin
        assert twin != report

    def test_findings(self) -> None:
        findings = create_report().findings

        assert isinstance(findings, Findings)
        assert findings[Placement((_Step("amet", _Shape.Plain),))] == 1
        assert findings[
            Placement((_Step("across", _Shape.Across), _Step("amet", _Shape.Plain)))
        ] == {"real": 1, "synthetic": 2}
        assert len(list(findings.each(int))) == 8

    def test_repr(self) -> None:
        assert repr(create_report()) == "Report('lorem', entries=3)"


if __name__ == "__main__":
    unittest.main()
