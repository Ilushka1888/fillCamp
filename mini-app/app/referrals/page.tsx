// mini-app/app/referrals/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api, type ReferralInfo } from "@/lib/api";

export default function ReferralsPage() {
  const [info, setInfo] = useState<ReferralInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getReferrals()
      .then(setInfo)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleCopy = async () => {
    if (!info) return;
    try {
      await navigator.clipboard.writeText(info.referral_link);
      alert("Ссылка скопирована");
    } catch {
      alert("Не удалось скопировать");
    }
  };

  if (loading) return <p>Загрузка...</p>;
  if (error) return <p>Ошибка: {error}</p>;
  if (!info) return <p>Нет данных.</p>;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-3">Реферальная программа</h1>

      <div className="bg-slate-900 rounded-lg p-3 mb-3 text-sm">
        <div className="mb-2">
          Ваша реферальная ссылка:
          <div className="mt-1 text-xs break-all bg-slate-800 rounded p-2">
            {info.referral_link}
          </div>
        </div>
        <button
          onClick={handleCopy}
          className="w-full text-xs mt-2 py-2 rounded bg-emerald-600"
        >
          Скопировать ссылку
        </button>
      </div>

      <div className="bg-slate-900 rounded-lg p-3 text-xs space-y-2 mb-3">
        <div>
          Приглашено: <span className="font-semibold">{info.invited_count}</span>
        </div>
        <div>
          Получено бонусов:{" "}
          <span className="font-semibold text-emerald-400">
            {info.bonus_earned}
          </span>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg p-3 text-xs">
        <div className="font-semibold mb-2">Список приглашённых</div>
        {info.invited_users.length === 0 ? (
          <div>Пока никого нет.</div>
        ) : (
          <ul className="space-y-1">
            {info.invited_users.map(u => (
              <li key={u.tg_id} className="flex justify-between">
                <span>{u.full_name}</span>
                <span className="text-slate-400 text-[10px]">TG ID: {u.tg_id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
