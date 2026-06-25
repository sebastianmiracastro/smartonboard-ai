"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MessageSquare, CheckSquare, BookOpen, ArrowRight, CheckCircle2, Clock, Circle, AlertTriangle, PartyPopper } from "lucide-react";
import { api } from "@/lib/api";

export default function PortalInicioPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [me, myPlans] = await Promise.all([api.getMe(), api.getMyPlans()]);
        setUser(me);
        setPlans(myPlans);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="text-slate-400 text-sm">Cargando...</div></div>
  );

  const activePlans = plans.filter((p) => p.status === "sin_empezar" || p.status === "en_progreso");
  const hasActive = activePlans.length > 0;
  const allFinalized = plans.length > 0 && !hasActive && plans.some((p) => p.status === "finalizado");

  // Progreso agregado de los planes activos (o del más reciente)
  const focus = activePlans[0] || plans[0];
  const totalSteps = activePlans.reduce((a, p) => a + p.total_steps, 0) || (focus?.total_steps ?? 0);
  const completedSteps = activePlans.reduce((a, p) => a + p.completed_steps, 0) || (focus?.completed_steps ?? 0);
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : (allFinalized ? 100 : 0);
  const recentSteps = (focus?.steps || []).slice().sort((a: any, b: any) => (a.status === "completada" ? 1 : 0) - (b.status === "completada" ? 1 : 0)).slice(0, 4);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-white text-2xl font-semibold">Buen día, {user?.full_name?.split(" ")[0]} 👋</h1>
        <p className="text-slate-400 text-sm mt-1">
          {hasActive
            ? <>Tienes <span className="text-white font-medium">{totalSteps - completedSteps} pasos</span> pendientes en tu onboarding.</>
            : allFinalized
            ? <>¡Completaste tu onboarding! 🎉</>
            : <>Aún no tienes un plan asignado.</>}
        </p>
      </div>

      {/* Aviso obligatorio / felicitación */}
      {hasActive ? (
        <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl px-5 py-4">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="text-amber-200/90 text-sm">
            Tu plan de onboarding es <span className="font-semibold">obligatorio</span>. Completa todos los pasos en <button onClick={() => router.push("/portal/tareas")} className="underline hover:text-amber-100">Mi plan</button>.
          </p>
        </div>
      ) : allFinalized ? (
        <div className="flex items-start gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl px-5 py-4">
          <PartyPopper size={18} className="text-emerald-400 shrink-0 mt-0.5" />
          <p className="text-emerald-200/90 text-sm">Finalizaste tu onboarding. ¡Bienvenido al equipo!</p>
        </div>
      ) : null}

      {/* Progreso */}
      <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white font-medium">Tu progreso</p>
          <span className="text-indigo-400 text-sm font-semibold">{progress}%</span>
        </div>
        <div className="h-2 bg-[#2a3354] rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-slate-500 text-xs">{completedSteps} pasos completados</span>
          <span className="text-slate-500 text-xs">{Math.max(0, totalSteps - completedSteps)} pendientes</span>
        </div>
      </div>

      {/* Accesos rápidos */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: MessageSquare, label: "Preguntarle al agente", sub: "Chat con IA", href: "/portal/chat", color: "text-indigo-400", bg: "bg-indigo-500/10" },
          { icon: CheckSquare, label: "Ver mi plan", sub: `${Math.max(0, totalSteps - completedSteps)} pasos pendientes`, href: "/portal/tareas", color: "text-amber-400", bg: "bg-amber-500/10" },
          { icon: BookOpen, label: "Recursos", sub: "Documentos de la empresa", href: "/portal/recursos", color: "text-emerald-400", bg: "bg-emerald-500/10" },
        ].map((item) => (
          <button key={item.href} onClick={() => router.push(item.href)} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5 text-left hover:border-[#3a4a72] transition-colors">
            <div className={`w-10 h-10 ${item.bg} rounded-xl flex items-center justify-center mb-3`}><item.icon size={20} className={item.color} /></div>
            <p className="text-white text-sm font-medium">{item.label}</p>
            <p className="text-slate-500 text-xs mt-0.5">{item.sub}</p>
          </button>
        ))}
      </div>

      {/* Pasos del plan */}
      <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3354]">
          <h2 className="text-white font-semibold">{focus ? focus.plan_name : "Mi plan"}</h2>
          <button onClick={() => router.push("/portal/tareas")} className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-sm transition-colors">Ver plan <ArrowRight size={14} /></button>
        </div>
        {recentSteps.length === 0 ? (
          <div className="px-6 py-12 text-center"><p className="text-slate-500 text-sm">No tienes pasos asignados aún</p></div>
        ) : (
          <div className="divide-y divide-[#2a3354]">
            {recentSteps.map((step: any) => (
              <div key={step.id} className="flex items-center gap-3 px-6 py-4">
                {step.status === "completada" ? <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                  : step.is_running ? <Clock size={18} className="text-amber-400 shrink-0" />
                  : <Circle size={18} className="text-slate-500 shrink-0" />}
                <div className="flex-1">
                  <p className={`text-sm ${step.status === "completada" ? "text-slate-500 line-through" : "text-white"}`}>{step.title}</p>
                  <p className="text-slate-600 text-xs">{step.estimated_minutes} min estimados</p>
                </div>
                <span className="text-xs text-slate-500 capitalize">{step.status === "completada" ? "Completado" : step.status === "en_progreso" ? "En progreso" : "Sin empezar"}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
