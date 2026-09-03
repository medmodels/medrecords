import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

import pytest

from medrecords.evaluation.analytic import (
    Assessment,
    Detail,
    Distribution,
    Measurement,
    Plot,
    Table,
)
from medrecords.evaluation.report import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
    Report,
    _Document,
    _Json,
)
from medrecords.medrecord import MedRecord


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes([("lorem", {}), ("ipsum", {}), ("dolor", {})])
        .add_edges([("lorem", "ipsum", {}), ("ipsum", "dolor", {})])
    )


def create_plot() -> Plot:
    return Plot(
        '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">'
        '<rect width="120" height="40" fill="#00B4D8"/></svg>'
    )


def create_failure() -> Failure:
    return Failure("builtins.ValueError", "sit", "Traceback\nValueError: sit\n")


def create_details() -> Dict[str, Detail]:
    return {
        "limit": 3,
        "groups": ["sit", "elit"],
        "since": datetime(2026, 9, 2, tzinfo=timezone.utc),
        "window": timedelta(days=1),
        "label": None,
    }


def create_analytic_entry(
    name: str = "amet",
    *,
    result: Union[
        str,
        float,
        datetime,
        timedelta,
        Table,
        Plot,
        Measurement,
        Assessment,
        Distribution,
        Failure,
        None,
    ] = 1,
    description: Optional[str] = None,
    parameters: Optional[Mapping[str, Detail]] = None,
) -> AnalyticEntry:
    return AnalyticEntry(
        name, "Amet", description, parameters or {}, timedelta(seconds=0.5), result
    )


def create_derivation_entry() -> DerivationEntry:
    return DerivationEntry({"node": "lorem"}, {"kept": 1}, timedelta(seconds=1), None)


def create_group_entry() -> GroupEntry:
    return GroupEntry(
        "sit",
        "sit",
        "adipiscing",
        [InputEntry("medrecord", 3, 2)],
        create_derivation_entry(),
        [
            create_analytic_entry(),
            GroupEntry(
                "elit",
                "elit",
                None,
                [],
                None,
                [create_analytic_entry("consectetur", result="dolor")],
            ),
        ],
    )


def create_report() -> Report:
    return Report(
        "lorem",
        None,
        [InputEntry("medrecord", 3, 2)],
        [create_analytic_entry(), create_group_entry()],
        datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        timedelta(seconds=2),
    )


def create_document() -> Dict[str, _Json]:
    return json.loads(create_report()._to_json())


def write_json(directory: str, content: object) -> Path:
    path = Path(directory) / "report.json"
    path.write_text(json.dumps(content))

    return path


class TestDocument(unittest.TestCase):
    def test_init(self) -> None:
        assert _Document({"amet": 1}, "report").path == "report"

    def test_invalid_init(self) -> None:
        with pytest.raises(ValueError, match="expected an object at report"):
            _Document([1], "report")

    def test_items(self) -> None:
        assert _Document({"amet": 1, "elit": None}, "report").items() == [
            ("amet", 1),
            ("elit", None),
        ]

    def test_content(self) -> None:
        assert _Document({"amet": 1}, "report").content("amet") == 1

    def test_invalid_content(self) -> None:
        with pytest.raises(ValueError, match="expected 'amet' at report"):
            _Document({}, "report").content("amet")

    def test_string(self) -> None:
        assert _Document({"amet": "sit"}, "report").string("amet") == "sit"

    def test_invalid_string(self) -> None:
        with pytest.raises(ValueError, match=r"expected a string at report\.amet"):
            _Document({"amet": 1}, "report").string("amet")

    def test_optional_string(self) -> None:
        assert _Document({"amet": None}, "report").optional_string("amet") is None
        assert _Document({"amet": "sit"}, "report").optional_string("amet") == "sit"

    def test_boolean(self) -> None:
        assert _Document({"amet": True}, "report").boolean("amet") is True

    def test_invalid_boolean(self) -> None:
        with pytest.raises(ValueError, match=r"expected a boolean at report\.amet"):
            _Document({"amet": 1}, "report").boolean("amet")

    def test_number(self) -> None:
        assert math.isclose(_Document({"amet": 1}, "report").number("amet"), 1.0)
        assert math.isclose(_Document({"amet": 1.5}, "report").number("amet"), 1.5)

    def test_invalid_number(self) -> None:
        truth = True

        with pytest.raises(ValueError, match=r"expected a number at report\.amet"):
            _Document({"amet": truth}, "report").number("amet")

    def test_optional_number(self) -> None:
        assert _Document({"amet": None}, "report").optional_number("amet") is None
        assert _Document({"amet": 2}, "report").optional_number("amet") == 2

    def test_integer(self) -> None:
        assert _Document({"amet": 1}, "report").integer("amet") == 1

    def test_invalid_integer(self) -> None:
        with pytest.raises(ValueError, match=r"expected an integer at report\.amet"):
            _Document({"amet": 1.5}, "report").integer("amet")

    def test_sequence(self) -> None:
        assert _Document({"amet": [1, 2]}, "report").sequence("amet") == [1, 2]

    def test_invalid_sequence(self) -> None:
        with pytest.raises(ValueError, match=r"expected an array at report\.amet"):
            _Document({"amet": 1}, "report").sequence("amet")

    def test_document(self) -> None:
        assert _Document({"amet": {"sit": 1}}, "report").document("amet").path == (
            "report.amet"
        )

    def test_optional_document(self) -> None:
        assert _Document({"amet": None}, "report").optional_document("amet") is None

        nested = _Document({"amet": {"sit": 1}}, "report").optional_document("amet")

        assert nested is not None
        assert nested.path == "report.amet"


class TestFailure(unittest.TestCase):
    def test_init(self) -> None:
        failure = create_failure()

        assert failure.exception_type == "builtins.ValueError"
        assert failure.message == "sit"
        assert failure.traceback == "Traceback\nValueError: sit\n"

    def test_from_exception(self) -> None:
        try:
            msg = "sit"
            raise ValueError(msg)
        except ValueError as error:
            failure = Failure._from_exception(error)

        assert failure.exception_type == "builtins.ValueError"
        assert failure.message == "sit"
        assert failure.traceback.startswith("Traceback")
        assert failure.traceback.endswith("ValueError: sit\n")

    def test_eq(self) -> None:
        assert create_failure() == create_failure()
        assert create_failure() != Failure("builtins.ValueError", "amet", "")
        assert create_failure() != "sit"

    def test_repr(self) -> None:
        assert repr(create_failure()) == "Failure(builtins.ValueError: sit)"


class TestInputEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = InputEntry("real", 3, 2)

        assert entry.name == "real"
        assert entry.node_count == 3
        assert entry.edge_count == 2

    def test_from_inputs(self) -> None:
        medrecord = create_medrecord()

        assert InputEntry._from_inputs(medrecord) == [InputEntry("medrecord", 3, 2)]
        assert InputEntry._from_inputs(
            {"real": medrecord, "synthetics": {"a": medrecord}, "limit": 1}
        ) == [InputEntry("real", 3, 2), InputEntry("synthetics.a", 3, 2)]
        assert InputEntry._from_inputs([medrecord, [medrecord]]) == [
            InputEntry("0", 3, 2),
            InputEntry("1.0", 3, 2),
        ]
        assert InputEntry._from_inputs("lorem") == []
        assert InputEntry._from_inputs(b"lorem") == []
        assert InputEntry._from_inputs(1) == []

    def test_repr(self) -> None:
        assert repr(InputEntry("medrecord", 3, 2)) == (
            "InputEntry('medrecord', node_count=3, edge_count=2)"
        )

    def test_eq(self) -> None:
        assert InputEntry("real", 3, 2) == InputEntry("real", 3, 2)
        assert InputEntry("real", 3, 2) != InputEntry("real", 3, 1)
        assert InputEntry("real", 3, 2) != "real"


class TestDerivationEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = DerivationEntry(
            {"node": "lorem"}, {"kept": 1}, timedelta(seconds=1), create_failure()
        )

        assert entry.parameters == {"node": "lorem"}
        assert entry.summary == {"kept": 1}
        assert entry.duration == timedelta(seconds=1)
        assert entry.outcome == create_failure()

        entry.parameters.clear()
        entry.summary.clear()

        assert entry.parameters == {"node": "lorem"}
        assert entry.summary == {"kept": 1}

    def test_eq(self) -> None:
        entry = create_derivation_entry()

        assert entry == create_derivation_entry()
        assert entry != DerivationEntry({}, {"kept": 1}, timedelta(seconds=1), None)
        assert entry != DerivationEntry(
            {"node": "lorem"}, {}, timedelta(seconds=1), None
        )
        assert entry != DerivationEntry(
            {"node": "lorem"}, {"kept": 1}, timedelta(seconds=1), create_failure()
        )
        assert entry != "sit"

    def test_repr(self) -> None:
        assert repr(DerivationEntry({}, {}, timedelta(seconds=1), None)) == (
            "DerivationEntry(completed in 0:00:01)"
        )
        assert repr(DerivationEntry({}, {}, timedelta(), create_failure())) == (
            "DerivationEntry(failed in 0:00:00)"
        )


class TestAnalyticEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = create_analytic_entry(description="adipiscing", parameters={"limit": 3})

        assert entry.name == "amet"
        assert entry.title == "Amet"
        assert entry.description == "adipiscing"
        assert entry.parameters == {"limit": 3}
        assert entry.duration == timedelta(seconds=0.5)
        assert entry.result == 1

        entry.parameters.clear()

        assert entry.parameters == {"limit": 3}

    def test_result(self) -> None:
        assert create_analytic_entry(result=1).result == 1
        assert create_analytic_entry(result=create_failure()).result == create_failure()

    def test_eq(self) -> None:
        assert create_analytic_entry() == create_analytic_entry()
        assert create_analytic_entry() != create_analytic_entry(result=2)
        assert create_analytic_entry() != create_analytic_entry(name="elit")
        assert create_analytic_entry() != create_analytic_entry(parameters={"limit": 3})
        assert create_analytic_entry() != "amet"

    def test_repr(self) -> None:
        assert repr(create_analytic_entry()) == "AnalyticEntry('amet', 1)"


class TestGroupEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = create_group_entry()

        assert entry.name == "sit"
        assert entry.title == "sit"
        assert entry.description == "adipiscing"
        assert entry.inputs == [InputEntry("medrecord", 3, 2)]
        assert entry.derivation == create_derivation_entry()
        assert len(entry.entries) == 2

        entry.inputs.clear()
        entry.entries.clear()

        assert len(entry.inputs) == 1
        assert len(entry.entries) == 2

    def test_group(self) -> None:
        assert create_group_entry().group("elit").name == "elit"

    def test_invalid_group(self) -> None:
        with pytest.raises(KeyError, match="cannot find group 'amet'"):
            create_group_entry().group("amet")

    def test_analytic(self) -> None:
        assert create_group_entry().analytic("amet") == create_analytic_entry()

    def test_invalid_analytic(self) -> None:
        with pytest.raises(KeyError, match="cannot find analytic 'elit'"):
            create_group_entry().analytic("elit")

    def test_analytics(self) -> None:
        assert list(create_group_entry().analytics()) == [
            (("amet",), create_analytic_entry()),
            (
                ("elit", "consectetur"),
                create_analytic_entry("consectetur", result="dolor"),
            ),
        ]

    def test_eq(self) -> None:
        assert create_group_entry() == create_group_entry()
        assert create_group_entry() != GroupEntry("sit", "sit", None, [], None, [])
        assert create_group_entry() != GroupEntry(
            "sit", "sit", None, create_group_entry().inputs, None, []
        )
        assert create_group_entry() != "sit"

    def test_repr(self) -> None:
        assert repr(create_group_entry()) == "GroupEntry('sit', entries=2)"


class TestReport(unittest.TestCase):
    def test_init(self) -> None:
        report = create_report()

        assert report.name == "lorem"
        assert report.description is None
        assert report.started_at == datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc)
        assert report.duration == timedelta(seconds=2)
        assert report.inputs == [InputEntry("medrecord", 3, 2)]
        assert [entry.name for entry in report.entries] == ["amet", "sit"]
        assert report.analytic("amet").result == 1
        assert [path for path, _ in report.analytics()] == [
            ("amet",),
            ("sit", "amet"),
            ("sit", "elit", "consectetur"),
        ]
        assert (
            report.group("sit").group("elit").analytic("consectetur").result == "dolor"
        )

    def test_to_json(self) -> None:
        rows: List[List[Union[str, int, float, bool, datetime, timedelta, None]]] = [
            ["sed", 1, 1.5, True, None],
            [
                datetime(2026, 9, 2, tzinfo=timezone.utc),
                timedelta(seconds=1.5),
                math.inf,
                -math.inf,
                "do",
            ],
        ]
        report = Report(
            "lorem",
            None,
            [InputEntry("real", 3, 2)],
            [
                create_analytic_entry("string", result="sed"),
                create_analytic_entry("integer", result=1),
                create_analytic_entry("float", result=1.5),
                create_analytic_entry("boolean", result=True),
                create_analytic_entry("null", result=None),
                create_analytic_entry(
                    "datetime", result=datetime(2026, 9, 2, tzinfo=timezone.utc)
                ),
                create_analytic_entry("timedelta", result=timedelta(seconds=1.5)),
                create_analytic_entry("infinity", result=math.inf),
                create_analytic_entry(
                    "table",
                    result=Table(["a", "b", "c", "d", "e"], rows),
                    description="sed",
                ),
                create_analytic_entry("failure", result=create_failure()),
                GroupEntry(
                    "failed",
                    "failed",
                    None,
                    [],
                    DerivationEntry({}, {}, timedelta(seconds=1), create_failure()),
                    [],
                ),
                create_group_entry(),
                create_analytic_entry("plot", result=create_plot()),
                create_analytic_entry(
                    "measurement",
                    result=Measurement(0.87, lower=0.82, upper=0.91, p_value=0.003),
                ),
                create_analytic_entry(
                    "assessment", result=Assessment(3, "at least 5", passed=False)
                ),
                create_analytic_entry(
                    "distribution", result=Distribution([4, 1, 3, 2, 10])
                ),
                create_analytic_entry(
                    "parameterized", result=1, parameters=create_details()
                ),
                GroupEntry(
                    "detailed",
                    "detailed",
                    None,
                    [],
                    DerivationEntry(
                        create_details(), {"kept": [1, 2]}, timedelta(seconds=1), None
                    ),
                    [],
                ),
                create_analytic_entry("bare", result=Measurement(1.0)),
                create_analytic_entry(
                    "dated",
                    result=Assessment(
                        datetime(2026, 9, 2, tzinfo=timezone.utc),
                        "after 2026",
                        passed=True,
                    ),
                ),
            ],
            datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
            timedelta(seconds=2),
        )

        document = json.loads(report._to_json())
        entries = document["entries"]
        assert entries[0]["result"] == "sed"
        assert entries[18]["result"] == {
            "kind": "measurement",
            "value": 1.0,
            "lower": None,
            "upper": None,
            "p_value": None,
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
        assert entries[9]["result"]["kind"] == "failure"
        assert entries[10]["derivation"]["outcome"]["kind"] == "failure"
        assert entries[11]["derivation"]["parameters"] == {"node": "lorem"}
        assert entries[11]["derivation"]["summary"] == {"kept": 1}
        assert entries[12]["result"] == {"kind": "plot", "svg": create_plot().svg}
        assert entries[13]["result"] == {
            "kind": "measurement",
            "value": 0.87,
            "lower": 0.82,
            "upper": 0.91,
            "p_value": 0.003,
        }
        assert entries[14]["result"] == {
            "kind": "assessment",
            "value": 3,
            "requirement_label": "at least 5",
            "passed": False,
        }
        assert entries[15]["result"]["values"] == [4.0, 1.0, 3.0, 2.0, 10.0]
        assert entries[15]["result"]["summary"]["count"] == 5
        assert math.isclose(entries[15]["result"]["summary"]["median"], 3.0)
        assert len(entries[15]["result"]["histogram"]) == 3
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
                    "measurement", result=Measurement(0.5, 0.4, 0.6, 0.01)
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
            ],
            datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
            timedelta(seconds=2),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            rich.to_json(path)
            loaded = Report.from_json(path)

        assert loaded == rich

    def test_invalid_from_json(self) -> None:
        document = create_document()
        analytic = create_analytic_entry()._to_document()
        group = create_group_entry()._to_document()
        broken: List[Tuple[object, str]] = [
            ([], "expected an object at report"),
            (
                {**document, "entries": [{**analytic, "kind": "lorem"}]},
                "expected an analytic or a group at report.entries",
            ),
            (
                {**document, "started_at": "lorem"},
                "Invalid isoformat string: 'lorem' at report",
            ),
            (
                {**document, "duration": math.inf},
                "cannot convert float infinity to integer at report",
            ),
            (
                {**document, "entries": [{**analytic, "duration": 1e30}]},
                "Python int too large to convert to C int at report.entries",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {
                                "kind": "timedelta",
                                "days": 10**9,
                                "seconds": 0,
                                "microseconds": 0,
                            },
                        }
                    ],
                },
                "must have magnitude <= 999999999 at report.entries.result",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {
                                "kind": "timedelta",
                                "days": 1.5,
                                "seconds": 0,
                                "microseconds": 0,
                            },
                        }
                    ],
                },
                "expected an integer at report.entries.result.days",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {"kind": "float", "value": "lorem"},
                        }
                    ],
                },
                "could not convert string to float: 'lorem' at report",
            ),
            (
                {**document, "entries": [{**analytic, "result": {"kind": "lorem"}}]},
                "expected a value at report.entries.result",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {"kind": "table", "headings": [1], "rows": []},
                        }
                    ],
                },
                "expected a string at report.entries.result.headings",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {
                                "kind": "table",
                                "headings": ["a"],
                                "rows": [[1, 2]],
                            },
                        }
                    ],
                },
                "one value per heading",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {
                                "kind": "distribution",
                                "values": [],
                                "bins": None,
                            },
                        }
                    ],
                },
                "at least one value",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **analytic,
                            "result": {
                                "kind": "distribution",
                                "values": [1.0],
                                "bins": 0,
                            },
                        }
                    ],
                },
                "at least one bin at report.entries.result",
            ),
            (
                {
                    **document,
                    "entries": [
                        {**analytic, "parameters": {"limit": {"kind": "lorem"}}}
                    ],
                },
                "expected a value at report.entries.parameters.limit",
            ),
            (
                {
                    **document,
                    "entries": [
                        {
                            **group,
                            "derivation": {
                                "parameters": {},
                                "summary": {},
                                "duration": 0.0,
                                "outcome": {"kind": "lorem"},
                            },
                        }
                    ],
                },
                "expected a failure at report.entries.derivation.outcome",
            ),
        ]

        for content, message in broken:
            with tempfile.TemporaryDirectory() as directory:
                path = write_json(directory, content)

                with pytest.raises(ValueError, match=message):
                    Report.from_json(path)

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

    def test_repr(self) -> None:
        assert repr(create_report()) == "Report('lorem', entries=2)"


if __name__ == "__main__":
    unittest.main()
