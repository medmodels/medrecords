# ruff: noqa: D100, D103, TD002, TD003

import hashlib
from typing import Dict

from fhir.resources.R4B.address import Address as AddressR4B
from fhir.resources.R4B.contactpoint import ContactPoint as ContactPointR4B
from fhir.resources.R4B.humanname import HumanName as HumanNameR4B
from fhir.resources.R4B.identifier import Identifier as IdentifierR4B
from fhir.resources.R4B.patient import Patient as PatientR4B
from fhir.resources.R4B.patient import PatientCommunication, PatientContact
from graphrecords import NodeIndex
from graphrecords.types import Attributes, Group

from medrecords.fhir.utils import (
    Edges,
    Nodes,
    add_period_attributes,
    handle_codeable_concept,
    insert_deduplicated_node,
    to_datetime,
)


def _hash_address(address: AddressR4B) -> str:
    parts = [
        address.use or "",
        address.type or "",
        address.text or "",
        address.city or "",
        address.district or "",
        address.state or "",
        address.postalCode or "",
        address.country or "",
    ]
    parts.extend(line or "" for line in address.line or [])

    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _add_name_node(
    name_index: NodeIndex,
    name: HumanNameR4B,
    nodes_by_group: Dict[Group, Nodes],
    edges_by_group: Dict[Group, Edges],
) -> None:
    attributes: Attributes = {
        "use": name.use,
        "text": name.text,
        "family": name.family,
    }
    add_period_attributes(attributes, name.period)

    nodes_by_group["Patient/Name"].append((name_index, attributes))

    for j, given in enumerate(name.given or []):
        given_index = f"{name_index}/Given/{j}"
        nodes_by_group["Patient/Given"].append((given_index, {"value": given}))
        edges_by_group["Patient/Name-Patient/Given"].append(
            (name_index, given_index, {})
        )

    for j, prefix in enumerate(name.prefix or []):
        prefix_index = f"{name_index}/Prefix/{j}"
        nodes_by_group["Patient/Prefix"].append((prefix_index, {"value": prefix}))
        edges_by_group["Patient/Name-Patient/Prefix"].append(
            (name_index, prefix_index, {})
        )

    for j, suffix in enumerate(name.suffix or []):
        suffix_index = f"{name_index}/Suffix/{j}"
        nodes_by_group["Patient/Suffix"].append((suffix_index, {"value": suffix}))
        edges_by_group["Patient/Name-Patient/Suffix"].append(
            (name_index, suffix_index, {})
        )


def _add_address_node(
    address: AddressR4B,
    parent_index: NodeIndex,
    parent_edge_group: str,
    nodes_by_group: Dict[Group, Nodes],
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    address_index = f"Address/{_hash_address(address)}"
    already_exists = address_index in deduplicated_nodes["Patient/Address"]

    attributes: Attributes = {
        "use": address.use,
        "type": address.type,
        "text": address.text,
        "city": address.city,
        "district": address.district,
        "state": address.state,
        "postalCode": address.postalCode,
        "country": address.country,
    }
    add_period_attributes(attributes, address.period)

    insert_deduplicated_node(
        deduplicated_nodes["Patient/Address"], address_index, attributes
    )
    edges_by_group[parent_edge_group].append((parent_index, address_index, {}))

    if already_exists:
        return

    for j, line in enumerate(address.line or []):
        line_index = f"{address_index}/Line/{j}"
        nodes_by_group["Patient/AddressLine"].append((line_index, {"value": line}))
        edges_by_group["Patient/Address-Patient/AddressLine"].append(
            (address_index, line_index, {})
        )


def _add_telecom_node(
    telecom_index: NodeIndex,
    telecom: ContactPointR4B,
    nodes_by_group: Dict[Group, Nodes],
) -> None:
    attributes: Attributes = {
        "system": telecom.system,
        "use": telecom.use,
        "value": telecom.value,
        "rank": telecom.rank,
    }
    add_period_attributes(attributes, telecom.period)

    nodes_by_group["Patient/Telecom"].append((telecom_index, attributes))


def _add_contact_node(
    contact_index: NodeIndex,
    contact: PatientContact,
    nodes_by_group: Dict[Group, Nodes],
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    attributes: Attributes = {"gender": contact.gender}
    add_period_attributes(attributes, contact.period)

    nodes_by_group["Patient/Contact"].append((contact_index, attributes))

    if contact.name:
        name_index = f"{contact_index}/Name/0"
        _add_name_node(name_index, contact.name, nodes_by_group, edges_by_group)
        edges_by_group["Patient/Contact-Patient/Name"].append(
            (contact_index, name_index, {})
        )

    if contact.address:
        _add_address_node(
            contact.address,
            contact_index,
            "Patient/Contact-Patient/Address",
            nodes_by_group,
            edges_by_group,
            deduplicated_nodes,
        )

    for j, telecom in enumerate(contact.telecom or []):
        telecom_index = f"{contact_index}/Telecom/{j}"
        _add_telecom_node(telecom_index, telecom, nodes_by_group)
        edges_by_group["Patient/Contact-Patient/Telecom"].append(
            (contact_index, telecom_index, {})
        )

    for relationship in contact.relationship or []:
        handle_codeable_concept(
            relationship,
            group="Patient/ContactRelationship",
            parent_index=contact_index,
            parent_edge_group="Patient/Contact-Patient/ContactRelationship",
            coding_edge_group="Patient/ContactRelationship-Coding",
            edges_by_group=edges_by_group,
            deduplicated_nodes=deduplicated_nodes,
        )

    # TODO: add back once Organization resources are handled
    # if contact.organization and contact.organization.reference:
    #     edges_by_group["Patient/Contact-Organization"].append(
    #         (contact_index, contact.organization.reference, {})
    #     )


def _add_identifier_node(
    identifier: IdentifierR4B,
    parent_index: NodeIndex,
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    if not identifier.system or not identifier.value:
        return

    identifier_index = f"Identifier/{identifier.system}/{identifier.value}"
    already_exists = identifier_index in deduplicated_nodes["Patient/Identifier"]

    identifier_attributes: Attributes = {
        "system": identifier.system,
        "value": identifier.value,
        "use": identifier.use,
    }
    add_period_attributes(identifier_attributes, identifier.period)

    insert_deduplicated_node(
        deduplicated_nodes["Patient/Identifier"],
        identifier_index,
        identifier_attributes,
    )
    edges_by_group["Patient-Patient/Identifier"].append(
        (parent_index, identifier_index, {})
    )

    if not already_exists and identifier.type:
        handle_codeable_concept(
            identifier.type,
            group="Patient/IdentifierType",
            parent_index=identifier_index,
            parent_edge_group="Patient/Identifier-Patient/IdentifierType",
            coding_edge_group="Patient/IdentifierType-Coding",
            edges_by_group=edges_by_group,
            deduplicated_nodes=deduplicated_nodes,
        )

    # TODO: add back once target resources are handled
    # if not already_exists and identifier.assigner:
    #     if identifier.assigner.reference:
    #         edges_by_group["Patient/Identifier-Assigner"].append(
    #             (identifier_index, identifier.assigner.reference, {})
    #         )


def _add_communication_node(
    communication_index: NodeIndex,
    communication: PatientCommunication,
    parent_index: NodeIndex,
    nodes_by_group: Dict[Group, Nodes],
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    nodes_by_group["Patient/Communication"].append(
        (communication_index, {"preferred": communication.preferred})
    )
    edges_by_group["Patient-Patient/Communication"].append(
        (parent_index, communication_index, {})
    )

    handle_codeable_concept(
        communication.language,
        group="Patient/Language",
        parent_index=communication_index,
        parent_edge_group="Patient/Communication-Patient/Language",
        coding_edge_group="Patient/Language-Coding",
        edges_by_group=edges_by_group,
        deduplicated_nodes=deduplicated_nodes,
    )


def handle_patient_r4b(
    patient: PatientR4B,
    nodes_by_group: Dict[Group, Nodes],
    edges_by_group: Dict[Group, Edges],
    deduplicated_nodes: Dict[Group, Dict[NodeIndex, Attributes]],
) -> None:
    patient_index = f"Patient/{patient.id}"

    nodes_by_group["Patient"].append(
        (
            patient_index,
            {
                "gender": patient.gender,
                "active": patient.active,
                "birthDate": to_datetime(patient.birthDate),
                "deceasedBoolean": patient.deceasedBoolean,
                "deceasedDateTime": to_datetime(patient.deceasedDateTime),
                "multipleBirthBoolean": patient.multipleBirthBoolean,
                "multipleBirthInteger": patient.multipleBirthInteger,
            },
        )
    )

    for i, name in enumerate(patient.name or []):
        name_index = f"{patient_index}/Name/{i}"
        _add_name_node(name_index, name, nodes_by_group, edges_by_group)
        edges_by_group["Patient-Patient/Name"].append((patient_index, name_index, {}))

    for identifier in patient.identifier or []:
        _add_identifier_node(
            identifier, patient_index, edges_by_group, deduplicated_nodes
        )

    for address in patient.address or []:
        _add_address_node(
            address,
            patient_index,
            "Patient-Patient/Address",
            nodes_by_group,
            edges_by_group,
            deduplicated_nodes,
        )

    for i, telecom in enumerate(patient.telecom or []):
        telecom_index = f"{patient_index}/Telecom/{i}"
        _add_telecom_node(telecom_index, telecom, nodes_by_group)
        edges_by_group["Patient-Patient/Telecom"].append(
            (patient_index, telecom_index, {})
        )

    for i, contact in enumerate(patient.contact or []):
        contact_index = f"{patient_index}/Contact/{i}"
        _add_contact_node(
            contact_index,
            contact,
            nodes_by_group,
            edges_by_group,
            deduplicated_nodes,
        )
        edges_by_group["Patient-Patient/Contact"].append(
            (patient_index, contact_index, {})
        )

    if patient.maritalStatus:
        handle_codeable_concept(
            patient.maritalStatus,
            group="Patient/MaritalStatus",
            parent_index=patient_index,
            parent_edge_group="Patient-Patient/MaritalStatus",
            coding_edge_group="Patient/MaritalStatus-Coding",
            edges_by_group=edges_by_group,
            deduplicated_nodes=deduplicated_nodes,
        )

    for i, communication in enumerate(patient.communication or []):
        if not communication.language:
            continue

        _add_communication_node(
            f"{patient_index}/Communication/{i}",
            communication,
            patient_index,
            nodes_by_group,
            edges_by_group,
            deduplicated_nodes,
        )

    # TODO: add back once Organization resources are handled
    # if patient.managingOrganization and patient.managingOrganization.reference:
    #     edges_by_group["Patient-Organization"].append(
    #         (patient_index, patient.managingOrganization.reference, {})
    #     )

    # TODO: add back once Practitioner resources are handled
    # for practitioner in patient.generalPractitioner or []:
    #     if practitioner.reference:
    #         edges_by_group["Patient-Practitioner"].append(
    #             (patient_index, practitioner.reference, {})
    #         )

    # TODO: add back once Patient/RelatedPerson cross-references are handled
    # for link in patient.link or []:
    #     if link.other and link.other.reference:
    #         edges_by_group["Patient-Patient/Link"].append(
    #             (patient_index, link.other.reference, {"type": link.type})
    #         )
