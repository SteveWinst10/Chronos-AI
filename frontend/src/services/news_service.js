import apiClient from "./api_client";

export const newsService = {
  fetchNews: async (category = "technology") => {
    const response = await apiClient.get(`/news/?category=${category}`);
    return response.data;
  },
};
