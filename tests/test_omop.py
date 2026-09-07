import tempfile
import unittest
from pathlib import Path

import polars as pl
import pytest
from graphrecords import OnConflict

from medrecords.medrecord import MedRecord
from medrecords.omop import OmopPlugin


def _create_vocabulary_folder(folder: Path, separator: str = "\t") -> None:
    pl.DataFrame(
        {
            "concept_id": [1, 2],
            "concept_name": ["Concept A", "Concept B"],
            "vocabulary_id": ["V1", "V2"],
            "domain_id": ["D1", "D2"],
            "concept_class_id": ["CC1", "CC2"],
        }
    ).write_csv(folder / "CONCEPT.csv", separator=separator)

    pl.DataFrame(
        {
            "ancestor_concept_id": [1],
            "descendant_concept_id": [2],
            "min_levels_of_separation": [1],
            "max_levels_of_separation": [1],
        }
    ).write_csv(folder / "CONCEPT_ANCESTOR.csv", separator=separator)

    pl.DataFrame(
        {
            "concept_class_id": ["CC1", "CC2"],
            "concept_class_name": ["Class 1", "Class 2"],
            "concept_class_concept_id": [1, 2],
        }
    ).write_csv(folder / "CONCEPT_CLASS.csv", separator=separator)

    pl.DataFrame(
        {
            "concept_id_1": [1],
            "concept_id_2": [2],
            "relationship_id": ["Maps to"],
            "valid_start_date": ["2020-01-01"],
            "valid_end_date": ["2099-12-31"],
        }
    ).write_csv(folder / "CONCEPT_RELATIONSHIP.csv", separator=separator)

    pl.DataFrame(
        {
            "concept_id": [1],
            "concept_synonym_name": ["Synonym A"],
            "language_concept_id": [2],
        }
    ).write_csv(folder / "CONCEPT_SYNONYM.csv", separator=separator)

    pl.DataFrame(
        {
            "domain_id": ["D1", "D2"],
            "domain_name": ["Domain 1", "Domain 2"],
            "domain_concept_id": [1, 2],
        }
    ).write_csv(folder / "DOMAIN.csv", separator=separator)

    pl.DataFrame(
        {
            "drug_concept_id": [1],
            "ingredient_concept_id": [2],
            "amount_value": [500.0],
        }
    ).write_csv(folder / "DRUG_STRENGTH.csv", separator=separator)

    pl.DataFrame(
        {
            "relationship_id": ["Maps to", "Mapped from"],
            "relationship_name": ["Maps to", "Mapped from"],
            "is_hierarchical": ["1", "0"],
            "reverse_relationship_id": ["Mapped from", "Maps to"],
            "relationship_concept_id": [1, 2],
        }
    ).write_csv(folder / "RELATIONSHIP.csv", separator=separator)

    pl.DataFrame(
        {
            "vocabulary_id": ["V1", "V2"],
            "vocabulary_name": ["Vocab 1", "Vocab 2"],
            "vocabulary_concept_id": [1, 2],
        }
    ).write_csv(folder / "VOCABULARY.csv", separator=separator)


def _create_medrecord(folder: Path) -> MedRecord:
    return (
        MedRecord()
        .add_node_in_group(1000, {"name": "lorem ipsum"}, "Patient")
        .add_plugin("omop", OmopPlugin(folder))
    )


class TestOmopPlugin(unittest.TestCase):
    def test_init_loads_vocabulary_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            assert len(plugin.vocabulary_nodes) == 5

            groups = [group for _, group in plugin.vocabulary_nodes]
            assert "OMOP_VOCABULARY" in groups
            assert "OMOP_CONCEPT" in groups
            assert "OMOP_DOMAIN" in groups
            assert "OMOP_CONCEPT_CLASS" in groups
            assert "OMOP_RELATIONSHIP" in groups

    def test_init_loads_vocabulary_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            assert len(plugin.vocabulary_edges) == 12

            groups = [group for _, group in plugin.vocabulary_edges]
            assert "OMOP_VOCABULARY_CONCEPT" in groups
            assert "OMOP_CONCEPT_VOCABULARY" in groups
            assert "OMOP_DOMAIN_CONCEPT" in groups
            assert "OMOP_CONCEPT_DOMAIN" in groups
            assert "OMOP_CONCEPT_CLASS_CONCEPT" in groups
            assert "OMOP_CONCEPT_CONCEPT_CLASS" in groups
            assert "OMOP_RELATIONSHIP_CONCEPT" in groups
            assert "OMOP_RELATIONSHIP_REVERSE" in groups
            assert "OMOP_CONCEPT_ANCESTOR" in groups
            assert "OMOP_CONCEPT_RELATIONSHIP" in groups
            assert "OMOP_CONCEPT_SYNONYM" in groups
            assert "OMOP_DRUG_STRENGTH" in groups

    def test_init_prefixes_vocabulary_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            vocabulary_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_VOCABULARY"
            )
            assert vocabulary_node["vocabulary_id"].to_list() == [
                "VOCABULARY/V1",
                "VOCABULARY/V2",
            ]

    def test_init_prefixes_domain_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            domain_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_DOMAIN"
            )
            assert domain_node["domain_id"].to_list() == [
                "DOMAIN/D1",
                "DOMAIN/D2",
            ]

    def test_init_prefixes_concept_class_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            concept_class_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_CONCEPT_CLASS"
            )
            assert concept_class_node["concept_class_id"].to_list() == [
                "CONCEPT_CLASS/CC1",
                "CONCEPT_CLASS/CC2",
            ]

    def test_init_prefixes_relationship_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            relationship_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_RELATIONSHIP"
            )
            assert relationship_node["relationship_id"].to_list() == [
                "RELATIONSHIP/Maps to",
                "RELATIONSHIP/Mapped from",
            ]

    def test_init_drops_foreign_key_columns_from_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            vocabulary_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_VOCABULARY"
            )
            assert "vocabulary_concept_id" not in vocabulary_node.columns

            domain_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_DOMAIN"
            )
            assert "domain_concept_id" not in domain_node.columns

            concept_class_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_CONCEPT_CLASS"
            )
            assert "concept_class_concept_id" not in concept_class_node.columns

            relationship_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_RELATIONSHIP"
            )
            assert "reverse_relationship_id" not in relationship_node.columns
            assert "relationship_concept_id" not in relationship_node.columns

            concept_node = next(
                dataframe
                for (dataframe, _), group in plugin.vocabulary_nodes
                if group == "OMOP_CONCEPT"
            )
            assert "vocabulary_id" not in concept_node.columns
            assert "domain_id" not in concept_node.columns
            assert "concept_class_id" not in concept_node.columns

    def test_init_with_custom_separator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder, separator=",")

            plugin = OmopPlugin(folder, separator=",")

            assert len(plugin.vocabulary_nodes) == 5
            assert len(plugin.vocabulary_edges) == 12

    def test_init_with_quote_char(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder, quote_char='"')

            assert len(plugin.vocabulary_nodes) == 5

    def test_concept_vocabulary_edge_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            concept_vocabulary_edge = next(
                dataframe
                for (dataframe, _, _), group in plugin.vocabulary_edges
                if group == "OMOP_CONCEPT_VOCABULARY"
            )
            assert all(
                value.startswith("VOCABULARY/")
                for value in concept_vocabulary_edge["vocabulary_id"].to_list()
            )

    def test_concept_domain_edge_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            concept_domain_edge = next(
                dataframe
                for (dataframe, _, _), group in plugin.vocabulary_edges
                if group == "OMOP_CONCEPT_DOMAIN"
            )
            assert all(
                value.startswith("DOMAIN/")
                for value in concept_domain_edge["domain_id"].to_list()
            )

    def test_concept_concept_class_edge_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            concept_concept_class_edge = next(
                dataframe
                for (dataframe, _, _), group in plugin.vocabulary_edges
                if group == "OMOP_CONCEPT_CONCEPT_CLASS"
            )
            assert all(
                value.startswith("CONCEPT_CLASS/")
                for value in concept_concept_class_edge["concept_class_id"].to_list()
            )

    def test_relationship_reverse_edge_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            relationship_reverse_edge = next(
                dataframe
                for (dataframe, _, _), group in plugin.vocabulary_edges
                if group == "OMOP_RELATIONSHIP_REVERSE"
            )
            assert all(
                value.startswith("RELATIONSHIP/")
                for value in relationship_reverse_edge[
                    "reverse_relationship_id"
                ].to_list()
            )

    def test_reserved_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)

            assert len(plugin.reserved_groups) == 17
            assert "OMOP_CONCEPT" in plugin.reserved_groups
            assert "OMOP_DRUG_STRENGTH" in plugin.reserved_groups

    def test_initialize_adds_nodes_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = MedRecord().add_plugin("omop", OmopPlugin(folder))

            assert medrecord.node_count() > 0
            assert medrecord.edge_count() > 0

            assert medrecord.contains_group("OMOP_VOCABULARY")
            assert medrecord.contains_group("OMOP_CONCEPT")
            assert medrecord.contains_group("OMOP_DOMAIN")
            assert medrecord.contains_group("OMOP_CONCEPT_CLASS")
            assert medrecord.contains_group("OMOP_RELATIONSHIP")
            assert medrecord.contains_group("OMOP_VOCABULARY_CONCEPT")
            assert medrecord.contains_group("OMOP_CONCEPT_VOCABULARY")
            assert medrecord.contains_group("OMOP_DOMAIN_CONCEPT")
            assert medrecord.contains_group("OMOP_CONCEPT_DOMAIN")
            assert medrecord.contains_group("OMOP_CONCEPT_CLASS_CONCEPT")
            assert medrecord.contains_group("OMOP_CONCEPT_CONCEPT_CLASS")
            assert medrecord.contains_group("OMOP_RELATIONSHIP_CONCEPT")
            assert medrecord.contains_group("OMOP_RELATIONSHIP_REVERSE")
            assert medrecord.contains_group("OMOP_CONCEPT_ANCESTOR")
            assert medrecord.contains_group("OMOP_CONCEPT_RELATIONSHIP")
            assert medrecord.contains_group("OMOP_CONCEPT_SYNONYM")
            assert medrecord.contains_group("OMOP_DRUG_STRENGTH")

    def test_invalid_initialize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = MedRecord().add_group("OMOP_CONCEPT")

            with pytest.raises(ValueError, match="already holds"):
                medrecord.add_plugin("omop", OmopPlugin(folder))

            attached = _create_medrecord(folder)

            with pytest.raises(ValueError, match="already holds"):
                attached.add_plugin("second", OmopPlugin(folder))

    def test_pre_add_nodes_in_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder).add_node_in_group(
                2000, {}, "Diagnosis"
            )

            assert medrecord.group("Diagnosis").nodes() == [2000]

    def test_invalid_pre_add_nodes_in_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.add_node_in_group(2000, {}, "OMOP_CONCEPT")

    def test_pre_add_edges_in_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]

            medrecord = medrecord.add_edge_in_group(
                1000, concept, {"role": "dolor"}, "Diagnosis"
            )

            assert len(medrecord.group("Diagnosis").edges()) == 1

    def test_invalid_pre_add_edges_in_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.add_edge_in_group(1000, concept, {}, "OMOP_CONCEPT_ANCESTOR")

    def test_pre_remove_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept_count = medrecord.group("OMOP_CONCEPT").node_count()

            removed = medrecord.remove_nodes(1000)

            assert not removed.contains_node(1000)
            assert removed.group("OMOP_CONCEPT").node_count() == concept_count

            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            spared = medrecord.remove_nodes(concept)

            assert spared.contains_node(concept)

            kept = medrecord.keep_nodes([1000])

            assert kept.contains_node(1000)
            assert kept.group("OMOP_CONCEPT").node_count() == concept_count

    def test_pre_remove_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge_in_group(1000, concept, {}, "Diagnosis")
            user_edge = medrecord.group("Diagnosis").edges()[0]
            vocabulary_count = medrecord.group("OMOP_CONCEPT_ANCESTOR").edge_count()

            removed = medrecord.remove_edges(user_edge)

            assert removed.group("Diagnosis").edge_count() == 0

            kept = medrecord.keep_edges([user_edge])

            assert kept.group("Diagnosis").edges() == [user_edge]
            assert kept.group("OMOP_CONCEPT_ANCESTOR").edge_count() == vocabulary_count

    def test_pre_set_node_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            attributes = medrecord.node(concept).attributes()

            assigned = medrecord.set_node_attributes(1000, {"name": "dolor"})

            assert assigned.node(1000).attributes() == {"name": "dolor"}

            spared = medrecord.set_node_attributes(concept, {"concept_name": "dolor"})

            assert spared.node(concept).attributes() == attributes

            other = MedRecord().add_nodes(
                [(concept, {"concept_name": "dolor"}), (3000, {"name": "sit"})]
            )
            merged = medrecord.merge(other, OnConflict.KeepOther)

            assert merged.node(concept).attributes() == attributes
            assert merged.contains_node(3000)

    def test_pre_replace_node_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            attributes = medrecord.node(concept).attributes()

            assigned = medrecord.replace_node_attributes(1000, {"name": "dolor"})

            assert assigned.node(1000).attributes() == {"name": "dolor"}

            spared = medrecord.replace_node_attributes(concept, {})

            assert spared.node(concept).attributes() == attributes

    def test_pre_remove_node_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            attributes = medrecord.node(concept).attributes()

            removed = medrecord.remove_node_attributes(1000, ["name"])

            assert removed.node(1000).attributes() == {}

            spared = medrecord.remove_node_attributes(concept, ["concept_name"])

            assert spared.node(concept).attributes() == attributes

    def test_pre_set_edge_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge_in_group(1000, concept, {}, "Diagnosis")
            user_edge = medrecord.group("Diagnosis").edges()[0]
            vocabulary_edge = medrecord.group("OMOP_CONCEPT_ANCESTOR").edges()[0]
            attributes = medrecord.edge(vocabulary_edge).attributes()

            assigned = medrecord.set_edge_attributes(user_edge, {"role": "dolor"})

            assert assigned.edge(user_edge).attributes() == {"role": "dolor"}

            spared = medrecord.set_edge_attributes(vocabulary_edge, {"role": "dolor"})

            assert spared.edge(vocabulary_edge).attributes() == attributes

    def test_pre_replace_edge_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge_in_group(
                1000, concept, {"role": "lorem"}, "Diagnosis"
            )
            user_edge = medrecord.group("Diagnosis").edges()[0]
            vocabulary_edge = medrecord.group("OMOP_CONCEPT_ANCESTOR").edges()[0]
            attributes = medrecord.edge(vocabulary_edge).attributes()

            assigned = medrecord.replace_edge_attributes(user_edge, {"role": "dolor"})

            assert assigned.edge(user_edge).attributes() == {"role": "dolor"}

            spared = medrecord.replace_edge_attributes(vocabulary_edge, {})

            assert spared.edge(vocabulary_edge).attributes() == attributes

    def test_pre_remove_edge_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge_in_group(
                1000, concept, {"role": "lorem"}, "Diagnosis"
            )
            user_edge = medrecord.group("Diagnosis").edges()[0]
            vocabulary_edge = medrecord.group("OMOP_CONCEPT_ANCESTOR").edges()[0]
            attributes = medrecord.edge(vocabulary_edge).attributes()

            removed = medrecord.remove_edge_attributes(user_edge, ["role"])

            assert removed.edge(user_edge).attributes() == {}

            spared = medrecord.remove_edge_attributes(
                vocabulary_edge, ["min_levels_of_separation"]
            )

            assert spared.edge(vocabulary_edge).attributes() == attributes

    def test_pre_add_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder).add_group("Diagnosis")

            assert medrecord.contains_group("Diagnosis")

    def test_invalid_pre_add_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.add_group("OMOP_CONCEPT")

    def test_pre_remove_groups(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            plugin = OmopPlugin(folder)
            medrecord = MedRecord().add_node_in_group(1000, {}, "Patient")
            medrecord = medrecord.add_plugin("omop", plugin)

            removed = medrecord.remove_groups("Patient")

            assert not removed.contains_group("Patient")
            assert removed.contains_group("OMOP_CONCEPT")

            spared = medrecord.remove_groups("OMOP_CONCEPT")

            assert spared.contains_group("OMOP_CONCEPT")

            kept = medrecord.keep_groups(["Patient"])

            assert kept.contains_group("OMOP_CONCEPT")

            stripped = medrecord.remove_groups(plugin.reserved_groups)

            assert stripped.contains_group("OMOP_CONCEPT")
            assert stripped.group("OMOP_CONCEPT").node_count() == 2

    def test_pre_add_nodes_to_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = (
                _create_medrecord(folder)
                .add_node(2000, {})
                .add_nodes_to_group(2000, "Patient")
            )

            assert medrecord.group("Patient").nodes() == [1000, 2000]

    def test_invalid_pre_add_nodes_to_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.add_nodes_to_group(1000, "OMOP_CONCEPT")

    def test_pre_remove_nodes_from_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder).remove_nodes_from_group(
                1000, "Patient"
            )

            assert medrecord.group("Patient").nodes() == []

    def test_invalid_pre_remove_nodes_from_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.remove_nodes_from_group(concept, "OMOP_CONCEPT")

    def test_pre_add_edges_to_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge(1000, concept, {})
            user_edge = medrecord.edge_indices()[-1]

            medrecord = medrecord.add_edges_to_group(user_edge, "Diagnosis")

            assert medrecord.group("Diagnosis").edges() == [user_edge]

    def test_invalid_pre_add_edges_to_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge(1000, concept, {})
            user_edge = medrecord.edge_indices()[-1]

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.add_edges_to_group(user_edge, "OMOP_CONCEPT_ANCESTOR")

    def test_pre_remove_edges_from_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            concept = medrecord.group("OMOP_CONCEPT").nodes()[0]
            medrecord = medrecord.add_edge_in_group(1000, concept, {}, "Diagnosis")
            user_edge = medrecord.group("Diagnosis").edges()[0]

            medrecord = medrecord.remove_edges_from_group(user_edge, "Diagnosis")

            assert medrecord.group("Diagnosis").edges() == []

    def test_invalid_pre_remove_edges_from_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            vocabulary_edge = medrecord.group("OMOP_CONCEPT_ANCESTOR").edges()[0]

            with pytest.raises(ValueError, match="is reserved by the OMOP plugin"):
                medrecord.remove_edges_from_group(
                    vocabulary_edge, "OMOP_CONCEPT_ANCESTOR"
                )

    def test_pre_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            folder = Path(temporary_directory)
            _create_vocabulary_folder(folder)

            medrecord = _create_medrecord(folder)
            node_count = medrecord.node_count()
            edge_count = medrecord.edge_count()

            cleared = medrecord.clear()

            assert not cleared.contains_node(1000)
            assert not cleared.contains_group("Patient")
            assert cleared.node_count() == node_count - 1
            assert cleared.edge_count() == edge_count
            assert cleared.contains_group("OMOP_CONCEPT")
            assert cleared.plugins == ["omop"]


if __name__ == "__main__":
    unittest.main()
