import { useState } from "react";
import Card from "../components/ui/card";
import ChatWindow from "../components/chat/chat_window";
import useStore from "../store/global_store";
import { chatService } from "../services/chat_service";

export default function ChatPage() {
  const { messages, addMessage, isLoadingChat, setIsLoadingChat } = useStore();
  const [inputVal, setInputVal] = useState("");

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userMsg = { role: "user", content: inputVal };
    addMessage(userMsg);
    setInputVal("");
    setIsLoadingChat(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const data = await chatService.sendMessage(inputVal, history);
      if (data && data.response) {
        addMessage({ role: "assistant", content: data.response });
      } else {
        addMessage({ role: "assistant", content: "No response received." });
      }
    } catch (err) {
      console.error("Chat failure", err);
      addMessage({ role: "assistant", content: "Failed to communicate with the AI engine." });
    } finally {
      setIsLoadingChat(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Assistant</h1>
        <p className="text-slate-400">Responses are augmented by vector memory and knowledge graph context.</p>
      </div>

      <Card className="flex-1 flex flex-col">
        <ChatWindow
          messages={messages}
          onSend={handleSend}
          isLoading={isLoadingChat}
          inputVal={inputVal}
          setInputVal={setInputVal}
        />
      </Card>
    </div>
  );
}
