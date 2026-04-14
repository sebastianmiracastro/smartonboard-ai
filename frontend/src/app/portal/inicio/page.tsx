"use client";

import { useRouter } from "next/navigation";
import { MessageSquare, CheckSquare, BookOpen, ArrowRight, CheckCircle2, Clock, Circle } from "lucide-react";
import { mockTasks } from "@/mock/data";

export default function PortalInicioPage() {
  const router = useRouter();

  const todayTasks = mockTasks.slice(0, 3);
  const completedCount = mockTasks.filter(t => t.status === "completada").length;

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-semibold">Buen día, Carlos 👋</h1>
        <p className="text-slate-400 text-sm mt-1">
          Estás en el día <span className="text-white font-medium">5 de 15</span> de tu onboarding.
        </p>
      </div>

      {/* Progreso general */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white font-medium">Tu progreso</p>
          <span className="text-indigo-400 text-sm font-semibold">60%</span>
        </div>
        <div className="h-2 bg-[#2a3349] rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full" style={{ width: "60%" }} />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-slate-500 text-xs">{completedCount} tareas completadas</span>
          <span className="text-slate-500 text-xs">{mockTasks.length - completedCount} pendientes</span>
        </div>
      </div>

      {/* Accesos rápidos */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: MessageSquare, label: "Preguntarle al agente", sub: "Chat con IA", href: "/portal/chat", color: "text-indigo-400", bg: "bg-indigo-500/10" },
          { icon: CheckSquare, label: "Ver mis tareas", sub: `${mockTasks.filter(t => t.status === "pendiente").length} pendientes`, href: "/portal/tareas", color: "text-amber-400", bg: "bg-amber-500/10" },
          { icon: BookOpen, label: "Recursos", sub: "Documentos de la empresa", href: "/portal/recursos", color: "text-emerald-400", bg: "bg-emerald-500/10" },
        ].map((item) => (
          <button
            key={item.href}
            onClick={() => router.push(item.href)}
            className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5 text-left hover:border-[#3d4f6e] transition-colors group"
          >
            <div className={`w-10 h-10 ${item.bg} rounded-xl flex items-center justify-center mb-3`}>
              <item.icon size={20} className={item.color} />
            </div>
            <p className="text-white text-sm font-medium">{item.label}</p>
            <p className="text-slate-500 text-xs mt-0.5">{item.sub}</p>
          </button>
        ))}
      </div>

      {/* Tareas de hoy */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
          <h2 className="text-white font-semibold">Tareas de hoy</h2>
          <button
            onClick={() => router.push("/portal/tareas")}
            className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-sm transition-colors"
          >
            Ver todas <ArrowRight size={14} />
          </button>
        </div>

        <div className="divide-y divide-[#2a3349]">
          {todayTasks.map((task) => (
            <div key={task.id} className="flex items-center gap-3 px-6 py-4 hover:bg-[#1e2536]/50 transition-colors">
              {task.status === "completada"
                ? <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                : task.status === "en_progreso"
                ? <Clock size={18} className="text-amber-400 shrink-0" />
                : <Circle size={18} className="text-slate-500 shrink-0" />
              }
              <div className="flex-1">
                <p className={`text-sm ${task.status === "completada" ? "text-slate-500 line-through" : "text-white"}`}>
                  {task.title}
                </p>
                <p className="text-slate-600 text-xs">Día {task.day}</p>
              </div>
              <span className="text-xs text-slate-500 capitalize">{task.status.replace("_", " ")}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}