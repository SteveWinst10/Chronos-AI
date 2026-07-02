import { create } from "zustand";

const useStore = create((set) => ({
  currentPage: "dashboard",
  setCurrentPage: (page) => set({ currentPage: page }),
  
  // Chat slice
  messages: [],
  isLoadingChat: false,
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setIsLoadingChat: (isLoading) => set({ isLoadingChat: isLoading }),

  // News slice
  newsArticles: [],
  isLoadingNews: false,
  setNewsArticles: (articles) => set({ newsArticles: articles }),
  setIsLoadingNews: (isLoading) => set({ isLoadingNews: isLoading }),

  // Memory/Graph slice
  nodes: [],
  edges: [],
  isLoadingGraph: false,
  setGraphData: (nodes, edges) => set({ nodes, edges }),
  setIsLoadingGraph: (isLoading) => set({ isLoadingGraph: isLoading }),
}));

export default useStore;
