import React, { useState, useEffect } from "react";
import Card from "../components/ui/card";
import Button from "../components/ui/button";
import Input from "../components/ui/input";
import { graphService } from "../services/graph_service";

export default function MemoryExplorer() {
  const [activeTab, setActiveTab] = useState("kv"); // "kv", "graph", "vector"

  // KV Cache State
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [lookupKey, setLookupKey] = useState("");
  const [lookupResult, setLookupResult] = useState(null);

  // Cognee Graph State
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);

  // Cognee Vector State
  const [vectorMemories, setVectorMemories] = useState([]);
  const [isLoadingVector, setIsLoadingVector] = useState(false);

  const [message, setMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Auto-clear notification messages
  useEffect(() => {
    if (message || errorMsg) {
      const timer = setTimeout(() => {
        setMessage("");
        setErrorMsg("");
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [message, errorMsg]);

  // Load Graph Memory
  const loadGraph = async () => {
    setIsLoadingGraph(true);
    try {
      const data = await graphService.fetchGraph();
      setGraphNodes(data.nodes || []);
      setGraphEdges(data.edges || []);
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to load Neo4j Graph memory.");
    } finally {
      setIsLoadingGraph(false);
    }
  };

  // Load Vector Memory
  const loadVectors = async () => {
    setIsLoadingVector(true);
    try {
      const data = await graphService.fetchVectorMemories();
      setVectorMemories(data.memories || []);
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to load LanceDB vector memories.");
    } finally {
      setIsLoadingVector(false);
    }
  };

  // Handle Tab Switch
  useEffect(() => {
    if (activeTab === "graph") {
      loadGraph();
    } else if (activeTab === "vector") {
      loadVectors();
    }
  }, [activeTab]);

  // Save Key-Value Cache
  const handleSave = async (e) => {
    e.preventDefault();
    if (!key.trim() || !value.trim()) return;

    try {
      await graphService.saveMemory(key.trim(), value.trim());
      setMessage(`Successfully saved KV cache: "${key}"`);
      setKey("");
      setValue("");
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to save memory cache.");
    }
  };

  // Lookup Key-Value Cache
  const handleLookup = async (e) => {
    e.preventDefault();
    if (!lookupKey.trim()) return;

    try {
      const data = await graphService.fetchMemory(lookupKey.trim());
      setLookupResult(data);
    } catch (err) {
      console.error(err);
      setLookupResult(null);
      setErrorMsg(`Cache key "${lookupKey}" not found.`);
    }
  };

  // Delete Key-Value Cache
  const handleDeleteCache = async () => {
    if (!lookupKey.trim()) return;

    try {
      await graphService.deleteMemory(lookupKey.trim());
      setMessage(`Deleted KV cache key: "${lookupKey}"`);
      setLookupResult(null);
      setLookupKey("");
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to delete memory cache.");
    }
  };

  // Purge Cognee Memory (deletes node from Neo4j & corresponding vector in LanceDB)
  const handlePurgeMemory = async (entityId, type) => {
    if (!window.confirm(`Are you sure you want to purge memory node "${entityId}" from Cognee? This will delete it across both Neo4j and LanceDB databases.`)) {
      return;
    }

    try {
      await graphService.purgeCogneeMemory(entityId);
      setMessage(`Successfully purged entity memory: "${entityId}"`);
      
      if (type === "node" || activeTab === "graph") {
        loadGraph();
      }
      if (type === "vector" || activeTab === "vector") {
        loadVectors();
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(`Failed to purge memory for "${entityId}".`);
    }
  };

  return (
    <div className="space-y-6 text-slate-100 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Memory & Cognee Explorer</h1>
        <p className="text-slate-400 mt-2">
          Diagnostic control panel to inspect, search, and purge cached, relational (Neo4j), and semantic (LanceDB) cognitive entities.
        </p>
      </div>

      {/* Tabs Menu */}
      <div className="flex border-b border-slate-800 space-x-4">
        <button
          onClick={() => setActiveTab("kv")}
          className={`py-3 px-4 text-sm font-medium border-b-2 transition-all duration-200 ${
            activeTab === "kv"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700"
          }`}
        >
          🔑 KV Cache Tier
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={`py-3 px-4 text-sm font-medium border-b-2 transition-all duration-200 ${
            activeTab === "graph"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700"
          }`}
        >
          🕸️ Neo4j Graph Memory
        </button>
        <button
          onClick={() => setActiveTab("vector")}
          className={`py-3 px-4 text-sm font-medium border-b-2 transition-all duration-200 ${
            activeTab === "vector"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-700"
          }`}
        >
          🧠 LanceDB Semantic Memory
        </button>
      </div>

      {/* Messages */}
      {message && (
        <div className="p-4 rounded-md bg-emerald-950/40 border border-emerald-900/60 text-emerald-400 text-sm font-medium">
          {message}
        </div>
      )}
      {errorMsg && (
        <div className="p-4 rounded-md bg-rose-950/40 border border-rose-900/60 text-rose-400 text-sm font-medium">
          {errorMsg}
        </div>
      )}

      {/* Tab Contents */}
      {activeTab === "kv" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Write Cache */}
          <Card className="bg-slate-900 border-slate-800 p-6">
            <h2 className="text-xl font-bold text-white mb-4">Ingest Cache Entry</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Key Name</label>
                <Input
                  placeholder="e.g. system_mode"
                  value={key}
                  onChange={(e) => setKey(e.target.value)}
                  required
                  className="bg-slate-950 border-slate-800 text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Value Text</label>
                <Input
                  placeholder="e.g. autonomous_active"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  required
                  className="bg-slate-950 border-slate-800 text-white"
                />
              </div>
              <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700">
                Commit Cache Entry
              </Button>
            </form>
          </Card>

          {/* Read/Delete Cache */}
          <Card className="bg-slate-900 border-slate-800 p-6">
            <h2 className="text-xl font-bold text-white mb-4">Lookup & Pruning</h2>
            <form onSubmit={handleLookup} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Search Key</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter key to lookup..."
                    value={lookupKey}
                    onChange={(e) => setLookupKey(e.target.value)}
                    required
                    className="bg-slate-950 border-slate-800 text-white flex-1"
                  />
                  <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700 px-6">
                    Query
                  </Button>
                </div>
              </div>
            </form>

            {lookupResult && (
              <div className="mt-6 p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-4">
                <div>
                  <span className="text-xs font-bold text-indigo-400 uppercase">Cached Key</span>
                  <p className="text-sm font-mono mt-1 text-white">{lookupResult.key}</p>
                </div>
                <div>
                  <span className="text-xs font-bold text-indigo-400 uppercase">Cached Value</span>
                  <p className="text-sm mt-1 text-slate-200 break-all">{lookupResult.value}</p>
                </div>
                <Button onClick={handleDeleteCache} className="bg-rose-600 hover:bg-rose-700 w-full mt-2">
                  Evict Cache Entry
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}

      {activeTab === "graph" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-white">Neo4j Relational Triple Store</h2>
            <Button onClick={loadGraph} disabled={isLoadingGraph} className="bg-slate-800 hover:bg-slate-700 text-slate-200">
              {isLoadingGraph ? "Refreshing..." : "🔄 Refresh Graph"}
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Graph Nodes */}
            <Card className="bg-slate-900 border-slate-800 p-6">
              <h3 className="text-lg font-bold text-indigo-400 mb-4">Extracted Entities (Nodes)</h3>
              {isLoadingGraph ? (
                <div className="text-center py-6 text-slate-500">Retrieving node registry...</div>
              ) : graphNodes.length === 0 ? (
                <div className="text-center py-6 text-slate-500">No ontology nodes currently in graph.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-slate-300">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 uppercase text-xs">
                        <th className="py-2">Entity Name</th>
                        <th className="py-2">Label</th>
                        <th className="py-2 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {graphNodes.map((node) => (
                        <tr key={node.name} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                          <td className="py-3 font-semibold text-white">{node.name}</td>
                          <td className="py-3">
                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                              node.label === "PERSON" ? "bg-blue-900/60 text-blue-300" :
                              node.label === "ORGANIZATION" ? "bg-amber-900/60 text-amber-300" :
                              node.label === "EVENT" ? "bg-rose-900/60 text-rose-300" :
                              "bg-purple-900/60 text-purple-300"
                            }`}>
                              {node.label}
                            </span>
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => handlePurgeMemory(node.name, "node")}
                              className="text-rose-400 hover:text-rose-300 font-medium text-xs px-2 py-1 rounded hover:bg-rose-950/40 transition-colors"
                            >
                              Purge Node
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Graph Edges */}
            <Card className="bg-slate-900 border-slate-800 p-6">
              <h3 className="text-lg font-bold text-indigo-400 mb-4">Semantic Relations (Edges)</h3>
              {isLoadingGraph ? (
                <div className="text-center py-6 text-slate-500">Retrieving edge matrix...</div>
              ) : graphEdges.length === 0 ? (
                <div className="text-center py-6 text-slate-500">No ontology connections mapped.</div>
              ) : (
                <div className="space-y-3">
                  {graphEdges.map((edge, index) => (
                    <div key={index} className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <div className="flex items-center space-x-2 flex-wrap text-sm">
                        <span className="font-semibold text-white">{edge.source}</span>
                        <span className="text-indigo-400 font-mono text-xs px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-900">
                          {edge.type}
                        </span>
                        <span className="font-semibold text-white">{edge.target}</span>
                      </div>
                      <span className="text-slate-500 text-xs font-mono">
                        {edge.properties?.conversation_id ? `conv: ${edge.properties.conversation_id.slice(-6)}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {activeTab === "vector" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-white">LanceDB Semantic Document Embeddings</h2>
            <Button onClick={loadVectors} disabled={isLoadingVector} className="bg-slate-800 hover:bg-slate-700 text-slate-200">
              {isLoadingVector ? "Refreshing..." : "🔄 Refresh Vectors"}
            </Button>
          </div>

          {isLoadingVector ? (
            <div className="text-center py-12 text-slate-500">Scanning LanceDB tables...</div>
          ) : vectorMemories.length === 0 ? (
            <div className="text-center py-12 text-slate-500 bg-slate-900 rounded-lg border border-slate-800">
              No vector embeddings recorded in memories namespace.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {vectorMemories.map((vector) => (
                <Card key={vector.id} className="bg-slate-900 border-slate-800 p-5 flex flex-col justify-between hover:border-slate-700 transition-all duration-200">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-mono text-indigo-400 break-all bg-indigo-950/40 border border-indigo-900 px-2 py-0.5 rounded">
                        UUID: {vector.id}
                      </span>
                      <span className="text-xs text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
                        Conv: {vector.conversation_id.slice(-8)}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 leading-relaxed italic bg-slate-950/45 p-3 rounded border border-slate-800/50">
                      "{vector.raw_text}"
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800/60 flex justify-end">
                    <button
                      onClick={() => handlePurgeMemory(vector.id, "vector")}
                      className="text-rose-400 hover:text-rose-300 font-semibold text-xs px-3 py-1.5 rounded bg-rose-950/20 hover:bg-rose-950/50 border border-rose-900/30 transition-all duration-150"
                    >
                      Purge Memory Block
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
