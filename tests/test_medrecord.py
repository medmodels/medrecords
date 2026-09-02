import copy
import pickle
import tempfile
import unittest
from pathlib import Path

from graphrecords import (
    GraphRecord,
    OnConflict,
    PolarsFrames,
    Schema,
    nodes,
)
from graphrecords import Plugin as GraphRecordPlugin
from graphrecords.graphrecord import EdgeView, GroupView, NodeView
from graphrecords.overview import GroupOverview, Overview
from graphrecords.querying import Series

from medrecords.medrecord import MedRecord
from medrecords.plugin import Plugin


class EmptyPlugin(Plugin):
    pass


class GraphRecordEmptyPlugin(GraphRecordPlugin):
    pass


def create_medrecord() -> MedRecord:
    return (
        MedRecord()
        .add_nodes([(1, {"name": "a"}), (2, {"name": "b"}), (3, {"name": "c"})])
        .add_edges([(1, 2, {"weight": 1}), (2, 3, {"weight": 2})])
        .add_group("group")
    )


class TestMedRecord(unittest.TestCase):
    def test_init(self) -> None:
        medrecord = MedRecord()

        assert isinstance(medrecord, MedRecord)
        assert not isinstance(medrecord, GraphRecord)
        assert medrecord.node_count() == 0

    def test_from_graphrecord(self) -> None:
        graphrecord = GraphRecord().add_nodes([(1, {"name": "a"})])

        medrecord = MedRecord.from_graphrecord(graphrecord)

        assert medrecord.node_count() == 1
        assert medrecord.contains_node(1)

    def test_with_schema(self) -> None:
        schema = Schema()

        medrecord = MedRecord.with_schema(schema)

        assert medrecord.schema == schema

    def test_from_ron_to_ron(self) -> None:
        medrecord = create_medrecord()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "medrecord.ron"
            medrecord.to_ron(path)
            loaded = MedRecord.from_ron(path)

        assert loaded == medrecord

    def test_plugins(self) -> None:
        medrecord = MedRecord()

        assert medrecord.plugins == []

        medrecord = medrecord.add_plugin("plugin", EmptyPlugin())

        assert medrecord.plugins == ["plugin"]

    def test_plugin_entries(self) -> None:
        plugin = EmptyPlugin()
        medrecord = MedRecord().add_plugin("plugin", plugin)

        assert medrecord.plugin_entries == {"plugin": plugin}

    def test_plugin_entries_wraps_graphrecord_plugin(self) -> None:
        graphrecord = GraphRecord().add_plugin("plugin", GraphRecordEmptyPlugin())

        medrecord = MedRecord.from_graphrecord(graphrecord)

        assert isinstance(medrecord.plugin_entries["plugin"], Plugin)

    def test_add_plugin(self) -> None:
        medrecord = MedRecord().add_plugin("plugin", EmptyPlugin())

        assert isinstance(medrecord, MedRecord)
        assert medrecord.plugins == ["plugin"]

    def test_remove_plugin(self) -> None:
        medrecord = MedRecord().add_plugin("plugin", EmptyPlugin())

        medrecord = medrecord.remove_plugin("plugin")

        assert medrecord.plugins == []

    def test_add_nodes(self) -> None:
        medrecord = MedRecord().add_nodes([(1, {"name": "a"}), (2, {"name": "b"})])

        assert medrecord.node_count() == 2

    def test_add_node(self) -> None:
        medrecord = MedRecord().add_node(1, {"name": "a"})

        assert medrecord.node_count() == 1
        assert medrecord.node(1).attributes() == {"name": "a"}

    def test_add_nodes_in_group(self) -> None:
        medrecord = MedRecord().add_nodes_in_group([(1, {}), (2, {})], "group")

        assert medrecord.group("group").nodes() == [1, 2]

    def test_add_node_in_group(self) -> None:
        medrecord = MedRecord().add_node_in_group(1, {"name": "a"}, "group")

        assert medrecord.group("group").nodes() == [1]

    def test_add_edges(self) -> None:
        medrecord = (
            MedRecord().add_nodes([(1, {}), (2, {})]).add_edges([(1, 2, {"weight": 1})])
        )

        assert medrecord.edge_count() == 1

    def test_add_edge(self) -> None:
        medrecord = (
            MedRecord().add_nodes([(1, {}), (2, {})]).add_edge(1, 2, {"weight": 1})
        )

        assert medrecord.edge_count() == 1

    def test_add_edges_in_group(self) -> None:
        medrecord = (
            MedRecord()
            .add_nodes([(1, {}), (2, {})])
            .add_edges_in_group([(1, 2, {})], "group")
        )

        assert medrecord.group("group").edge_count() == 1

    def test_add_edge_in_group(self) -> None:
        medrecord = (
            MedRecord()
            .add_nodes([(1, {}), (2, {})])
            .add_edge_in_group(1, 2, {}, "group")
        )

        assert medrecord.group("group").edge_count() == 1

    def test_remove_nodes(self) -> None:
        medrecord = create_medrecord().remove_nodes([1])

        assert not medrecord.contains_node(1)
        assert medrecord.node_count() == 2
        assert medrecord.edge_count() == 1

    def test_remove_edges(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.remove_edges([edge_index])

        assert not medrecord.contains_edge(edge_index)
        assert medrecord.edge_count() == 1

    def test_keep_nodes(self) -> None:
        medrecord = create_medrecord().keep_nodes([1, 2])

        assert medrecord.node_indices() == [1, 2]
        assert medrecord.edge_count() == 1

    def test_keep_edges(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.keep_edges([edge_index])

        assert medrecord.edge_indices() == [edge_index]

    def test_keep_groups(self) -> None:
        medrecord = create_medrecord().add_group("other").keep_groups(["group"])

        assert medrecord.group_indices() == ["group"]

    def test_intersect(self) -> None:
        medrecord = create_medrecord()

        assert medrecord.intersect(medrecord) == medrecord

    def test_difference(self) -> None:
        medrecord = create_medrecord()

        assert medrecord.difference(medrecord).node_count() == 0

    def test_merge(self) -> None:
        medrecord = create_medrecord()

        merged = medrecord.merge(medrecord, on_conflict=OnConflict.KeepSelf)

        assert merged == medrecord

    def test_set_node_attributes(self) -> None:
        medrecord = create_medrecord().set_node_attributes([1], {"age": 30})

        assert medrecord.node(1).attributes() == {"name": "a", "age": 30}

    def test_replace_node_attributes(self) -> None:
        medrecord = create_medrecord().replace_node_attributes([1], {"age": 30})

        assert medrecord.node(1).attributes() == {"age": 30}

    def test_remove_node_attributes(self) -> None:
        medrecord = create_medrecord().remove_node_attributes([1], ["name"])

        assert medrecord.node(1).attributes() == {}

    def test_set_edge_attributes(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.set_edge_attributes([edge_index], {"type": "related"})

        assert medrecord.edge(edge_index).attributes() == {
            "weight": 1,
            "type": "related",
        }

    def test_replace_edge_attributes(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.replace_edge_attributes([edge_index], {"type": "related"})

        assert medrecord.edge(edge_index).attributes() == {"type": "related"}

    def test_remove_edge_attributes(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.remove_edge_attributes([edge_index], ["weight"])

        assert medrecord.edge(edge_index).attributes() == {}

    def test_add_group(self) -> None:
        medrecord = MedRecord().add_group("group")

        assert medrecord.contains_group("group")

    def test_remove_groups(self) -> None:
        medrecord = create_medrecord().remove_groups(["group"])

        assert not medrecord.contains_group("group")

    def test_add_nodes_to_group(self) -> None:
        medrecord = create_medrecord().add_nodes_to_group([1, 2], "group")

        assert medrecord.group("group").nodes() == [1, 2]

    def test_remove_nodes_from_group(self) -> None:
        medrecord = create_medrecord().add_nodes_to_group([1, 2], "group")

        medrecord = medrecord.remove_nodes_from_group([1], "group")

        assert medrecord.group("group").nodes() == [2]
        assert medrecord.contains_node(1)

    def test_add_edges_to_group(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        medrecord = medrecord.add_edges_to_group([edge_index], "group")

        assert medrecord.group("group").edges() == [edge_index]

    def test_remove_edges_from_group(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]
        medrecord = medrecord.add_edges_to_group([edge_index], "group")

        medrecord = medrecord.remove_edges_from_group([edge_index], "group")

        assert medrecord.group("group").edges() == []
        assert medrecord.contains_edge(edge_index)

    def test_schema(self) -> None:
        medrecord = MedRecord()

        assert isinstance(medrecord.schema, Schema)

    def test_set_schema(self) -> None:
        schema = Schema()

        medrecord = MedRecord().set_schema(schema)

        assert medrecord.schema == schema

    def test_freeze_schema_unfreeze_schema(self) -> None:
        medrecord = create_medrecord()

        frozen = medrecord.freeze_schema()

        assert frozen.unfreeze_schema() == medrecord

    def test_clear(self) -> None:
        medrecord = create_medrecord().clear()

        assert medrecord.node_count() == 0
        assert medrecord.edge_count() == 0
        assert medrecord.group_count() == 0

    def test_compact(self) -> None:
        medrecord = MedRecord().add_nodes([(1, {}), (2, {})]).add_group("group")

        assert medrecord.compact() == medrecord

    def test_node_count(self) -> None:
        assert create_medrecord().node_count() == 3

    def test_edge_count(self) -> None:
        assert create_medrecord().edge_count() == 2

    def test_group_count(self) -> None:
        assert create_medrecord().group_count() == 1

    def test_contains_node(self) -> None:
        medrecord = create_medrecord()

        assert medrecord.contains_node(1)
        assert not medrecord.contains_node(4)

    def test_contains_edge(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        assert medrecord.contains_edge(edge_index)

    def test_contains_group(self) -> None:
        medrecord = create_medrecord()

        assert medrecord.contains_group("group")
        assert not medrecord.contains_group("other")

    def test_node_indices(self) -> None:
        assert create_medrecord().node_indices() == [1, 2, 3]

    def test_edge_indices(self) -> None:
        assert len(create_medrecord().edge_indices()) == 2

    def test_group_indices(self) -> None:
        assert create_medrecord().group_indices() == ["group"]

    def test_nodes(self) -> None:
        assert isinstance(create_medrecord().nodes(), Series)

    def test_edges(self) -> None:
        assert isinstance(create_medrecord().edges(), Series)

    def test_groups(self) -> None:
        assert isinstance(create_medrecord().groups(), Series)

    def test_query(self) -> None:
        assert isinstance(create_medrecord().query(nodes()), Series)

    def test_node(self) -> None:
        node = create_medrecord().node(1)

        assert isinstance(node, NodeView)
        assert node.index() == 1
        assert node.attributes() == {"name": "a"}

    def test_edge(self) -> None:
        medrecord = create_medrecord()
        edge_index = medrecord.edge_indices()[0]

        edge = medrecord.edge(edge_index)

        assert isinstance(edge, EdgeView)
        assert edge.source() == 1
        assert edge.target() == 2

    def test_group(self) -> None:
        group = create_medrecord().group("group")

        assert isinstance(group, GroupView)
        assert group.index() == "group"

    def test_export(self) -> None:
        export = create_medrecord().export(PolarsFrames())

        assert export["ungrouped"]["nodes"].shape[0] == 3

    def test_to_polars(self) -> None:
        export = create_medrecord().to_polars()

        assert export["ungrouped"]["nodes"].shape[0] == 3
        assert export["ungrouped"]["edges"].shape[0] == 2

    def test_to_arrow(self) -> None:
        export = create_medrecord().to_arrow()

        assert len(export["ungrouped"]["nodes"]) == 3
        assert len(export["ungrouped"]["edges"]) == 2

    def test_to_pandas(self) -> None:
        export = create_medrecord().to_pandas()

        assert export["ungrouped"]["nodes"].shape[0] == 3
        assert export["ungrouped"]["edges"].shape[0] == 2

    def test_overview(self) -> None:
        assert isinstance(create_medrecord().overview(), Overview)

    def test_group_overview(self) -> None:
        assert isinstance(create_medrecord().group_overview("group"), GroupOverview)

    def test_eq(self) -> None:
        medrecord = MedRecord().add_nodes([(1, {"name": "a"})])

        assert medrecord == MedRecord().add_nodes([(1, {"name": "a"})])
        assert medrecord != MedRecord()
        assert medrecord != "medrecord"

    def test_copy(self) -> None:
        medrecord = create_medrecord()

        assert copy.copy(medrecord) == medrecord

    def test_deepcopy(self) -> None:
        medrecord = create_medrecord()

        assert copy.deepcopy(medrecord) == medrecord

    def test_reduce(self) -> None:
        medrecord = create_medrecord()

        assert pickle.loads(pickle.dumps(medrecord)) == medrecord

    def test_repr(self) -> None:
        medrecord = create_medrecord()

        assert repr(medrecord) == repr(medrecord._graphrecord)


if __name__ == "__main__":
    unittest.main()
