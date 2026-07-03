import React, { useEffect } from "react";
import Card from "../components/ui/card";
import useStore from "../store/global_store";
import { newsService } from "../services/news_service";

export default function DashboardPage() {
  const { newsArticles, isLoadingNews, setNewsArticles, setIsLoadingNews } = useStore();

  useEffect(() => {
    const fetchArticles = async () => {
      setIsLoadingNews(true);
      try {
        const data = await newsService.fetchNews();
        if (data && data.articles) {
          // Convert the index dictionary objects to an array if necessary
          const articlesArray = Object.values(data.articles);
          setNewsArticles(articlesArray);
        }
      } catch (err) {
        console.error("Failed to load dashboard news", err);
      } finally {
        setIsLoadingNews(false);
      }
    };
    fetchArticles();
  }, [setNewsArticles, setIsLoadingNews]);

  return (
    <div className="space-y-6 text-slate-100">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">System Dashboard</h1>
        <p className="text-slate-400">Welcome to Chronos-AI control center. Observe pipelines and real-time state mappings.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <h3 className="text-slate-400 text-sm font-medium">Cognitive Node Count</h3>
          <p className="text-3xl font-bold text-indigo-400 mt-2">1,024</p>
        </Card>
        <Card>
          <h3 className="text-slate-400 text-sm font-medium">Relational Synapses</h3>
          <p className="text-3xl font-bold text-violet-400 mt-2">4,812</p>
        </Card>
        <Card>
          <h3 className="text-slate-400 text-sm font-medium">Ingestion Pipeline status</h3>
          <p className="text-3xl font-bold text-emerald-400 mt-2">Nominal</p>
        </Card>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-white">Ingested News Stream</h2>
        {isLoadingNews ? (
          <p className="text-slate-400">Loading ingested stream...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {newsArticles.map((article, idx) => (
              <Card key={idx} className="hover:border-slate-700 transition">
                <h3 className="font-semibold text-white text-base leading-snug">{article.title}</h3>
                <p className="text-sm text-slate-400 mt-2 line-clamp-3">{article.description}</p>
                <div className="flex items-center justify-between mt-4 text-xs text-slate-500">
                  <span>{article.source}</span>
                  <span>{article.date}</span>
                </div>
              </Card>
            ))}
            {newsArticles.length === 0 && (
              <p className="text-slate-500 col-span-2">No news ingested. Launch pipelines to fill dashboard stream.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
