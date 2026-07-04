"""Tests for the chat and health endpoints."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_returns_messages():
    response = client.get("/api/v1/chat/")
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) > 0


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_graph_endpoint():
    response = client.get("/api/v1/graph/")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


def test_stories_endpoint():
    response = client.get("/api/v1/stories/")
    assert response.status_code == 200
    assert "stories" in response.json()


def test_timeline_endpoint():
    response = client.get("/api/v1/timeline/")
    assert response.status_code == 200
    assert "timeline" in response.json()


def test_memory_set_and_get():
    # Set a value
    resp = client.post("/api/v1/memory/testkey", json={"value": "testval"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"
    # Get it back
    resp = client.get("/api/v1/memory/testkey")
    assert resp.status_code == 200
    assert resp.json()["value"] == "testval"
    # Delete it
    resp = client.delete("/api/v1/memory/testkey")
    assert resp.status_code == 200
    # Confirm gone
    resp = client.get("/api/v1/memory/testkey")
    assert resp.status_code == 404


def test_cognee_memory_endpoints():
    # 1. Fetch graph snapshot
    resp = client.get("/api/v1/graph/")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data

    # 2. Fetch vector memories
    resp = client.get("/api/v1/memory/vector")
    assert resp.status_code == 200
    data = resp.json()
    assert "memories" in data
    assert isinstance(data["memories"], list)

    # 3. Purge Cognee memory node/vector
    resp = client.delete("/api/v1/memory/cognee/TestNode")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["purged"] == "TestNode"
