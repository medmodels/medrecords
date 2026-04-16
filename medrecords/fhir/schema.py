# ruff: noqa: D100, TD002, TD003

from __future__ import annotations

from graphrecords import (
    AttributeType,
    Bool,
    DateTime,
    GroupSchema,
    Int,
    Option,
    Schema,
    SchemaType,
    String,
)

_CODING_NODE_SCHEMA = GroupSchema(
    nodes={
        "system": (String(), AttributeType.Unstructured),
        "code": (String(), AttributeType.Unstructured),
        "display": (Option(String()), AttributeType.Unstructured),
    }
)

_CODEABLE_CONCEPT_NODE_SCHEMA = GroupSchema(
    nodes={
        "text": (Option(String()), AttributeType.Unstructured),
    }
)

_STRING_VALUE_SCHEMA = GroupSchema(
    nodes={"value": (String(), AttributeType.Unstructured)}
)

fhir_r4b_schema = Schema(
    groups={
        "Patient": GroupSchema(
            nodes={
                "gender": (Option(String()), AttributeType.Categorical),
                "active": (Option(Bool()), AttributeType.Categorical),
                "birthDate": (Option(DateTime()), AttributeType.Temporal),
                "deceasedBoolean": (
                    Option(Bool()),
                    AttributeType.Categorical,
                ),
                "deceasedDateTime": (
                    Option(DateTime()),
                    AttributeType.Temporal,
                ),
                "multipleBirthBoolean": (
                    Option(Bool()),
                    AttributeType.Categorical,
                ),
                "multipleBirthInteger": (
                    Option(Int()),
                    AttributeType.Continuous,
                ),
            }
        ),
        "Patient/Name": GroupSchema(
            nodes={
                "use": (Option(String()), AttributeType.Unstructured),
                "text": (Option(String()), AttributeType.Unstructured),
                "family": (Option(String()), AttributeType.Unstructured),
                "period.start": (Option(DateTime()), AttributeType.Temporal),
                "period.end": (Option(DateTime()), AttributeType.Temporal),
            }
        ),
        "Patient/Given": _STRING_VALUE_SCHEMA,
        "Patient/Prefix": _STRING_VALUE_SCHEMA,
        "Patient/Suffix": _STRING_VALUE_SCHEMA,
        "Patient/Identifier": GroupSchema(
            nodes={
                "system": (String(), AttributeType.Unstructured),
                "value": (String(), AttributeType.Unstructured),
                "use": (Option(String()), AttributeType.Unstructured),
                "period.start": (Option(DateTime()), AttributeType.Temporal),
                "period.end": (Option(DateTime()), AttributeType.Temporal),
            }
        ),
        "Patient/IdentifierType": _CODEABLE_CONCEPT_NODE_SCHEMA,
        "Patient/Address": GroupSchema(
            nodes={
                "use": (Option(String()), AttributeType.Unstructured),
                "type": (Option(String()), AttributeType.Unstructured),
                "text": (Option(String()), AttributeType.Unstructured),
                "city": (Option(String()), AttributeType.Unstructured),
                "district": (Option(String()), AttributeType.Unstructured),
                "state": (Option(String()), AttributeType.Unstructured),
                "postalCode": (Option(String()), AttributeType.Unstructured),
                "country": (Option(String()), AttributeType.Unstructured),
                "period.start": (Option(DateTime()), AttributeType.Temporal),
                "period.end": (Option(DateTime()), AttributeType.Temporal),
            }
        ),
        "Patient/AddressLine": _STRING_VALUE_SCHEMA,
        "Patient/Telecom": GroupSchema(
            nodes={
                "system": (Option(String()), AttributeType.Unstructured),
                "use": (Option(String()), AttributeType.Unstructured),
                "value": (Option(String()), AttributeType.Unstructured),
                "rank": (Option(Int()), AttributeType.Continuous),
                "period.start": (Option(DateTime()), AttributeType.Temporal),
                "period.end": (Option(DateTime()), AttributeType.Temporal),
            }
        ),
        "Patient/Contact": GroupSchema(
            nodes={
                "gender": (Option(String()), AttributeType.Categorical),
                "period.start": (Option(DateTime()), AttributeType.Temporal),
                "period.end": (Option(DateTime()), AttributeType.Temporal),
            }
        ),
        "Patient/ContactRelationship": _CODEABLE_CONCEPT_NODE_SCHEMA,
        "Patient/Communication": GroupSchema(
            nodes={
                "preferred": (Option(Bool()), AttributeType.Categorical),
            }
        ),
        "Patient/MaritalStatus": _CODEABLE_CONCEPT_NODE_SCHEMA,
        "Patient/Language": _CODEABLE_CONCEPT_NODE_SCHEMA,
        "Coding": _CODING_NODE_SCHEMA,
        "Patient-Patient/Name": GroupSchema(),
        "Patient/Name-Patient/Given": GroupSchema(),
        "Patient/Name-Patient/Prefix": GroupSchema(),
        "Patient/Name-Patient/Suffix": GroupSchema(),
        "Patient-Patient/Identifier": GroupSchema(),
        "Patient/Identifier-Patient/IdentifierType": GroupSchema(),
        "Patient/IdentifierType-Coding": GroupSchema(),
        "Patient-Patient/Address": GroupSchema(),
        "Patient/Address-Patient/AddressLine": GroupSchema(),
        "Patient-Patient/Telecom": GroupSchema(),
        "Patient-Patient/Contact": GroupSchema(),
        "Patient/Contact-Patient/Name": GroupSchema(),
        "Patient/Contact-Patient/Address": GroupSchema(),
        "Patient/Contact-Patient/Telecom": GroupSchema(),
        "Patient/Contact-Patient/ContactRelationship": GroupSchema(),
        "Patient/ContactRelationship-Coding": GroupSchema(),
        "Patient-Patient/Communication": GroupSchema(),
        "Patient/Communication-Patient/Language": GroupSchema(),
        "Patient-Patient/MaritalStatus": GroupSchema(),
        "Patient/MaritalStatus-Coding": GroupSchema(),
        "Patient/Language-Coding": GroupSchema(),
        # TODO: add back once Organization resources are handled
        # "Patient-Organization": GroupSchema(),
        # "Patient/Contact-Organization": GroupSchema(),
        # TODO: add back once Practitioner resources are handled
        # "Patient-Practitioner": GroupSchema(),
        # TODO: add back once Patient/RelatedPerson cross-references are handled
        # "Patient-Patient/Link": GroupSchema(),
        # TODO: add back once assigner target resources are handled
        # "Patient/Identifier-Assigner": GroupSchema(),
    },
    schema_type=SchemaType.Inferred,
)

fhir_r5_schema = Schema(
    groups={},
    schema_type=SchemaType.Provided,
)
