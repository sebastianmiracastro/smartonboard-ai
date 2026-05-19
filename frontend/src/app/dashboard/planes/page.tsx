"use client";

import { useState, useEffect } from "react";
import { ClipboardList, Users, Calendar, Plus, ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

const categoryColors: Record<string, string> = {
  lectura: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  reunion: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  configuracion: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  entregable: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  entrenamiento: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
};

export default function PlanesPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [tasks, setTasks] = useState<Record<string, any[]>>({});
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getPlans();
        setPlans(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggle = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!tasks[id]) {
      try {
        const data = await api.getPlanTasks(id);
        setTasks(prev => ({ ...prev, [id]: data }));
      } catch (err) {
        console.error(err);
      }
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Planes de onboarding</h1>
          <p className="text-slate-400 text-sm mt-1">
            Plantillas de incorporación por rol y departamento
          </p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
          <Plus size={16} />
          Nuevo plan
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Planes activos", value: plans.length },
          { label: "Promedio de días", value: plans.length > 0 ? Math.round(plans.reduce((a, p) => a + p.duration_days, 0) / plans.length) : 0 },
          { label: "Total tareas", value: Object.values(tasks).reduce((a, t) => a + t.length, 0) },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {plans.map((plan) => (
          <div key={plan.id} className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">

            <div
              className="flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-[#1e2536]/50 transition-colors"
              onClick={() => toggle(plan.id)}
            >
              <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center shrink-0">
                <ClipboardList size={18} className="text-indigo-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium">{plan.name}</p>
                <p className="text-slate-500 text-xs mt-0.5">{plan.description}</p>
              </div>
              <div className="flex items-center gap-6 shrink-0">
                <div className="flex items-center gap-1.5 text-slate-400 text-sm">
                  <Calendar size={14} />
                  <span>{plan.duration_days} días</span>
                </div>
                {tasks[plan.id] && (
                  <div className="flex items-center gap-1.5 text-slate-400 text-sm">
                    <ClipboardList size={14} />
                    <span>{tasks[plan.id].length} tareas</span>
                  </div>
                )}
              </div>
              <div className="text-slate-500 ml-2">
                {expanded === plan.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </div>

            {expanded === plan.id && (
              <div className="border-t border-[#2a3349] px-6 py-4 bg-[#1e2536]/30">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">Tareas del plan</p>
                  <button className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs transition-colors">
                    <Plus size={12} /> Agregar tarea
                  </button>
                </div>

                {!tasks[plan.id] ? (
                  <p className="text-slate-500 text-sm">Cargando tareas...</p>
                ) : tasks[plan.id].length === 0 ? (
                  <p className="text-slate-500 text-sm">No hay tareas en este plan</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {tasks[plan.id].map((task) => (
                      <div
                        key={task.id}
                        className="flex items-center gap-3 bg-[#161b27] border border-[#2a3349] rounded-xl px-4 py-3"
                      >
                        <CheckCircle2 size={14} className="text-slate-600 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-slate-200 text-sm truncate">{task.title}</p>
                          <p className="text-slate-600 text-xs">Día {task.day_number} · {task.estimated_minutes} min</p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryColors[task.category] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                          {task.category}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}