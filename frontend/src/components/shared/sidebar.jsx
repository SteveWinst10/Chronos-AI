import React from "react";
import useStore from "../../store/global_store";

export default function Sidebar() {
  const { currentPage, setCurrentPage } = useStore();

  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "chat", label: "AI Chat", icon: "💬" },
    { id: "memory_explorer", label: "Memory Explorer", icon: "🧠" },
    { id: "timeline", label: "Timeline", icon: "⏳" },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950 p-4 flex flex-col space-y-2">
      {menuItems.map((item) => (
        <button
          key={item.id}
          onClick={() => setCurrentPage(item.id)}
          className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition duration-150 ${
            currentPage === item.id
              ? "bg-indigo-600/10 text-indigo-400 border-l-4 border-indigo-500"
              : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
          }`}
        >
          <span className="text-base">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </aside>
  );
}
