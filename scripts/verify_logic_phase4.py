import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.api.schemas.story_models import StoryEvent, SupportingMemory
from app.services.analytics.event_clustering import EventClustering
from app.services.analytics.importance_scorer import ImportanceScorer
from app.services.analytics.story_engine import StoryEvolutionEngine
from app.services.cognee.recall import MemoryItem

class MockLLM:
    async def get_completion(self, p, s=None):
        return "MODERN MOCK: Reconstructed timeline showing significant AI market shift with grounded evidence."

async def run_mocked_verification():
    print("=== Phase 4 Mocked Logic Verification ===")
    
    # 1. Prepare Mock Memories
    now = datetime.utcnow()
    memories = [
        MemoryItem(
            title="OpenAI GPT-5 Leak",
            content="Internal sources say GPT-5 is coming in December.",
            source="Reddit",
            link="http://reddit.com",
            score=0.9,
            metadata={"id": "m1", "publication_date": now.isoformat()}
        ),
        MemoryItem(
            title="OpenAI Hiring for GPT-5",
            content="OpenAI is hiring 50 new engineers for the GPT-5 team.",
            source="LinkedIn",
            link="http://linkedin.com",
            score=0.85,
            metadata={"id": "m2", "publication_date": (now + timedelta(hours=2)).isoformat()}
        ),
        MemoryItem(
            title="NVIDIA H200 Announced",
            content="NVIDIA announced its most powerful GPU yet, the H200.",
            source="Reuters",
            link="http://reuters.com",
            score=0.8,
            metadata={"id": "m3", "publication_date": now.isoformat()}
        )
    ]
    
    # 2. Test Clustering (Static method)
    print("\n[1/3] Testing Event Clustering...")
    clusters = EventClustering.cluster_memories(memories)
    print(f"Total Events Detected: {len(clusters)}")
    for i, event in enumerate(clusters):
        print(f"Event {i+1}: {event.title} ({len(event.memories)} memories)")
        print(f"  Description: {event.description}")
    
    # 3. Test Importance Scoring (Static method)
    print("\n[2/3] Testing Importance Scoring...")
    scored_events = ImportanceScorer.score_events(clusters)
    for event in scored_events:
        print(f"Event: {event.title} | Score: {event.importance}")
    
    # 4. Test Engine Orchestration (Sub-stages)
    print("\n[3/3] Testing Story Evolution Engine Orchestration...")
    engine = StoryEvolutionEngine()
    
    # Timeline construction
    timeline = sorted(scored_events, key=lambda x: x.start_date)
    print(f"Timeline Length: {len(timeline)}")
    
    # Chaptering
    chapters_struct = engine._generate_chapters_structure(timeline)
    print(f"Structure Chapters: {len(chapters_struct)}")
    
    # Narrative (Mocked LLM)
    # Monkeypatch LLMClient in the engine context
    import app.services.analytics.story_engine as engine_module
    original_llm = engine_module.LLMClient
    engine_module.LLMClient = lambda: MockLLM()
    
    final_chapters = await engine._generate_narratives("AI Hardware and Software", chapters_struct)
    
    # Restore
    engine_module.LLMClient = original_llm
    
    for chapter in final_chapters:
        print(f"Chapter: {chapter.title}")
        print(f"Summary: {chapter.summary}")
        print(f"Sources: {len(chapter.sources)}")
        
    print("\n=== Logic Verification Successful! ===")

if __name__ == "__main__":
    asyncio.run(run_mocked_verification())
