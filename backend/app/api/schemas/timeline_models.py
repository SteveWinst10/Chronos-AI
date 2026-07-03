from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    headline: str
    entity_node_ids: list[str] = Field(default_factory=list)
