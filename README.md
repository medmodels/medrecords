<div align="center">
  <img alt="Python Versions" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue">
  <a href="https://github.com/medmodels/medrecords/actions/workflows/testing.yml">
    <img src="https://github.com/medmodels/medrecords/actions/workflows/testing.yml/badge.svg?branch=main" alt="Tests">
  </a>
  <a href="https://pypi.org/project/medrecords/">
    <img src="https://img.shields.io/pypi/v/medrecords" alt="PyPI Version">
  </a>
  <a href="https://github.com/astral-sh/ruff">
    <img alt="Code Style" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json">
  </a>
</div>

# MedRecords

MedRecords is an opinionated wrapper around [GraphRecords](https://github.com/medmodels/graphrecords) for medical data. It puts a graph record to work in a medical context and makes it the input medical analyses and products run on.

## Installation

```bash
pip install medrecords
```

Rendering a report to PDF needs the `pdf` extra:

```bash
pip install medrecords[pdf]
```

## Building a Record

Every call returns a new record:

```python
import medrecords as mr

medrecord = (
    mr.MedRecord()
    .add_nodes_in_group(
        [
            ("p1", {"gender": "F", "age": 71}),
            ("p2", {"gender": "M", "age": 64}),
            ("p3", {"gender": "F", "age": 38}),
        ],
        "Patient",
    )
    .add_nodes_in_group(
        [("I10", {"label": "Essential hypertension"})],
        "Diagnosis",
    )
    .add_edges_in_group(
        [("p1", "I10", {"year": 2019}), ("p2", "I10", {"year": 2021})],
        "Patient_Diagnosis",
    )
)
```

`add_nodes` and `add_edges` do the same without a group. Polars DataFrames work as a source, naming the index columns: `add_nodes((frame, "patient_id"))`, `add_edges((frame, "patient_id", "diagnosis_id"))`.

## Reading a Record

```python
medrecord.node_count()  # 4
medrecord.group_indices()  # ['Patient', 'Diagnosis', 'Patient_Diagnosis']
medrecord.group("Patient").nodes()  # ['p1', 'p2', 'p3']

patient = medrecord.node("p1")
patient.attributes()  # {'gender': 'F', 'age': 71}
patient.groups()  # ['Patient']
```

## Querying

`mr.nodes()` and `mr.edges()` start an expression tied to no record. `medrecord.nodes()` binds one to a record, which makes it a series. A series runs when you call `evaluate()`.

```python
older = medrecord.nodes().filter(
    mr.nodes().in_group("Patient") & (mr.nodes().attribute("age") > 60)
)
list(older.evaluate())  # ['p1', 'p2']
```

```python
diagnosed = (
    medrecord.edges().filter(mr.edges().in_group("Patient_Diagnosis")).source_node()
)
list(diagnosed.evaluate())  # ['p1', 'p2']
```

```python
medrecord.nodes().filter(mr.nodes().in_group("Patient")).attribute("age").mean().evaluate()
# 57.666666666666664
```

`medrecord.query(expression)` binds a free expression the same way.

## Evaluations

An analytic is a class with one `compute` that returns one value. Analytics go into groups, groups into an evaluation:

```python
from typing import Union

from medrecords.evaluation import Analytic, Evaluation, EvaluationGroup, read
from medrecords.evaluation.catalogue import AttributeCounts, AttributeMean, ElementCount

PATIENTS = mr.nodes().filter(mr.nodes().in_group("Patient"))


class OldestPatient(Analytic[mr.MedRecord]):
    """The age of the oldest patient."""

    def compute(self, medrecord: mr.MedRecord) -> Union[mr.Value, mr.QueryError]:
        return read(medrecord.query(PATIENTS).attribute("age").max().evaluate(), int)


evaluation = (
    Evaluation[mr.MedRecord]("Practice snapshot")
    .add_group(
        "Demographics",
        EvaluationGroup[mr.MedRecord]()
        .add_analytic("Patients", ElementCount(PATIENTS))
        .add_analytic("Mean age", AttributeMean("age", PATIENTS))
        .add_analytic("Sex", AttributeCounts("gender", PATIENTS)),
    )
    .add_analytic("Oldest", OldestPatient())
)
```

The report is read by name:

```python
report = evaluation.report(medrecord)

report.group("Demographics").analytic("Patients").result  # 3
report.group("Demographics").analytic("Mean age").result  # 57.666666666666664
report.analytic("Oldest").result  # 71
```

A result is a number or a string, or one of `Table`, `Plot`, `Measurement`, `Assessment` and `Distribution`. `report.group("Demographics").analytic("Sex").result.to_polars()` gives

```
┌───────┬───────┬──────────┐
│ value ┆ count ┆ share    │
╞═══════╪═══════╪══════════╡
│ F     ┆ 2     ┆ 0.666667 │
│ M     ┆ 1     ┆ 0.333333 │
└───────┴───────┴──────────┘
```

`medrecords.evaluation.catalogue` holds analytics for counts, attribute statistics, completeness, ranges and uniqueness. `add_group_over` and `add_group_over_each` run a group against something derived from the record, a cohort or one part per attribute value.

JSON and PDF are exports:

```python
from medrecords.evaluation import Document, Report

report.to_json("report.json")
Report.from_json("report.json")

Document(report).to_pdf("report.pdf")  # needs the pdf extra
```

## Documentation

- [Documentation](https://www.medmodels.de/docs/medrecords/latest/index.html)
