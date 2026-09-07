"""MedRecord."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple, TypeVar, Union

from graphrecords import GraphRecord, OnConflict
from graphrecords.overview import DEFAULT_TRUNCATE_DETAILS

from medrecords.plugin import Plugin

if TYPE_CHECKING:
    import os
    from typing import Callable

    import pandas as pd
    import polars as pl
    from graphrecords import (
        EdgeView,
        GroupView,
        NodeView,
        RecordBatch,
        Schema,
        Writer,
    )
    from graphrecords.graphrecord import Export
    from graphrecords.overview import GroupOverview, Overview
    from graphrecords.querying import (
        C,
        EdgesSeries,
        Expression,
        GroupsSeries,
        Levels,
        NodesSeries,
        S,
        Series,
        Unbound,
    )
    from graphrecords.types import (
        AttributeName,
        Attributes,
        EdgeIndex,
        EdgeSource,
        GroupIndex,
        MultipleEdgeSelection,
        MultipleGroupSelection,
        MultipleNodeSelection,
        NodeIndex,
        NodeSource,
        PluginName,
        SingleGroupSelection,
        SingleNodeSelection,
    )
    from typing_extensions import Unpack

T = TypeVar("T")


class MedRecord:
    """A GraphRecord with built-in medical data handling."""

    _graphrecord: GraphRecord

    def __init__(self) -> None:
        """Initializes an empty MedRecord."""
        self._graphrecord = GraphRecord()

    @classmethod
    def from_graphrecord(cls, graphrecord: GraphRecord) -> MedRecord:
        """Creates a MedRecord around an existing GraphRecord.

        Args:
            graphrecord (GraphRecord): The GraphRecord to wrap.

        Returns:
            MedRecord: A MedRecord holding the contents of the GraphRecord.
        """
        instance = cls()
        instance._graphrecord = graphrecord
        return instance

    @classmethod
    def with_schema(cls, schema: Schema) -> MedRecord:
        """Creates an empty MedRecord that validates against the given schema.

        Args:
            schema (Schema): The schema the MedRecord validates against.

        Returns:
            MedRecord: An empty MedRecord carrying the schema.
        """
        instance = cls()
        instance._graphrecord = GraphRecord.with_schema(schema)
        return instance

    @classmethod
    def from_ron(cls, path: Union[str, os.PathLike[str]]) -> MedRecord:
        """Reads a MedRecord from a RON file.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the file to read.

        Returns:
            MedRecord: The MedRecord stored in the file.
        """
        instance = cls()
        instance._graphrecord = GraphRecord.from_ron(path)
        return instance

    @property
    def graphrecord(self) -> GraphRecord:
        """The GraphRecord the MedRecord holds.

        Returns:
            GraphRecord: The GraphRecord holding the contents of the MedRecord.
        """
        return self._graphrecord

    @property
    def plugins(self) -> List[PluginName]:
        """The names of the plugins attached to the MedRecord.

        Returns:
            List[PluginName]: The name of every attached plugin.
        """
        return self._graphrecord.plugins

    @property
    def plugin_entries(self) -> Dict[PluginName, Plugin]:
        """The plugins attached to the MedRecord, by the name they are attached under.

        Returns:
            Dict[PluginName, Plugin]: Every attached plugin, by its name.
        """
        return {
            name: plugin
            if isinstance(plugin, Plugin)
            else Plugin.from_graphrecord_plugin(plugin)
            for name, plugin in self._graphrecord.plugin_entries.items()
        }

    def add_plugin(self, name: PluginName, plugin: Plugin) -> MedRecord:
        """Attaches a plugin under the given name.

        Args:
            name (PluginName): The name to attach the plugin under.
            plugin (Plugin): The plugin to attach.

        Returns:
            MedRecord: A MedRecord with the plugin attached.
        """
        return MedRecord.from_graphrecord(self._graphrecord.add_plugin(name, plugin))

    def remove_plugin(self, name: PluginName) -> MedRecord:
        """Detaches the plugin attached under the given name.

        Args:
            name (PluginName): The name the plugin is attached under.

        Returns:
            MedRecord: A MedRecord without that plugin.
        """
        return MedRecord.from_graphrecord(self._graphrecord.remove_plugin(name))

    def add_nodes(self, source: NodeSource) -> MedRecord:
        """Adds the nodes of the given source.

        Args:
            source (NodeSource): The nodes to add.

        Returns:
            MedRecord: A MedRecord containing the added nodes.
        """
        return MedRecord.from_graphrecord(self._graphrecord.add_nodes(source))

    def add_node(
        self, node_index: SingleNodeSelection, attributes: Attributes
    ) -> MedRecord:
        """Adds a single node with the given attributes.

        Args:
            node_index (SingleNodeSelection): The index of the node to add.
            attributes (Attributes): The attributes of the node.

        Returns:
            MedRecord: A MedRecord containing the added node.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_node(node_index, attributes)
        )

    def add_nodes_in_group(
        self, source: NodeSource, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Adds the nodes of the given source to a group.

        Args:
            source (NodeSource): The nodes to add.
            group_index (SingleGroupSelection): The group the nodes are added in.

        Returns:
            MedRecord: A MedRecord containing the added nodes.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_nodes_in_group(source, group_index)
        )

    def add_node_in_group(
        self,
        node_index: SingleNodeSelection,
        attributes: Attributes,
        group_index: SingleGroupSelection,
    ) -> MedRecord:
        """Adds a single node with the given attributes to a group.

        Args:
            node_index (SingleNodeSelection): The index of the node to add.
            attributes (Attributes): The attributes of the node.
            group_index (SingleGroupSelection): The group the node is added in.

        Returns:
            MedRecord: A MedRecord containing the added node.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_node_in_group(node_index, attributes, group_index)
        )

    def add_edges(self, source: EdgeSource) -> MedRecord:
        """Adds the edges of the given source.

        Args:
            source (EdgeSource): The edges to add.

        Returns:
            MedRecord: A MedRecord containing the added edges.
        """
        return MedRecord.from_graphrecord(self._graphrecord.add_edges(source))

    def add_edge(
        self,
        source_node_index: SingleNodeSelection,
        target_node_index: SingleNodeSelection,
        attributes: Attributes,
    ) -> MedRecord:
        """Adds a single edge with the given attributes.

        Args:
            source_node_index (SingleNodeSelection): The node the edge starts at.
            target_node_index (SingleNodeSelection): The node the edge ends at.
            attributes (Attributes): The attributes of the edge.

        Returns:
            MedRecord: A MedRecord containing the added edge.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_edge(source_node_index, target_node_index, attributes)
        )

    def add_edges_in_group(
        self, source: EdgeSource, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Adds the edges of the given source to a group.

        Args:
            source (EdgeSource): The edges to add.
            group_index (SingleGroupSelection): The group the edges are added in.

        Returns:
            MedRecord: A MedRecord containing the added edges.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_edges_in_group(source, group_index)
        )

    def add_edge_in_group(
        self,
        source_node_index: SingleNodeSelection,
        target_node_index: SingleNodeSelection,
        attributes: Attributes,
        group_index: SingleGroupSelection,
    ) -> MedRecord:
        """Adds a single edge with the given attributes to a group.

        Args:
            source_node_index (SingleNodeSelection): The node the edge starts at.
            target_node_index (SingleNodeSelection): The node the edge ends at.
            attributes (Attributes): The attributes of the edge.
            group_index (SingleGroupSelection): The group the edge is added in.

        Returns:
            MedRecord: A MedRecord containing the added edge.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_edge_in_group(
                source_node_index, target_node_index, attributes, group_index
            )
        )

    def remove_nodes(self, node_indices: MultipleNodeSelection) -> MedRecord:
        """Removes the selected nodes and the edges attached to them.

        Args:
            node_indices (MultipleNodeSelection): The nodes to remove.

        Returns:
            MedRecord: A MedRecord without those nodes.
        """
        return MedRecord.from_graphrecord(self._graphrecord.remove_nodes(node_indices))

    def remove_edges(self, edge_indices: MultipleEdgeSelection) -> MedRecord:
        """Removes the selected edges.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to remove.

        Returns:
            MedRecord: A MedRecord without those edges.
        """
        return MedRecord.from_graphrecord(self._graphrecord.remove_edges(edge_indices))

    def keep_nodes(self, node_indices: MultipleNodeSelection) -> MedRecord:
        """Keeps only the selected nodes and the edges between them.

        Args:
            node_indices (MultipleNodeSelection): The nodes to keep.

        Returns:
            MedRecord: A MedRecord holding only those nodes.
        """
        return MedRecord.from_graphrecord(self._graphrecord.keep_nodes(node_indices))

    def keep_edges(self, edge_indices: MultipleEdgeSelection) -> MedRecord:
        """Keeps only the selected edges.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to keep.

        Returns:
            MedRecord: A MedRecord holding only those edges.
        """
        return MedRecord.from_graphrecord(self._graphrecord.keep_edges(edge_indices))

    def keep_groups(self, group_indices: MultipleGroupSelection) -> MedRecord:
        """Keeps only the selected groups and their members.

        Args:
            group_indices (MultipleGroupSelection): The groups to keep.

        Returns:
            MedRecord: A MedRecord holding only those groups.
        """
        return MedRecord.from_graphrecord(self._graphrecord.keep_groups(group_indices))

    def intersect(self, other: MedRecord) -> MedRecord:
        """Keeps what this MedRecord and the other one have in common.

        Args:
            other (MedRecord): The MedRecord to intersect with.

        Returns:
            MedRecord: A MedRecord holding the shared nodes, edges and groups.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.intersect(other._graphrecord)
        )

    def difference(self, other: MedRecord) -> MedRecord:
        """Removes everything the other MedRecord also holds.

        Args:
            other (MedRecord): The MedRecord to subtract.

        Returns:
            MedRecord: A MedRecord holding what only this one held.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.difference(other._graphrecord)
        )

    def merge(
        self, other: MedRecord, on_conflict: OnConflict = OnConflict.Raise
    ) -> MedRecord:
        """Merges the other MedRecord into this one.

        Args:
            other (MedRecord): The MedRecord to merge in.
            on_conflict (OnConflict): How attributes both MedRecords define are
                resolved. Defaults to OnConflict.Raise.

        Returns:
            MedRecord: A MedRecord holding both.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.merge(other._graphrecord, on_conflict)
        )

    def set_node_attributes(
        self, node_indices: MultipleNodeSelection, attributes: Attributes
    ) -> MedRecord:
        """Sets the given attributes on the selected nodes, keeping the others.

        Args:
            node_indices (MultipleNodeSelection): The nodes to set the attributes on.
            attributes (Attributes): The attributes to set.

        Returns:
            MedRecord: A MedRecord with the attributes set.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.set_node_attributes(node_indices, attributes)
        )

    def replace_node_attributes(
        self, node_indices: MultipleNodeSelection, attributes: Attributes
    ) -> MedRecord:
        """Replaces all attributes of the selected nodes with the given ones.

        Args:
            node_indices (MultipleNodeSelection): The nodes to replace the attributes
                of.
            attributes (Attributes): The attributes the nodes end up with.

        Returns:
            MedRecord: A MedRecord with the attributes replaced.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.replace_node_attributes(node_indices, attributes)
        )

    def remove_node_attributes(
        self,
        node_indices: MultipleNodeSelection,
        attribute_names: Iterable[AttributeName],
    ) -> MedRecord:
        """Removes the named attributes from the selected nodes.

        Args:
            node_indices (MultipleNodeSelection): The nodes to remove the attributes
                from.
            attribute_names (Iterable[AttributeName]): The names of the attributes to
                remove.

        Returns:
            MedRecord: A MedRecord without those attributes.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.remove_node_attributes(node_indices, attribute_names)
        )

    def set_edge_attributes(
        self, edge_indices: MultipleEdgeSelection, attributes: Attributes
    ) -> MedRecord:
        """Sets the given attributes on the selected edges, keeping the others.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to set the attributes on.
            attributes (Attributes): The attributes to set.

        Returns:
            MedRecord: A MedRecord with the attributes set.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.set_edge_attributes(edge_indices, attributes)
        )

    def replace_edge_attributes(
        self, edge_indices: MultipleEdgeSelection, attributes: Attributes
    ) -> MedRecord:
        """Replaces all attributes of the selected edges with the given ones.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to replace the attributes
                of.
            attributes (Attributes): The attributes the edges end up with.

        Returns:
            MedRecord: A MedRecord with the attributes replaced.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.replace_edge_attributes(edge_indices, attributes)
        )

    def remove_edge_attributes(
        self,
        edge_indices: MultipleEdgeSelection,
        attribute_names: Iterable[AttributeName],
    ) -> MedRecord:
        """Removes the named attributes from the selected edges.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to remove the attributes
                from.
            attribute_names (Iterable[AttributeName]): The names of the attributes to
                remove.

        Returns:
            MedRecord: A MedRecord without those attributes.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.remove_edge_attributes(edge_indices, attribute_names)
        )

    def add_group(self, group_index: SingleGroupSelection) -> MedRecord:
        """Adds an empty group.

        Args:
            group_index (SingleGroupSelection): The index of the group to add.

        Returns:
            MedRecord: A MedRecord containing the added group.
        """
        return MedRecord.from_graphrecord(self._graphrecord.add_group(group_index))

    def remove_groups(self, group_indices: MultipleGroupSelection) -> MedRecord:
        """Removes the selected groups, keeping their members ungrouped.

        Args:
            group_indices (MultipleGroupSelection): The groups to remove.

        Returns:
            MedRecord: A MedRecord without those groups.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.remove_groups(group_indices)
        )

    def add_nodes_to_group(
        self, node_indices: MultipleNodeSelection, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Adds the selected nodes to a group.

        Args:
            node_indices (MultipleNodeSelection): The nodes to add.
            group_index (SingleGroupSelection): The group the nodes join.

        Returns:
            MedRecord: A MedRecord with those nodes in the group.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_nodes_to_group(node_indices, group_index)
        )

    def remove_nodes_from_group(
        self, node_indices: MultipleNodeSelection, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Removes the selected nodes from a group, keeping the nodes themselves.

        Args:
            node_indices (MultipleNodeSelection): The nodes to remove.
            group_index (SingleGroupSelection): The group the nodes leave.

        Returns:
            MedRecord: A MedRecord without those nodes in the group.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.remove_nodes_from_group(node_indices, group_index)
        )

    def add_edges_to_group(
        self, edge_indices: MultipleEdgeSelection, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Adds the selected edges to a group.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to add.
            group_index (SingleGroupSelection): The group the edges join.

        Returns:
            MedRecord: A MedRecord with those edges in the group.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.add_edges_to_group(edge_indices, group_index)
        )

    def remove_edges_from_group(
        self, edge_indices: MultipleEdgeSelection, group_index: SingleGroupSelection
    ) -> MedRecord:
        """Removes the selected edges from a group, keeping the edges themselves.

        Args:
            edge_indices (MultipleEdgeSelection): The edges to remove.
            group_index (SingleGroupSelection): The group the edges leave.

        Returns:
            MedRecord: A MedRecord without those edges in the group.
        """
        return MedRecord.from_graphrecord(
            self._graphrecord.remove_edges_from_group(edge_indices, group_index)
        )

    @property
    def schema(self) -> Schema:
        """The schema the MedRecord validates against.

        Returns:
            Schema: The schema of the MedRecord.
        """
        return self._graphrecord.schema

    def set_schema(self, schema: Schema) -> MedRecord:
        """Validates the MedRecord against the given schema and adopts it.

        Args:
            schema (Schema): The schema to adopt.

        Returns:
            MedRecord: A MedRecord carrying the schema.
        """
        return MedRecord.from_graphrecord(self._graphrecord.set_schema(schema))

    def freeze_schema(self) -> MedRecord:
        """Stops the schema from growing with the data written to the MedRecord.

        Returns:
            MedRecord: A MedRecord with a frozen schema.
        """
        return MedRecord.from_graphrecord(self._graphrecord.freeze_schema())

    def unfreeze_schema(self) -> MedRecord:
        """Lets the schema grow with the data written to the MedRecord again.

        Returns:
            MedRecord: A MedRecord with an unfrozen schema.
        """
        return MedRecord.from_graphrecord(self._graphrecord.unfreeze_schema())

    def clear(self) -> MedRecord:
        """Removes all nodes, edges and groups, keeping the schema and the plugins.

        Returns:
            MedRecord: An empty MedRecord.
        """
        return MedRecord.from_graphrecord(self._graphrecord.clear())

    def compact(self) -> MedRecord:
        """Reclaims the space that removed nodes and edges still occupy.

        Returns:
            MedRecord: A MedRecord holding the same contents, compacted.
        """
        return MedRecord.from_graphrecord(self._graphrecord.compact())

    def node_count(self) -> int:
        """Counts the nodes of the MedRecord.

        Returns:
            int: The number of nodes.
        """
        return self._graphrecord.node_count()

    def edge_count(self) -> int:
        """Counts the edges of the MedRecord.

        Returns:
            int: The number of edges.
        """
        return self._graphrecord.edge_count()

    def group_count(self) -> int:
        """Counts the groups of the MedRecord.

        Returns:
            int: The number of groups.
        """
        return self._graphrecord.group_count()

    def contains_node(self, node_index: NodeIndex) -> bool:
        """Checks whether the MedRecord holds a node with the given index.

        Args:
            node_index (NodeIndex): The index to look for.

        Returns:
            bool: True if the node exists, otherwise False.
        """
        return self._graphrecord.contains_node(node_index)

    def contains_edge(self, edge_index: EdgeIndex) -> bool:
        """Checks whether the MedRecord holds an edge with the given index.

        Args:
            edge_index (EdgeIndex): The index to look for.

        Returns:
            bool: True if the edge exists, otherwise False.
        """
        return self._graphrecord.contains_edge(edge_index)

    def contains_group(self, group_index: GroupIndex) -> bool:
        """Checks whether the MedRecord holds a group with the given index.

        Args:
            group_index (GroupIndex): The index to look for.

        Returns:
            bool: True if the group exists, otherwise False.
        """
        return self._graphrecord.contains_group(group_index)

    def node_indices(self) -> List[NodeIndex]:
        """Lists the indices of all nodes.

        Returns:
            List[NodeIndex]: The index of every node.
        """
        return self._graphrecord.node_indices()

    def edge_indices(self) -> List[EdgeIndex]:
        """Lists the indices of all edges.

        Returns:
            List[EdgeIndex]: The index of every edge.
        """
        return self._graphrecord.edge_indices()

    def group_indices(self) -> List[GroupIndex]:
        """Lists the indices of all groups.

        Returns:
            List[GroupIndex]: The index of every group.
        """
        return self._graphrecord.group_indices()

    def nodes(self) -> NodesSeries:
        """Starts a query over the nodes of the MedRecord.

        Returns:
            NodesSeries: A series of all nodes, bound to this MedRecord.
        """
        return self._graphrecord.nodes()

    def edges(self) -> EdgesSeries:
        """Starts a query over the edges of the MedRecord.

        Returns:
            EdgesSeries: A series of all edges, bound to this MedRecord.
        """
        return self._graphrecord.edges()

    def groups(self) -> GroupsSeries:
        """Starts a query over the groups of the MedRecord.

        Returns:
            GroupsSeries: A series of all groups, bound to this MedRecord.
        """
        return self._graphrecord.groups()

    def query(
        self, expression: Expression[Unbound, S, C, Unpack[Levels]]
    ) -> Series[S, C, Unpack[Levels]]:
        """Binds an expression to the MedRecord.

        Args:
            expression (Expression[Unbound, S, C, Unpack[Levels]]): The expression to
                bind.

        Returns:
            Series[S, C, Unpack[Levels]]: The expression, bound to this MedRecord.
        """
        return self._graphrecord.query(expression)

    def node(self, node_index: NodeIndex) -> NodeView:
        """Views a single node.

        Args:
            node_index (NodeIndex): The index of the node to view.

        Returns:
            NodeView: A view of the node as this MedRecord holds it.
        """
        return self._graphrecord.node(node_index)

    def edge(self, edge_index: EdgeIndex) -> EdgeView:
        """Views a single edge.

        Args:
            edge_index (EdgeIndex): The index of the edge to view.

        Returns:
            EdgeView: A view of the edge as this MedRecord holds it.
        """
        return self._graphrecord.edge(edge_index)

    def group(self, group_index: GroupIndex) -> GroupView:
        """Views a single group.

        Args:
            group_index (GroupIndex): The index of the group to view.

        Returns:
            GroupView: A view of the group as this MedRecord holds it.
        """
        return self._graphrecord.group(group_index)

    def export(self, writer: Writer[T]) -> T:
        """Exports the MedRecord through a writer.

        Args:
            writer (Writer[T]): The writer to export through.

        Returns:
            T: What the writer handed back.
        """
        return self._graphrecord.export(writer)

    def to_polars(self) -> Export[pl.DataFrame]:
        """Exports the MedRecord to Polars DataFrames, partitioned by group.

        Returns:
            Export[pl.DataFrame]: The node and edge tables of every group and of
                the ungrouped part.
        """
        return self._graphrecord.to_polars()

    def to_arrow(self) -> Export[RecordBatch]:
        """Exports the MedRecord to Arrow record batches, partitioned by group.

        Returns:
            Export[RecordBatch]: The node and edge tables of every group and of
                the ungrouped part.
        """
        return self._graphrecord.to_arrow()

    def to_pandas(self) -> Export[pd.DataFrame]:
        """Exports the MedRecord to Pandas DataFrames, partitioned by group.

        Returns:
            Export[pd.DataFrame]: The node and edge tables of every group and of
                the ungrouped part.
        """
        return self._graphrecord.to_pandas()

    def to_ron(self, path: Union[str, os.PathLike[str]]) -> None:
        """Writes the MedRecord to a RON file.

        Args:
            path (Union[str, os.PathLike[str]]): The path of the file to write.
        """
        self._graphrecord.to_ron(path)

    def overview(
        self, truncate_details: Optional[int] = DEFAULT_TRUNCATE_DETAILS
    ) -> Overview:
        """Summarizes the contents of the MedRecord.

        Args:
            truncate_details (Optional[int]): The width detail columns are truncated
                to. No truncation if None. Defaults to DEFAULT_TRUNCATE_DETAILS.

        Returns:
            Overview: The summary of every group and of the ungrouped part.
        """
        return self._graphrecord.overview(truncate_details)

    def group_overview(
        self,
        group_index: GroupIndex,
        truncate_details: Optional[int] = DEFAULT_TRUNCATE_DETAILS,
    ) -> GroupOverview:
        """Summarizes the contents of a single group.

        Args:
            group_index (GroupIndex): The group to summarize.
            truncate_details (Optional[int]): The width detail columns are truncated
                to. No truncation if None. Defaults to DEFAULT_TRUNCATE_DETAILS.

        Returns:
            GroupOverview: The summary of the group.
        """
        return self._graphrecord.group_overview(group_index, truncate_details)

    def __eq__(self, other: object) -> bool:
        """Compares the MedRecord with another one by its contents.

        Args:
            other (object): The object to compare against.

        Returns:
            bool: True if both hold the same nodes, edges and groups, otherwise
                False.
        """
        if not isinstance(other, MedRecord):
            return NotImplemented

        return self._graphrecord == other._graphrecord

    def __copy__(self) -> MedRecord:
        """Copies the MedRecord.

        Returns:
            MedRecord: A MedRecord holding the same contents.
        """
        return MedRecord.from_graphrecord(self._graphrecord.__copy__())

    def __deepcopy__(self, memo: Optional[Dict[int, object]] = None) -> MedRecord:
        """Deep copies the MedRecord.

        Args:
            memo (Optional[Dict[int, object]]): The objects copied so far.

        Returns:
            MedRecord: A MedRecord holding the same contents.
        """
        return MedRecord.from_graphrecord(self._graphrecord.__deepcopy__(memo))

    def __reduce__(
        self,
    ) -> Tuple[Callable[[GraphRecord], MedRecord], Tuple[GraphRecord]]:
        """Reduces the MedRecord to what pickle needs to restore it.

        Returns:
            Tuple[Callable[[GraphRecord], MedRecord], Tuple[GraphRecord]]: The
                callable that restores the MedRecord and its arguments.
        """
        return self.from_graphrecord, (self._graphrecord,)

    def __repr__(self) -> str:
        """Returns the string representation of the MedRecord.

        Returns:
            str: The overview of the MedRecord.
        """
        return repr(self._graphrecord)
