// mini-app/app/game/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface GameState {
  bonus_balance: number;
  game_progress: number;
}

export default function GamePage() {
  const [state, setState] = useState<GameState | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Опционально можно загрузить стартовый профиль, но проще – получать из ответа /click
  useEffect(() => {
    // Можно запросить профиль и взять оттуда стартовые значения, если нужно.
  }, []);

  const handleClick = async () => {
    setPending(true);
    setError(null);
    try {
      const res = await api.gameClick();
      setState({
        bonus_balance: res.new_bonus_balance,
        game_progress: res.game_progress
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex flex-col items-center">
      <h1 className="text-lg font-semibold mb-4">Игра</h1>

      <div className="mb-3 text-sm">
        Бонусы:{" "}
        <span className="font-semibold text-emerald-400">
          {state?.bonus_balance ?? "—"}
        </span>
      </div>
      <div className="mb-6 text-sm">
        Прогресс: <span className="font-semibold">{state?.game_progress ?? "—"}</span>
      </div>

      <button
        onClick={handleClick}
        disabled={pending}
        className="w-40 h-40 rounded-full bg-emerald-600 text-center flex items-center justify-center text-sm font-semibold active:scale-95 transition"
      >
        {pending ? "..." : "Нажми меня"}
      </button>

      {error && <p className="mt-3 text-xs text-red-400">Ошибка: {error}</p>}

      <p className="mt-4 text-xs text-center text-slate-400 max-w-xs">
        Каждый клик по кругу начисляет бонусы и увеличивает прогресс игры.
      </p>
    </div>
  );
}
