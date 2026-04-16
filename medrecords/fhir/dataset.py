# ruff: noqa: D100, D101, D107

import json
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, Generic, List, Type, TypeVar

from fhir.resources import get_fhir_model_class as get_fhir_model_class_r5
from fhir.resources.R4B import get_fhir_model_class as get_fhir_model_class_r4b
from fhir.resources.R4B.resource import Resource as ResourceR4B
from fhir.resources.resource import Resource as ResourceR5
from fhir_core.fhirabstractmodel import FHIRAbstractModel

R = TypeVar("R", bound=FHIRAbstractModel)
ResourceT = TypeVar("ResourceT", ResourceR4B, ResourceR5)


class _FHIRDataset(Generic[ResourceT]):
    def __init__(
        self,
        path: Path,
        resource_base: Type[ResourceT],
        get_fhir_model_class: Callable[[str], Type[FHIRAbstractModel]],
    ) -> None:
        self._resource_base = resource_base
        self._get_fhir_model_class = get_fhir_model_class
        self._resources: Dict[str, List[ResourceT]] = defaultdict(list)

        for file in Path(path).iterdir():
            if file.suffix == ".ndjson":
                with file.open() as handle:
                    for line in handle:
                        if line.strip():
                            self._parse_resource(json.loads(line))
            elif file.suffix == ".json":
                raw = json.loads(file.read_text())

                if raw.get("resourceType") == "Bundle":
                    for entry in raw.get("entry", []):
                        if "resource" in entry:
                            self._parse_resource(entry["resource"])
                else:
                    self._parse_resource(raw)

    def _parse_resource(self, raw: Dict[str, object]) -> None:
        resource_type = raw.get("resourceType")

        if not isinstance(resource_type, str):
            return

        resource = self._get_fhir_model_class(resource_type).model_validate(raw)

        if isinstance(resource, self._resource_base):
            self._resources[resource_type].append(resource)

    def get(self, resource_type: Type[R]) -> List[R]:
        resource_type_name = resource_type.get_resource_type()

        return [
            resource
            for resource in self._resources.get(resource_type_name, [])
            if isinstance(resource, resource_type)
        ]


class FHIRDatasetR4B(_FHIRDataset[ResourceR4B]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, ResourceR4B, get_fhir_model_class_r4b)


class FHIRDatasetR5(_FHIRDataset[ResourceR5]):
    def __init__(self, path: Path) -> None:
        super().__init__(path, ResourceR5, get_fhir_model_class_r5)
