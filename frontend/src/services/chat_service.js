import apiClient from "./api_client";

export const chatService = {
  sendMessage: async (message, history = []) => {
    const response = await apiClient.post("/chat/", { message, history });
    return response.data;
  },
};
