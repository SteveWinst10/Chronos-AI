import React from "react";
import useStore from "../../store/global_store";

export default function Navbar() {
  return (
    <nav className="h-16 px-6 border-b border-slate-800 bg-slate-950 flex items-center justify-between text-slate-100">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
          C
        </div>
        <span className="font-semibold text-lg tracking-wide">Chronos-AI</span>
      </div>
      <div className="text-sm text-slate-400">
        System Status: <span className="text-emerald-500 font-medium">Active</span>
      </div>
    </nav>
  );
}
