# ruff: noqa: D100, D101, D102

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict

from fhir.resources.R4B.patient import Patient as PatientR4B
from graphrecords import (
    GraphRecord,
    IngestConnector,
    NodeIndex,
)

from medrecords.fhir.dataset import FHIRDatasetR4B, FHIRDatasetR5
from medrecords.fhir.patient import handle_patient_r4b
from medrecords.fhir.schema import fhir_r4b_schema, fhir_r5_schema

if TYPE_CHECKING:
    from graphrecords.types import Attributes, Group

    from medrecords.fhir.utils import Edges, Nodes


class FHIRConnectorR4B(IngestConnector[FHIRDatasetR4B]):
    def initialize(self, graphrecord: GraphRecord) -> None:
        graphrecord.set_schema(fhir_r4b_schema)

    def ingest(self, graphrecord: GraphRecord, data: FHIRDatasetR4B) -> None:
        nodes_by_group: Dict[Group, Nodes] = defaultdict(list)
        edges_by_group: Dict[Group, Edges] = defaultdict(list)
        deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]] = defaultdict(dict)

        for patient in data.get(PatientR4B):
            handle_patient_r4b(
                patient, nodes_by_group, edges_by_group, deduplicated_nodes
            )

        for group, group_nodes in nodes_by_group.items():
            graphrecord.add_nodes(group_nodes, group)

        for group, deduped in deduplicated_nodes.items():
            graphrecord.add_nodes(list(deduped.items()), group)

        for group, group_edges in edges_by_group.items():
            graphrecord.add_edges(group_edges, group)


class FHIRConnectorR5(IngestConnector[FHIRDatasetR5]):
    def initialize(self, graphrecord: GraphRecord) -> None:
        graphrecord.set_schema(fhir_r5_schema)

    def ingest(self, graphrecord: GraphRecord, data: FHIRDatasetR5) -> None:
        pass
