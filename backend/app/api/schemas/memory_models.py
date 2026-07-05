from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

class GraphStatistics(BaseModel):
    memory_count: int
    entities_count: int
    relationships_count: int
    graph_density: float
    duplicate_ratio: float
    orphan_nodes: int
    average_degree: float
    memory_freshness_score: float # 0.0 to 1.0
    most_connected_entity: Optional[str] = None
    least_connected_entity: Optional[str] = None

class MemoryHealthReport(BaseModel):
    health_score: float # 0 to 100
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    statistics: GraphStatistics
    status: str # "Healthy", "Needs Improvement", "Degraded"
    recommendations: list[str] = Field(default_factory=list)

class ImprovementReport(BaseModel):
    id: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    dataset: str
    status: str # "completed", "failed"
    error: Optional[str] = None
    
    # State change
    before: GraphStatistics
    after: GraphStatistics
    
    # Impact summary
    new_relationships: int
    removed_duplicates: int
    strengthened_relationships: int
    new_entities: int
    health_score_change: float

class RecallComparison(BaseModel):
    query: str
    before_recall_count: int
    after_recall_count: int
    newly_discovered_memories: list[str] = Field(default_factory=list)
    impact_description: str

class MemoryEvolutionDemo(BaseModel):
    topic: str
    improvement: ImprovementReport
    recall_impact: RecallComparison
    explanation: str

class ImprovementHistoryResponse(BaseModel):
    history: list[ImprovementReport]
    total_runs: int
    last_run_at: Optional[datetime] = None
