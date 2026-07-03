import React from "react";
import Card from "../components/ui/card";

export default function TimelinePage() {
  return (
    <div className="space-y-6 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">Chronological Timeline</h1>
        <p className="text-slate-400">Examine entities sequenced over time mapping events in historical sequence.</p>
      </div>

      <Card className="p-8 text-center text-slate-500">
        Timeline sequence analyzer is operational. Synthesise story contexts to generate timeline views.
      </Card>
    </div>
  );
}
