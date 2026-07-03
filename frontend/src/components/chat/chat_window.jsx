import MessageBubble from "./message_bubble";
import Input from "../ui/input";
import Button from "../ui/button";

export default function ChatWindow({ messages, onSend, isLoading, inputVal, setInputVal }) {
  return (
    <div className="flex-1 flex flex-col min-h-[400px]">
      <div className="flex-1 overflow-y-auto space-y-4 p-2">
        {messages.map((m, idx) => (
          <MessageBubble key={idx} message={m} />
        ))}
        {isLoading && (
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

      <form onSubmit={onSend} className="flex gap-2 border-t border-slate-800 pt-4 mt-4">
        <Input
          placeholder="Type your message to search and associate..."
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
        />
        <Button type="submit" disabled={isLoading}>
          Send
        </Button>
      </form>
    </div>
  );
}
