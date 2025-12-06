// mini-app/context/CartContext.tsx
"use client";

import React, { createContext, useContext, useMemo, useState } from "react";
import type { ShopItem } from "@/lib/api";

export interface CartItem {
  item: ShopItem;
  quantity: number;
}

interface CartContextValue {
  items: CartItem[];
  addItem: (item: ShopItem) => void;
  removeItem: (itemId: number) => void;
  changeQuantity: (itemId: number, quantity: number) => void;
  clear: () => void;
  totalBonus: number;
}

const CartContext = createContext<CartContextValue | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<CartItem[]>([]);

  const addItem = (item: ShopItem) => {
    setItems(prev => {
      const existing = prev.find(ci => ci.item.id === item.id);
      if (existing) {
        return prev.map(ci =>
          ci.item.id === item.id ? { ...ci, quantity: ci.quantity + 1 } : ci
        );
      }
      return [...prev, { item, quantity: 1 }];
    });
  };

  const removeItem = (itemId: number) => {
    setItems(prev => prev.filter(ci => ci.item.id !== itemId));
  };

  const changeQuantity = (itemId: number, quantity: number) => {
    if (quantity <= 0) return removeItem(itemId);
    setItems(prev =>
      prev.map(ci =>
        ci.item.id === itemId ? { ...ci, quantity } : ci
      )
    );
  };

  const clear = () => setItems([]);

  const totalBonus = useMemo(
    () => items.reduce((sum, ci) => sum + ci.item.price_bonus * ci.quantity, 0),
    [items]
  );

  const value: CartContextValue = {
    items,
    addItem,
    removeItem,
    changeQuantity,
    clear,
    totalBonus
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
};

export const useCart = () => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
};
