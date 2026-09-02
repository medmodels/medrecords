import tempfile
import unittest
from pathlib import Path

import polars as pl

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


if __name__ == "__main__":
    unittest.main()
