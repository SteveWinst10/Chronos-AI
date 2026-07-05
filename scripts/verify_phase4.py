import os
import sys

# Manually load .env since we are running as a standalone script
def load_env():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

load_env()

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

import asyncio
import json
from datetime import datetime

from app.services.analytics.story_engine import StoryEvolutionEngine
from app.services.cognee.recall import recall_memories

async def verify_real_story(topic: str):
    print(f"\n{'='*80}")
    print(f"VERIFYING STORY EVOLUTION: {topic}")
    print(f"{'='*80}")

    # 1. Recall Check
    print(f"\n[STEP 1] RECAPPING RECALL RESULTS FROM COGNEE...")
    memories = await recall_memories(topic, limit=15)
    print(f"Found {len(memories)} memories in Cognee.")
    for i, m in enumerate(memories):
        print(f"  {i+1}. [{m.source}] {m.title} (Score: {m.score:.2f})")
    
    if not memories:
        print("  !!! CRITICAL: No memories found. Ensure ingest_news.py has been run recently.")
        return

    # 2. Complete Story Engine Execution
    print(f"\n[STEP 2] EXECUTING STORY EVOLUTION ENGINE...")
    story = await StoryEvolutionEngine.generate_story(topic, debug=True)
    
    print(f"\n--- STORY ANALYSIS ---")
    print(f"Title: {story.title}")
    print(f"Confidence: {story.confidence}")
    print(f"Events Detected: {story.statistics.events_detected}")
    print(f"Chapters Generated: {story.statistics.chapters_generated}")
    print(f"Related Entities: {', '.join(story.related_entities)}")

    # 3. Cluster & Timeline Verification
    print(f"\n[STEP 3] EVENT & TIMELINE AUDIT (Chronological Order)")
    for i, event in enumerate(story.timeline):
        print(f"  [{event.start_date}] Importance: {event.importance}* - {event.title}")
        print(f"    Evidence: {len(event.memories)} memories.")
        for m in event.memories[:2]:
            print(f"      - {m.title} ({m.source})")

    # 4. Chapter & Narrative Verification
    print(f"\n[STEP 4] CHAPTER NARRATIVE & ATTRIBUTION")
    for chapter in story.chapters:
        print(f"\n  CHAPTER: {chapter.title}")
        print(f"  Summary: {chapter.summary[:200]}...")
        print(f"  Grounded Sources: {len(chapter.sources)}")
        for src in chapter.sources[:2]:
             print(f"    - \"{src.title}\" | {src.url}")

async def verify_comparison(topic_a: str, topic_b: str):
    print(f"\n{'='*80}")
    print(f"VERIFYING STORY COMPARISON: {topic_a} vs {topic_b}")
    print(f"{'='*80}")
    
    comparison = await StoryEvolutionEngine.compare_stories(topic_a, topic_b, debug=True)
    
    print(f"Shared Entities: {', '.join(comparison.shared_entities)}")
    print(f"Common Events: {len(comparison.common_events)}")
    print(f"\nCOMPARISON SUMMARY:\n{comparison.summary_comparison}")

async def main():
    queries = [
        "OpenAI",
        "NVIDIA",
        "Microsoft"
    ]
    
    for q in queries:
        await verify_real_story(q)
    
    await verify_comparison("OpenAI", "NVIDIA")

if __name__ == "__main__":
    asyncio.run(main())
