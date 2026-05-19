"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, FileText, Bot, TrendingDown, ArrowRight, Clock } from "lucide-react";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<any[]>([]);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [me, users] = await Promise.all([
          api.getMe(),
          api.getUsers(),
        ]);
        setUser(me);
        setEmployees(users);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const onboarding = employees.filter(e => e.status === "onboarding");

  const metrics = [
    {
      label: "En onboarding",
      value: onboarding.length,
      sub: `${onboarding.length} activos`,
      subColor: "text-emerald-400",
      icon: Users,
      iconBg: "bg-indigo-500/10",
      iconColor: "text-indigo-400",
    },
    {
      label: "Empleados totales",
      value: employees.length,
      sub: "registrados",
      subColor: "text-slate-500",
      icon: Clock,
      iconBg: "bg-emerald-500/10",
      iconColor: "text-emerald-400",
    },
    {
      label: "Resolución IA",
      value: "94%",
      sub: "sin intervención humana",
      subColor: "text-emerald-400",
      icon: Bot,
      iconBg: "bg-violet-500/10",
      iconColor: "text-violet-400",
    },
    {
      label: "Tiempo promedio",
      value: "4.2d",
      sub: "↓ 2.1d vs manual",
      subColor: "text-emerald-400",
      icon: TrendingDown,
      iconBg: "bg-amber-500/10",
      iconColor: "text-amber-400",
    },
  ];

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">

      <div>
        <h1 className="text-white text-2xl font-semibold">
          Buen día, {user?.full_name?.split(" ")[0]} 👋
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Tienes <span className="text-white font-medium">{onboarding.length} empleados</span> en proceso de onboarding.
        </p>
      </div>

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

      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
          <div>
            <h2 className="text-white font-semibold">Empleados en onboarding</h2>
            <p className="text-slate-500 text-xs mt-0.5">Datos en tiempo real</p>
          </div>
          <button
            onClick={() => router.push("/dashboard/empleados")}
            className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 text-sm transition-colors"
          >
            Ver todos <ArrowRight size={14} />
          </button>
        </div>

        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3349] bg-[#1e2536]/50">
          <span className="col-span-4 text-slate-500 text-xs uppercase tracking-wider">Empleado</span>
          <span className="col-span-3 text-slate-500 text-xs uppercase tracking-wider">Rol</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Estado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Día</span>
          <span className="col-span-1"></span>
        </div>

        {onboarding.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-slate-500 text-sm">No hay empleados en onboarding</p>
          </div>
        ) : (
          onboarding.map((emp) => (
            <div
              key={emp.id}
              className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3349] last:border-0 hover:bg-[#1e2536]/50 transition-colors items-center"
            >
              <div className="col-span-4 flex items-center gap-3">
                <div className="w-8 h-8 bg-indigo-500/20 border border-indigo-500/20 rounded-full flex items-center justify-center shrink-0">
                  <span className="text-indigo-400 text-xs font-semibold">
                    {emp.full_name?.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium truncate">{emp.full_name}</p>
                  <p className="text-slate-500 text-xs truncate">{emp.email}</p>
                </div>
              </div>

              <div className="col-span-3">
                <p className="text-slate-300 text-sm">{emp.system_role}</p>
              </div>

              <div className="col-span-2">
                <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {emp.status}
                </span>
              </div>

              <div className="col-span-2">
                <p className="text-slate-300 text-sm">Día {emp.onboarding_day}</p>
                <p className="text-slate-500 text-xs">de {emp.onboarding_total_days}</p>
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
          ))
        )}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: FileText, label: "Documentos indexados", value: "12", sub: "4.231 chunks", color: "text-blue-400", bg: "bg-blue-500/10" },
          { icon: Bot, label: "Precisión del agente", value: "98.2%", sub: "últimas 48h", color: "text-violet-400", bg: "bg-violet-500/10" },
          { icon: Users, label: "Empleados totales", value: employees.length.toString(), sub: "registrados", color: "text-emerald-400", bg: "bg-emerald-500/10" },
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