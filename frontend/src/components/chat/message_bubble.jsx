export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[70%] rounded-xl px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-slate-800 text-slate-100 border border-slate-700"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
