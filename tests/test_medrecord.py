import unittest

from graphrecords import GraphRecord

from medrecords.medrecord import MedRecord


class TestMedRecord(unittest.TestCase):
    def test_is_graphrecord_subclass(self) -> None:
        assert issubclass(MedRecord, GraphRecord)

    def test_init(self) -> None:
        medrecord = MedRecord()

        assert isinstance(medrecord, MedRecord)
        assert isinstance(medrecord, GraphRecord)

    def test_node_operations(self) -> None:
        medrecord = MedRecord()

        medrecord.add_nodes([(1, {"name": "a"}), (2, {"name": "b"})], "patients")

        assert medrecord.node_count() == 2
        assert medrecord.contains_node(1)
        assert medrecord.contains_node(2)

    def test_edge_operations(self) -> None:
        medrecord = MedRecord()

        medrecord.add_nodes([(1, {}), (2, {})], "nodes")
        medrecord.add_edges([(1, 2, {"type": "related"})], "edges")

        assert medrecord.edge_count() == 1


if __name__ == "__main__":
    unittest.main()
