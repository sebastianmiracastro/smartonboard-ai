"use client";

import { useState } from "react";
import { CheckCircle2, Clock, Circle, AlertCircle, ExternalLink } from "lucide-react";
import { mockTasks } from "@/mock/data";

const statusConfig: Record<string, { label: string; icon: React.ReactNode; classes: string }> = {
  completada: {
    label: "Completada",
    icon: <CheckCircle2 size={16} className="text-emerald-400" />,
    classes: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  },
  en_progreso: {
    label: "En progreso",
    icon: <Clock size={16} className="text-amber-400" />,
    classes: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  },
  pendiente: {
    label: "Pendiente",
    icon: <Circle size={16} className="text-slate-500" />,
    classes: "bg-slate-500/10 text-slate-400 border border-slate-500/20",
  },
  bloqueada: {
    label: "Bloqueada",
    icon: <AlertCircle size={16} className="text-red-400" />,
    classes: "bg-red-500/10 text-red-400 border border-red-500/20",
  },
};

const categoryColors: Record<string, string> = {
  lectura: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  reunion: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  configuracion: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  entregable: "bg-coral-500/10 text-orange-400 border border-orange-500/20",
};

export default function TareasPage() {
  const [filter, setFilter] = useState("todas");
  const [tasks, setTasks] = useState(mockTasks);

  const filtered = tasks.filter((t) => {
    if (filter === "todas") return true;
    return t.status === filter;
  });

  const markDone = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => t.id === id ? { ...t, status: "completada" } : t)
    );
  };

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-semibold">Mis tareas</h1>
        <p className="text-slate-400 text-sm mt-1">
          {tasks.filter(t => t.status === "completada").length} de {tasks.length} completadas
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Total", value: tasks.length, color: "text-white" },
          { label: "Completadas", value: tasks.filter(t => t.status === "completada").length, color: "text-emerald-400" },
          { label: "En progreso", value: tasks.filter(t => t.status === "en_progreso").length, color: "text-amber-400" },
          { label: "Pendientes", value: tasks.filter(t => t.status === "pendiente").length, color: "text-slate-400" },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className={`text-2xl font-semibold ${s.color}`}>{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div className="flex gap-2">
        {["todas", "pendiente", "en_progreso", "completada"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors capitalize
              ${filter === f
                ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                : "bg-[#161b27] border border-[#2a3349] text-slate-400 hover:text-slate-200"
              }`}
          >
            {f === "todas" ? "Todas" : f.replace("_", " ")}
          </button>
        ))}
      </div>

      {/* Lista tareas */}
      <div className="flex flex-col gap-3">
        {filtered.map((task) => (
          <div
            key={task.id}
            className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 flex items-center gap-4 hover:border-[#3d4f6e] transition-colors"
          >
            {/* Icono estado */}
            <div className="shrink-0">
              {statusConfig[task.status]?.icon}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${task.status === "completada" ? "text-slate-500 line-through" : "text-white"}`}>
                {task.title}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-slate-600 text-xs">Día {task.day}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryColors[task.category] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                  {task.category}
                </span>
              </div>
            </div>

            {/* Jira key simulado */}
            <div className="flex items-center gap-1.5 text-slate-500 text-xs">
              <ExternalLink size={12} />
              <span>TC-{100 + parseInt(task.id.replace("t", ""))}</span>
            </div>

            {/* Estado + acción */}
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusConfig[task.status]?.classes}`}>
                {statusConfig[task.status]?.label}
              </span>
              {task.status !== "completada" && (
                <button
                  onClick={() => markDone(task.id)}
                  className="text-xs bg-[#1e2536] hover:bg-emerald-500/10 border border-[#2a3349] hover:border-emerald-500/20 text-slate-400 hover:text-emerald-400 px-3 py-1.5 rounded-xl transition-colors"
                >
                  Completar
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}