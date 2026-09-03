import json
import math
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib.resources import files
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Union
from unittest.mock import patch

import pytest
import typst

from medrecords.evaluation.analytic import (
    Assessment,
    Distribution,
    Measurement,
    Plot,
    ReportValue,
    Table,
)
from medrecords.evaluation.document import _DEFAULT_COMPANY, Company, Document
from medrecords.evaluation.report import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    InputEntry,
    Report,
    _Json,
)

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    '<rect width="10" height="10" fill="black"/></svg>'
)


class TypstCall(TypedDict):
    source: Path
    output: Path
    root: Optional[Path]
    font_paths: List[Path]
    ignore_system_fonts: bool
    inputs: Dict[str, str]
    options: Dict[str, _Json]


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
            create_entry("failure", Failure("builtins.ValueError", "sit", "")),
            create_entry("tiny", Measurement(0.5, p_value=1e-30)),
            create_entry("huge", 1e300),
            create_entry("negative", timedelta(seconds=-5)),
            create_entry("infinite", math.inf),
            create_entry("undefined", math.nan),
            create_entry("wide", Distribution([0.0, 2000000.0, 3000000.0])),
            create_entry("same", Distribution([7.5, 7.5])),
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
            "company": _DEFAULT_COMPANY,
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
            "company": create_company(),
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
