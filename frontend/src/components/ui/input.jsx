import React from "react";

export default function Input({ type = "text", placeholder = "", value, onChange, className = "", required = false }) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      required={required}
      className={`px-4 py-2 border border-slate-700 bg-slate-900 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full ${className}`}
    />
  );
}
