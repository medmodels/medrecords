import json
import math
import re
import unittest
from datetime import timedelta

import pytest

from medrecords.evaluation._json import JsonObject
from medrecords.evaluation.analytic import (
    Assessment,
    Bins,
    Distribution,
    Measurement,
    Scale,
    Table,
    Unit,
)
from medrecords.evaluation.entry import (
    AnalyticEntry,
    DerivationEntry,
    Failure,
    GroupEntry,
    KeyedAnalyticEntry,
    KeyedGroupEntry,
    KeyedResult,
    Layout,
)

from ._fixtures import (
    create_analytic_entry,
    create_derivation_entry,
    create_failure,
    create_group_entry,
    create_keyed_analytic_entry,
    create_keyed_group_entry,
    create_keyed_result,
    create_report,
    create_rich_report,
)


def create_object(content: object) -> JsonObject:
    return JsonObject(json.loads(json.dumps(content)), "sit")


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

    def test_from_document(self) -> None:
        document = create_object(create_failure()._to_document())

        assert Failure._from_document(document) == create_failure()

    def test_to_document(self) -> None:
        assert create_failure()._to_document() == {
            "kind": "failure",
            "exception_type": "builtins.ValueError",
            "message": "sit",
            "traceback": "Traceback\nValueError: sit\n",
        }

    def test_eq(self) -> None:
        assert create_failure() == create_failure()
        assert create_failure() != Failure("builtins.ValueError", "amet", "")
        assert create_failure() != "sit"

    def test_repr(self) -> None:
        assert repr(create_failure()) == "Failure(builtins.ValueError: sit)"


class TestDerivationEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = DerivationEntry(
            {"node": "lorem"}, {"kept": 1}, timedelta(seconds=1), create_failure()
        )

        assert entry.parameters == {"node": "lorem"}
        assert entry.summary == {"kept": 1}
        assert entry.duration == timedelta(seconds=1)
        assert entry.failure == create_failure()

        entry.parameters.clear()
        entry.summary.clear()

        assert entry.parameters == {"node": "lorem"}
        assert entry.summary == {"kept": 1}

    def test_from_document(self) -> None:
        failed = DerivationEntry({}, {}, timedelta(), create_failure())

        for entry in (create_derivation_entry(), failed):
            document = create_object(entry._to_document())

            assert DerivationEntry._from_document(document) == entry

    def test_invalid_from_document(self) -> None:
        derivation = create_derivation_entry()._to_document()

        with pytest.raises(
            ValueError, match=re.escape("expected a failure at sit.failure")
        ):
            DerivationEntry._from_document(
                create_object({**derivation, "failure": {"kind": "lorem"}})
            )

    def test_to_document(self) -> None:
        assert create_derivation_entry()._to_document() == {
            "parameters": {"node": "lorem"},
            "summary": {"kept": 1},
            "duration": 1.0,
            "failure": None,
        }
        assert DerivationEntry(
            {}, {}, timedelta(), create_failure()
        )._to_document() == {
            "parameters": {},
            "summary": {},
            "duration": 0.0,
            "failure": create_failure()._to_document(),
        }

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

    def test_from_document(self) -> None:
        entries = [
            create_analytic_entry(),
            create_analytic_entry(2023, result=create_failure()),
            create_analytic_entry("measurement", result=Measurement(1.0)),
            create_analytic_entry(
                "infinite",
                result=Measurement(math.inf, -math.inf, math.inf, math.inf),
            ),
            create_analytic_entry(
                "assessment", result=Assessment(1, "at least 1", passed=True)
            ),
        ]

        rich = [
            entry
            for entry in create_rich_report().entries
            if isinstance(entry, AnalyticEntry)
        ]

        for entry in entries + rich:
            document = create_object(entry._to_document())

            assert AnalyticEntry._from_document(document) == entry

    def test_invalid_from_document(self) -> None:
        analytic = create_analytic_entry()._to_document()
        measurement = {
            "kind": "measurement",
            "value": 1.0,
            "lower": None,
            "upper": None,
            "p_value": None,
            "unit": "lorem",
        }
        assessment = {
            "kind": "assessment",
            "value": 1,
            "requirement_label": "at least 1",
            "passed": True,
            "unit": 1,
        }

        with pytest.raises(
            ValueError, match=re.escape("expected a value at sit.result")
        ):
            AnalyticEntry._from_document(
                create_object({**analytic, "result": {"kind": "lorem"}})
            )

        with pytest.raises(
            ValueError, match=re.escape("expected a value of Unit at sit.result.unit")
        ):
            AnalyticEntry._from_document(
                create_object({**analytic, "result": measurement})
            )

        with pytest.raises(
            ValueError, match=re.escape("expected a value of Unit at sit.result.unit")
        ):
            AnalyticEntry._from_document(
                create_object({**analytic, "result": assessment})
            )

    def test_to_document(self) -> None:
        table = Table(["amet", 2024], [[1, 0.5]], units={2024: Unit.Share})

        assert create_analytic_entry(parameters={"limit": 3})._to_document() == {
            "kind": "analytic",
            "name": "amet",
            "title": "Amet",
            "description": None,
            "parameters": {"limit": 3},
            "duration": 0.5,
            "result": 1,
        }
        assert create_analytic_entry(result=table)._to_document()["result"] == {
            "kind": "table",
            "headings": ["amet", 2024],
            "rows": [[1, 0.5]],
            "units": [None, "share"],
            "printed_rows": None,
        }

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
        assert entry.derivation == create_derivation_entry()
        assert len(entry.entries) == 2
        assert entry.layout is Layout.Section
        assert (
            GroupEntry("sit", "sit", None, None, [], layout=Layout.Inline).layout
            is Layout.Inline
        )

        entry.entries.clear()

        assert len(entry.entries) == 2

    def test_from_document(self) -> None:
        appendix = GroupEntry("sit", "sit", None, None, [], layout=Layout.Appendix)

        for entry in (create_group_entry(), create_report().group("across"), appendix):
            document = create_object(entry._to_document())

            assert GroupEntry._from_document(document) == entry

    def test_invalid_from_document(self) -> None:
        analytic = create_analytic_entry()._to_document()
        group = create_group_entry()._to_document()

        with pytest.raises(
            ValueError, match=re.escape("expected an entry at sit.entries[0]")
        ):
            GroupEntry._from_document(
                create_object({**group, "entries": [{**analytic, "kind": "lorem"}]})
            )

    def test_to_document(self) -> None:
        document = create_group_entry()._to_document()

        assert document["kind"] == "group"
        assert document["name"] == "sit"
        assert document["title"] == "sit"
        assert document["description"] == "adipiscing"
        assert document["layout"] == "section"
        assert document["derivation"] == create_derivation_entry()._to_document()
        assert document["entries"] == [
            entry._to_document() for entry in create_group_entry().entries
        ]

    def test_with_entries(self) -> None:
        entry = create_group_entry()

        emptied = entry._with_entries([])

        assert emptied.entries == []
        assert emptied.name == "sit"
        assert emptied.title == "sit"
        assert emptied.description == "adipiscing"
        assert emptied.derivation == entry.derivation
        assert len(entry.entries) == 2
        assert entry._with_entries(entry.entries) == entry
        assert (
            GroupEntry("sit", "sit", None, None, [], layout=Layout.Inline)
            ._with_entries([])
            .layout
            is Layout.Inline
        )

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
        assert list(create_report().group("across").analytics()) == []

    def test_keyed_group(self) -> None:
        across = create_report().group("across")

        assert across.keyed_group("sit") == create_keyed_group_entry()

    def test_invalid_keyed_group(self) -> None:
        with pytest.raises(KeyError, match="cannot find keyed group 'amet'"):
            create_report().group("across").keyed_group("amet")

    def test_keyed_analytic(self) -> None:
        across = create_report().group("across")

        assert across.keyed_analytic("amet") == create_keyed_analytic_entry()

    def test_invalid_keyed_analytic(self) -> None:
        with pytest.raises(KeyError, match="cannot find keyed analytic 'sit'"):
            create_report().group("across").keyed_analytic("sit")

    def test_keyed_analytics(self) -> None:
        assert list(create_report().group("across").keyed_analytics()) == [
            (("amet",), create_keyed_analytic_entry()),
            (("sit", "amet"), create_keyed_analytic_entry()),
            (
                ("sit", "elit", "consectetur"),
                create_keyed_analytic_entry("consectetur"),
            ),
        ]
        assert list(create_group_entry().keyed_analytics()) == []

    def test_eq(self) -> None:
        assert create_group_entry() == create_group_entry()
        assert create_group_entry() != GroupEntry("sit", "sit", None, None, [])
        assert create_group_entry() != GroupEntry("sit", "sit", None, None, [])
        assert GroupEntry("sit", "sit", None, None, []) != GroupEntry(
            "sit", "sit", None, None, [], layout=Layout.Inline
        )
        assert create_group_entry() != "sit"

    def test_repr(self) -> None:
        assert repr(create_group_entry()) == "GroupEntry('sit', entries=2)"


class TestKeyedResult(unittest.TestCase):
    def test_init(self) -> None:
        keyed = create_keyed_result()

        assert keyed.key == "real"
        assert keyed.duration == timedelta(seconds=0.25)
        assert keyed.result == 1
        assert create_keyed_result(2023).key == 2023

    def test_from_document(self) -> None:
        for keyed in (create_keyed_result(), create_keyed_result(2023, result=2)):
            document = create_object(keyed._to_document())

            assert KeyedResult._from_document(document) == keyed

    def test_to_document(self) -> None:
        assert create_keyed_result()._to_document() == {
            "key": "real",
            "duration": 0.25,
            "result": 1,
        }

    def test_eq(self) -> None:
        assert create_keyed_result() == create_keyed_result()
        assert create_keyed_result() != create_keyed_result(result=2)
        assert create_keyed_result() != create_keyed_result("synthetic")
        assert create_keyed_result() != KeyedResult("real", timedelta(), 1)
        assert create_keyed_result() != "real"

    def test_repr(self) -> None:
        assert repr(create_keyed_result()) == "KeyedResult('real', 1)"


class TestKeyedAnalyticEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = create_keyed_analytic_entry()

        assert entry.name == "amet"
        assert entry.title == "Amet"
        assert entry.description is None
        assert entry.parameters == {"limit": 3}
        assert entry.results == [
            create_keyed_result(),
            create_keyed_result("synthetic", result=2),
        ]
        assert entry.keys == ["real", "synthetic"]

        entry.parameters.clear()
        entry.results.clear()

        assert entry.parameters == {"limit": 3}
        assert len(entry.results) == 2

    def test_from_document(self) -> None:
        rich = [
            entry
            for entry in create_rich_report().entries
            if isinstance(entry, KeyedAnalyticEntry)
        ]

        for entry in [create_keyed_analytic_entry(), *rich]:
            document = create_object(entry._to_document())

            assert KeyedAnalyticEntry._from_document(document) == entry

    def test_to_document(self) -> None:
        document = create_keyed_analytic_entry()._to_document()

        assert document["kind"] == "keyed_analytic"
        assert document["name"] == "amet"
        assert document["title"] == "Amet"
        assert document["description"] is None
        assert document["parameters"] == {"limit": 3}
        assert document["results"] == [
            create_keyed_result()._to_document(),
            create_keyed_result("synthetic", result=2)._to_document(),
        ]

    def test_to_document_distributions(self) -> None:
        distributions = [Distribution([1.0, 2.0]), Distribution([8.0, 9.0])]
        shared = create_keyed_analytic_entry(
            results=[
                create_keyed_result(result=distributions[0]),
                create_keyed_result("synthetic", result=distributions[1]),
            ]
        )._to_document()
        partial = create_keyed_analytic_entry(
            results=[
                create_keyed_result(result=distributions[0]),
                create_keyed_result("synthetic", result=create_failure()),
            ]
        )._to_document()

        histograms = Distribution.shared_histograms(distributions)
        assert [keyed["result"] for keyed in shared["results"]] == [
            distributions[0]._to_document(histograms[0]),
            distributions[1]._to_document(histograms[1]),
        ]
        assert partial["results"][0]["result"] == distributions[0]._to_document(
            distributions[0].histogram()
        )
        assert partial["results"][1]["result"] == create_failure()._to_document()

        disagreeing = [
            Distribution([1.5, 2.5], bins=Bins(scale=Scale.Linear)),
            Distribution([20.5, 2.5], bins=Bins(scale=Scale.Logarithmic)),
        ]
        separate = create_keyed_analytic_entry(
            results=[
                create_keyed_result(result=disagreeing[0]),
                create_keyed_result("synthetic", result=disagreeing[1]),
            ]
        )._to_document()

        assert [keyed["result"] for keyed in separate["results"]] == [
            disagreeing[0]._to_document(disagreeing[0].histogram()),
            disagreeing[1]._to_document(disagreeing[1].histogram()),
        ]

    def test_result(self) -> None:
        assert create_keyed_analytic_entry().result("synthetic") == 2

    def test_invalid_result(self) -> None:
        with pytest.raises(KeyError, match="cannot find key 'holdout'"):
            create_keyed_analytic_entry().result("holdout")

    def test_eq(self) -> None:
        assert create_keyed_analytic_entry() == create_keyed_analytic_entry()
        assert create_keyed_analytic_entry() != create_keyed_analytic_entry("elit")
        assert create_keyed_analytic_entry() != create_keyed_analytic_entry(
            results=[create_keyed_result()]
        )
        assert create_keyed_analytic_entry() != KeyedAnalyticEntry(
            "amet", "Amet", None, {}, create_keyed_analytic_entry().results
        )
        assert create_keyed_analytic_entry() != "amet"

    def test_repr(self) -> None:
        assert repr(create_keyed_analytic_entry()) == (
            "KeyedAnalyticEntry('amet', keys=['real', 'synthetic'])"
        )


class TestKeyedGroupEntry(unittest.TestCase):
    def test_init(self) -> None:
        entry = create_keyed_group_entry()

        assert entry.name == "sit"
        assert entry.title == "sit"
        assert entry.description == "adipiscing"
        assert entry.derivations["real"] == create_derivation_entry()
        assert entry.derivations["synthetic"].failure == create_failure()
        assert list(entry.derivations) == ["real", "synthetic"]
        assert len(entry.entries) == 2
        assert entry.layout is Layout.Section
        assert (
            KeyedGroupEntry("sit", "sit", None, {}, [], layout=Layout.Appendix).layout
            is Layout.Appendix
        )

        entry.derivations.clear()
        entry.entries.clear()

        assert len(entry.derivations) == 2
        assert len(entry.entries) == 2

    def test_from_document(self) -> None:
        document = create_object(create_keyed_group_entry()._to_document())
        inline = KeyedGroupEntry("sit", "sit", None, {}, [], layout=Layout.Inline)

        assert KeyedGroupEntry._from_document(document) == create_keyed_group_entry()
        assert (
            KeyedGroupEntry._from_document(create_object(inline._to_document()))
            == inline
        )

    def test_invalid_from_document(self) -> None:
        analytic = create_analytic_entry()._to_document()
        keyed_group = create_keyed_group_entry()._to_document()

        with pytest.raises(
            ValueError,
            match=re.escape(
                "expected a keyed analytic or a keyed group at sit.entries[0]"
            ),
        ):
            KeyedGroupEntry._from_document(
                create_object(
                    {**keyed_group, "entries": [{**analytic, "kind": "group"}]}
                )
            )

        with pytest.raises(
            ValueError,
            match=re.escape("expected 'derivation' at sit.derivations[0]"),
        ):
            KeyedGroupEntry._from_document(
                create_object({**keyed_group, "derivations": [{"key": "real"}]})
            )

    def test_to_document(self) -> None:
        document = create_keyed_group_entry()._to_document()

        assert document["kind"] == "keyed_group"
        assert document["name"] == "sit"
        assert document["title"] == "sit"
        assert document["description"] == "adipiscing"
        assert document["layout"] == "section"
        assert document["derivations"] == [
            {"key": "real", "derivation": create_derivation_entry()._to_document()},
            {
                "key": "synthetic",
                "derivation": DerivationEntry(
                    {}, {}, timedelta(), create_failure()
                )._to_document(),
            },
        ]
        assert document["entries"] == [
            entry._to_document() for entry in create_keyed_group_entry().entries
        ]

    def test_keyed_group(self) -> None:
        assert create_keyed_group_entry().keyed_group("elit").name == "elit"

    def test_invalid_keyed_group(self) -> None:
        with pytest.raises(KeyError, match="cannot find keyed group 'amet'"):
            create_keyed_group_entry().keyed_group("amet")

    def test_keyed_analytic(self) -> None:
        assert create_keyed_group_entry().keyed_analytic("amet") == (
            create_keyed_analytic_entry()
        )

    def test_invalid_keyed_analytic(self) -> None:
        with pytest.raises(KeyError, match="cannot find keyed analytic 'elit'"):
            create_keyed_group_entry().keyed_analytic("elit")

    def test_keyed_analytics(self) -> None:
        assert list(create_keyed_group_entry().keyed_analytics()) == [
            (("amet",), create_keyed_analytic_entry()),
            (("elit", "consectetur"), create_keyed_analytic_entry("consectetur")),
        ]

    def test_eq(self) -> None:
        assert create_keyed_group_entry() == create_keyed_group_entry()
        assert create_keyed_group_entry() != KeyedGroupEntry("sit", "sit", None, {}, [])
        assert create_keyed_group_entry() != KeyedGroupEntry(
            "sit",
            "sit",
            "adipiscing",
            {},
            create_keyed_group_entry().entries,
        )
        assert KeyedGroupEntry("sit", "sit", None, {}, []) != KeyedGroupEntry(
            "sit", "sit", None, {}, [], layout=Layout.Inline
        )
        assert create_keyed_group_entry() != "sit"

    def test_repr(self) -> None:
        assert repr(create_keyed_group_entry()) == "KeyedGroupEntry('sit', entries=2)"


if __name__ == "__main__":
    unittest.main()
