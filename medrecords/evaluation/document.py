"""Typesetting of reports to PDF through Typst."""

from __future__ import annotations

import copy
import json
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Final, Optional, TypedDict, Union

import typst

if TYPE_CHECKING:
    import os

    from medrecords.evaluation.report import Report


class Company(TypedDict):
    """The company block a template prints on the cover and in the footer."""

    name: str
    street: str
    city: str
    web: str
    mail: str


class _Options(TypedDict):
    """The settings a template reads from ``sys.inputs.options``."""

    kind: str
    cover: bool
    contents: bool
    section_breaks: bool
    parameter_lines: bool
    failure_details: bool
    run_details: bool
    company: Optional[Company]
    version: str


#: The company block a document prints unless another one is given.
_DEFAULT_COMPANY: Final[Company] = {
    "name": "MedModels GmbH",
    "street": "Prinz-Eugen-Straße 17",
    "city": "13347 Berlin",
    "web": "medmodels.de",
    "mail": "info@medmodels.de",
}

#: The directory holding the bundled template, its logo and its fonts.
_TEMPLATE: Final[Path] = Path(__file__).parent / "template"

#: The logo a document prints unless another one is given, or none.
_DEFAULT_LOGO: Final[Path] = _TEMPLATE / "logo.svg"

#: The directory the bundled template's Typst packages are loaded from, offline.
_PACKAGES: Final[Path] = _TEMPLATE / "packages"


class Document:
    """A typeset rendering of a report."""

    _report: Report
    _template: Optional[Path]
    _logo: Optional[Path]
    _company: Optional[Company]
    _kind: str
    _cover: bool
    _contents: bool
    _section_breaks: bool
    _parameter_lines: bool
    _failure_details: bool
    _run_details: bool

    def __init__(
        self,
        report: Report,
        *,
        template: Optional[Union[str, os.PathLike[str]]] = None,
        logo: Optional[Union[str, os.PathLike[str]]] = _DEFAULT_LOGO,
        company: Optional[Company] = _DEFAULT_COMPANY,
        kind: str = "Evaluation report",
        cover: bool = True,
        contents: bool = True,
        section_breaks: bool = True,
        parameter_lines: bool = True,
        failure_details: bool = True,
        run_details: bool = False,
    ) -> None:
        """Initializes a document of a report.

        Args:
            report (Report): The report to typeset.
            template (Optional[Union[str, os.PathLike[str]]]): The Typst file to
                compile, compiled with its parent directory as root, or None for
                the bundled template. Defaults to None.
            logo (Optional[Union[str, os.PathLike[str]]]): The SVG file to print
                as the logo, or None for a document without one. Defaults to the
                logo of the bundled template.
            company (Optional[Company]): The company block to print on the cover
                and in the footer, or None for none. Defaults to the MedModels
                one.
            kind (str): The kind of document, printed above the title. Defaults
                to "Evaluation report".
            cover (bool): Whether to open with a cover page of its own, holding
                the logo and the company, the kind, the title, the description,
                the report's parameters, the date of the run and the medrecords
                version; without one, the first page opens with them. Defaults
                to True.
            contents (bool): Whether to print the contents, listing the headings
                of the outer three levels with their pages. Defaults to True.
            section_breaks (bool): Whether to start a new page for every
                top-level section. Defaults to True.
            parameter_lines (bool): Whether to print the parameters of every
                analytic and derivation under its title. Defaults to True.
            failure_details (bool): Whether to print the exception type and
                message of every failure, or only that the entry was not
                computed. Defaults to True.
            run_details (bool): Whether to end with an appendix holding when the
                run started, how long it took and the time every entry took, and
                to print the summary of every derivation under its group.
                Defaults to False.
        """
        self._report = report
        self._template = None if template is None else Path(template)
        self._logo = None if logo is None else Path(logo)
        self._company = copy.copy(company)
        self._kind = kind
        self._cover = cover
        self._contents = contents
        self._section_breaks = section_breaks
        self._parameter_lines = parameter_lines
        self._failure_details = failure_details
        self._run_details = run_details

    def to_pdf(self, path: Union[str, os.PathLike[str]]) -> None:
        """Typesets the document to a PDF.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the PDF to write.
        """
        inputs = {
            "report": self._report._to_json(),
            "logo": self._logo_text(),
            "options": json.dumps(self._options()),
        }

        if self._template is None:
            typst.compile(
                _TEMPLATE / "report.typ",
                output=Path(path),
                font_paths=[_TEMPLATE],
                ignore_system_fonts=True,
                sys_inputs=inputs,
                package_path=_PACKAGES,
            )
        else:
            typst.compile(
                self._template,
                output=Path(path),
                root=self._template.parent,
                font_paths=[_TEMPLATE],
                sys_inputs=inputs,
                package_path=_PACKAGES,
            )

    def _logo_text(self) -> str:
        if self._logo is None:
            return ""

        return self._logo.read_text(encoding="utf-8")

    def _options(self) -> _Options:
        return {
            "kind": self._kind,
            "cover": self._cover,
            "contents": self._contents,
            "section_breaks": self._section_breaks,
            "parameter_lines": self._parameter_lines,
            "failure_details": self._failure_details,
            "run_details": self._run_details,
            "company": self._company,
            "version": version("medrecords"),
        }

    def __repr__(self) -> str:
        """Returns the string representation of the Document.

        Returns:
            str: The name of the report the document typesets.
        """
        return f"Document({self._report.name!r})"
