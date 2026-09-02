"""Plugin base class for MedRecord plugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from graphrecords.plugins import Plugin as GraphRecordPlugin
from graphrecords.plugins import _PluginBridge as GraphRecordPluginBridge

if TYPE_CHECKING:
    from graphrecords._graphrecords.graphrecord import PyGraphRecord
    from graphrecords.plugins import (
        AddEdges,
        AddEdgesInGroup,
        AddEdgesToGroup,
        AddGroup,
        AddNodes,
        AddNodesInGroup,
        AddNodesToGroup,
        Changes,
        Clear,
        FreezeSchema,
        RemoveEdgeAttributes,
        RemoveEdges,
        RemoveEdgesFromGroup,
        RemoveGroups,
        RemoveNodeAttributes,
        RemoveNodes,
        RemoveNodesFromGroup,
        ReplaceEdgeAttributes,
        ReplaceNodeAttributes,
        SetEdgeAttributes,
        SetNodeAttributes,
        SetSchema,
        UnfreezeSchema,
    )

    from medrecords.medrecord import MedRecord


class Plugin(GraphRecordPlugin):
    """Base class for MedRecord plugins.

    Every hook is optional: a MedRecord calls a hook only when the plugin defines
    it. A ``pre_`` hook returns what the MedRecord applies in place of the change
    it received: ``None`` keeps that change, a change or a list of changes replaces
    it, and an empty list drops it. ``initialize`` and ``finalize`` return changes
    the same way, but receive no change, so ``None`` means no changes. A ``post_``
    hook observes the MedRecords before and after the applied changes together
    with the change that was applied and must return ``None``. The two MedRecords
    bracket every change applied in the call, not only the change the hook
    received. The hooks are declared for type checkers only, which keeps a plugin
    free of the hooks it does not implement and keeps a MedRecord from building
    payloads nobody reads.
    """

    def _bridge(self) -> GraphRecordPluginBridge:
        """Wraps the plugin in the bridge a GraphRecord calls its hooks through.

        Returns:
            GraphRecordPluginBridge: The bridge around this plugin.
        """
        return _PluginBridge(self)

    @classmethod
    def from_graphrecord_plugin(cls, plugin: GraphRecordPlugin) -> Plugin:
        """Wraps an existing GraphRecord plugin into a MedRecord plugin.

        The wrapped plugin keeps receiving GraphRecords in its hooks, as it is
        written against.

        Args:
            plugin (GraphRecordPlugin): The GraphRecord plugin to wrap.

        Returns:
            Plugin: A MedRecord plugin holding the GraphRecord plugin.
        """
        return _PluginAdapter(plugin)

    if TYPE_CHECKING:

        def initialize(self, medrecord: MedRecord) -> Optional[Changes]:
            """Handles the plugin being added to a MedRecord.

            Args:
                medrecord (MedRecord): The MedRecord the plugin is added to.

            Returns:
                Optional[Changes]: The changes to apply, or None to apply none.
            """

        def finalize(self, medrecord: MedRecord) -> Optional[Changes]:
            """Handles the plugin being removed from a MedRecord.

            Args:
                medrecord (MedRecord): The MedRecord the plugin is removed from.

            Returns:
                Optional[Changes]: The changes to apply, or None to apply none.
            """

        def pre_add_nodes(
            self, medrecord: MedRecord, addition: AddNodes
        ) -> Optional[Changes]:
            """Handles nodes being added.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                addition (AddNodes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_nodes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            addition: AddNodes,
        ) -> None:
            """Observes the MedRecord after nodes were added.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                addition (AddNodes): The change that was applied.
            """

        def pre_add_nodes_in_group(
            self, medrecord: MedRecord, addition: AddNodesInGroup
        ) -> Optional[Changes]:
            """Handles nodes being added in a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                addition (AddNodesInGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_nodes_in_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            addition: AddNodesInGroup,
        ) -> None:
            """Observes the MedRecord after nodes were added in a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                addition (AddNodesInGroup): The change that was applied.
            """

        def pre_add_edges(
            self, medrecord: MedRecord, addition: AddEdges
        ) -> Optional[Changes]:
            """Handles edges being added.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                addition (AddEdges): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_edges(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            addition: AddEdges,
        ) -> None:
            """Observes the MedRecord after edges were added.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                addition (AddEdges): The change that was applied.
            """

        def pre_add_edges_in_group(
            self, medrecord: MedRecord, addition: AddEdgesInGroup
        ) -> Optional[Changes]:
            """Handles edges being added in a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                addition (AddEdgesInGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_edges_in_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            addition: AddEdgesInGroup,
        ) -> None:
            """Observes the MedRecord after edges were added in a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                addition (AddEdgesInGroup): The change that was applied.
            """

        def pre_remove_nodes(
            self, medrecord: MedRecord, removal: RemoveNodes
        ) -> Optional[Changes]:
            """Handles nodes being removed.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                removal (RemoveNodes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_nodes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            removal: RemoveNodes,
        ) -> None:
            """Observes the MedRecord after nodes were removed.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                removal (RemoveNodes): The change that was applied.
            """

        def pre_remove_edges(
            self, medrecord: MedRecord, removal: RemoveEdges
        ) -> Optional[Changes]:
            """Handles edges being removed.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                removal (RemoveEdges): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_edges(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            removal: RemoveEdges,
        ) -> None:
            """Observes the MedRecord after edges were removed.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                removal (RemoveEdges): The change that was applied.
            """

        def pre_set_node_attributes(
            self, medrecord: MedRecord, assignment: SetNodeAttributes
        ) -> Optional[Changes]:
            """Handles node attributes being set.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                assignment (SetNodeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_set_node_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            assignment: SetNodeAttributes,
        ) -> None:
            """Observes the MedRecord after node attributes were set.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                assignment (SetNodeAttributes): The change that was applied.
            """

        def pre_replace_node_attributes(
            self, medrecord: MedRecord, assignment: ReplaceNodeAttributes
        ) -> Optional[Changes]:
            """Handles node attributes being replaced.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                assignment (ReplaceNodeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_replace_node_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            assignment: ReplaceNodeAttributes,
        ) -> None:
            """Observes the MedRecord after node attributes were replaced.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                assignment (ReplaceNodeAttributes): The change that was applied.
            """

        def pre_remove_node_attributes(
            self, medrecord: MedRecord, removal: RemoveNodeAttributes
        ) -> Optional[Changes]:
            """Handles node attributes being removed.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                removal (RemoveNodeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_node_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            removal: RemoveNodeAttributes,
        ) -> None:
            """Observes the MedRecord after node attributes were removed.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                removal (RemoveNodeAttributes): The change that was applied.
            """

        def pre_set_edge_attributes(
            self, medrecord: MedRecord, assignment: SetEdgeAttributes
        ) -> Optional[Changes]:
            """Handles edge attributes being set.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                assignment (SetEdgeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_set_edge_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            assignment: SetEdgeAttributes,
        ) -> None:
            """Observes the MedRecord after edge attributes were set.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                assignment (SetEdgeAttributes): The change that was applied.
            """

        def pre_replace_edge_attributes(
            self, medrecord: MedRecord, assignment: ReplaceEdgeAttributes
        ) -> Optional[Changes]:
            """Handles edge attributes being replaced.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                assignment (ReplaceEdgeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_replace_edge_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            assignment: ReplaceEdgeAttributes,
        ) -> None:
            """Observes the MedRecord after edge attributes were replaced.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                assignment (ReplaceEdgeAttributes): The change that was applied.
            """

        def pre_remove_edge_attributes(
            self, medrecord: MedRecord, removal: RemoveEdgeAttributes
        ) -> Optional[Changes]:
            """Handles edge attributes being removed.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                removal (RemoveEdgeAttributes): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_edge_attributes(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            removal: RemoveEdgeAttributes,
        ) -> None:
            """Observes the MedRecord after edge attributes were removed.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                removal (RemoveEdgeAttributes): The change that was applied.
            """

        def pre_add_group(
            self, medrecord: MedRecord, addition: AddGroup
        ) -> Optional[Changes]:
            """Handles a group being added.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                addition (AddGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            addition: AddGroup,
        ) -> None:
            """Observes the MedRecord after a group was added.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                addition (AddGroup): The change that was applied.
            """

        def pre_remove_groups(
            self, medrecord: MedRecord, removal: RemoveGroups
        ) -> Optional[Changes]:
            """Handles groups being removed.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                removal (RemoveGroups): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_groups(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            removal: RemoveGroups,
        ) -> None:
            """Observes the MedRecord after groups were removed.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                removal (RemoveGroups): The change that was applied.
            """

        def pre_add_nodes_to_group(
            self, medrecord: MedRecord, membership: AddNodesToGroup
        ) -> Optional[Changes]:
            """Handles nodes being added to a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                membership (AddNodesToGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_nodes_to_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            membership: AddNodesToGroup,
        ) -> None:
            """Observes the MedRecord after nodes were added to a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                membership (AddNodesToGroup): The change that was applied.
            """

        def pre_remove_nodes_from_group(
            self, medrecord: MedRecord, membership: RemoveNodesFromGroup
        ) -> Optional[Changes]:
            """Handles nodes being removed from a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                membership (RemoveNodesFromGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_nodes_from_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            membership: RemoveNodesFromGroup,
        ) -> None:
            """Observes the MedRecord after nodes were removed from a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                membership (RemoveNodesFromGroup): The change that was applied.
            """

        def pre_add_edges_to_group(
            self, medrecord: MedRecord, membership: AddEdgesToGroup
        ) -> Optional[Changes]:
            """Handles edges being added to a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                membership (AddEdgesToGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_add_edges_to_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            membership: AddEdgesToGroup,
        ) -> None:
            """Observes the MedRecord after edges were added to a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                membership (AddEdgesToGroup): The change that was applied.
            """

        def pre_remove_edges_from_group(
            self, medrecord: MedRecord, membership: RemoveEdgesFromGroup
        ) -> Optional[Changes]:
            """Handles edges being removed from a group.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                membership (RemoveEdgesFromGroup): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_remove_edges_from_group(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            membership: RemoveEdgesFromGroup,
        ) -> None:
            """Observes the MedRecord after edges were removed from a group.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                membership (RemoveEdgesFromGroup): The change that was applied.
            """

        def pre_set_schema(
            self, medrecord: MedRecord, schema_change: SetSchema
        ) -> Optional[Changes]:
            """Handles the schema being set.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                schema_change (SetSchema): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_set_schema(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            schema_change: SetSchema,
        ) -> None:
            """Observes the MedRecord after the schema was set.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                schema_change (SetSchema): The change that was applied.
            """

        def pre_freeze_schema(
            self, medrecord: MedRecord, schema_change: FreezeSchema
        ) -> Optional[Changes]:
            """Handles the schema being frozen.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                schema_change (FreezeSchema): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_freeze_schema(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            schema_change: FreezeSchema,
        ) -> None:
            """Observes the MedRecord after the schema was frozen.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                schema_change (FreezeSchema): The change that was applied.
            """

        def pre_unfreeze_schema(
            self, medrecord: MedRecord, schema_change: UnfreezeSchema
        ) -> Optional[Changes]:
            """Handles the schema being unfrozen.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                schema_change (UnfreezeSchema): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_unfreeze_schema(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            schema_change: UnfreezeSchema,
        ) -> None:
            """Observes the MedRecord after the schema was unfrozen.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                schema_change (UnfreezeSchema): The change that was applied.
            """

        def pre_clear(self, medrecord: MedRecord, clearing: Clear) -> Optional[Changes]:
            """Handles the MedRecord being cleared.

            Args:
                medrecord (MedRecord): The MedRecord the change is applied to.
                clearing (Clear): The change that is applied.

            Returns:
                Optional[Changes]: The changes to apply instead, or None to apply
                    the change unchanged.
            """

        def post_clear(
            self,
            previous: MedRecord,
            candidate: MedRecord,
            clearing: Clear,
        ) -> None:
            """Observes the MedRecord after it was cleared.

            Args:
                previous (MedRecord): The MedRecord before the applied changes.
                candidate (MedRecord): The MedRecord with all changes applied.
                clearing (Clear): The change that was applied.
            """


class _PluginAdapter(Plugin):
    """A MedRecord plugin around an existing GraphRecord plugin.

    Attaching the adapter attaches the GraphRecord plugin as it is, so its hooks
    keep receiving GraphRecords.
    """

    _plugin: GraphRecordPlugin

    def __init__(self, plugin: GraphRecordPlugin) -> None:
        """Initializes an adapter around a GraphRecord plugin.

        Args:
            plugin (GraphRecordPlugin): The GraphRecord plugin to adapt.
        """
        self._plugin = plugin

    def _bridge(self) -> GraphRecordPluginBridge:
        """Wraps the adapted plugin in the bridge it is attached through.

        Returns:
            GraphRecordPluginBridge: The bridge around the adapted plugin.
        """
        return self._plugin._bridge()


class _PluginBridge(GraphRecordPluginBridge):
    """The bridge that hands the hooks of a MedRecord plugin MedRecords.

    Every hook a GraphRecord calls receives its records through _record, so
    overriding it is all it takes to hand the hooks MedRecords.
    """

    @staticmethod
    def _record(py_record: PyGraphRecord) -> MedRecord:
        """Converts a py_record a GraphRecord passed to a hook.

        Args:
            py_record (PyGraphRecord): The py_record to convert.

        Returns:
            MedRecord: The converted py_record.
        """
        from medrecords.medrecord import MedRecord

        return MedRecord.from_graphrecord(GraphRecordPluginBridge._record(py_record))
