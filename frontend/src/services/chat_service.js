import apiClient from "./api_client";

export const chatService = {
  sendMessage: async (message, history = []) => {
    const response = await apiClient.post("/chat/", { message, history });
    return response.data;
  },
  streamMessage: async (message, history = [], onChunk, onError, onDone) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
    try {
      const response = await fetch(`${baseUrl}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message, history }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last partial line in the buffer
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6);
            try {
              const data = JSON.parse(dataStr);
              if (data.error) {
                if (onError) onError(data.error);
              } else if (data.chunk) {
                if (onChunk) onChunk(data.chunk);
              }
            } catch (err) {
              console.error("Failed to parse SSE line", trimmed, err);
            }
          }
        }
      }

      if (onDone) onDone();
    } catch (err) {
      if (onError) onError(err.message || err);
    }
  },
};
