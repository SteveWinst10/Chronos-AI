from typing import Any

from pydantic import BaseModel, Field, StrictFloat


class NodeSchema(BaseModel):
    id: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class EdgeSchema(BaseModel):
    source: str
    target: str
    relationship_type: str
    strength: StrictFloat = Field(default=1.0, ge=0.0)


class GraphDataResponse(BaseModel):
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]
