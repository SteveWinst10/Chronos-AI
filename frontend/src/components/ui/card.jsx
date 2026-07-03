import React from "react";

export default function Card({ children, className = "" }) {
  return (
    <div className={`p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-lg ${className}`}>
      {children}
    </div>
  );
}
