import json
import math
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Union
from unittest.mock import patch

import pytest
import typst

from medrecords.evaluation._json import Json
from medrecords.evaluation.analytic import (
    Assessment,
    Counts,
    Distribution,
    Histogram,
    Measurement,
    Plot,
    ReportValue,
    Table,
    Unit,
)
from medrecords.evaluation.document import _DEFAULT_COMPANY, Company, Document
from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    KeyedResult,
)
from medrecords.evaluation.report import Report

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10" fill="black"/></svg>'
)

EDGES = [10.0, 20.0, 30.0, 40.0, 50.0]


class TypstCall(TypedDict):
    source: Path
    output: Path
    root: Optional[Path]
    font_paths: List[Path]
    ignore_system_fonts: bool
    inputs: Dict[str, str]
    options: Dict[str, Json]


class RecordingTypst:
    def __init__(self) -> None:
        self.calls: List[TypstCall] = []

    def compile(
        self,
        source: Path,
        output: Path,
        root: Optional[Path] = None,
        font_paths: Optional[List[Path]] = None,
        *,
        ignore_system_fonts: bool = False,
        sys_inputs: Optional[Dict[str, str]] = None,
    ) -> None:
        self.calls.append(
            {
                "source": source,
                "output": output,
                "root": root,
                "font_paths": [] if font_paths is None else font_paths,
                "ignore_system_fonts": ignore_system_fonts,
                "inputs": {} if sys_inputs is None else sys_inputs,
                "options": {},
            }
        )


def create_entry(name: str, result: Union[ReportValue, Failure]) -> AnalyticEntry:
    return AnalyticEntry(
        name, name.capitalize(), None, {}, timedelta(seconds=0.5), result
    )


def create_keyed(
    name: str,
    *results: Union[ReportValue, Failure],
) -> KeyedAnalyticEntry:
    return KeyedAnalyticEntry(
        name,
        name.capitalize(),
        None,
        {},
        [
            KeyedResult(key, timedelta(seconds=0.25), result)
            for key, result in zip(("real", "synthetic", 2024), results, strict=False)
        ],
    )


def create_codes(start: int, total: int) -> Counts:
    return Counts(
        {f"C{code:02d}": 100 - code for code in range(start, start + 20)}, total
    )


def create_across() -> GroupEntry:
    return GroupEntry(
        "across",
        "Cohort",
        "sit amet",
        [InputEntry("real", 3, 2), InputEntry("synthetic", 2, 1)],
        DerivationEntry({}, {}, timedelta(seconds=1), None),
        [
            create_keyed("count", 3, 2),
            create_keyed(
                "histograms",
                Histogram.from_values([5.0, 12.0, 33.0, 34.0, 45.0, 51.0], EDGES),
                Histogram.from_values([22.0, 28.0, 35.0, 44.0], EDGES),
                Histogram(EDGES, [0, 0, 0, 0]),
            ),
            create_keyed(
                "differing",
                Histogram.from_values([12.0], EDGES),
                Histogram.from_values([1.0, 2.5], [0.0, 1.0, 2.0, 3.0]),
            ),
            create_keyed(
                "half_broken",
                Histogram.from_values([12.0], EDGES),
                Failure("builtins.ValueError", "sit", ""),
            ),
            create_keyed(
                "sexes",
                Counts({"F": 162, "M": 137, None: 1}),
                Counts({"M": 140, "F": 150}),
            ),
            create_keyed("codes", create_codes(0, 2500), create_codes(5, 2300)),
            create_keyed(
                "listed",
                Counts({"I10": 50, "E78": 40}, 300),
                Counts({"I10": 20}, 100),
                Counts({}),
            ),
            create_keyed("unlisted", Counts({}), Counts({}, 3)),
            create_keyed("nothing", Counts({}), Counts({})),
            create_keyed("share", Measurement(0.5, lower=0.2, upper=0.8), 0.5),
            create_keyed(
                "percent",
                Measurement(0.5, lower=0.2, upper=0.8, unit=Unit.Share),
                Measurement(0.1, unit=Unit.Points),
            ),
            create_keyed(
                "check",
                Assessment(3, "at least 3", passed=True),
                Assessment(2, "at least 3", passed=False),
            ),
            create_keyed(
                "complete",
                Assessment(0.75, "at least 50.0%", passed=True, unit=Unit.Share),
                Assessment(0.25, "at least 50.0%", passed=False, unit=Unit.Share),
            ),
            create_keyed("broken", 3, Failure("builtins.ValueError", "sit", "")),
            create_keyed(
                "ages", Distribution([34.0, 41.0, 45.0]), Distribution([30.0, 80.0])
            ),
            create_keyed("same", Distribution([7.5]), Distribution([7.5, 7.5])),
            create_keyed("tables", Table(["a"], [[1], [2]]), Table(["a"], [[3]])),
            create_keyed("mixed", Table(["a"], [[1]]), Table(["b"], [[2]])),
            create_keyed("pictures", Plot(SVG), Plot(SVG)),
            create_keyed("empty", Table([], []), Table([], [])),
            create_keyed("years", 1, 2, 3),
            KeyedAnalyticEntry("none", "None", None, {}, []),
            KeyedGroupEntry(
                "older",
                "older",
                "dolor",
                [InputEntry("real", 1, 0)],
                {
                    "real": DerivationEntry(
                        {"seed": 7}, {"kept": 1}, timedelta(seconds=1), None
                    ),
                    "synthetic": DerivationEntry(
                        {}, {}, timedelta(), Failure("E", "m", "")
                    ),
                    2024: DerivationEntry({}, {}, timedelta(), None),
                },
                [create_keyed("count", 1)],
            ),
            KeyedGroupEntry("by_sex", "by_sex", None, [], {}, []),
        ],
    )


def create_report() -> Report:
    truth = True

    return Report(
        "lorem",
        "adipiscing",
        [InputEntry("medrecord", 3, 2)],
        [
            create_entry("integer", 1),
            create_entry("string", "sed"),
            create_entry("null", None),
            create_entry("datetime", datetime(2026, 9, 2, tzinfo=timezone.utc)),
            create_entry("timedelta", timedelta(seconds=1.5)),
            create_entry("measurement", Measurement(0.87, lower=0.82, upper=0.91)),
            create_entry("lower_only", Measurement(1.0, lower=0.5, p_value=0.05)),
            create_entry("upper_only", Measurement(1.0, upper=1.5)),
            create_entry("passed", Assessment(5, "at least 5", passed=True)),
            create_entry("failed", Assessment(3, "at least 5", passed=False)),
            create_entry(
                "share", Measurement(0.87, lower=0.82, upper=0.91, unit=Unit.Share)
            ),
            create_entry("points", Measurement(0.05, unit=Unit.Points)),
            create_entry(
                "complete",
                Assessment(0.75, "at least 50.0%", passed=True, unit=Unit.Share),
            ),
            create_entry("failure", Failure("builtins.ValueError", "sit", "")),
            create_entry("tiny", Measurement(0.5, p_value=1e-30)),
            create_entry("huge", 1e300),
            create_entry("negative", timedelta(seconds=-5)),
            create_entry("infinite", math.inf),
            create_entry("undefined", math.nan),
            create_entry("wide", Distribution([0.0, 2000000.0, 3000000.0])),
            create_entry("same", Distribution([7.5, 7.5])),
            create_entry(
                "histogram",
                Histogram.from_values([5.0, 12.0, 33.0, 34.0, 45.0, 51.0], EDGES),
            ),
            create_entry(
                "one_bin", Histogram([0.0, 1.0], [3], below_count=1, above_count=2)
            ),
            create_entry(
                "many_bins",
                Histogram.from_values(
                    [float(value) for value in range(1000)],
                    [float(edge) for edge in range(0, 1001, 10)],
                ),
            ),
            create_entry("empty_histogram", Histogram(EDGES, [0, 0, 0, 0])),
            create_entry("counts", Counts({"F": 162, "M": 137, None: 1})),
            create_entry("many_counts", create_codes(0, 2500)),
            create_entry("listed", Counts({"I10": 50, "E78": 40}, 300)),
            create_entry("empty_counts", Counts({})),
            create_entry("unlisted", Counts({}, 4)),
            GroupEntry(
                "amet",
                "amet",
                None,
                [InputEntry("medrecord", 3, 2)],
                DerivationEntry(
                    {"seed": 7}, {"kept": [1, 2]}, timedelta(seconds=1), None
                ),
                [
                    create_entry(
                        "table",
                        Table(["a", "b"], [[1, None], [4, 2.5]]),
                    ),
                    create_entry(
                        "long",
                        Table(["a"], [[row] for row in range(20)]),
                    ),
                    create_entry(
                        "shares",
                        Table(
                            ["value", "count", "share"],
                            [["F", 3, 0.75], ["M", 1, 0.25], [None, 0, None]],
                            units={"share": Unit.Share},
                        ),
                    ),
                    create_entry("plot", Plot(SVG)),
                    create_entry("distribution", Distribution([4, 1, 3, 2, 10])),
                    GroupEntry(
                        "keyed",
                        "keyed",
                        None,
                        [InputEntry("medrecord", 1, 0)],
                        None,
                        [create_entry("count", 1)],
                    ),
                ],
            ),
            GroupEntry(
                "failed_group",
                "failed_group",
                None,
                [],
                DerivationEntry({}, {}, timedelta(seconds=1), Failure("E", "m", "")),
                [],
            ),
            GroupEntry(
                "failed_derivation",
                "failed_derivation",
                None,
                [],
                DerivationEntry({}, {}, timedelta(), Failure("E", "m", "")),
                [],
            ),
            GroupEntry("vacant", "Vacant", "consectetur", [], None, []),
            create_across(),
            create_entry("empty_table", Table([], [])),
            create_entry("truth", truth),
            create_entry("ratio", 1.5),
            create_entry("nan", math.nan),
        ],
        datetime(2026, 9, 2, 10, 0, tzinfo=timezone.utc),
        timedelta(seconds=2),
    )


def create_company() -> Company:
    return {
        "name": "Lorem Clinic",
        "street": "Ipsum 1",
        "city": "Dolor",
        "web": "lorem.example",
        "mail": "sit@lorem.example",
    }


def create_call(document: Document) -> TypstCall:
    typst = RecordingTypst()

    with patch.dict(sys.modules, {"typst": typst}):
        document.to_pdf("report.pdf")

    call = typst.calls[0]
    call["options"] = json.loads(call["inputs"]["options"])
    return call


def create_page_count(pdf: bytes) -> int:
    match = re.search(rb"/Type\s*/Pages\s*/Count\s+(\d+)", pdf)
    assert match is not None
    return int(match.group(1))


class TestDocument(unittest.TestCase):
    def test_init(self) -> None:
        call = create_call(Document(create_report()))

        assert call["source"].name == "report.typ"
        assert call["output"] == Path("report.pdf")
        assert call["inputs"]["logo"].startswith("<svg")
        assert call["root"] is None
        assert [path.name for path in call["font_paths"]] == ["template"]
        assert call["ignore_system_fonts"] is True
        assert json.loads(call["inputs"]["report"])["name"] == "lorem"
        assert call["options"] == {
            "kind": "Evaluation report",
            "run_details": True,
            "section_breaks": True,
            "parameter_lines": True,
            "failure_details": True,
            "company": _DEFAULT_COMPANY,
            "version": version("medrecords"),
        }

        company = create_company()
        call = create_call(
            Document(
                create_report(),
                template="amet/template.typ",
                logo=None,
                company=company,
                kind="Release check",
                run_details=False,
                section_breaks=False,
                parameter_lines=False,
                failure_details=False,
            )
        )
        company["name"] = "sit"

        assert call["source"] == Path("amet/template.typ")
        assert call["root"] == Path("amet")
        assert call["ignore_system_fonts"] is False
        assert call["inputs"]["logo"] == ""
        assert call["options"] == {
            "kind": "Release check",
            "run_details": False,
            "section_breaks": False,
            "parameter_lines": False,
            "failure_details": False,
            "company": create_company(),
            "version": version("medrecords"),
        }

        with tempfile.TemporaryDirectory() as directory:
            logo = Path(directory) / "logo.svg"
            logo.write_text(SVG)
            typst = RecordingTypst()

            with patch.dict(sys.modules, {"typst": typst}):
                Document(create_report(), logo=logo).to_pdf("report.pdf")

        assert typst.calls[0]["inputs"]["logo"] == SVG

    def test_to_pdf(self) -> None:
        report = create_report()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"

            Document(report).to_pdf(path)
            default = path.read_bytes()

            Document(
                report,
                logo=None,
                company=create_company(),
                kind="Release check",
                run_details=False,
                section_breaks=False,
                parameter_lines=False,
                failure_details=False,
            ).to_pdf(path)
            configured = path.read_bytes()

            template = Path(directory) / "template.typ"
            template.write_text(
                "#let report = json(bytes(sys.inputs.report))\n= #report.name\n"
            )
            Document(report, template=template, logo=None).to_pdf(path)
            custom = path.read_bytes()

        assert default.startswith(b"%PDF")
        assert b"Run details" in default
        assert b"MedModels GmbH" in default
        assert b"Lorem Clinic" not in default
        assert configured.startswith(b"%PDF")
        assert b"Run details" not in configured
        assert b"Lorem Clinic" in configured
        assert create_page_count(configured) < create_page_count(default)
        assert custom.startswith(b"%PDF")
        assert create_page_count(custom) == 1

        headings = json.loads(
            typst.query(
                str(
                    files("medrecords.evaluation")
                    .joinpath("template")
                    .joinpath("report.typ")
                ),
                "heading",
                sys_inputs=create_call(Document(report))["inputs"],
            )
        )

        assert [
            (heading["level"], heading["body"]["text"]) for heading in headings
        ] == [
            (1, "amet"),
            (2, "keyed"),
            (1, "failed_group"),
            (1, "failed_derivation"),
            (1, "Vacant"),
            (1, "Cohort"),
            (2, "older"),
            (2, "by_sex"),
            (1, "Run details"),
        ]

    def test_invalid_to_pdf(self) -> None:
        with (
            patch.dict(sys.modules, {"typst": None}),
            pytest.raises(ImportError, match=r"medrecords\[pdf\]"),
        ):
            Document(create_report()).to_pdf("report.pdf")

    def test_repr(self) -> None:
        assert repr(Document(create_report())) == "Document('lorem')"


if __name__ == "__main__":
    unittest.main()
