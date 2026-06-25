"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Mail, Calendar, Building2, Briefcase, CheckCircle2, Clock, Circle, AlertCircle, MessageSquare, Lightbulb, TrendingUp, Brain, Target, RefreshCw, TrendingDown, ClipboardList, Award } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { api } from "@/lib/api";

const categoryColors: Record<string, string> = {
  procesos: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  rol: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  cultura: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  herramientas: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  relaciones: "bg-pink-500/10 text-pink-400 border border-pink-500/20",
  lectura: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  reunion: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  configuracion: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  entregable: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
};

const categoryLabels: Record<string, string> = {
  procesos: "Procesos",
  rol: "Rol",
  cultura: "Cultura",
  herramientas: "Herramientas",
  relaciones: "Relaciones",
  sin_categoria: "Sin categoría",
};

const CHART_COLORS = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#ec4899", "#64748b"];

const insightStyles: Record<string, { border: string; icon: any; color: string }> = {
  positivo: { border: "border-emerald-500/20 bg-emerald-500/5", icon: TrendingUp, color: "text-emerald-400" },
  alerta: { border: "border-red-500/20 bg-red-500/5", icon: AlertCircle, color: "text-red-400" },
  advertencia: { border: "border-amber-500/20 bg-amber-500/5", icon: Lightbulb, color: "text-amber-400" },
};

// Estado de comprensión por categoría (color = semántica del estado, no el valor crudo)
const knowledgeStatus: Record<string, { label: string; color: string; bg: string; bar: string }> = {
  ok:        { label: "Sólido",          color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", bar: "#10b981" },
  parcial:   { label: "Datos insuf.",    color: "text-indigo-300",  bg: "bg-indigo-500/10 border-indigo-500/20",   bar: "#6366f1" },
  refuerzo:  { label: "A reforzar",      color: "text-amber-400",   bg: "bg-amber-500/10 border-amber-500/20",     bar: "#f59e0b" },
  perdida:   { label: "Posible pérdida", color: "text-red-400",     bg: "bg-red-500/10 border-red-500/20",         bar: "#ef4444" },
  sin_datos: { label: "Sin datos",       color: "text-slate-500",   bg: "bg-slate-500/10 border-slate-500/20",     bar: "#64748b" },
};

const planStatusMeta: Record<string, { label: string; cls: string }> = {
  sin_empezar: { label: "Sin empezar", cls: "bg-slate-500/10 text-slate-400 border border-slate-500/20" },
  en_progreso: { label: "En progreso", cls: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
  finalizado: { label: "Finalizado", cls: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
  perdido: { label: "No aprobado", cls: "bg-red-500/10 text-red-400 border border-red-500/20" },
};

function fmtDur(sec: number) {
  const m = Math.round((sec || 0) / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

const taskStatusIcon = (status: string) => {
  if (status === "completada") return <CheckCircle2 size={16} className="text-emerald-400" />;
  if (status === "en_progreso") return <Clock size={16} className="text-amber-400" />;
  if (status === "bloqueada") return <AlertCircle size={16} className="text-red-400" />;
  return <Circle size={16} className="text-slate-500" />;
};

export default function EmpleadoDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [employee, setEmployee] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [insights, setInsights] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any>(null);
  const [onboarding, setOnboarding] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [emp, empTasks, empStats, empInsights, empKnowledge, empOnboarding] = await Promise.all([
          api.getUser(id as string),
          api.getUserTasks(id as string),
          api.getUserStats(id as string).catch(() => null),
          api.getUserInsights(id as string).catch(() => null),
          api.getUserKnowledge(id as string).catch(() => null),
          api.getUserOnboarding(id as string).catch(() => null),
        ]);
        setEmployee(emp);
        setTasks(empTasks);
        setStats(empStats);
        setInsights(empInsights?.insights || []);
        setKnowledge(empKnowledge);
        setOnboarding(empOnboarding);
      } catch {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    };
    if (id) load();
  }, [id]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando empleado...</div>
    </div>
  );

  if (notFound || !employee) return (
    <div className="text-slate-400 text-sm">Empleado no encontrado.</div>
  );

  const progress = employee.onboarding_total_days > 0
    ? Math.round((employee.onboarding_day / employee.onboarding_total_days) * 100)
    : 0;

  const initials = employee.full_name
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .slice(0, 2);

  const categoryData = Object.entries(stats?.category_distribution || {})
    .map(([key, value]) => ({ key, label: categoryLabels[key] || key, value: value as number }))
    .sort((a, b) => b.value - a.value);

  const completedTasks = tasks.filter((t) => t.status === "completada").length;

  return (
    <div className="flex flex-col gap-6">

      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors w-fit"
      >
        <ArrowLeft size={16} /> Volver a empleados
      </button>

      {/* Header empleado */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6 flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-indigo-500/20 border border-indigo-500/20 rounded-2xl flex items-center justify-center">
            <span className="text-indigo-400 text-lg font-semibold">{initials}</span>
          </div>
          <div>
            <h1 className="text-white text-xl font-semibold">{employee.full_name}</h1>
            <div className="flex items-center gap-4 mt-1.5">
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Mail size={12} /> {employee.email}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Building2 size={12} /> {employee.department_name || "—"}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Briefcase size={12} /> {employee.role_name || "—"}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Calendar size={12} /> Desde {employee.start_date || "—"}
              </span>
            </div>
          </div>
        </div>

        {/* Actividad con el agente */}
        <div className="text-right">
          <p className="text-slate-500 text-xs mb-1">Preguntas al agente</p>
          <p className="text-3xl font-semibold text-indigo-400">{stats?.total_questions ?? 0}</p>
          <p className="text-slate-500 text-xs">{stats?.total_conversations ?? 0} conversaciones</p>
        </div>
      </div>

      {/* Progreso onboarding */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white font-medium">Progreso de onboarding</p>
          <span className="text-slate-400 text-sm">Día {employee.onboarding_day} de {employee.onboarding_total_days}</span>
        </div>
        <div className="h-2 bg-[#2a3349] rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-slate-500 text-xs">Inicio</span>
          <span className="text-indigo-400 text-xs font-medium">{progress}% · {completedTasks}/{tasks.length} tareas</span>
          <span className="text-slate-500 text-xs">Meta</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">

        {/* Preguntas por categoría (datos reales del chat) */}
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-1">Preguntas por categoría</h2>
          <p className="text-slate-500 text-xs mb-4">En qué temas consulta más al agente</p>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={categoryData} layout="vertical" margin={{ left: 8, right: 16 }}>
                <XAxis type="number" stroke="#475569" fontSize={11} allowDecimals={false} />
                <YAxis type="category" dataKey="label" stroke="#94a3b8" fontSize={11} width={84} />
                <Tooltip
                  cursor={{ fill: "#1e2536" }}
                  contentStyle={{ background: "#0f1320", border: "1px solid #2a3349", borderRadius: 12, fontSize: 12 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]} name="Preguntas">
                  {categoryData.map((entry, i) => (
                    <Cell key={entry.key} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[240px] flex flex-col items-center justify-center gap-2 text-slate-600">
              <MessageSquare size={28} />
              <p className="text-sm">Este empleado aún no ha consultado al agente</p>
            </div>
          )}
        </div>

        {/* Tareas */}
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-4">Tareas del plan</h2>
          {tasks.length === 0 ? (
            <p className="text-slate-500 text-sm">Sin tareas asignadas.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-3 bg-[#1e2536]/50 rounded-xl border border-[#2a3349]"
                >
                  {taskStatusIcon(task.status)}
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm truncate ${task.status === "completada" ? "text-slate-500 line-through" : "text-white"}`}>
                      {task.title}
                    </p>
                    <p className="text-slate-600 text-xs">Día {task.day_number}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryColors[task.category] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                    {task.category}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Onboarding y plan (avance, tiempo real vs estimado, evaluaciones) */}
      {onboarding && onboarding.plans.length > 0 && (
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <ClipboardList size={16} className="text-indigo-400" />
            <h2 className="text-white font-semibold">Onboarding y plan</h2>
          </div>
          <p className="text-slate-500 text-xs mb-4">Avance, tiempo real vs estimado y resultados de evaluaciones</p>

          {(() => {
            const s = onboarding.summary;
            const eff = s.efficiency_ratio;
            const effLabel = eff == null ? "—" : `${Math.round(eff * 100)}%`;
            const effColor = eff == null ? "text-slate-300" : eff <= 1 ? "text-emerald-400" : "text-amber-400";
            return (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <Stat label="Tiempo real" value={fmtDur(s.total_time_seconds)} sub={`est. ${fmtDur(s.estimated_seconds)}`} />
                <Stat label="Eficiencia" value={effLabel} sub={eff == null ? "" : eff <= 1 ? "a tiempo" : "sobre lo estimado"} color={effColor} />
                <Stat label="Nota media" value={s.avg_quiz_score != null ? `${s.avg_quiz_score}` : "—"} sub={s.total_quiz_attempts ? `${s.total_quiz_attempts} intento(s)` : "sin evaluaciones"} />
                <Stat label="Intentos fallidos" value={s.failed_attempts} color={s.failed_attempts > 0 ? "text-red-400" : "text-slate-300"} />
              </div>
            );
          })()}

          <div className="flex flex-col gap-2">
            {onboarding.plans.map((p: any) => {
              const meta = planStatusMeta[p.status] || planStatusMeta.sin_empezar;
              const pct = p.total_steps > 0 ? Math.round((p.completed_steps / p.total_steps) * 100) : 0;
              return (
                <div key={p.id} className="bg-[#1e2536]/50 rounded-xl border border-[#2a3349] p-3">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white text-sm">{p.plan_name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${meta.cls}`}>{meta.label}</span>
                      {p.attempt_number > 1 && <span className="text-xs text-slate-500">Intento {p.attempt_number}</span>}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1"><Clock size={11} /> {fmtDur(p.time_spent_seconds)} / {fmtDur(p.estimated_seconds)}</span>
                      {p.score != null && <span className="flex items-center gap-1 text-emerald-400"><Award size={11} /> {p.score}/100</span>}
                    </div>
                  </div>
                  <div className="mt-2 h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex items-center justify-between mt-1.5 gap-2 flex-wrap">
                    <span className="text-slate-500 text-xs">{p.completed_steps}/{p.total_steps} pasos · {pct}%</span>
                    {p.quiz_attempts.length > 0 && (
                      <span className="flex items-center gap-1">
                        <span className="text-slate-600 text-xs mr-0.5">Notas:</span>
                        {p.quiz_attempts.map((a: any, i: number) => (
                          <span key={i} className={`text-xs px-1.5 py-0.5 rounded ${a.passed ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>{a.score}</span>
                        ))}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Conocimiento y comprensión (cobertura, comprensión por categoría, pérdida) */}
      {knowledge && (
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-1">
            <Brain size={16} className="text-indigo-400" />
            <h2 className="text-white font-semibold">Conocimiento y comprensión</h2>
          </div>
          <p className="text-slate-500 text-xs mb-4">
            Índice relativo basado en la coincidencia con los documentos. Importa la comparación entre temas y la tendencia, no el valor absoluto.
          </p>

          {/* Cobertura temática */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-4 p-3 bg-[#1e2536]/50 rounded-xl border border-[#2a3349]">
            <Target size={16} className="text-indigo-400 shrink-0" />
            {knowledge.coverage?.available > 0 ? (
              <>
                <span className="text-slate-300 text-sm">
                  Cobertura temática:{" "}
                  <span className="text-white font-medium">
                    {knowledge.coverage.covered}/{knowledge.coverage.available}
                  </span>{" "}
                  categorías
                  {knowledge.coverage.ratio != null && (
                    <span className="text-indigo-400"> · {Math.round(knowledge.coverage.ratio * 100)}%</span>
                  )}
                </span>
                {knowledge.coverage.missing_categories?.length > 0 && (
                  <span className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-500 text-xs">Sin consultar:</span>
                    {knowledge.coverage.missing_categories.map((c: string) => (
                      <span key={c} className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[c] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>
                        {categoryLabels[c] || c}
                      </span>
                    ))}
                  </span>
                )}
              </>
            ) : (
              <span className="text-slate-400 text-sm">Aún no hay documentos categorizados para este cargo.</span>
            )}
          </div>

          {/* Alertas de pérdida de conocimiento */}
          {knowledge.knowledge_loss_alerts?.length > 0 && (
            <div className="flex flex-col gap-2 mb-4">
              {knowledge.knowledge_loss_alerts.map((a: any) => (
                <div key={a.category} className="flex items-start gap-3 p-3 rounded-xl border border-red-500/20 bg-red-500/5">
                  <TrendingDown size={16} className="text-red-400 mt-0.5 shrink-0" />
                  <p className="text-slate-300 text-sm">{a.message}</p>
                </div>
              ))}
            </div>
          )}

          {/* Comprensión por categoría */}
          {knowledge.total_questions > 0 ? (
            <div className="flex flex-col gap-2">
              {knowledge.by_category?.map((row: any) => {
                const st = knowledgeStatus[row.status] || knowledgeStatus.sin_datos;
                const pct = row.comprehension != null ? Math.round(row.comprehension * 100) : null;
                return (
                  <div key={row.category} className="grid grid-cols-12 items-center gap-3 p-3 bg-[#1e2536]/50 rounded-xl border border-[#2a3349]">
                    <div className="col-span-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[row.category] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>
                        {categoryLabels[row.category] || row.category}
                      </span>
                    </div>
                    <div className="col-span-5 flex items-center gap-2">
                      <div className="flex-1 h-2 bg-[#2a3349] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${pct != null ? Math.max(pct, 4) : 0}%`, background: st.bar }}
                        />
                      </div>
                      <span className="text-slate-300 text-xs w-9 text-right">{pct != null ? `${pct}%` : "—"}</span>
                    </div>
                    <div className="col-span-2 text-slate-500 text-xs">
                      {row.questions} {row.questions === 1 ? "pregunta" : "preguntas"}
                    </div>
                    <div className="col-span-2 flex justify-end">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${st.bg} ${st.color}`}>{st.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">Este empleado aún no ha consultado al agente; todavía no hay datos de comprensión.</p>
          )}

          {/* Candidatos a refuerzo / re-entreno */}
          {knowledge.retraining_candidates?.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-[#2a3349]">
              <RefreshCw size={14} className="text-amber-400 shrink-0" />
              <span className="text-slate-400 text-xs">Temas candidatos a refuerzo / re-entreno:</span>
              {knowledge.retraining_candidates.map((r: any) => (
                <span key={r.category} className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  {categoryLabels[r.category] || r.category}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Insights automáticos generados a partir de las preguntas */}
      {insights.length > 0 && (
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Lightbulb size={16} className="text-amber-400" />
            <h2 className="text-white font-semibold">Insights del onboarding</h2>
          </div>
          <div className="flex flex-col gap-2">
            {insights.map((ins, i) => {
              const style = insightStyles[ins.type] || insightStyles.advertencia;
              const Icon = style.icon;
              return (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border ${style.border}`}>
                  <Icon size={16} className={`${style.color} mt-0.5 shrink-0`} />
                  <p className="text-slate-300 text-sm">{ins.message}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, sub, color }: { label: string; value: any; sub?: string; color?: string }) {
  return (
    <div className="bg-[#1e2536]/50 border border-[#2a3349] rounded-xl p-3">
      <p className="text-slate-500 text-xs">{label}</p>
      <p className={`text-lg font-semibold mt-0.5 ${color || "text-white"}`}>{value}</p>
      {sub && <p className="text-slate-600 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}
