"""OMOP vocabulary plugin for MedRecord."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

import polars as pl
from graphrecords.plugins import (
    AddEdgesInGroup,
    AddNodesInGroup,
    EdgeBatch,
    NodeBatch,
)

from medrecords.plugin import Plugin

if TYPE_CHECKING:
    from pathlib import Path

    from graphrecords.plugins import Changes
    from graphrecords.types import GroupIndex

    from medrecords.medrecord import MedRecord


class OmopPlugin(Plugin):
    """Plugin that loads OMOP vocabulary tables into a MedRecord."""

    vocabulary_nodes: List[Tuple[Tuple[pl.DataFrame, str], GroupIndex]]
    vocabulary_edges: List[Tuple[Tuple[pl.DataFrame, str, str], GroupIndex]]

    def __init__(
        self,
        vocabulary_folder_path: Path,
        separator: str = "\t",
        quote_char: Optional[str] = None,
    ) -> None:
        """Initializes the OMOP plugin by reading vocabulary CSV files.

        Args:
            vocabulary_folder_path (Path): Path to the folder containing OMOP
                vocabulary CSV files.
            separator (str): Column separator for CSV files. Defaults to tab.
            quote_char (Optional[str]): Quote character for CSV files.
                Defaults to None.
        """
        concept_ancestor = pl.read_csv(
            vocabulary_folder_path / "CONCEPT_ANCESTOR.csv",
            separator=separator,
            quote_char=quote_char,
        )
        concept_class = pl.read_csv(
            vocabulary_folder_path / "CONCEPT_CLASS.csv",
            separator=separator,
            quote_char=quote_char,
        )
        concept_relationship = pl.read_csv(
            vocabulary_folder_path / "CONCEPT_RELATIONSHIP.csv",
            separator=separator,
            quote_char=quote_char,
        )
        concept_synonym = pl.read_csv(
            vocabulary_folder_path / "CONCEPT_SYNONYM.csv",
            separator=separator,
            quote_char=quote_char,
        )
        concept = pl.read_csv(
            vocabulary_folder_path / "CONCEPT.csv",
            separator=separator,
            quote_char=quote_char,
        )
        domain = pl.read_csv(
            vocabulary_folder_path / "DOMAIN.csv",
            separator=separator,
            quote_char=quote_char,
        )
        drug_strength = pl.read_csv(
            vocabulary_folder_path / "DRUG_STRENGTH.csv",
            separator=separator,
            quote_char=quote_char,
        )
        relationship = pl.read_csv(
            vocabulary_folder_path / "RELATIONSHIP.csv",
            separator=separator,
            quote_char=quote_char,
        )
        vocabulary = pl.read_csv(
            vocabulary_folder_path / "VOCABULARY.csv",
            separator=separator,
            quote_char=quote_char,
        )

        vocabulary = vocabulary.with_columns(
            pl.concat_str([pl.lit("VOCABULARY/"), pl.col("vocabulary_id")]).alias(
                "vocabulary_id"
            )
        )
        domain = domain.with_columns(
            pl.concat_str([pl.lit("DOMAIN/"), pl.col("domain_id")]).alias("domain_id")
        )
        concept_class = concept_class.with_columns(
            pl.concat_str([pl.lit("CONCEPT_CLASS/"), pl.col("concept_class_id")]).alias(
                "concept_class_id"
            )
        )
        relationship = relationship.with_columns(
            pl.concat_str([pl.lit("RELATIONSHIP/"), pl.col("relationship_id")]).alias(
                "relationship_id"
            ),
            pl.concat_str(
                [pl.lit("RELATIONSHIP/"), pl.col("reverse_relationship_id")]
            ).alias("reverse_relationship_id"),
        )

        vocabulary_concept_edges = vocabulary.select(
            "vocabulary_id", "vocabulary_concept_id"
        )
        concept_vocabulary_edges = concept.select(
            "concept_id", "vocabulary_id"
        ).with_columns(
            pl.concat_str([pl.lit("VOCABULARY/"), pl.col("vocabulary_id")]).alias(
                "vocabulary_id"
            )
        )

        domain_concept_edges = domain.select("domain_id", "domain_concept_id")
        concept_domain_edges = concept.select("concept_id", "domain_id").with_columns(
            pl.concat_str([pl.lit("DOMAIN/"), pl.col("domain_id")]).alias("domain_id")
        )

        concept_class_concept_edges = concept_class.select(
            "concept_class_id", "concept_class_concept_id"
        )
        concept_concept_class_edges = concept.select(
            "concept_id", "concept_class_id"
        ).with_columns(
            pl.concat_str([pl.lit("CONCEPT_CLASS/"), pl.col("concept_class_id")]).alias(
                "concept_class_id"
            )
        )

        relationship_concept_edges = relationship.select(
            "relationship_id", "relationship_concept_id"
        )
        relationship_reverse_edges = relationship.select(
            "relationship_id", "reverse_relationship_id"
        )

        concept_ancestor_edges = concept_ancestor
        concept_relationship_edges = concept_relationship
        concept_synonym_edges = concept_synonym
        drug_strength_edges = drug_strength

        vocabulary = vocabulary.drop("vocabulary_concept_id")
        domain = domain.drop("domain_concept_id")
        concept_class = concept_class.drop("concept_class_concept_id")
        relationship = relationship.drop(
            "reverse_relationship_id", "relationship_concept_id"
        )
        concept = concept.drop("vocabulary_id", "domain_id", "concept_class_id")

        self.vocabulary_nodes = [
            ((vocabulary, "vocabulary_id"), "OMOP_VOCABULARY"),
            ((concept, "concept_id"), "OMOP_CONCEPT"),
            ((domain, "domain_id"), "OMOP_DOMAIN"),
            ((concept_class, "concept_class_id"), "OMOP_CONCEPT_CLASS"),
            ((relationship, "relationship_id"), "OMOP_RELATIONSHIP"),
        ]
        self.vocabulary_edges = [
            (
                (vocabulary_concept_edges, "vocabulary_id", "vocabulary_concept_id"),
                "OMOP_VOCABULARY_CONCEPT",
            ),
            (
                (concept_vocabulary_edges, "concept_id", "vocabulary_id"),
                "OMOP_CONCEPT_VOCABULARY",
            ),
            (
                (domain_concept_edges, "domain_id", "domain_concept_id"),
                "OMOP_DOMAIN_CONCEPT",
            ),
            (
                (concept_domain_edges, "concept_id", "domain_id"),
                "OMOP_CONCEPT_DOMAIN",
            ),
            (
                (
                    concept_class_concept_edges,
                    "concept_class_id",
                    "concept_class_concept_id",
                ),
                "OMOP_CONCEPT_CLASS_CONCEPT",
            ),
            (
                (concept_concept_class_edges, "concept_id", "concept_class_id"),
                "OMOP_CONCEPT_CONCEPT_CLASS",
            ),
            (
                (
                    relationship_concept_edges,
                    "relationship_id",
                    "relationship_concept_id",
                ),
                "OMOP_RELATIONSHIP_CONCEPT",
            ),
            (
                (
                    relationship_reverse_edges,
                    "relationship_id",
                    "reverse_relationship_id",
                ),
                "OMOP_RELATIONSHIP_REVERSE",
            ),
            (
                (
                    concept_ancestor_edges,
                    "ancestor_concept_id",
                    "descendant_concept_id",
                ),
                "OMOP_CONCEPT_ANCESTOR",
            ),
            (
                (concept_relationship_edges, "concept_id_1", "concept_id_2"),
                "OMOP_CONCEPT_RELATIONSHIP",
            ),
            (
                (concept_synonym_edges, "concept_id", "language_concept_id"),
                "OMOP_CONCEPT_SYNONYM",
            ),
            (
                (drug_strength_edges, "drug_concept_id", "ingredient_concept_id"),
                "OMOP_DRUG_STRENGTH",
            ),
        ]

    def initialize(self, medrecord: MedRecord) -> Changes:
        """Adds OMOP vocabulary nodes and edges to the MedRecord.

        Args:
            medrecord (MedRecord): The MedRecord the plugin is added to.

        Returns:
            Changes: The changes that add the vocabulary nodes and edges, each in
                its group.
        """
        node_changes = [
            AddNodesInGroup(NodeBatch(node_source), group)
            for node_source, group in self.vocabulary_nodes
        ]
        edge_changes = [
            AddEdgesInGroup(EdgeBatch(edge_source), group)
            for edge_source, group in self.vocabulary_edges
        ]

        return [*node_changes, *edge_changes]
