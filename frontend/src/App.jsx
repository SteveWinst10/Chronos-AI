import Navbar from "./components/shared/navbar.jsx";
import Sidebar from "./components/shared/sidebar.jsx";
import ChatPage from "./pages/chat.jsx";
import DashboardPage from "./pages/dashboard.jsx";
import MemoryExplorer from "./pages/memory_explorer.jsx";
import TimelinePage from "./pages/timeline.jsx";
import useStore from "./store/global_store.js";

export default function App() {
  const currentPage = useStore((s) => s.currentPage);
  return (
    <div className="flex h-screen flex-col">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-4">
          {currentPage === "chat" && <ChatPage />}
          {currentPage === "dashboard" && <DashboardPage />}
          {currentPage === "memory_explorer" && <MemoryExplorer />}
          {currentPage === "timeline" && <TimelinePage />}
        </main>
      </div>
    </div>
  );
}
