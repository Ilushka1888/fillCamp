// mini-app/app/shop/cart/page.tsx
"use client";

import { useState } from "react";
import { useCart } from "@/context/CartContext";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function CartPage() {
  const { items, changeQuantity, removeItem, totalBonus, clear } = useCart();
  const [payWithBonus, setPayWithBonus] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async () => {
    if (items.length === 0) return;
    setPending(true);
    setError(null);
    try {
      await api.createOrder({
        items: items.map(ci => ({
          item_id: ci.item.id,
          quantity: ci.quantity
        })),
        pay_with_bonus: payWithBonus
      });
      clear();
      alert("Заказ оформлен!");
      router.push("/shop");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPending(false);
    }
  };

  return (
    <div>
      <h1 className="text-lg font-semibold mb-3">Корзина</h1>

      {items.length === 0 ? (
        <p className="text-sm">Корзина пуста.</p>
      ) : (
        <>
          <ul className="space-y-2 text-xs mb-3">
            {items.map(ci => (
              <li
                key={ci.item.id}
                className="bg-slate-900 rounded-lg p-2 flex justify-between items-center gap-2"
              >
                <div>
                  <div className="font-semibold">{ci.item.name}</div>
                  <div className="text-slate-400">
                    {ci.item.price_bonus} баллов × {ci.quantity}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() =>
                        changeQuantity(ci.item.id, ci.quantity - 1)
                      }
                      className="w-6 h-6 rounded bg-slate-800"
                    >
                      −
                    </button>
                    <span>{ci.quantity}</span>
                    <button
                      onClick={() =>
                        changeQuantity(ci.item.id, ci.quantity + 1)
                      }
                      className="w-6 h-6 rounded bg-slate-800"
                    >
                      +
                    </button>
                  </div>
                  <button
                    onClick={() => removeItem(ci.item.id)}
                    className="text-[10px] text-red-400"
                  >
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ul>

          <div className="bg-slate-900 rounded-lg p-3 text-xs mb-3">
            <div className="mb-2">
              Итого:{" "}
              <span className="font-semibold text-emerald-400">
                {totalBonus} баллов
              </span>
            </div>
            <label className="flex items-center gap-2 mb-1">
              <input
                type="checkbox"
                checked={payWithBonus}
                onChange={e => setPayWithBonus(e.target.checked)}
              />
              <span>Оплатить бонусами</span>
            </label>
            <p className="text-[10px] text-slate-400">
              Оплата картой предполагается через TG/встроенный эквайринг – можно
              добавить позже.
            </p>
          </div>

          {error && <p className="text-xs text-red-400 mb-2">Ошибка: {error}</p>}

          <button
            disabled={pending || items.length === 0}
            onClick={handleSubmit}
            className="w-full py-2 rounded bg-emerald-600 text-sm font-semibold"
          >
            {pending ? "Отправка..." : "Оформить заказ"}
          </button>
        </>
      )}
    </div>
  );
}
