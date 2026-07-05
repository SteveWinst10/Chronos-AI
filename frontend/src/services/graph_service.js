import apiClient from "./api_client";

export const graphService = {
  fetchGraph: async () => {
    const response = await apiClient.get("/graph/");
    return response.data;
  },
  fetchMemory: async (key) => {
    const response = await apiClient.get(`/memory/${key}`);
    return response.data;
  },
  saveMemory: async (key, value) => {
    const response = await apiClient.post(`/memory/${key}`, { value });
    return response.data;
  },
  deleteMemory: async (key) => {
    const response = await apiClient.delete(`/memory/${key}`);
    return response.data;
  },
  fetchVectorMemories: async () => {
    const response = await apiClient.get("/memory/vector");
    return response.data;
  },
  purgeCogneeMemory: async (entityId) => {
    const response = await apiClient.delete(`/memory/cognee/${entityId}`);
    return response.data;
  },
};
