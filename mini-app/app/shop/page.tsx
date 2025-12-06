// mini-app/app/shop/page.tsx
"use client";

import { useEffect, useState } from "react";
import { api, type ShopItem } from "@/lib/api";
import { useCart } from "@/context/CartContext";
import Link from "next/link";

export default function ShopPage() {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { addItem, totalBonus } = useCart();

  useEffect(() => {
    api
      .getShopItems()
      .then(setItems)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Загрузка магазина...</p>;
  if (error) return <p>Ошибка: {error}</p>;

  return (
    <div>
      <h1 className="text-lg font-semibold mb-3">Магазин</h1>

      <div className="flex justify-between items-center text-xs mb-3">
        <span>Товары: {items.length}</span>
        <Link href="/shop/cart" className="underline">
          Корзина (≈ {totalBonus} баллов)
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {items.map(item => (
          <div key={item.id} className="bg-slate-900 rounded-lg p-2 text-xs">
            {item.image_url && (
              <img
                src={item.image_url}
                alt={item.name}
                className="w-full h-24 object-cover rounded mb-1"
              />
            )}
            <div className="font-semibold mb-1">{item.name}</div>
            <div className="text-[11px] text-slate-300 line-clamp-2 mb-1">
              {item.description}
            </div>
            <div className="mb-1">
              <span className="font-semibold text-emerald-400">
                {item.price_bonus} баллов
              </span>
              {item.price_money && (
                <span className="ml-1 text-slate-400">
                  + {item.price_money} ₽
                </span>
              )}
            </div>
            <button
              onClick={() => addItem(item)}
              className="w-full py-1 rounded bg-emerald-600"
            >
              В корзину
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
