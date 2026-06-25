"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2, Circle, Clock, Play, Pause, BookOpen, Users, FileText,
  HelpCircle, CheckSquare, AlertTriangle, X, RotateCcw, Award, ClipboardList,
} from "lucide-react";
import { api } from "@/lib/api";

const STEP_META: Record<string, { label: string; icon: any }> = {
  lectura: { label: "Lectura", icon: BookOpen },
  reunion: { label: "Reunión", icon: Users },
  documento: { label: "Documento", icon: FileText },
  cuestionario: { label: "Cuestionario", icon: HelpCircle },
  tarea: { label: "Tarea", icon: CheckSquare },
  configuracion: { label: "Configuración", icon: CheckSquare },
  entregable: { label: "Entregable", icon: CheckSquare },
};

const planStatusMeta: Record<string, { label: string; cls: string }> = {
  sin_empezar: { label: "Sin empezar", cls: "bg-slate-500/10 text-slate-400 border-slate-500/20" },
  en_progreso: { label: "En progreso", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  finalizado: { label: "Finalizado", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  perdido: { label: "No aprobado", cls: "bg-red-500/10 text-red-400 border-red-500/20" },
};

function fmt(s: number) {
  s = Math.max(0, Math.floor(s));
  const m = Math.floor(s / 60), ss = s % 60;
  if (m < 60) return `${m}:${String(ss).padStart(2, "0")}`;
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

export default function MiPlanPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchedAt, setFetchedAt] = useState(Date.now());
  const [, setClock] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  // Cuestionario
  const [quiz, setQuiz] = useState<any>(null);            // { stepId, title, questions, threshold }
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [quizResult, setQuizResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    const d = await api.getMyPlans();
    setPlans(d);
    setFetchedAt(Date.now());
  };
  useEffect(() => {
    (async () => { try { await load(); } catch (e) { console.error(e); } finally { setLoading(false); } })();
  }, []);
  useEffect(() => {
    const i = setInterval(() => setClock((c) => c + 1), 1000);
    return () => clearInterval(i);
  }, []);

  const liveTime = (step: any) =>
    step.time_spent_seconds + (step.is_running ? Math.floor((Date.now() - fetchedAt) / 1000) : 0);

  const act = async (fn: () => Promise<any>, stepId: string) => {
    setBusy(stepId);
    try { await fn(); await load(); } catch (e) { console.error(e); } finally { setBusy(null); }
  };

  const openQuiz = async (step: any, plan: any) => {
    setQuizResult(null); setAnswers({});
    try {
      const q = await api.getStepQuiz(step.id);
      setQuiz({ ...q, threshold: plan.pass_threshold });
    } catch (e) { console.error(e); }
  };

  const pickAnswer = (q: any, optId: string) => {
    setAnswers((prev) => {
      if (q.qtype === "single") return { ...prev, [q.id]: [optId] };
      const cur = prev[q.id] || [];
      return { ...prev, [q.id]: cur.includes(optId) ? cur.filter((x) => x !== optId) : [...cur, optId] };
    });
  };

  const submitQuiz = async () => {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const payload = quiz.questions.map((q: any) => ({ question_id: q.id, selected_option_ids: answers[q.id] || [] }));
      const res = await api.submitQuiz(quiz.stepId, payload);
      setQuizResult(res);
    } catch (e) { console.error(e); } finally { setSubmitting(false); }
  };

  const closeQuiz = async () => {
    setQuiz(null); setQuizResult(null);
    await load();
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="text-slate-400 text-sm">Cargando...</div></div>
  );

  const hasActive = plans.some((p) => p.status === "sin_empezar" || p.status === "en_progreso");
  const allAnswered = quiz && quiz.questions.every((q: any) => (answers[q.id] || []).length > 0);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-white text-2xl font-semibold">Mi plan de onboarding</h1>
        <p className="text-slate-400 text-sm mt-1">Completa cada paso para avanzar en tu incorporación</p>
      </div>

      {/* Aviso obligatorio */}
      {hasActive && (
        <div className="flex items-start gap-3 bg-amber-500/10 border border-amber-500/20 rounded-2xl px-5 py-4">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <p className="text-amber-200/90 text-sm">
            Tu onboarding es <span className="font-semibold">obligatorio</span>. Debes completar todos los pasos de tu plan;
            si tu plan incluye una evaluación y no la apruebas, el plan se reiniciará y deberás repetirlo.
          </p>
        </div>
      )}

      {plans.length === 0 ? (
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-10 text-center">
          <ClipboardList size={28} className="text-slate-600 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">Aún no tienes un plan asignado.</p>
        </div>
      ) : plans.map((plan) => {
        const meta = planStatusMeta[plan.status] || planStatusMeta.sin_empezar;
        const active = plan.status === "sin_empezar" || plan.status === "en_progreso";
        const pct = plan.total_steps > 0 ? Math.round((plan.completed_steps / plan.total_steps) * 100) : 0;
        return (
          <div key={plan.id} className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#2a3349]">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-white font-semibold">{plan.plan_name}</h2>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${meta.cls}`}>{meta.label}</span>
                  {plan.attempt_number > 1 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/20">Intento {plan.attempt_number}</span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-slate-400 text-xs">
                  <span className="flex items-center gap-1.5"><Clock size={13} /> {fmt(plan.time_spent_seconds)}</span>
                  {plan.score != null && <span className="flex items-center gap-1.5 text-emerald-400"><Award size={13} /> {plan.score}/100</span>}
                </div>
              </div>
              <div className="mt-3">
                <div className="h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                </div>
                <p className="text-slate-500 text-xs mt-1.5">{plan.completed_steps} de {plan.total_steps} pasos · {pct}%</p>
              </div>
            </div>

            <div className="divide-y divide-[#2a3349]">
              {plan.steps.map((step: any, i: number) => {
                const m = STEP_META[step.category] || { label: step.category, icon: Circle };
                const Icon = m.icon;
                const done = step.status === "completada";
                const t = liveTime(step);
                return (
                  <div key={step.id} className="flex items-center gap-3 px-6 py-3.5">
                    <span className="text-slate-600 text-xs w-5 text-center shrink-0">{i + 1}</span>
                    {done ? <CheckCircle2 size={18} className="text-emerald-400 shrink-0" /> : <Icon size={17} className="text-slate-400 shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${done ? "text-slate-500 line-through" : "text-white"}`}>{step.title}</p>
                      <p className="text-slate-600 text-xs flex items-center gap-2 flex-wrap">
                        <span>{m.label}</span>
                        <span>· est. {step.estimated_minutes}m</span>
                        <span className={step.is_running ? "text-amber-400" : ""}>· {fmt(t)}{step.is_running ? " ⏱" : ""}</span>
                        {step.category === "documento" && step.document_name && <span className="text-cyan-400/80 truncate">· 📄 {step.document_name}</span>}
                        {step.has_quiz && <span className="text-fuchsia-400/80">· {step.question_count} pregunta{step.question_count === 1 ? "" : "s"}</span>}
                      </p>
                    </div>

                    {/* Controles (solo plan activo y paso no completado) */}
                    {active && !done && (
                      step.category === "cuestionario" ? (
                        <button onClick={() => openQuiz(step, plan)} disabled={busy === step.id}
                          className="text-xs bg-fuchsia-500/10 hover:bg-fuchsia-500/20 border border-fuchsia-500/20 text-fuchsia-300 px-3 py-1.5 rounded-xl transition-colors disabled:opacity-50">
                          Responder
                        </button>
                      ) : (
                        <div className="flex items-center gap-1.5 shrink-0">
                          {step.is_running ? (
                            <button onClick={() => act(() => api.pauseStep(step.id), step.id)} disabled={busy === step.id}
                              className="flex items-center gap-1 text-xs bg-[#1e2536] hover:bg-amber-500/10 border border-[#2a3349] hover:border-amber-500/20 text-slate-300 hover:text-amber-400 px-2.5 py-1.5 rounded-xl transition-colors disabled:opacity-50">
                              <Pause size={12} /> Pausar
                            </button>
                          ) : (
                            <button onClick={() => act(() => api.startStep(step.id), step.id)} disabled={busy === step.id}
                              className="flex items-center gap-1 text-xs bg-[#1e2536] hover:bg-indigo-500/10 border border-[#2a3349] hover:border-indigo-500/20 text-slate-300 hover:text-indigo-400 px-2.5 py-1.5 rounded-xl transition-colors disabled:opacity-50">
                              <Play size={12} /> {t > 0 ? "Reanudar" : "Iniciar"}
                            </button>
                          )}
                          <button onClick={() => act(() => api.completeStep(step.id), step.id)} disabled={busy === step.id}
                            className="flex items-center gap-1 text-xs bg-[#1e2536] hover:bg-emerald-500/10 border border-[#2a3349] hover:border-emerald-500/20 text-slate-300 hover:text-emerald-400 px-2.5 py-1.5 rounded-xl transition-colors disabled:opacity-50">
                            <CheckCircle2 size={12} /> Completar
                          </button>
                        </div>
                      )
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* ─── MODAL CUESTIONARIO ─── */}
      {quiz && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !submitting && (quizResult ? closeQuiz() : setQuiz(null))}>
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349] sticky top-0 bg-[#161b27]">
              <h2 className="text-white font-semibold flex items-center gap-2"><HelpCircle size={18} className="text-fuchsia-400" /> {quiz.title}</h2>
              <button onClick={() => quizResult ? closeQuiz() : setQuiz(null)} className="text-slate-500 hover:text-slate-200"><X size={18} /></button>
            </div>

            {quizResult ? (
              <div className="px-6 py-8 flex flex-col items-center text-center gap-3">
                {quizResult.passed ? (
                  <>
                    <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center"><Award size={28} className="text-emerald-400" /></div>
                    <p className="text-emerald-400 text-lg font-semibold">¡Aprobado!</p>
                    <p className="text-slate-300 text-sm">Obtuviste <span className="text-white font-medium">{quizResult.score}/100</span> ({quizResult.correct_count}/{quizResult.total} correctas). Mínimo: {quizResult.threshold}.</p>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center"><RotateCcw size={26} className="text-red-400" /></div>
                    <p className="text-red-400 text-lg font-semibold">No aprobado</p>
                    <p className="text-slate-300 text-sm">Obtuviste <span className="text-white font-medium">{quizResult.score}/100</span> ({quizResult.correct_count}/{quizResult.total}). Necesitabas {quizResult.threshold}.</p>
                    <p className="text-amber-300/90 text-sm bg-amber-500/10 border border-amber-500/20 rounded-xl px-3 py-2">El plan se reinició: todos los pasos vuelven a empezar y deberás repetirlo.</p>
                  </>
                )}
                <button onClick={closeQuiz} className="mt-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors">Entendido</button>
              </div>
            ) : (
              <>
                <div className="px-6 py-5 flex flex-col gap-5">
                  <p className="text-slate-500 text-xs">Nota mínima para aprobar: {quiz.threshold}/100</p>
                  {quiz.questions.map((q: any, qi: number) => (
                    <div key={q.id} className="flex flex-col gap-2">
                      <p className="text-white text-sm font-medium">{qi + 1}. {q.text}
                        <span className="text-slate-500 text-xs font-normal ml-2">{q.qtype === "multiple" ? "(varias)" : "(una)"}</span>
                      </p>
                      <div className="flex flex-col gap-1.5">
                        {q.options.map((o: any) => {
                          const sel = (answers[q.id] || []).includes(o.id);
                          return (
                            <button key={o.id} onClick={() => pickAnswer(q, o.id)}
                              className={`flex items-center gap-2.5 text-left px-3 py-2 rounded-xl border text-sm transition-colors
                                ${sel ? "bg-indigo-500/10 border-indigo-500/40 text-white" : "bg-[#0f1117] border-[#2a3349] text-slate-300 hover:border-[#3d4f6e]"}`}>
                              <span className={`w-4 h-4 ${q.qtype === "single" ? "rounded-full" : "rounded-md"} border flex items-center justify-center shrink-0
                                ${sel ? "bg-indigo-500 border-indigo-500" : "border-[#2a3349]"}`}>
                                {sel && <CheckCircle2 size={11} className="text-white" />}
                              </span>
                              {o.text}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349] sticky bottom-0 bg-[#161b27]">
                  <button onClick={() => setQuiz(null)} disabled={submitting} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl disabled:opacity-40">Cancelar</button>
                  <button onClick={submitQuiz} disabled={submitting || !allAnswered}
                    className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                    {submitting ? "Enviando..." : "Enviar respuestas"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
