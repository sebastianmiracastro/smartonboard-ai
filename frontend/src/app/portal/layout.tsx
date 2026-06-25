"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Zap, Home, MessageSquare, CheckSquare, BookOpen, LogOut } from "lucide-react";
import { api } from "@/lib/api";

const navItems = [
  { icon: Home, label: "Mi inicio", href: "/portal/inicio" },
  { icon: MessageSquare, label: "Chat IA", href: "/portal/chat" },
  { icon: CheckSquare, label: "Mi plan", href: "/portal/tareas" },
  { icon: BookOpen, label: "Recursos", href: "/portal/recursos" },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    api.getMe().then(setUser).catch(() => router.push("/login"));
  }, []);

  const initials = user?.full_name
    ?.split(" ")
    .map((n: string) => n[0])
    .join("")
    .slice(0, 2) ?? "—";

  const progress = user && user.onboarding_total_days > 0
    ? Math.round((user.onboarding_day / user.onboarding_total_days) * 100)
    : 0;

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-[#0f1629] flex">

      {/* Sidebar */}
      <aside className="w-60 bg-[#161e33] border-r border-[#2a3354] flex flex-col fixed h-full">

        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-[#2a3354]">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center shrink-0">
            <Zap size={16} className="text-white" />
          </div>
          <span className="text-white text-sm font-semibold tracking-tight">
            SmartOnboard <span className="text-indigo-400">AI</span>
          </span>
        </div>

        {/* Empleado info */}
        <div className="px-4 py-4 border-b border-[#2a3354]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-500/20 border border-indigo-500/20 rounded-full flex items-center justify-center shrink-0">
              <span className="text-indigo-400 text-xs font-semibold">{initials}</span>
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {user?.full_name ?? "—"}
              </p>
              <p className="text-slate-500 text-xs truncate">
                {[user?.role_name, user?.department_name].filter(Boolean).join(" · ") || "—"}
              </p>
            </div>
          </div>

          {/* Progreso */}
          <div className="mt-3">
            <div className="flex justify-between mb-1">
              <span className="text-slate-500 text-xs">
                Día {user?.onboarding_day ?? 0} de {user?.onboarding_total_days ?? 0}
              </span>
              <span className="text-indigo-400 text-xs font-medium">{progress}%</span>
            </div>
            <div className="h-1.5 bg-[#2a3354] rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-4 flex flex-col gap-1">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <button
                key={item.href}
                onClick={() => router.push(item.href)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors w-full text-left
                  ${active
                    ? "bg-indigo-500/10 text-indigo-400"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#1c2540]"
                  }`}
              >
                <item.icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="px-2 pb-4 border-t border-[#2a3354] pt-4">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors w-full"
          >
            <LogOut size={18} />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 ml-60">
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
