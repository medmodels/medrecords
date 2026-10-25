import unittest
from datetime import timedelta
from typing import List, Mapping, Optional, Sequence, Union

import pytest
from graphrecords import Value

from medrecords.evaluation.analytic import (
    Analytic,
    Assessment,
    EntryPath,
    ReportValue,
)
from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Entry,
    Failure,
    GroupEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    KeyedResult,
)
from medrecords.evaluation.findings import Findings
from medrecords.evaluation.group import EvaluationGroup
from medrecords.evaluation.placement import (
    _UNKEYED,
    AtRoot,
    GroupPlacement,
    KeyedGroupPlacement,
    NoResultError,
    Placement,
    _Shape,
    _Step,
    _Unkeyed,
)
from medrecords.medrecord import MedRecord

COUNT = _Step("count", _Shape.Plain)
FAILED = _Step("failed", _Shape.Plain)
CHECK = _Step("check", _Shape.Plain)
NESTED = _Step("nested", _Shape.Plain)
DERIVED = _Step("derived", _Shape.Plain)
BROKEN = _Step("broken", _Shape.Plain)
EACH = _Step("each", _Shape.Each)
ACROSS = _Step("across", _Shape.Across)
PARTIAL = _Step("partial", _Shape.Plain)
INNER = _Step("inner", _Shape.Plain)
COMPLETE = _Step("complete", _Shape.Plain)
INSIDE = _Step("inside", _Shape.Each)
AGAIN = _Step("again", _Shape.Across)
MISSING = _Step("missing", _Shape.Plain)
SPARSE = _Step("sparse", _Shape.Plain)


def create_failure(message: str = "consectetur") -> Failure:
    return Failure("builtins.ValueError", message, "")


def create_analytic(name: Value, result: Union[ReportValue, Failure]) -> AnalyticEntry:
    return AnalyticEntry(name, str(name), None, {}, timedelta(), result)


def create_keyed(
    name: Value, results: Mapping[Value, Union[ReportValue, Failure]]
) -> KeyedAnalyticEntry:
    return KeyedAnalyticEntry(
        name,
        str(name),
        None,
        {},
        [KeyedResult(key, timedelta(), result) for key, result in results.items()],
    )


def create_derivation(
    summary: Optional[Mapping[str, int]] = None, failure: Optional[Failure] = None
) -> DerivationEntry:
    return DerivationEntry({}, summary or {}, timedelta(), failure)


def create_group(
    name: Value,
    entries: Sequence[Entry],
    derivation: Optional[DerivationEntry] = None,
) -> GroupEntry:
    return GroupEntry(name, str(name), None, derivation, entries)


def create_keyed_group(
    name: Value,
    entries: Sequence[Union[KeyedAnalyticEntry, KeyedGroupEntry]],
    derivations: Optional[Mapping[Value, DerivationEntry]] = None,
) -> KeyedGroupEntry:
    return KeyedGroupEntry(name, str(name), None, derivations or {}, entries)


def create_across_entries() -> List[Union[KeyedAnalyticEntry, KeyedGroupEntry]]:
    return [
        create_keyed("count", {"a": 1, "b": 2}),
        create_keyed("partial", {"a": 1, "b": create_failure("adipiscing")}),
        create_keyed_group(
            "inner",
            [create_keyed("count", {"a": 1})],
            {
                "a": create_derivation({"kept": 1}),
                "b": create_derivation(failure=create_failure("elit")),
            },
        ),
        create_keyed_group(
            "complete",
            [create_keyed("count", {"a": 1, "b": 2})],
            {"a": create_derivation({"kept": 1}), "b": create_derivation({"kept": 2})},
        ),
        create_keyed_group(
            "inside",
            [
                create_keyed_group("x", [create_keyed("count", {"a": 1, "b": 2})]),
                create_keyed_group("y", [create_keyed("count", {"a": 3, "b": 4})]),
            ],
        ),
        create_keyed_group(
            "again",
            [create_keyed_group("x", [create_keyed("count", {"a": 5, "b": 6})])],
        ),
        create_keyed_group(
            "sparse",
            [create_keyed("count", {"a": 1})],
            {"a": create_derivation({"kept": 1}), "b": create_derivation({"kept": 0})},
        ),
    ]


def create_entries() -> List[Entry]:
    return [
        create_analytic("count", 3),
        create_analytic("failed", create_failure()),
        create_group(
            "nested",
            [
                create_analytic("count", 1),
                create_analytic("check", Assessment(1, "at least 1", passed=True)),
            ],
        ),
        create_group(
            "derived", [create_analytic("count", 2)], create_derivation({"kept": 1})
        ),
        create_group("broken", [], create_derivation(failure=create_failure("sed"))),
        create_group(
            "each",
            [
                create_group("a", [create_analytic("count", 1)]),
                create_group("b", [create_analytic("count", 2)]),
            ],
            create_derivation(),
        ),
        create_group("across", create_across_entries(), create_derivation()),
    ]


def create_findings(
    entries: Optional[Sequence[Entry]] = None,
    owner: Optional[EvaluationGroup[MedRecord]] = None,
    key: Union[Value, _Unkeyed] = _UNKEYED,
    path: EntryPath = (),
) -> Findings[AtRoot]:
    return Findings(create_entries() if entries is None else entries, owner, key, path)


def create_placement(*steps: _Step) -> Placement[AtRoot, int]:
    return Placement(steps)


class NodeCount(Analytic[MedRecord, int]):
    def compute(self, medrecord: MedRecord) -> int:
        return medrecord.node_count()


class TestFindings(unittest.TestCase):
    def test_init(self) -> None:
        entries = create_entries()

        findings = Findings(entries, None, "a", ("lorem",))

        assert findings._entries is entries
        assert findings._owner is None
        assert findings._key == "a"
        assert findings._path == ("lorem",)

    def test_getitem(self) -> None:
        findings = create_findings()

        assert findings[create_placement(COUNT)] == 3
        assert findings[create_placement(NESTED, COUNT)] == 1
        assert findings[create_placement(DERIVED, COUNT)] == 2
        assert findings[create_placement(EACH, COUNT)] == {"a": 1, "b": 2}
        assert findings[create_placement(ACROSS, COUNT)] == {"a": 1, "b": 2}
        assert findings[create_placement(ACROSS, INSIDE, COUNT)] == {
            "a": {"x": 1, "y": 3},
            "b": {"x": 2, "y": 4},
        }
        assert findings[create_placement(ACROSS, AGAIN, COUNT)] == {
            "a": {"x": 5},
            "b": {"x": 6},
        }

        keyed = create_findings(create_across_entries(), key="a")

        assert keyed[create_placement(COUNT)] == 1
        assert keyed[create_placement(PARTIAL)] == 1
        assert keyed[create_placement(INNER, COUNT)] == 1
        assert keyed[create_placement(INSIDE, COUNT)] == {"x": 1, "y": 3}

        group, count = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ())

        assert owned[count] == 3
        assert NodeCount().compute(MedRecord()) == 0

    def test_invalid_getitem(self) -> None:
        findings = create_findings()

        with pytest.raises(NoResultError, match="missing is not in the findings"):
            findings[create_placement(MISSING)]

        with pytest.raises(
            NoResultError, match="nested / missing is not in the findings"
        ):
            findings[create_placement(NESTED, MISSING)]

        with pytest.raises(NoResultError, match="count is an analytic, not a group"):
            findings[create_placement(COUNT, COUNT)]

        with pytest.raises(NoResultError, match="nested is a group, not an analytic"):
            findings[create_placement(NESTED)]

        with pytest.raises(NoResultError, match="failed failed: consectetur"):
            findings[create_placement(FAILED)]

        with pytest.raises(
            NoResultError, match="across / partial / b failed: adipiscing"
        ):
            findings[create_placement(ACROSS, PARTIAL)]

        with pytest.raises(
            NoResultError, match="across / count is an analytic, not a group"
        ):
            findings[create_placement(ACROSS, COUNT, COUNT)]

        with pytest.raises(
            NoResultError, match="across / inside is a group, not an analytic"
        ):
            findings[create_placement(ACROSS, INSIDE)]

        with pytest.raises(NoResultError, match="across / inner / b failed: elit"):
            findings[create_placement(ACROSS, INNER, COUNT)]

        with pytest.raises(
            NoResultError, match="across / inside / x / missing is not in the findings"
        ):
            findings[create_placement(ACROSS, INSIDE, MISSING)]

        keyed = create_findings(create_across_entries(), key="b")

        with pytest.raises(NoResultError, match="partial failed: adipiscing"):
            keyed[create_placement(PARTIAL)]

        with pytest.raises(NoResultError, match="inner failed: elit"):
            keyed[create_placement(INNER, COUNT)]

        with pytest.raises(
            NoResultError, match="sparse / count was not computed under 'b'"
        ):
            keyed[create_placement(SPARSE, COUNT)]

        group, _ = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        _, foreign = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ())

        with pytest.raises(
            NoResultError, match=r"Placement\('count'\) was not placed in this group"
        ):
            owned[foreign]

    def test_path(self) -> None:
        findings = create_findings()

        assert findings.path(create_placement(COUNT)) == ("count",)
        assert findings.path(create_placement(NESTED, COUNT)) == ("nested", "count")
        assert findings.path(create_placement(EACH, COUNT), "a") == (
            "each",
            "a",
            "count",
        )
        assert findings.path(create_placement(ACROSS, COUNT)) == ("across", "count")
        assert findings.path(create_placement(ACROSS, INSIDE, COUNT), "x") == (
            "across",
            "inside",
            "x",
            "count",
        )
        assert findings.path(create_placement(ACROSS, AGAIN, COUNT), "x") == (
            "across",
            "again",
            "x",
            "count",
        )
        assert findings.path(create_placement(NESTED, MISSING)) == (
            "nested",
            "missing",
        )

        keyed = create_findings(create_across_entries(), key="a", path=("across",))

        assert keyed.path(create_placement(INSIDE, COUNT), "y") == (
            "across",
            "inside",
            "y",
            "count",
        )

        group, count = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ("sit",))

        assert owned.path(count) == ("sit", "count")

    def test_invalid_path(self) -> None:
        findings = create_findings()

        with pytest.raises(ValueError, match="expected a key for each"):
            findings.path(create_placement(EACH, COUNT))

        with pytest.raises(ValueError, match="expected 0 keys, got 1"):
            findings.path(create_placement(COUNT), "a")

        with pytest.raises(NoResultError, match="each / z is not in the findings"):
            findings.path(create_placement(EACH, COUNT), "z")

        with pytest.raises(NoResultError, match="missing is not in the findings"):
            findings.path(create_placement(MISSING, COUNT))

        group, _ = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        _, foreign = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ())

        with pytest.raises(
            NoResultError, match=r"Placement\('count'\) was not placed in this group"
        ):
            owned.path(foreign)

    def test_each(self) -> None:
        findings = create_findings()

        assert list(findings.each(int)) == [
            (("count",), 3),
            (("nested", "count"), 1),
            (("derived", "count"), 2),
            (("each", "a", "count"), 1),
            (("each", "b", "count"), 2),
            (("across", "count", "a"), 1),
            (("across", "count", "b"), 2),
            (("across", "partial", "a"), 1),
            (("across", "inner", "count", "a"), 1),
            (("across", "complete", "count", "a"), 1),
            (("across", "complete", "count", "b"), 2),
            (("across", "inside", "x", "count", "a"), 1),
            (("across", "inside", "x", "count", "b"), 2),
            (("across", "inside", "y", "count", "a"), 3),
            (("across", "inside", "y", "count", "b"), 4),
            (("across", "again", "x", "count", "a"), 5),
            (("across", "again", "x", "count", "b"), 6),
            (("across", "sparse", "count", "a"), 1),
        ]
        assert list(findings.each(Assessment)) == [
            (("nested", "check"), Assessment(1, "at least 1", passed=True))
        ]
        assert list(findings.each(Failure)) == [
            (("failed",), create_failure()),
            (("across", "partial", "b"), create_failure("adipiscing")),
        ]
        assert list(findings.each(int, GroupPlacement(NESTED))) == [
            (("nested", "count"), 1)
        ]
        assert list(findings.each(int, KeyedGroupPlacement(EACH))) == [
            (("each", "a", "count"), 1),
            (("each", "b", "count"), 2),
        ]
        assert list(findings.each(int, KeyedGroupPlacement(ACROSS))) == [
            (("across", "count", "a"), 1),
            (("across", "count", "b"), 2),
            (("across", "partial", "a"), 1),
            (("across", "inner", "count", "a"), 1),
            (("across", "complete", "count", "a"), 1),
            (("across", "complete", "count", "b"), 2),
            (("across", "inside", "x", "count", "a"), 1),
            (("across", "inside", "x", "count", "b"), 2),
            (("across", "inside", "y", "count", "a"), 3),
            (("across", "inside", "y", "count", "b"), 4),
            (("across", "again", "x", "count", "a"), 5),
            (("across", "again", "x", "count", "b"), 6),
            (("across", "sparse", "count", "a"), 1),
        ]

        keyed = create_findings(create_across_entries(), key="b")

        assert list(keyed.each(int)) == [
            (("count",), 2),
            (("complete", "count"), 2),
            (("inside", "x", "count"), 2),
            (("inside", "y", "count"), 4),
            (("again", "x", "count"), 6),
        ]
        assert list(keyed.each(int, GroupPlacement(INNER))) == []
        assert list(keyed.each(int, KeyedGroupPlacement(INSIDE))) == [
            (("inside", "x", "count"), 2),
            (("inside", "y", "count"), 4),
        ]

        placed = create_findings(create_across_entries(), key="b", path=("across",))

        assert list(placed.each(int, GroupPlacement(COMPLETE))) == [
            (("across", "complete", "count"), 2)
        ]
        assert list(placed.each(int, KeyedGroupPlacement(AGAIN))) == [
            (("across", "again", "x", "count"), 6)
        ]

        group, _ = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ())

        assert list(owned.each(int)) == [(("count",), 3)]

    def test_invalid_each(self) -> None:
        findings = create_findings()

        with pytest.raises(NoResultError, match="missing is not in the findings"):
            list(findings.each(int, GroupPlacement(MISSING)))

        with pytest.raises(NoResultError, match="count is an analytic, not a group"):
            list(findings.each(int, GroupPlacement(COUNT)))

        keyed = create_findings(create_across_entries(), key="a")

        with pytest.raises(NoResultError, match="count is an analytic, not a group"):
            list(keyed.each(int, GroupPlacement(COUNT)))

        group, _ = EvaluationGroup[MedRecord]().place_analytic("count", NodeCount())
        _, foreign = EvaluationGroup[MedRecord]().place_group(
            "nested", EvaluationGroup[MedRecord]()
        )
        owned = Findings([create_analytic("count", 3)], group, _UNKEYED, ())

        with pytest.raises(
            NoResultError,
            match=r"GroupPlacement\('nested'\) was not placed in this group",
        ):
            list(owned.each(int, foreign))

    def test_failures(self) -> None:
        findings = create_findings()

        assert list(findings.failures()) == [
            (("failed",), create_failure()),
            (("broken",), create_failure("sed")),
            (("across", "partial", "b"), create_failure("adipiscing")),
            (("across", "inner", "b"), create_failure("elit")),
        ]
        assert list(findings.failures(GroupPlacement(NESTED))) == []
        assert list(findings.failures(KeyedGroupPlacement(ACROSS))) == [
            (("across", "partial", "b"), create_failure("adipiscing")),
            (("across", "inner", "b"), create_failure("elit")),
        ]

        keyed = create_findings(create_across_entries(), key="b")

        assert list(keyed.failures()) == [
            (("partial",), create_failure("adipiscing")),
            (("inner",), create_failure("elit")),
        ]
        assert list(create_findings(create_across_entries(), key="a").failures()) == []
        assert list(
            create_findings(
                create_across_entries(), key="b", path=("across",)
            ).failures()
        ) == [
            (("across", "partial"), create_failure("adipiscing")),
            (("across", "inner"), create_failure("elit")),
        ]

    def test_repr(self) -> None:
        assert repr(create_findings()) == "Findings(entries=7)"


if __name__ == "__main__":
    unittest.main()
