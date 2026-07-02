import React from "react";
import Card from "../components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-6 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">System Settings</h1>
        <p className="text-slate-400">Configure parameters for LLMs, thresholds, and multi-modal indexes.</p>
      </div>

      <Card className="space-y-4">
        <div>
          <h3 className="font-semibold text-white">Multi-modal Indexing Mode</h3>
          <p className="text-sm text-slate-500 mt-1">Select graph extraction heuristics.</p>
          <select className="mt-2 block w-full px-4 py-2 border border-slate-700 bg-slate-900 rounded-lg text-slate-100 focus:ring-2 focus:ring-indigo-500">
            <option>Strict Schema-First (Ontology Mode)</option>
            <option>Dynamic Heuristic (Entity-Relation Mode)</option>
          </select>
        </div>
      </Card>
    </div>
  );
}
