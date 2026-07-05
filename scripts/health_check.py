"""Quick health check across all phases + API key."""
import os, sys, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

RESULTS = []

def check(label, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((status, label, detail))
    print(f"  [{status}] {label}" + (f": {detail}" if detail else ""))

# ── API KEY ──────────────────────────────────────────────────────────────────
def test_api_key():
    print("\n[API KEY]")
    key = None
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("OPENAI_API_KEY="):
                key = line.strip().split("=", 1)[1]
    check("Key present in .env", bool(key), key[:12] + "..." if key else "MISSING")
    if not key:
        return
    try:
        from openai import OpenAI
        
        is_groq = key.startswith("gsk_")
        
        if is_groq:
            client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            model = "llama-3.1-8b-instant"
        else:
            client = OpenAI(api_key=key)
            model = "gpt-3.5-turbo"
            
        r = client.chat.completions.create(
            model=model, messages=[{"role":"user","content":"hi"}], max_tokens=3
        )
        check(f"{'Groq' if is_groq else 'OpenAI'} API call", True, r.choices[0].message.content)
    except Exception as e:
        check("API call", False, str(e)[:100])

# ── PHASE 1: Imports ─────────────────────────────────────────────────────────
def test_phase1():
    print("\n[PHASE 1 — Ingestion]")
    try:
        from app.services.cognee.remember import remember_article
        check("remember.py import", True)
    except Exception as e:
        check("remember.py import", False, str(e)[:80])
    try:
        import cognee
        check("cognee SDK import", True, f"v{getattr(cognee,'__version__','?')}")
    except Exception as e:
        check("cognee SDK import", False, str(e)[:80])

# ── PHASE 2: Recall ───────────────────────────────────────────────────────────
def test_phase2():
    print("\n[PHASE 2 — Recall]")
    try:
        from app.services.cognee.recall import recall_memories, MemoryItem
        check("recall.py import", True)
    except Exception as e:
        check("recall.py import", False, str(e)[:80])
    try:
        from app.services.retrieval.context_builder import build_context_prompt
        check("context_builder.py import", True)
    except Exception as e:
        check("context_builder.py import", False, str(e)[:80])
    try:
        from app.services.llm.llm_client import LLMClient
        check("llm_client.py import", True)
    except Exception as e:
        check("llm_client.py import", False, str(e)[:80])

# ── PHASE 3: Graph ────────────────────────────────────────────────────────────
def test_phase3():
    print("\n[PHASE 3 — Graph Exploration]")
    try:
        from app.storage.neo4j_graph import neo4j_graph
        nodes = neo4j_graph.get_all_nodes()
        check("neo4j_graph singleton", True, f"{len(nodes)} nodes")
    except Exception as e:
        check("neo4j_graph singleton", False, str(e)[:80])
    try:
        from app.services.analytics.relationship_strength import RelationshipDiscovery
        check("relationship_strength.py import", True)
    except Exception as e:
        check("relationship_strength.py import", False, str(e)[:80])

# ── PHASE 4: Story Engine ─────────────────────────────────────────────────────
def test_phase4():
    print("\n[PHASE 4 — Story Evolution]")
    try:
        from app.services.analytics.story_engine import StoryEvolutionEngine
        check("story_engine.py import", True)
    except Exception as e:
        check("story_engine.py import", False, str(e)[:80])
    try:
        from app.services.analytics.event_clustering import EventClustering
        check("event_clustering.py import", True)
    except Exception as e:
        check("event_clustering.py import", False, str(e)[:80])
    try:
        from app.services.analytics.importance_scorer import ImportanceScorer
        check("importance_scorer.py import", True)
    except Exception as e:
        check("importance_scorer.py import", False, str(e)[:80])
    try:
        from app.api.schemas.story_models import StoryEvent
        check("story_models.py schema", True)
    except Exception as e:
        check("story_models.py schema", False, str(e)[:80])

# ── PHASE 5: Self-Improving Memory ────────────────────────────────────────────
def test_phase5():
    print("\n[PHASE 5 — Self-Improving Memory]")
    try:
        from app.api.schemas.memory_models import GraphStatistics, MemoryHealthReport, ImprovementReport
        check("memory_models.py schema", True)
    except Exception as e:
        check("memory_models.py schema", False, str(e)[:80])
    try:
        from app.services.analytics.memory_analyzer import MemoryAnalyzer
        check("memory_analyzer.py import", True)
    except Exception as e:
        check("memory_analyzer.py import", False, str(e)[:80])
    try:
        from app.services.analytics.improvement_service import ImprovementService
        check("improvement_service.py import", True)
    except Exception as e:
        check("improvement_service.py import", False, str(e)[:80])
    try:
        from app.api.endpoints import memory as mem_ep
        check("memory.py endpoint import", True)
    except Exception as e:
        check("memory.py endpoint import", False, str(e)[:80])
    try:
        from app.services.cognee.memory_manager import MemoryManager
        mm = MemoryManager()
        check("MemoryManager Phase 5 methods", 
              all(hasattr(mm, m) for m in ["improve_memory","get_memory_health","get_memory_statistics","get_improvement_history"]))
    except Exception as e:
        check("MemoryManager Phase 5 methods", False, str(e)[:80])

# ── PHASE 6: Memory Lifecycle Demonstration Layer ──────────────────────────────
def test_phase6():
    print("\n[PHASE 6 — Lifecycle & Observability]")
    try:
        from app.services.analytics.lifecycle_tracker import LifecycleTracker
        check("lifecycle_tracker.py import", True)
    except Exception as e:
        check("lifecycle_tracker.py import", False, str(e)[:80])
    try:
        from app.services.analytics.system_health import SystemHealth
        check("system_health.py import", True)
    except Exception as e:
        check("system_health.py import", False, str(e)[:80])
    try:
        from app.services.cognee.memory_manager import MemoryManager
        mm = MemoryManager()
        check("MemoryManager Phase 6 methods", hasattr(mm, "forget_memory"))
    except Exception as e:
        check("MemoryManager Phase 6 methods", False, str(e)[:80])

# ── ROUTER ────────────────────────────────────────────────────────────────────
def test_router():
    print("\n[API ROUTER]")
    try:
        from app.api.router import api_router
        routes = [
            getattr(r, "path", getattr(r, "prefix", type(r).__name__))
            for r in api_router.routes
        ]
        check("api_router loads", True, f"{len(routes)} routes")
    except Exception as e:
        check("api_router loads", False, str(e)[:80])

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print(" Chronos AI — Full Phase Health Check")
    print("=" * 60)

    test_api_key()
    test_phase1()
    test_phase2()
    test_phase3()
    test_phase4()
    test_phase5()
    test_phase6()
    test_router()

    passed = sum(1 for r in RESULTS if r[0] == "PASS")

    failed = sum(1 for r in RESULTS if r[0] == "FAIL")
    print(f"\n{'='*60}")
    print(f" Summary: {passed} passed, {failed} failed out of {len(RESULTS)} checks")
    print(f"{'='*60}")
    if failed:
        print("\nFailed checks:")
        for r in RESULTS:
            if r[0] == "FAIL":
                print(f"  - {r[1]}: {r[2]}")
    sys.exit(0 if failed == 0 else 1)
