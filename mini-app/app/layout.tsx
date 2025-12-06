// mini-app/app/layout.tsx
import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import { CartProvider } from "@/context/CartContext";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "FillCamp Mini App",
  description: "Лагерь: новости, профиль, игра и магазин"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-slate-950 text-slate-50">
        <CartProvider>
          <div className="flex flex-col min-h-screen">
            <main className="flex-1 p-3 pb-16">{children}</main>
            <nav className="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-800">
              <div className="flex justify-around text-xs py-2">
                <Link href="/">Лента</Link>
                <Link href="/profile">Профиль</Link>
                <Link href="/game">Игра</Link>
                <Link href="/referrals">Рефералы</Link>
                <Link href="/shop">Магазин</Link>
              </div>
            </nav>
          </div>
        </CartProvider>
      </body>
    </html>
  );
}
