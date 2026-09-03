"""Analytics over the nodes, edges and groups a MedRecord holds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Generic, List, Mapping, Optional

from graphrecords import EdgeEndpointRole

from medrecords.evaluation.analytic import Analytic, Distribution, Table
from medrecords.evaluation.catalogue.attributes import IndexType
from medrecords.evaluation.results import read, read_pairs
from medrecords.medrecord import MedRecord

if TYPE_CHECKING:
    from graphrecords import GroupIndex, Value, querying

    from medrecords.evaluation.analytic import Detail


class ElementCount(Analytic[MedRecord], Generic[IndexType]):
    """How many nodes or edges a selection holds."""

    _elements: querying.ElementsExpression[IndexType, querying.Unordered]

    def __init__(
        self, elements: querying.ElementsExpression[IndexType, querying.Unordered]
    ) -> None:
        """Initializes a count of elements.

        Args:
            elements (querying.ElementsExpression[IndexType, querying.Unordered]):
                The nodes or edges to count.
        """
        self._elements = elements

    def compute(self, medrecord: MedRecord) -> int:
        """Counts the elements.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            int: The number of elements.
        """
        return read(medrecord.query(self._elements).count().evaluate(), int)


class GroupSizes(Analytic[MedRecord]):
    """How many nodes and edges every group holds."""

    def compute(self, medrecord: MedRecord) -> Table:
        """Counts the nodes and edges per group.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Table: One row per group with its node and edge counts.
        """
        edge_counts: Dict[GroupIndex, int] = dict(
            read_pairs(medrecord.groups().edge_count().evaluate(), int)
        )
        rows: List[List[Value]] = [
            [group, node_count, edge_counts[group]]
            for group, node_count in read_pairs(
                medrecord.groups().node_count().evaluate(), int
            )
        ]
        return Table(["group", "nodes", "edges"], rows)

    def title(self) -> Optional[str]:
        """Names the analytic.

        Returns:
            Optional[str]: The heading.
        """
        return "Group sizes"


class EdgesPerNode(Analytic[MedRecord]):
    """How many of the selected edges the selected nodes take part in."""

    _nodes: querying.NodesExpression
    _edges: querying.EdgesExpression
    _role: EdgeEndpointRole

    def __init__(
        self,
        nodes: querying.NodesExpression,
        edges: querying.EdgesExpression,
        role: EdgeEndpointRole,
    ) -> None:
        """Initializes a count of edges per node.

        Args:
            nodes (querying.NodesExpression): The nodes counted for.
            edges (querying.EdgesExpression): The edges counted.
            role (EdgeEndpointRole): Whether a node takes part as the source or
                the target of an edge.
        """
        self._nodes = nodes
        self._edges = edges
        self._role = role

    def compute(self, medrecord: MedRecord) -> Distribution:
        """Counts the edges per node.

        Nodes without any edge count as zero.

        Args:
            medrecord (MedRecord): The MedRecord to look at.

        Returns:
            Distribution: One count per selected node, of which there must be at
                least one.
        """
        links = medrecord.query(self._edges)
        members = medrecord.query(self._nodes)
        from_source = self._role is EdgeEndpointRole.Source
        ends = links.via_source_node() if from_source else links.via_target_node()
        inside = links.filter(ends.index().is_in(members.index()))
        reached = inside.via_source_node() if from_source else inside.via_target_node()
        counts = read_pairs(
            inside.group_by(reached.index()).count().ungroup_keyed().evaluate(), int
        )
        total = read(members.count().evaluate(), int)

        return Distribution(
            [count for _, count in counts] + [0] * (total - len(counts))
        )

    def description(self) -> Optional[str]:
        """Explains the analytic.

        Returns:
            Optional[str]: The text under the heading.
        """
        return "Nodes without any edge count as zero."

    def parameters(self) -> Mapping[str, Detail]:
        """Records the role.

        Returns:
            Mapping[str, Detail]: The role.
        """
        return {"role": self._role.name.lower()}
