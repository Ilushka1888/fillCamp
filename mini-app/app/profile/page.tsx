// mini-app/app/profile/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api, type UserProfile } from "@/lib/api";
import { useTelegramUser } from "@/hooks/useTelegram";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const tgUser = useTelegramUser();

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Загрузка профиля...</p>;
  if (error) return <p>Ошибка: {error}</p>;
  if (!profile) return <p>Профиль не найден.</p>;

  const isChild = profile.role === "child";

  return (
    <div>
      <h1 className="text-lg font-semibold mb-3">Личный кабинет</h1>

      <div className="bg-slate-900 rounded-lg p-3 mb-3 flex gap-3 items-center">
        <div className="w-12 h-12 rounded-full overflow-hidden bg-slate-800">
          <img
            src={profile.avatar_url || tgUser?.photo_url || "/avatar-placeholder.png"}
            alt={profile.full_name}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="text-sm">
          <div className="font-semibold">{profile.full_name}</div>
          {profile.username && (
            <div className="text-xs text-slate-400">@{profile.username}</div>
          )}
          <div className="text-xs mt-1">
            Роль: <span className="font-medium">{isChild ? "Ребёнок" : "Родитель"}</span>
          </div>
          <div className="text-xs">
            TG ID: <span className="font-mono">{profile.tg_id}</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg p-3 mb-3 text-sm">
        <div className="mb-1">
          Баланс бонусов:{" "}
          <span className="font-semibold text-emerald-400">{profile.bonus_balance}</span>
        </div>
        <div>
          Прогресс игры:{" "}
          <span className="font-semibold">{profile.game_progress}</span>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg p-3 text-xs space-y-2">
        {isChild ? (
          <>
            <div className="font-semibold">Привязанный родитель</div>
            {profile.linked_parent_tg_id ? (
              <div>TG ID родителя: {profile.linked_parent_tg_id}</div>
            ) : (
              <div>Родитель ещё не привязан.</div>
            )}
          </>
        ) : (
          <>
            <div className="font-semibold">Привязанный ребёнок</div>
            {profile.linked_child_tg_id ? (
              <div>TG ID ребёнка: {profile.linked_child_tg_id}</div>
            ) : (
              <div>Ребёнок ещё не привязан.</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
