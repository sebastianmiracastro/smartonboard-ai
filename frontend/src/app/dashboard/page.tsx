"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Users, FileText, Bot, TrendingDown, ArrowRight, Clock, AlertTriangle, CheckCircle2, Wrench, Brain } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie,
} from "recharts";
import { api } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  procesos: "Procesos",
  rol: "Rol",
  cultura: "Cultura",
  herramientas: "Herramientas",
  relaciones: "Relaciones",
  sin_categoria: "Sin categoría",
};

const DEPTH_LABELS: Record<string, string> = {
  basico: "Básico",
  intermedio: "Intermedio",
  avanzado: "Avanzado",
};

// Tipos de alerta de RR.HH. con su etiqueta y color
const ALERT_KINDS: Record<string, { label: string; classes: string }> = {
  solicitud: { label: "Pidió ayuda", classes: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" },
  sin_respuesta: { label: "Pregunta sin respuesta", classes: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  plan_fallido: { label: "No aprobó un plan", classes: "bg-red-500/15 text-red-300 border-red-500/30" },
};

const CATEGORY_COLORS = ["#6d5cff", "#8b5cf6", "#10b981", "#f59e0b", "#ec4899", "#64748b"];

// Color de celda del heatmap por índice de comprensión (buckets consistentes con la app)
function heatColor(v: number | null): string {
  if (v == null) return "bg-[#1c2540] text-slate-600 border-[#2a3354]";
  if (v < 0.4) return "bg-red-500/15 text-red-300 border-red-500/25";
  if (v < 0.6) return "bg-amber-500/15 text-amber-300 border-amber-500/25";
  return "bg-emerald-500/15 text-emerald-300 border-emerald-500/25";
}
const DEPTH_COLORS: Record<string, string> = {
  basico: "#10b981",
  intermedio: "#f59e0b",
  avanzado: "#6d5cff",
};

export default function DashboardPage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<any[]>([]);
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [knowledgeMap, setKnowledgeMap] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [me, users, summary, analytics, alertsResp, kmap] = await Promise.all([
          api.getMe(),
          api.getUsers(),
          api.getCompanySummary(),
          api.getCompanyAnalytics(),
          api.getAlerts(),
          api.getCompanyKnowledgeMap().catch(() => null),
        ]);
        setUser(me);
        setEmployees(users);
        setSummary(summary);
        setAnalytics(analytics);
        setAlerts(alertsResp?.alerts || []);
        setKnowledgeMap(kmap);
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const resolveAlert = async (id: string) => {
    try {
      await api.resolveAlert(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: "atendida" } : a))
      );
    } catch (e) {
      console.error(e);
    }
  };

  const categoryData = (analytics?.categories || []).map((c: any) => ({
    label: CATEGORY_LABELS[c.name] || c.name,
    value: c.value,
    key: c.name,
  }));
  const depthData = (analytics?.depths || []).map((d: any) => ({
    label: DEPTH_LABELS[d.name] || d.name,
    value: d.value,
    key: d.name,
  }));
  const toolData = analytics?.tools || [];
  const hasChatData = (analytics?.total_questions || 0) > 0;
  const pendingAlerts = alerts.filter((a) => a.status === "pendiente");

  // Mapa de conocimiento: matriz cargo × categoría
  const kmCats: string[] = knowledgeMap?.categories || [];
  const kmCells: any[] = knowledgeMap?.cells || [];
  const cellMap: Record<string, any> = {};
  kmCells.forEach((c) => { cellMap[`${c.cargo_id}|${c.category}`] = c; });
  // Solo cargos con al menos una celda con datos (evita filas vacías)
  const kmRows = (knowledgeMap?.cargos || []).filter(
    (cg: any) => kmCells.some((c) => c.cargo_id === cg.id)
  );
  const hasKnowledgeMap = kmCells.length > 0;

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
      value: summary && summary.ai_resolution_rate != null ? `${Math.round(summary.ai_resolution_rate * 100)}%` : "—",
      sub: "sin intervención humana",
      subColor: "text-emerald-400",
      icon: Bot,
      iconBg: "bg-violet-500/10",
      iconColor: "text-violet-400",
    },
    {
      label: "Tiempo promedio",
      value: summary && summary.avg_onboarding_days != null ? `${summary.avg_onboarding_days}d` : "—",
      sub: "días de onboarding",
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
          <div key={m.label} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
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

      {/* Alertas generadas por el agente para RR.HH. */}
      {pendingAlerts.length > 0 && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-amber-500/20">
            <AlertTriangle size={16} className="text-amber-400" />
            <h2 className="text-white font-semibold">Alertas de acompañamiento</h2>
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-medium">
              {pendingAlerts.length} pendiente{pendingAlerts.length > 1 ? "s" : ""}
            </span>
          </div>
          <div className="divide-y divide-amber-500/10">
            {pendingAlerts.map((a) => {
              const kind = ALERT_KINDS[a.kind as string] || ALERT_KINDS.solicitud;
              return (
              <div key={a.id} className="flex items-center gap-3 px-6 py-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-white text-sm font-medium">{a.user_name}</p>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium border ${kind.classes}`}>
                      {kind.label}
                    </span>
                  </div>
                  <p className="text-slate-400 text-xs truncate">{a.motivo}</p>
                </div>
                <button
                  onClick={() => resolveAlert(a.id)}
                  className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 text-xs transition-colors shrink-0"
                >
                  <CheckCircle2 size={14} /> Marcar atendida
                </button>
              </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Analítica de las preguntas al agente */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-1">Preguntas por categoría</h2>
          <p className="text-slate-500 text-xs mb-4">Temas que más consultan los empleados al agente</p>
          {hasChatData && categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" stroke="#475569" fontSize={11} allowDecimals={false} />
                <YAxis type="category" dataKey="label" stroke="#94a3b8" fontSize={11} width={84} />
                <Tooltip
                  cursor={{ fill: "#1c2540" }}
                  contentStyle={{ background: "#0f1320", border: "1px solid #2a3354", borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} name="Preguntas">
                  {categoryData.map((entry: any, i: number) => (
                    <Cell key={entry.key} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">
              Aún no hay preguntas registradas
            </div>
          )}
        </div>

        <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-1">Profundidad de las preguntas</h2>
          <p className="text-slate-500 text-xs mb-4">Nivel de las consultas realizadas</p>
          {hasChatData && depthData.length > 0 ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="60%" height={220}>
                <PieChart>
                  <Pie data={depthData} dataKey="value" nameKey="label" cx="50%" cy="50%"
                       innerRadius={50} outerRadius={80} paddingAngle={3}>
                    {depthData.map((entry: any) => (
                      <Cell key={entry.key} fill={DEPTH_COLORS[entry.key] || "#64748b"} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#0f1320", border: "1px solid #2a3354", borderRadius: 12, fontSize: 12 }}
                    labelStyle={{ color: "#e2e8f0" }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-col gap-2">
                {depthData.map((entry: any) => (
                  <div key={entry.key} className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-sm" style={{ background: DEPTH_COLORS[entry.key] || "#64748b" }} />
                    <span className="text-slate-300 text-sm">{entry.label}</span>
                    <span className="text-slate-500 text-xs">({entry.value})</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-600 text-sm">
              Aún no hay preguntas registradas
            </div>
          )}
        </div>
      </div>

      {/* Mapa de conocimiento por cargo (heatmap cargo × categoría) */}
      {hasKnowledgeMap && (
        <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Brain size={16} className="text-indigo-400" />
            <h2 className="text-white font-semibold">Mapa de conocimiento por cargo</h2>
          </div>
          <p className="text-slate-500 text-xs mb-4">
            Índice relativo de comprensión (similitud con los documentos) por cargo y categoría. Compara entre celdas, no el valor absoluto.
          </p>

          <div className="overflow-x-auto">
            <table className="border-separate" style={{ borderSpacing: "4px" }}>
              <thead>
                <tr>
                  <th></th>
                  {kmCats.map((cat) => (
                    <th key={cat} className="text-slate-400 text-xs font-medium px-2 pb-1 text-center">
                      {CATEGORY_LABELS[cat] || cat}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {kmRows.map((cg: any) => (
                  <tr key={cg.id}>
                    <td className="text-slate-300 text-xs pr-3 whitespace-nowrap">{cg.name}</td>
                    {kmCats.map((cat) => {
                      const cell = cellMap[`${cg.id}|${cat}`];
                      const v = cell ? cell.comprehension : null;
                      const pct = v != null ? Math.round(v * 100) : null;
                      return (
                        <td key={cat} className="p-0">
                          <div
                            title={cell ? `${cell.questions} pregunta${cell.questions === 1 ? "" : "s"}` : "Sin consultas"}
                            className={`h-10 min-w-[68px] rounded-lg border flex items-center justify-center text-xs font-medium ${heatColor(v)}`}
                          >
                            {pct != null ? `${pct}%` : "—"}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Leyenda */}
          <div className="flex flex-wrap items-center gap-4 mt-4">
            <span className="text-slate-500 text-xs">Índice:</span>
            <span className="flex items-center gap-1.5 text-xs text-slate-400"><span className="w-3 h-3 rounded-sm bg-red-500/30 border border-red-500/30" />Bajo</span>
            <span className="flex items-center gap-1.5 text-xs text-slate-400"><span className="w-3 h-3 rounded-sm bg-amber-500/30 border border-amber-500/30" />Medio</span>
            <span className="flex items-center gap-1.5 text-xs text-slate-400"><span className="w-3 h-3 rounded-sm bg-emerald-500/30 border border-emerald-500/30" />Alto</span>
            <span className="flex items-center gap-1.5 text-xs text-slate-400"><span className="w-3 h-3 rounded-sm bg-[#1c2540] border border-[#2a3354]" />Sin datos</span>
          </div>
        </div>
      )}

      {/* Acciones del agente (herramientas usadas) */}
      {toolData.length > 0 && (
        <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Wrench size={16} className="text-indigo-400" />
            <h2 className="text-white font-semibold">Acciones del agente</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {toolData.map((t: any) => (
              <div key={t.key} className="bg-[#1c2540]/50 border border-[#2a3354] rounded-xl p-3">
                <p className="text-white text-2xl font-semibold">{t.value}</p>
                <p className="text-slate-400 text-xs mt-0.5">{t.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3354]">
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

        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3354] bg-[#1c2540]/50">
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
              className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3354] last:border-0 hover:bg-[#1c2540]/50 transition-colors items-center"
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
                {emp.onboarding_state === "sin_plan" ? (
                  <p className="text-slate-500 text-xs">Sin plan</p>
                ) : (
                  <>
                    <p className="text-slate-300 text-sm">{emp.onboarding_progress ?? 0}%</p>
                    <p className="text-slate-500 text-xs">
                      {emp.onboarding_state === "completado" ? "completado" : "onboarding"}
                    </p>
                  </>
                )}
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
          {
            icon: FileText,
            label: "Documentos indexados",
            value: summary?.total_documents?.toString() || "0",
            sub: `${summary?.total_chunks || 0} chunks`,
            color: "text-blue-400",
            bg: "bg-blue-500/10"
          },
          {
            icon: Bot,
            label: "Preguntas respondidas",
            value: summary?.total_questions?.toString() || "0",
            sub: `${summary?.total_conversations || 0} conversaciones`,
            color: "text-violet-400",
            bg: "bg-violet-500/10"
          },
          {
            icon: Users,
            label: "Empleados totales",
            value: employees.length.toString(),
            sub: "registrados",
            color: "text-emerald-400",
            bg: "bg-emerald-500/10"
          },
        ].map((s) => (
          <div key={s.label} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-4 flex items-center gap-4">
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