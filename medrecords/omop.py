"""OMOP vocabulary plugin for MedRecord."""

from __future__ import annotations

from typing import TYPE_CHECKING, FrozenSet, List, Optional, Tuple

import polars as pl
from graphrecords.plugins import (
    AddEdgesInGroup,
    AddNodesInGroup,
    EdgeBatch,
    NodeBatch,
    RemoveEdgeAttributes,
    RemoveEdges,
    RemoveGroups,
    RemoveNodeAttributes,
    RemoveNodes,
    ReplaceEdgeAttributes,
    ReplaceNodeAttributes,
    SetEdgeAttributes,
    SetNodeAttributes,
)

from medrecords.plugin import Plugin

if TYPE_CHECKING:
    from pathlib import Path

    from graphrecords.plugins import (
        AddEdgesToGroup,
        AddGroup,
        AddNodesToGroup,
        Change,
        Changes,
        Clear,
        RemoveEdgesFromGroup,
        RemoveNodesFromGroup,
    )
    from graphrecords.types import EdgeIndex, GroupIndex, NodeIndex

    from medrecords.medrecord import MedRecord


class OmopPlugin(Plugin):
    """Plugin that loads OMOP vocabulary tables into a MedRecord.

    The plugin reserves one group per vocabulary table. It refuses to attach to a
    MedRecord that already holds one of them, and refuses every change that names
    a reserved group. Every other change is narrowed to the part of the MedRecord
    that is not the vocabulary, so the vocabulary survives changes that would
    otherwise sweep it up. Removing the plugin leaves the vocabulary in the
    MedRecord, where changes reach it like any other data.
    """

    vocabulary_nodes: List[Tuple[Tuple[pl.DataFrame, str], GroupIndex]]
    vocabulary_edges: List[Tuple[Tuple[pl.DataFrame, str, str], GroupIndex]]
    _reserved_groups: FrozenSet[GroupIndex]

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

        self._reserved_groups = frozenset(self.reserved_groups)

    @property
    def reserved_groups(self) -> List[GroupIndex]:
        """The groups the plugin reserves for the OMOP vocabulary.

        Returns:
            List[GroupIndex]: The group of every vocabulary node and edge table.
        """
        return [group for _, group in self.vocabulary_nodes] + [
            group for _, group in self.vocabulary_edges
        ]

    def initialize(self, medrecord: MedRecord) -> Changes:
        """Checks that the reserved groups are free and adds the vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the plugin is added to.

        Returns:
            Changes: The changes that add the vocabulary.

        Raises:
            ValueError: If the MedRecord already holds a reserved group.
        """
        taken_groups = [
            group for group in self.reserved_groups if medrecord.contains_group(group)
        ]

        if taken_groups:
            listed_groups = ", ".join(repr(group) for group in taken_groups)
            msg = f"the MedRecord already holds {listed_groups}, reserved by the OMOP plugin"
            raise ValueError(msg)

        return self._vocabulary_changes()

    def pre_add_nodes_in_group(
        self, medrecord: MedRecord, addition: AddNodesInGroup
    ) -> None:
        """Refuses nodes added in a group the plugin reserves.

        A MedRecord hands the changes initialize returns back to this hook, where
        the reserved groups do not exist yet, so only a group that is already
        there is refused.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            addition (AddNodesInGroup): The change that is applied.
        """
        if medrecord.contains_group(addition.group_index):
            self._refuse_reserved_group(addition.group_index)

    def pre_add_edges_in_group(
        self, medrecord: MedRecord, addition: AddEdgesInGroup
    ) -> None:
        """Refuses edges added in a group the plugin reserves.

        A MedRecord hands the changes initialize returns back to this hook, where
        the reserved groups do not exist yet, so only a group that is already
        there is refused.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            addition (AddEdgesInGroup): The change that is applied.
        """
        if medrecord.contains_group(addition.group_index):
            self._refuse_reserved_group(addition.group_index)

    def pre_remove_nodes(
        self, medrecord: MedRecord, removal: RemoveNodes
    ) -> Optional[Changes]:
        """Keeps a removal off the nodes of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            removal (RemoveNodes): The change that is applied.

        Returns:
            Optional[Changes]: The removal without the vocabulary nodes, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_nodes(medrecord, removal.node_indices)

        if len(kept_indices) == len(removal.node_indices):
            return None

        return RemoveNodes(kept_indices)

    def pre_remove_edges(
        self, medrecord: MedRecord, removal: RemoveEdges
    ) -> Optional[Changes]:
        """Keeps a removal off the edges of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            removal (RemoveEdges): The change that is applied.

        Returns:
            Optional[Changes]: The removal without the vocabulary edges, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_edges(medrecord, removal.edge_indices)

        if len(kept_indices) == len(removal.edge_indices):
            return None

        return RemoveEdges(kept_indices)

    def pre_set_node_attributes(
        self, medrecord: MedRecord, assignment: SetNodeAttributes
    ) -> Optional[Changes]:
        """Keeps an assignment off the nodes of the OMOP vocabulary.

        A merge that resolves conflicts in favour of the other MedRecord arrives
        here, and would otherwise write over the attributes of a vocabulary node.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            assignment (SetNodeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The assignment without the vocabulary nodes, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_nodes(
            medrecord, assignment.node_indices
        )

        if len(kept_indices) == len(assignment.node_indices):
            return None

        return SetNodeAttributes(kept_indices, assignment.attributes)

    def pre_replace_node_attributes(
        self, medrecord: MedRecord, assignment: ReplaceNodeAttributes
    ) -> Optional[Changes]:
        """Keeps a replacement off the nodes of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            assignment (ReplaceNodeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The replacement without the vocabulary nodes, or
                None when it names none.
        """
        kept_indices = self._without_vocabulary_nodes(
            medrecord, assignment.node_indices
        )

        if len(kept_indices) == len(assignment.node_indices):
            return None

        return ReplaceNodeAttributes(kept_indices, assignment.attributes)

    def pre_remove_node_attributes(
        self, medrecord: MedRecord, removal: RemoveNodeAttributes
    ) -> Optional[Changes]:
        """Keeps an attribute removal off the nodes of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            removal (RemoveNodeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The removal without the vocabulary nodes, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_nodes(medrecord, removal.node_indices)

        if len(kept_indices) == len(removal.node_indices):
            return None

        return RemoveNodeAttributes(kept_indices, removal.attribute_names)

    def pre_set_edge_attributes(
        self, medrecord: MedRecord, assignment: SetEdgeAttributes
    ) -> Optional[Changes]:
        """Keeps an assignment off the edges of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            assignment (SetEdgeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The assignment without the vocabulary edges, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_edges(
            medrecord, assignment.edge_indices
        )

        if len(kept_indices) == len(assignment.edge_indices):
            return None

        return SetEdgeAttributes(kept_indices, assignment.attributes)

    def pre_replace_edge_attributes(
        self, medrecord: MedRecord, assignment: ReplaceEdgeAttributes
    ) -> Optional[Changes]:
        """Keeps a replacement off the edges of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            assignment (ReplaceEdgeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The replacement without the vocabulary edges, or
                None when it names none.
        """
        kept_indices = self._without_vocabulary_edges(
            medrecord, assignment.edge_indices
        )

        if len(kept_indices) == len(assignment.edge_indices):
            return None

        return ReplaceEdgeAttributes(kept_indices, assignment.attributes)

    def pre_remove_edge_attributes(
        self, medrecord: MedRecord, removal: RemoveEdgeAttributes
    ) -> Optional[Changes]:
        """Keeps an attribute removal off the edges of the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            removal (RemoveEdgeAttributes): The change that is applied.

        Returns:
            Optional[Changes]: The removal without the vocabulary edges, or None
                when it names none.
        """
        kept_indices = self._without_vocabulary_edges(medrecord, removal.edge_indices)

        if len(kept_indices) == len(removal.edge_indices):
            return None

        return RemoveEdgeAttributes(kept_indices, removal.attribute_names)

    def pre_add_group(self, medrecord: MedRecord, addition: AddGroup) -> None:
        """Refuses adding a group the plugin reserves.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            addition (AddGroup): The change that is applied.
        """
        self._refuse_reserved_group(addition.group_index)

    def pre_remove_groups(
        self, medrecord: MedRecord, removal: RemoveGroups
    ) -> Optional[Changes]:
        """Keeps a removal off the reserved groups.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            removal (RemoveGroups): The change that is applied.

        Returns:
            Optional[Changes]: The removal without the reserved groups, or None
                when it names none.
        """
        kept_groups = [
            group_index
            for group_index in removal.group_indices
            if group_index not in self._reserved_groups
        ]

        if len(kept_groups) == len(removal.group_indices):
            return None

        return RemoveGroups(kept_groups)

    def pre_add_nodes_to_group(
        self, medrecord: MedRecord, membership: AddNodesToGroup
    ) -> None:
        """Refuses nodes joining a group the plugin reserves.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            membership (AddNodesToGroup): The change that is applied.
        """
        self._refuse_reserved_group(membership.group_index)

    def pre_remove_nodes_from_group(
        self, medrecord: MedRecord, membership: RemoveNodesFromGroup
    ) -> None:
        """Refuses nodes leaving a group the plugin reserves.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            membership (RemoveNodesFromGroup): The change that is applied.
        """
        self._refuse_reserved_group(membership.group_index)

    def pre_add_edges_to_group(
        self, medrecord: MedRecord, membership: AddEdgesToGroup
    ) -> None:
        """Refuses edges joining a group the plugin reserves.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            membership (AddEdgesToGroup): The change that is applied.
        """
        self._refuse_reserved_group(membership.group_index)

    def pre_remove_edges_from_group(
        self, medrecord: MedRecord, membership: RemoveEdgesFromGroup
    ) -> None:
        """Refuses edges leaving a group the plugin reserves.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            membership (RemoveEdgesFromGroup): The change that is applied.
        """
        self._refuse_reserved_group(membership.group_index)

    def pre_clear(self, medrecord: MedRecord, clearing: Clear) -> Changes:
        """Puts the OMOP vocabulary back into a cleared MedRecord.

        Args:
            medrecord (MedRecord): The MedRecord the change is applied to.
            clearing (Clear): The change that is applied.

        Returns:
            Changes: The clearing, followed by the changes that add the vocabulary.
        """
        return [clearing, *self._vocabulary_changes()]

    def _vocabulary_changes(self) -> List[Change]:
        """Builds the changes that put the vocabulary into a MedRecord.

        Returns:
            List[Change]: The changes that add the vocabulary nodes and edges,
                each in its group.
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

    def _refuse_reserved_group(self, group_index: GroupIndex) -> None:
        """Refuses a group the plugin reserves.

        Args:
            group_index (GroupIndex): The group the change names.

        Raises:
            ValueError: If the plugin reserves the group.
        """
        if group_index in self._reserved_groups:
            msg = f"group {group_index!r} is reserved by the OMOP plugin"
            raise ValueError(msg)

    def _without_vocabulary_nodes(
        self, medrecord: MedRecord, node_indices: List[NodeIndex]
    ) -> List[NodeIndex]:
        """Drops the nodes that belong to the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord holding the nodes.
            node_indices (List[NodeIndex]): The nodes the change names.

        Returns:
            List[NodeIndex]: The nodes that are not part of the vocabulary.
        """
        return [
            node_index
            for node_index in node_indices
            if self._reserved_groups.isdisjoint(medrecord.node(node_index).groups())
        ]

    def _without_vocabulary_edges(
        self, medrecord: MedRecord, edge_indices: List[EdgeIndex]
    ) -> List[EdgeIndex]:
        """Drops the edges that belong to the OMOP vocabulary.

        Args:
            medrecord (MedRecord): The MedRecord holding the edges.
            edge_indices (List[EdgeIndex]): The edges the change names.

        Returns:
            List[EdgeIndex]: The edges that are not part of the vocabulary.
        """
        return [
            edge_index
            for edge_index in edge_indices
            if self._reserved_groups.isdisjoint(medrecord.edge(edge_index).groups())
        ]
