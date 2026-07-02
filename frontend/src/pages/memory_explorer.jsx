import React, { useState } from "react";
import Card from "../components/ui/card";
import Button from "../components/ui/button";
import Input from "../components/ui/input";
import { graphService } from "../services/graph_service";

export default function MemoryExplorer() {
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [lookupKey, setLookupKey] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [message, setMessage] = useState("");

  const handleSave = async (e) => {
    e.preventDefault();
    if (!key.trim() || !value.trim()) return;

    try {
      await graphService.saveMemory(key.trim(), value.trim());
      setMessage(`Successfully saved memory for key: "${key}"`);
      setKey("");
      setValue("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to save memory.");
    }
  };

  const handleLookup = async (e) => {
    e.preventDefault();
    if (!lookupKey.trim()) return;

    try {
      const data = await graphService.fetchMemory(lookupKey.trim());
      setLookupResult(data);
      setMessage("");
    } catch (err) {
      console.error(err);
      setLookupResult(null);
      setMessage(`Memory key "${lookupKey}" not found.`);
    }
  };

  const handleDelete = async () => {
    if (!lookupKey.trim()) return;

    try {
      await graphService.deleteMemory(lookupKey.trim());
      setMessage(`Deleted memory key: "${lookupKey}"`);
      setLookupResult(null);
      setLookupKey("");
    } catch (err) {
      console.error(err);
      setMessage("Failed to delete memory.");
    }
  };

  return (
    <div className="space-y-6 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">Memory Explorer</h1>
        <p className="text-slate-400">Direct interface to write, read, and delete cognitive entities within the key-value relational cache tier.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Write Side */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Ingest Memory Entity</h2>
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Entity Key</label>
              <Input
                placeholder="e.g. user_theme"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Value Context</label>
              <Input
                placeholder="e.g. dark_neon"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              Commit Memory Node
            </Button>
          </form>
        </Card>

        {/* Read/Delete Side */}
        <Card>
          <h2 className="text-lg font-semibold text-white mb-4">Lookup & Pruning</h2>
          <form onSubmit={handleLookup} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Query Key</label>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter key to lookup..."
                  value={lookupKey}
                  onChange={(e) => setLookupKey(e.target.value)}
                  required
                />
                <Button type="submit">Query</Button>
              </div>
            </div>
          </form>

          {lookupResult && (
            <div className="mt-6 p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-4">
              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase">Key</span>
                <p className="text-sm font-mono mt-1 text-white">{lookupResult.key}</p>
              </div>
              <div>
                <span className="text-xs font-bold text-indigo-400 uppercase">Value Content</span>
                <p className="text-sm mt-1 text-slate-200">{lookupResult.value}</p>
              </div>
              <Button onClick={handleDelete} className="bg-rose-600 hover:bg-rose-700 w-full mt-2">
                Prune Memory Node
              </Button>
            </div>
          )}
        </Card>
      </div>

      {message && (
        <Card className="border-indigo-900/50 bg-indigo-950/20 text-center py-3">
          <p className="text-sm text-indigo-300 font-medium">{message}</p>
        </Card>
      )}
    </div>
  );
}
