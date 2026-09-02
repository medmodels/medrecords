import unittest
from typing import List, Optional

import pytest
from graphrecords import GraphRecord
from graphrecords import Plugin as GraphRecordPlugin
from graphrecords.plugins import AddGroup, AddNodes, Changes

from medrecords.medrecord import MedRecord
from medrecords.plugin import Plugin, _PluginBridge


class EmptyPlugin(Plugin):
    pass


class GraphRecordLifecyclePlugin(GraphRecordPlugin):
    def __init__(self) -> None:
        self.initialized_with: Optional[GraphRecord] = None

    def initialize(self, record: GraphRecord) -> None:
        self.initialized_with = record


class LifecyclePlugin(Plugin):
    def __init__(self) -> None:
        self.initialized_with: Optional[MedRecord] = None
        self.finalized_with: Optional[MedRecord] = None

    def initialize(self, medrecord: MedRecord) -> Changes:
        self.initialized_with = medrecord
        return [AddGroup("initialized")]

    def finalize(self, medrecord: MedRecord) -> None:
        self.finalized_with = medrecord


class PreHookPlugin(Plugin):
    def __init__(self) -> None:
        self.medrecord: Optional[MedRecord] = None
        self.addition: Optional[AddNodes] = None

    def pre_add_nodes(self, medrecord: MedRecord, addition: AddNodes) -> None:
        self.medrecord = medrecord
        self.addition = addition


class ReplacingPlugin(Plugin):
    def pre_add_group(self, medrecord: MedRecord, addition: AddGroup) -> Changes:
        return [AddGroup("replaced")]


class DroppingPlugin(Plugin):
    def pre_add_group(self, medrecord: MedRecord, addition: AddGroup) -> Changes:
        return []


class PostHookPlugin(Plugin):
    def __init__(self) -> None:
        self.observations: List[tuple[MedRecord, MedRecord, AddNodes]] = []

    def post_add_nodes(
        self, previous: MedRecord, candidate: MedRecord, addition: AddNodes
    ) -> None:
        self.observations.append((previous, candidate, addition))


class TestPlugin(unittest.TestCase):
    def test_initialize(self) -> None:
        plugin = LifecyclePlugin()

        medrecord = MedRecord().add_plugin("plugin", plugin)

        assert isinstance(plugin.initialized_with, MedRecord)
        assert medrecord.contains_group("initialized")

    def test_finalize(self) -> None:
        plugin = LifecyclePlugin()

        medrecord = MedRecord().add_plugin("plugin", plugin)
        medrecord.remove_plugin("plugin")

        assert isinstance(plugin.finalized_with, MedRecord)

    def test_pre_hook(self) -> None:
        plugin = PreHookPlugin()

        medrecord = MedRecord().add_plugin("plugin", plugin)
        medrecord = medrecord.add_nodes([(1, {"name": "a"})])

        assert isinstance(plugin.medrecord, MedRecord)
        assert isinstance(plugin.addition, AddNodes)
        assert medrecord.contains_node(1)

    def test_pre_hook_replaces_change(self) -> None:
        medrecord = MedRecord().add_plugin("plugin", ReplacingPlugin())

        medrecord = medrecord.add_group("group")

        assert not medrecord.contains_group("group")
        assert medrecord.contains_group("replaced")

    def test_pre_hook_drops_change(self) -> None:
        medrecord = MedRecord().add_plugin("plugin", DroppingPlugin())

        medrecord = medrecord.add_group("group")

        assert not medrecord.contains_group("group")

    def test_post_hook(self) -> None:
        plugin = PostHookPlugin()

        medrecord = MedRecord().add_plugin("plugin", plugin)
        medrecord.add_nodes([(1, {}), (2, {})])

        assert len(plugin.observations) == 1

        previous, candidate, addition = plugin.observations[0]
        assert isinstance(previous, MedRecord)
        assert isinstance(candidate, MedRecord)
        assert isinstance(addition, AddNodes)
        assert previous.node_count() == 0
        assert candidate.node_count() == 2
        assert len(addition.batch) == 2

    def test_undefined_hooks_are_skipped(self) -> None:
        bridge = EmptyPlugin()._bridge()

        assert not hasattr(bridge, "initialize")
        assert not hasattr(bridge, "pre_add_nodes")
        assert not hasattr(bridge, "post_add_nodes")

        medrecord = MedRecord().add_plugin("plugin", EmptyPlugin())
        medrecord = medrecord.add_nodes([(1, {})])

        assert medrecord.contains_node(1)

    def test_non_hook_attribute_raises(self) -> None:
        bridge = _PluginBridge(EmptyPlugin())

        with pytest.raises(AttributeError):
            _ = bridge.not_a_hook

    def test_from_graphrecord_plugin(self) -> None:
        plugin = GraphRecordLifecyclePlugin()

        medrecord = MedRecord().add_plugin(
            "plugin", Plugin.from_graphrecord_plugin(plugin)
        )

        assert isinstance(plugin.initialized_with, GraphRecord)
        assert not isinstance(plugin.initialized_with, MedRecord)
        assert isinstance(medrecord.plugin_entries["plugin"], Plugin)


if __name__ == "__main__":
    unittest.main()
