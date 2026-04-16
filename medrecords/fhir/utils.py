# ruff: noqa: D100, D103

import datetime
import hashlib
from typing import Dict, List, Optional, Tuple, TypeAlias

from fhir.resources.R4B.codeableconcept import (
    CodeableConcept as CodeableConceptR4B,
)
from fhir.resources.R4B.period import Period as PeriodR4B
from graphrecords import NodeIndex
from graphrecords.types import Attributes, Group

Nodes: TypeAlias = List[Tuple[NodeIndex, Attributes]]
Edges: TypeAlias = List[Tuple[NodeIndex, NodeIndex, Attributes]]


def to_datetime(value: object) -> Optional[datetime.datetime]:
    if isinstance(value, datetime.datetime):
        return value

    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time())

    return None


def add_period_attributes(
    attributes: Attributes,
    period: Optional[PeriodR4B],
) -> None:
    if period is None:
        attributes["period.start"] = None
        attributes["period.end"] = None
        return

    attributes["period.start"] = to_datetime(period.start)
    attributes["period.end"] = to_datetime(period.end)


def insert_deduplicated_node(
    nodes: Dict[NodeIndex, Attributes],
    node_index: NodeIndex,
    attributes: Attributes,
) -> None:
    if node_index in nodes:
        if nodes[node_index] != attributes:
            message = (
                f"Node {node_index} already exists with different attributes: "
                f"{nodes[node_index]} != {attributes}"
            )
            raise ValueError(message)
        return

    nodes[node_index] = attributes


def _hash_codeable_concept(codeable_concept: CodeableConceptR4B) -> str:
    parts = sorted(
        f"{coding.system}|{coding.code}"
        for coding in (codeable_concept.coding or [])
        if coding.system and coding.code
    )

    if codeable_concept.text:
        parts.append(f"text|{codeable_concept.text}")

    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def handle_codeable_concept(
    codeable_concept: CodeableConceptR4B,
    group: str,
    parent_index: NodeIndex,
    parent_edge_group: str,
    coding_edge_group: str,
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    has_codings = any(
        coding.system and coding.code for coding in (codeable_concept.coding or [])
    )

    if not has_codings and not codeable_concept.text:
        return

    concept_index = f"{group}/{_hash_codeable_concept(codeable_concept)}"
    already_exists = concept_index in deduplicated_nodes[group]

    insert_deduplicated_node(
        deduplicated_nodes[group],
        concept_index,
        {"text": codeable_concept.text},
    )
    edges_by_group[parent_edge_group].append((parent_index, concept_index, {}))

    if already_exists:
        return

    for coding in codeable_concept.coding or []:
        if not coding.system or not coding.code:
            continue

        coding_index = f"Coding/{coding.system}/{coding.code}"

        insert_deduplicated_node(
            deduplicated_nodes["Coding"],
            coding_index,
            {
                "system": coding.system,
                "code": coding.code,
                "display": coding.display,
            },
        )

        edges_by_group[coding_edge_group].append((concept_index, coding_index, {}))
