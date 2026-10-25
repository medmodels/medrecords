import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Union

from graphrecords import Value

from medrecords.evaluation.analytic import (
    Arrangement,
    Assessment,
    Bins,
    Counts,
    Detail,
    Distribution,
    Histogram,
    Measurement,
    Plot,
    Scale,
    Scatter,
    Table,
    Unit,
)
from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    KeyedResult,
    Layout,
)
from medrecords.evaluation.report import Report
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
    name: Value = "amet",
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
        Histogram,
        Counts,
        Scatter,
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


def create_keyed_result(
    key: Union[str, int, datetime] = "real",
    *,
    result: Union[int, Distribution, Histogram, Counts, Table, Failure] = 1,
) -> KeyedResult:
    return KeyedResult(key, timedelta(seconds=0.25), result)


def create_keyed_analytic_entry(
    name: Union[str, int] = "amet",
    *,
    results: Optional[List[KeyedResult]] = None,
) -> KeyedAnalyticEntry:
    if results is None:
        results = [create_keyed_result(), create_keyed_result("synthetic", result=2)]

    return KeyedAnalyticEntry(name, "Amet", None, {"limit": 3}, results)


def create_keyed_group_entry() -> KeyedGroupEntry:
    return KeyedGroupEntry(
        "sit",
        "sit",
        "adipiscing",
        [InputEntry("real", 3, 2), InputEntry("synthetic", 2, 1)],
        {
            "real": create_derivation_entry(),
            "synthetic": DerivationEntry({}, {}, timedelta(), create_failure()),
        },
        [
            create_keyed_analytic_entry(),
            KeyedGroupEntry(
                "elit",
                "elit",
                None,
                [],
                {},
                [create_keyed_analytic_entry("consectetur")],
            ),
        ],
    )


def create_report() -> Report:
    return Report(
        "lorem",
        None,
        [InputEntry("medrecord", 3, 2)],
        [
            create_analytic_entry(),
            create_group_entry(),
            GroupEntry(
                "across",
                "across",
                None,
                [InputEntry("real", 3, 2), InputEntry("synthetic", 2, 1)],
                create_derivation_entry(),
                [create_keyed_analytic_entry(), create_keyed_group_entry()],
            ),
        ],
        datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        timedelta(seconds=2),
    )


def write_json(directory: str, content: object) -> Path:
    path = Path(directory) / "report.json"
    path.write_text(json.dumps(content))

    return path


def create_rich_report() -> Report:
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
    return Report(
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
            create_analytic_entry(2023, result=1),
            create_keyed_analytic_entry(
                "shared",
                results=[
                    create_keyed_result(result=Distribution([1.0, 2.0, 3.0])),
                    create_keyed_result(
                        datetime(2026, 9, 2, tzinfo=timezone.utc),
                        result=Distribution([8.0, 9.0]),
                    ),
                ],
            ),
            create_keyed_analytic_entry(
                "unshared",
                results=[
                    create_keyed_result(result=Distribution([1.0, 2.0])),
                    create_keyed_result("synthetic", result=create_failure()),
                ],
            ),
            create_keyed_group_entry(),
            create_analytic_entry(
                "histogram",
                result=Histogram.from_values([4, 1, 3, 2, 10], [0.0, 5.0, 10.0]),
            ),
            create_analytic_entry(
                "counts",
                result=Counts(
                    {"sit": 2, datetime(2026, 9, 2, tzinfo=timezone.utc): 1}, 4
                ),
            ),
            create_analytic_entry("empty", result=Histogram([0.0, 1.0], [0])),
            create_analytic_entry(
                "outside",
                result=Histogram([0.0, 1.0], [3], below_count=1, above_count=2),
            ),
            create_analytic_entry(
                "shares",
                result=Table(
                    ["value", "share"],
                    [["sit", 0.75]],
                    units={"share": Unit.Share},
                ),
            ),
            create_analytic_entry(
                "share", result=Measurement(0.5, lower=0.4, unit=Unit.Share)
            ),
            create_analytic_entry(
                "complete",
                result=Assessment(
                    0.75, "at least 50.0%", passed=True, unit=Unit.Points
                ),
            ),
            create_analytic_entry(
                "scatter",
                result=Scatter(
                    [(0.1, 0.2), (0.5, 0.4)],
                    x_label="share of real patients",
                    y_label="share of synthetic patients",
                    x_scale=Scale.Logarithmic,
                    labels={1: "lorem"},
                    diagonal=True,
                ),
            ),
            create_analytic_entry(
                "paths",
                result=Table(
                    ["entry", "value"], [[("sit", 2024), 1], [("across",), None]]
                ),
            ),
            create_analytic_entry(
                "labelled",
                result=Histogram.from_values(
                    [2.0, 20.0],
                    [1.0, 10.0, 100.0],
                    scale=Scale.Logarithmic,
                    value_label="dose in mg",
                    count_label="prescriptions",
                    arrangement=Arrangement.Panels,
                ),
            ),
            create_analytic_entry(
                "binned",
                result=Distribution(
                    [1.0, 20.0, 300.0],
                    bins=Bins(count=3, scale=Scale.Logarithmic, outside_share=0.0),
                    value_label="days",
                    count_label="intervals",
                    arrangement=Arrangement.Overlay,
                ),
            ),
            create_analytic_entry(
                "categories",
                result=Counts(
                    {"sit": 2},
                    3,
                    value_label="diagnosis",
                    count_label="patients",
                    remainder_label="less frequent values",
                    arrangement=Arrangement.Overlay,
                ),
            ),
            GroupEntry(
                "inline",
                "Inline",
                None,
                [],
                None,
                [create_analytic_entry()],
                layout=Layout.Inline,
            ),
            KeyedGroupEntry(
                "appendix",
                "Appendix",
                None,
                [],
                {},
                [create_keyed_analytic_entry()],
                layout=Layout.Appendix,
            ),
        ],
        datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        timedelta(seconds=2),
        parameters={"seed": 7, "records": ["real", "synthetic"]},
    )
