import React, { useState } from "react";
import Card from "../components/ui/card";
import Button from "../components/ui/button";
import Input from "../components/ui/input";
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
      const data = await chatService.sendMessage(inputVal);
      if (data && data.messages) {
        addMessage({ role: "assistant", content: data.messages.join(" ") });
      } else {
        addMessage({ role: "assistant", content: "No response received." });
      }
    } catch (err) {
      console.error("Chat failure", err);
      addMessage({ role: "assistant", content: "Failed to communicate with LLM gateway." });
    } finally {
      setIsLoadingChat(false);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold text-white">Knowledge Assistant</h1>
        <p className="text-slate-400">Interact with the multi-modal agent backend. Queries fetch relational database contexts.</p>
      </div>

      <Card className="flex-1 flex flex-col min-h-[400px]">
        <div className="flex-1 overflow-y-auto space-y-4 p-2">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[70%] rounded-xl px-4 py-2 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-100 border border-slate-700"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {isLoadingChat && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-400 border border-slate-700 rounded-xl px-4 py-2 text-sm animate-pulse">
                Assistant is thinking...
              </div>
            </div>
          )}
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center text-slate-500">
              Start a conversation to query multi-modal node relationships.
            </div>
          )}
        </div>

        <form onSubmit={handleSend} className="flex gap-2 border-t border-slate-800 pt-4 mt-4">
          <Input
            placeholder="Type your message to search and associate..."
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
          />
          <Button type="submit" disabled={isLoadingChat}>
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
