"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/signals", label: "Signals", icon: "🎯" },
  { href: "/options", label: "Options Chain", icon: "📈" },
  { href: "/trades", label: "Trade Journal", icon: "💰" },
  { href: "/backtest", label: "Backtest", icon: "🧪" },
  { href: "/screener2", label: "F&O Screener", icon: "🔍" },
  { href: "/paper", label: "Paper Trade", icon: "📝" },
  { href: "/scanner", label: "Calculator", icon: "🧮" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col min-h-screen">
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-lg font-bold text-orange-400">Trading Engine</h1>
        <p className="text-xs text-gray-500 mt-1">Decision Support</p>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-orange-500/10 text-orange-400 font-medium"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-xs text-gray-500">Broker: Offline</span>
        </div>
      </div>
    </aside>
  );
}
