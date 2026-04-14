"use client";

import { useRouter } from "next/navigation";
import { Users, FileText, Bot, TrendingDown, ArrowRight, Clock } from "lucide-react";
import { mockMetrics, mockEmployees } from "@/mock/data";

const statusColors: Record<string, string> = {
  onboarding: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20",
  activo: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  inactivo: "bg-slate-500/10 text-slate-400 border border-slate-500/20",
};

const statusLabels: Record<string, string> = {
  onboarding: "En onboarding",
  activo: "Activo",
  inactivo: "Inactivo",
};

export default function DashboardPage() {
  const router = useRouter();

  const metrics = [
    {
      label: "En onboarding",
      value: mockMetrics.totalOnboarding,
      sub: "+2 esta semana",
      subColor: "text-emerald-400",
      icon: Users,
      iconBg: "bg-indigo-500/10",
      iconColor: "text-indigo-400",
    },
    {
      label: "Completados este mes",
      value: mockMetrics.completedThisMonth,
      sub: "empleados incorporados",
      subColor: "text-slate-500",
      icon: Clock,
      iconBg: "bg-emerald-500/10",
      iconColor: "text-emerald-400",
    },
    {
      label: "Resolución IA",
      value: `${mockMetrics.aiResolutionRate}%`,
      sub: "sin intervención humana",
      subColor: "text-emerald-400",
      icon: Bot,
      iconBg: "bg-violet-500/10",
      iconColor: "text-violet-400",
    },
    {
      label: "Tiempo promedio",
      value: `${mockMetrics.avgOnboardingDays}d`,
      sub: `↓ ${(mockMetrics.avgOnboardingDaysManual - mockMetrics.avgOnboardingDays).toFixed(1)}d vs manual`,
      subColor: "text-emerald-400",
      icon: TrendingDown,
      iconBg: "bg-amber-500/10",
      iconColor: "text-amber-400",
    },
  ];

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-semibold">Buen día, Andrea 👋</h1>
        <p className="text-slate-400 text-sm mt-1">
          Tienes <span className="text-white font-medium">{mockMetrics.totalOnboarding} empleados</span> en proceso de onboarding esta semana.
        </p>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
            <div className="flex items-start justify-between mb-4">
              <p className="text-slate-400 text-xs uppercase tracking-wider">{m.label}</p>
              <div className={`w-8 h-8 ${m.iconBg} rounded-lg flex items-center justify-center`}>
                <m.icon size={16} className={m.iconColor} />
              </div>
            </div>
            <p className="text-white text-3xl font-semibold mb-1">{m.value}</p>
            <p className={`text-xs ${m.subColor}`}>{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Tabla empleados activos */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
          <div>
            <h2 className="text-white font-semibold">Empleados en onboarding</h2>
            <p className="text-slate-500 text-xs mt-0.5">Seguimiento en tiempo real</p>
          </div>
          <button
            onClick={() => router.push("/dashboard/empleados")}
            className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 text-sm transition-colors"
          >
            Ver todos <ArrowRight size={14} />
          </button>
        </div>

        {/* Header tabla */}
        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3349] bg-[#1e2536]/50">
          <span className="col-span-3 text-slate-500 text-xs uppercase tracking-wider">Empleado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Área</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Estado</span>
          <span className="col-span-1 text-slate-500 text-xs uppercase tracking-wider">Día</span>
          <span className="col-span-3 text-slate-500 text-xs uppercase tracking-wider">Progreso</span>
          <span className="col-span-1"></span>
        </div>

        {/* Filas */}
        {mockEmployees.map((emp) => (
          <div
            key={emp.id}
            className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3349] last:border-0 hover:bg-[#1e2536]/50 transition-colors items-center"
          >
            <div className="col-span-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-500/20 border border-indigo-500/20 rounded-full flex items-center justify-center shrink-0">
                  <span className="text-indigo-400 text-xs font-semibold">
                    {emp.fullName.split(" ").map(n => n[0]).join("").slice(0, 2)}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium truncate">{emp.fullName}</p>
                  <p className="text-slate-500 text-xs truncate">{emp.email}</p>
                </div>
              </div>
            </div>

            <div className="col-span-2">
              <p className="text-slate-300 text-sm">{emp.department}</p>
              <p className="text-slate-500 text-xs">{emp.role}</p>
            </div>

            <div className="col-span-2">
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[emp.status]}`}>
                {statusLabels[emp.status]}
              </span>
            </div>

            <div className="col-span-1">
              <p className="text-slate-300 text-sm">Día {emp.onboardingDay}</p>
              <p className="text-slate-500 text-xs">de {emp.onboardingTotalDays}</p>
            </div>

            <div className="col-span-3">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-indigo-500 transition-all"
                    style={{ width: `${emp.progress}%` }}
                  />
                </div>
                <span className="text-slate-400 text-xs w-8 text-right">{emp.progress}%</span>
              </div>
            </div>

            <div className="col-span-1 flex justify-end">
              <button
                onClick={() => router.push(`/dashboard/empleados/${emp.id}`)}
                className="text-slate-500 hover:text-indigo-400 transition-colors"
              >
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Footer stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: FileText, label: "Documentos indexados", value: "12", sub: "4.231 chunks", color: "text-blue-400", bg: "bg-blue-500/10" },
          { icon: Bot, label: "Precisión del agente", value: "98.2%", sub: "últimas 48h", color: "text-violet-400", bg: "bg-violet-500/10" },
          { icon: Users, label: "Empleados totales", value: "30", sub: "4 departamentos", color: "text-emerald-400", bg: "bg-emerald-500/10" },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 flex items-center gap-4">
            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center shrink-0`}>
              <s.icon size={18} className={s.color} />
            </div>
            <div>
              <p className="text-white font-semibold">{s.value}</p>
              <p className="text-slate-400 text-xs">{s.label}</p>
              <p className="text-slate-600 text-xs">{s.sub}</p>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}