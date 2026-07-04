import { useState } from "react";
import Card from "../components/ui/card";
import ChatWindow from "../components/chat/chat_window";
import useStore from "../store/global_store";
import { chatService } from "../services/chat_service";

export default function ChatPage() {
  const { messages, setMessages, isLoadingChat, setIsLoadingChat } = useStore();
  const [inputVal, setInputVal] = useState("");

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userMsg = { role: "user", content: inputVal };
    const currentMessages = [...messages, userMsg];
    setMessages(currentMessages);
    setInputVal("");
    setIsLoadingChat(true);

    let assistantText = "";

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      await chatService.streamMessage(
        userMsg.content,
        history,
        (chunk) => {
          setIsLoadingChat(false);
          assistantText += chunk;
          setMessages([...currentMessages, { role: "assistant", content: assistantText }]);
        },
        (err) => {
          console.error("Streaming error", err);
          setIsLoadingChat(false);
          setMessages([...currentMessages, { role: "assistant", content: "Error: Failed to stream response." }]);
        },
        () => {
          setIsLoadingChat(false);
        }
      );
    } catch (err) {
      console.error("Chat failure", err);
      setIsLoadingChat(false);
      setMessages([...currentMessages, { role: "assistant", content: "Failed to communicate with the AI engine." }]);
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
