from abc import ABC
from enum import Enum
from typing import List, Optional, Tuple, TypedDict

from graphrecords import GraphRecord, Schema
from graphrecords.builder import GraphRecordBuilder
from graphrecords.plugin import (  # pyright: ignore[reportMissingImports] - This will be available, once plugins are implemented.
    GraphRecordPlugin,
)
from graphrecords.types import Attributes, EdgeIndex, Group, NodeIndex

class MiddlewareResult(TypedDict):  # This type lives in graphrecords.plugin.
    added_nodes: Optional[List[Tuple[NodeIndex, Attributes]]]
    added_edges: Optional[List[Tuple[NodeIndex, NodeIndex, Attributes]]]
    removed_nodes: Optional[List[NodeIndex]]
    removed_edges: Optional[List[EdgeIndex]]

class FhirDataset(ABC): ...
class FhirDatabase(FhirDataset): ...
class OmopDataset(ABC): ...
class OmopDatabase(OmopDataset): ...
class OmopVocabulary(ABC): ...

class OmopMode(Enum):
    MAPPED = "mapped"
    INFERRED = "inferred"
    STRICT = "strict"

class OmopMappingPlugin(GraphRecordPlugin):  # pyright: ignore[reportUntypedBaseClass]
    def __init__(self, vocabulary: OmopVocabulary, mode: OmopMode) -> None: ...
    def initialize(self, graphrecord: GraphRecord) -> GraphRecord: ...
    def add_node(
        self, node_index: NodeIndex, attributes: Attributes
    ) -> MiddlewareResult: ...
    def add_edge(
        self,
        source_index: NodeIndex,
        target_index: NodeIndex,
        attributes: Attributes,
    ) -> MiddlewareResult: ...
    # and much more

class OmopInferencePlugin(GraphRecordPlugin):  # pyright: ignore[reportUntypedBaseClass]
    def __init__(self, vocabulary: OmopVocabulary, mode: OmopMode) -> None: ...
    def initialize(self, graphrecord: GraphRecord) -> GraphRecord: ...
    def add_node(
        self, node_index: NodeIndex, attributes: Attributes
    ) -> MiddlewareResult: ...
    def add_edge(
        self,
        source_index: NodeIndex,
        target_index: NodeIndex,
        attributes: Attributes,
    ) -> MiddlewareResult: ...
    # and much more

OmopSchema: Schema = ...

# Reserved Groups
PATIENTS: Group = "patients"
ENCOUNTERS: Group = "encounters"
CONDITIONS: Group = "conditions"
OBSERVATIONS: Group = "observations"
DRUGS: Group = "drugs"
# etc.
RESERVED_GROUPS: List[Group] = ...

class ReservedGroupsPlugin(GraphRecordPlugin):  # pyright: ignore[reportUntypedBaseClass]
    def __init__(self, reserved_groups: List[Group]) -> None: ...
    def initialize(self, graphrecord: GraphRecord) -> GraphRecord: ...
    def add_group(self, group: Group) -> MiddlewareResult: ...
    def remove_group(self, group: Group) -> MiddlewareResult: ...
    # and many more methods to intercept group modifications

class MedRecordBuilder(GraphRecordBuilder):
    _omop_vocabulary: Optional[OmopVocabulary]

    def __init__(self) -> None: ...
    def with_omop_validation(
        self, vocabulary: OmopVocabulary, mode: OmopMode
    ) -> MedRecordBuilder: ...
    def add_fhir(self, dataset: FhirDataset) -> MedRecordBuilder: ...
    def add_omop(self, dataset: OmopDataset) -> MedRecordBuilder: ...
    def build(self) -> MedRecord: ...

class MedRecord(GraphRecord):
    @staticmethod
    def builder() -> MedRecordBuilder: ...
