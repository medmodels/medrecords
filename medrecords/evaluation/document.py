"""Typesetting of reports to PDF through Typst."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING, Final, Optional, TypedDict, Union

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
    run_details: bool
    section_breaks: bool
    company: Company


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


class Document:
    """A typeset rendering of a report."""

    _report: Report
    _template: Optional[Path]
    _logo: Optional[Path]
    _company: Company
    _kind: str
    _run_details: bool
    _section_breaks: bool

    def __init__(
        self,
        report: Report,
        *,
        template: Optional[Union[str, os.PathLike[str]]] = None,
        logo: Optional[Union[str, os.PathLike[str]]] = _DEFAULT_LOGO,
        company: Company = _DEFAULT_COMPANY,
        kind: str = "Evaluation report",
        run_details: bool = True,
        section_breaks: bool = True,
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
            company (Company): The company block to print. Defaults to the
                MedModels one.
            kind (str): The kind of document, printed above the title. Defaults
                to "Evaluation report".
            run_details (bool): Whether to print the appendix timing every
                analytic and every derivation. Defaults to True.
            section_breaks (bool): Whether to start a new page for every
                top-level group. Defaults to True.
        """
        self._report = report
        self._template = None if template is None else Path(template)
        self._logo = None if logo is None else Path(logo)
        self._company = copy.copy(company)
        self._kind = kind
        self._run_details = run_details
        self._section_breaks = section_breaks

    def to_pdf(self, path: Union[str, os.PathLike[str]]) -> None:
        """Typesets the document to a PDF.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the PDF to write.

        Raises:
            ImportError: If the typst package is not installed.
        """
        try:
            import typst
        except ImportError as error:
            msg = "cannot typeset without the typst package: install medrecords[pdf]"
            raise ImportError(msg) from error

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
            )
        else:
            typst.compile(
                self._template,
                output=Path(path),
                root=self._template.parent,
                font_paths=[_TEMPLATE],
                sys_inputs=inputs,
            )

    def _logo_text(self) -> str:
        """Reads the logo as SVG text.

        Returns:
            str: The logo as SVG text, or "" for a document without one.
        """
        if self._logo is None:
            return ""

        return self._logo.read_text(encoding="utf-8")

    def _options(self) -> _Options:
        """Collects the settings a template reads.

        Returns:
            _Options: The settings as they are serialized to JSON.
        """
        return {
            "kind": self._kind,
            "run_details": self._run_details,
            "section_breaks": self._section_breaks,
            "company": self._company,
        }

    def __repr__(self) -> str:
        """Returns the string representation of the Document.

        Returns:
            str: The name of the report the document typesets.
        """
        return f"Document({self._report.name!r})"
