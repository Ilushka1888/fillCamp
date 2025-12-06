// mini-app/app/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api, type NewsPost } from "@/lib/api";

export default function NewsPage() {
  const [news, setNews] = useState<NewsPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getNews()
      .then(setNews)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Загрузка ленты...</p>;
  if (error) return <p>Ошибка: {error}</p>;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-3">Лента новостей</h1>
      {news.length === 0 && <p>Новостей пока нет.</p>}
      <div className="space-y-3">
        {news.map(post => (
          <article key={post.id} className="bg-slate-900 rounded-lg p-3">
            {post.image_url && (
              <img
                src={post.image_url}
                alt={post.title}
                className="w-full h-40 object-cover rounded-md mb-2"
              />
            )}
            <h2 className="font-semibold text-sm mb-1">{post.title}</h2>
            <p className="text-xs text-slate-300 mb-1">{post.text}</p>
            <p className="text-[10px] text-slate-500">
              {new Date(post.created_at).toLocaleString("ru-RU")}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
