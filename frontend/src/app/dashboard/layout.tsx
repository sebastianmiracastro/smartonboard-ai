"use client";

import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  Zap, LayoutDashboard, Users, FileText,
  Building2, ClipboardList, Settings, LogOut, Menu, X
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: Users, label: "Empleados", href: "/dashboard/empleados" },
  { icon: FileText, label: "Documentos", href: "/dashboard/documentos" },
  { icon: Building2, label: "Departamentos", href: "/dashboard/departamentos" },
  { icon: ClipboardList, label: "Planes", href: "/dashboard/planes" },
  { icon: Settings, label: "Configuración", href: "/dashboard/configuracion" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-[#0f1117] flex">

      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-60" : "w-16"} bg-[#161b27] border-r border-[#2a3349] flex flex-col transition-all duration-300 fixed h-full z-10`}>

        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-[#2a3349]">
          <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center shrink-0">
            <Zap size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <span className="text-white text-sm font-semibold tracking-tight truncate">
              SmartOnboard <span className="text-indigo-400">AI</span>
            </span>
          )}
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
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#1e2536]"
                  }`}
              >
                <item.icon size={18} className="shrink-0" />
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Usuario */}
        <div className="px-2 pb-4 border-t border-[#2a3349] pt-4 flex flex-col gap-1">
          {sidebarOpen && (
            <div className="px-3 py-2 mb-1">
              <p className="text-white text-sm font-medium truncate">Andrea Salcedo</p>
              <p className="text-slate-500 text-xs truncate">Recursos Humanos</p>
            </div>
          )}
          <button
            onClick={() => router.push("/login")}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors w-full"
          >
            <LogOut size={18} className="shrink-0" />
            {sidebarOpen && <span>Cerrar sesión</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className={`flex-1 flex flex-col ${sidebarOpen ? "ml-60" : "ml-16"} transition-all duration-300`}>

        {/* Topbar */}
        <header className="h-16 bg-[#161b27] border-b border-[#2a3349] flex items-center px-6 gap-4 sticky top-0 z-10">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-slate-400 hover:text-white transition-colors"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="flex-1" />
          <div className="w-8 h-8 bg-indigo-500/20 border border-indigo-500/30 rounded-full flex items-center justify-center">
            <span className="text-indigo-400 text-xs font-semibold">AS</span>
          </div>
        </header>

        {/* Contenido */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}