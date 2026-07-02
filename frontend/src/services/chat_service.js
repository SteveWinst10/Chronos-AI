import apiClient from "./api_client";

export const chatService = {
  sendMessage: async (message) => {
    // For demo purposes, we send message and expect response stream or block
    const response = await apiClient.get("/chat/");
    return response.data;
  },
};
