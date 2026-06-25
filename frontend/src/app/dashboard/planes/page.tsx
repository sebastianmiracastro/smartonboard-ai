"use client";

import { useState, useEffect } from "react";
import {
  ClipboardList, Calendar, Plus, ChevronDown, ChevronUp, X, Trash2, Pencil,
  UserPlus, BookOpen, Users, FileText, HelpCircle, CheckSquare, Clock, Zap,
  AlertTriangle, Check,
} from "lucide-react";
import { api } from "@/lib/api";

const STEP_TYPES = [
  { key: "lectura", label: "Lectura", icon: BookOpen },
  { key: "reunion", label: "Reunión", icon: Users },
  { key: "documento", label: "Documento", icon: FileText },
  { key: "cuestionario", label: "Cuestionario", icon: HelpCircle },
  { key: "tarea", label: "Tarea", icon: CheckSquare },
];

const categoryColors: Record<string, string> = {
  lectura: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  reunion: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  documento: "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20",
  cuestionario: "bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20",
  tarea: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  configuracion: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  entregable: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  entrenamiento: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
};
const labelOf = (k: string) => STEP_TYPES.find((s) => s.key === k)?.label || k;

const emptyPlan = {
  name: "", description: "", target_role_id: "", target_department_id: "",
  duration_days: 15, auto_assign: false, pass_threshold: 70,
};
const emptyStep = () => ({
  title: "", description: "", category: "lectura", day_number: 1,
  estimated_minutes: 30, document_id: "",
  questions: [] as any[],
});
const emptyQuestion = () => ({ text: "", qtype: "single", category: "", options: [{ text: "", is_correct: true }, { text: "", is_correct: false }] });

export default function PlanesPage() {
  const [plans, setPlans] = useState<any[]>([]);
  const [tasks, setTasks] = useState<Record<string, any[]>>({});
  const [roles, setRoles] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Modal plan (crear/editar)
  const [planModal, setPlanModal] = useState<{ open: boolean; edit: any | null }>({ open: false, edit: null });
  const [planForm, setPlanForm] = useState({ ...emptyPlan });
  // Modal paso
  const [stepModal, setStepModal] = useState<{ open: boolean; planId: string | null }>({ open: false, planId: null });
  const [stepForm, setStepForm] = useState<any>(emptyStep());
  // Modal asignar
  const [assignModal, setAssignModal] = useState<{ open: boolean; plan: any | null }>({ open: false, plan: null });
  const [assignUser, setAssignUser] = useState("");
  // Confirmar borrado
  const [deleteTarget, setDeleteTarget] = useState<{ kind: "plan" | "step"; id: string; name: string; planId?: string } | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadPlans = async () => setPlans(await api.getPlans());

  useEffect(() => {
    (async () => {
      try {
        const [pls, rls, deps, docs, usrs] = await Promise.all([
          api.getPlans(),
          api.getRoles().catch(() => []),
          api.getDepartments().catch(() => []),
          api.getDocuments().catch(() => []),
          api.getUsers().catch(() => []),
        ]);
        setPlans(pls); setRoles(rls); setDepartments(deps);
        setDocuments(docs); setEmployees(usrs.filter((u: any) => u.system_role === "empleado"));
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const loadTasks = async (planId: string) => {
    const data = await api.getPlanTasks(planId);
    setTasks((prev) => ({ ...prev, [planId]: data }));
  };

  const toggle = async (id: string) => {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    if (!tasks[id]) { try { await loadTasks(id); } catch (e) { console.error(e); } }
  };

  const roleName = (id: string) => roles.find((r) => r.id === id)?.name;

  // ── Plan crear/editar ──
  const openPlanCreate = () => { setPlanForm({ ...emptyPlan }); setError(""); setPlanModal({ open: true, edit: null }); };
  const openPlanEdit = (p: any) => {
    setPlanForm({
      name: p.name, description: p.description || "", target_role_id: p.target_role_id || "",
      target_department_id: p.target_department_id || "", duration_days: p.duration_days,
      auto_assign: p.auto_assign, pass_threshold: p.pass_threshold,
    });
    setError(""); setPlanModal({ open: true, edit: p });
  };
  const savePlan = async () => {
    setError("");
    if (!planForm.name.trim()) { setError("El nombre del plan es obligatorio."); return; }
    if (planForm.auto_assign && !planForm.target_role_id) {
      setError("Para asignación automática debes elegir un cargo objetivo."); return;
    }
    setSaving(true);
    try {
      const payload = {
        ...planForm,
        target_role_id: planForm.target_role_id || null,
        target_department_id: planForm.target_department_id || null,
      };
      if (planModal.edit) await api.updatePlan(planModal.edit.id, payload);
      else await api.createPlan(payload);
      setPlanModal({ open: false, edit: null });
      await loadPlans();
    } catch (e: any) { setError(e.message || "No se pudo guardar el plan."); }
    finally { setSaving(false); }
  };
  const toggleActive = async (p: any) => {
    try { await api.updatePlan(p.id, { is_active: !p.is_active }); await loadPlans(); }
    catch (e) { console.error(e); }
  };

  // ── Paso ──
  const openStep = (planId: string) => { setStepForm(emptyStep()); setError(""); setStepModal({ open: true, planId }); };
  const saveStep = async () => {
    setError("");
    if (!stepForm.title.trim()) { setError("El título del paso es obligatorio."); return; }
    if (stepForm.category === "documento" && !stepForm.document_id) { setError("Selecciona un documento."); return; }
    if (stepForm.category === "cuestionario") {
      if (stepForm.questions.length === 0) { setError("Agrega al menos una pregunta."); return; }
      for (const [i, q] of stepForm.questions.entries()) {
        if (!q.text.trim()) { setError(`La pregunta ${i + 1} no tiene enunciado.`); return; }
        if (q.options.length < 2) { setError(`La pregunta ${i + 1} necesita al menos 2 opciones.`); return; }
        if (q.options.some((o: any) => !o.text.trim())) { setError(`Hay opciones vacías en la pregunta ${i + 1}.`); return; }
        const correct = q.options.filter((o: any) => o.is_correct).length;
        if (correct < 1) { setError(`Marca la respuesta correcta de la pregunta ${i + 1}.`); return; }
        if (q.qtype === "single" && correct !== 1) { setError(`La pregunta ${i + 1} es de respuesta única.`); return; }
      }
    }
    setSaving(true);
    try {
      const payload: any = {
        title: stepForm.title, description: stepForm.description, category: stepForm.category,
        day_number: stepForm.day_number, estimated_minutes: stepForm.estimated_minutes,
      };
      if (stepForm.category === "documento") payload.document_id = stepForm.document_id;
      if (stepForm.category === "cuestionario") payload.questions = stepForm.questions;
      await api.createPlanTask(stepModal.planId!, payload);
      setStepModal({ open: false, planId: null });
      await Promise.all([loadTasks(stepModal.planId!), loadPlans()]);
    } catch (e: any) { setError(e.message || "No se pudo crear el paso."); }
    finally { setSaving(false); }
  };

  // ── Asignar ──
  const openAssign = (plan: any) => { setAssignUser(""); setError(""); setAssignModal({ open: true, plan }); };
  const doAssign = async () => {
    setError("");
    if (!assignUser) { setError("Selecciona un empleado."); return; }
    setSaving(true);
    try {
      await api.assignPlan(assignModal.plan.id, assignUser);
      setAssignModal({ open: false, plan: null });
    } catch (e: any) { setError(e.message || "No se pudo asignar."); }
    finally { setSaving(false); }
  };

  // ── Borrar ──
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setSaving(true); setError("");
    try {
      if (deleteTarget.kind === "plan") { await api.deletePlan(deleteTarget.id); await loadPlans(); }
      else { await api.deletePlanTask(deleteTarget.id); await Promise.all([loadTasks(deleteTarget.planId!), loadPlans()]); }
      setDeleteTarget(null);
    } catch (e: any) { setError(e.message || "No se pudo eliminar."); }
    finally { setSaving(false); }
  };

  // ── Mutadores del editor de cuestionario ──
  const setQuestions = (qs: any[]) => setStepForm({ ...stepForm, questions: qs });
  const addQuestion = () => setQuestions([...stepForm.questions, emptyQuestion()]);
  const removeQuestion = (qi: number) => setQuestions(stepForm.questions.filter((_: any, i: number) => i !== qi));
  const updateQuestion = (qi: number, patch: any) => setQuestions(stepForm.questions.map((q: any, i: number) => i === qi ? { ...q, ...patch } : q));
  const addOption = (qi: number) => updateQuestion(qi, { options: [...stepForm.questions[qi].options, { text: "", is_correct: false }] });
  const removeOption = (qi: number, oi: number) => updateQuestion(qi, { options: stepForm.questions[qi].options.filter((_: any, i: number) => i !== oi) });
  const updateOption = (qi: number, oi: number, patch: any) =>
    updateQuestion(qi, { options: stepForm.questions[qi].options.map((o: any, i: number) => i === oi ? { ...o, ...patch } : o) });
  const setCorrect = (qi: number, oi: number) => {
    const q = stepForm.questions[qi];
    if (q.qtype === "single") {
      updateQuestion(qi, { options: q.options.map((o: any, i: number) => ({ ...o, is_correct: i === oi })) });
    } else {
      updateOption(qi, oi, { is_correct: !q.options[oi].is_correct });
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="text-slate-400 text-sm">Cargando...</div></div>
  );

  const totalSteps = plans.reduce((a, p) => a + (p.task_count || 0), 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Planes de onboarding</h1>
          <p className="text-slate-400 text-sm mt-1">Plantillas de incorporación por cargo, con pasos y cuestionarios</p>
        </div>
        <button onClick={openPlanCreate} className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
          <Plus size={16} /> Nuevo plan
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Planes", value: plans.length },
          { label: "Auto-asignables", value: plans.filter((p) => p.auto_assign).length },
          { label: "Total pasos", value: totalSteps },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {plans.length === 0 ? (
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-10 text-center">
            <ClipboardList size={28} className="text-slate-600 mx-auto mb-2" />
            <p className="text-slate-400 text-sm">Aún no hay planes. Crea el primero.</p>
          </div>
        ) : plans.map((plan) => (
          <div key={plan.id} className={`bg-[#161b27] border rounded-2xl overflow-hidden ${plan.is_active ? "border-[#2a3349]" : "border-[#2a3349] opacity-60"}`}>
            <div className="flex items-center gap-4 px-6 py-4">
              <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center shrink-0 cursor-pointer" onClick={() => toggle(plan.id)}>
                <ClipboardList size={18} className="text-indigo-400" />
              </div>
              <div className="flex-1 min-w-0 cursor-pointer" onClick={() => toggle(plan.id)}>
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-white font-medium">{plan.name}</p>
                  {plan.auto_assign && (
                    <span className="flex items-center gap-1 text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                      <Zap size={10} /> Auto · {roleName(plan.target_role_id) || "sin cargo"}
                    </span>
                  )}
                  {!plan.is_active && (
                    <span className="text-xs bg-slate-500/10 text-slate-400 border border-slate-500/20 px-2 py-0.5 rounded-full">Inactivo</span>
                  )}
                </div>
                <p className="text-slate-500 text-xs mt-0.5 truncate">{plan.description}</p>
              </div>
              <div className="flex items-center gap-4 shrink-0 text-slate-400 text-sm">
                <span className="flex items-center gap-1.5"><Calendar size={14} /> {plan.duration_days}d</span>
                <span className="flex items-center gap-1.5"><ClipboardList size={14} /> {plan.task_count}</span>
                <span className="flex items-center gap-1.5 text-emerald-400/80"><Check size={14} /> {plan.pass_threshold}%</span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => openAssign(plan)} className="p-2 text-slate-500 hover:text-indigo-400 transition-colors" title="Asignar a empleado"><UserPlus size={16} /></button>
                <button onClick={() => toggleActive(plan)} className="p-2 text-slate-500 hover:text-amber-400 transition-colors text-xs" title={plan.is_active ? "Desactivar" : "Activar"}>{plan.is_active ? "On" : "Off"}</button>
                <button onClick={() => openPlanEdit(plan)} className="p-2 text-slate-500 hover:text-slate-200 transition-colors" title="Editar"><Pencil size={15} /></button>
                <button onClick={() => setDeleteTarget({ kind: "plan", id: plan.id, name: plan.name })} className="p-2 text-slate-500 hover:text-red-400 transition-colors" title="Eliminar"><Trash2 size={15} /></button>
                <button onClick={() => toggle(plan.id)} className="p-2 text-slate-500">{expanded === plan.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button>
              </div>
            </div>

            {expanded === plan.id && (
              <div className="border-t border-[#2a3349] px-6 py-4 bg-[#1e2536]/30">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">Pasos del plan</p>
                  <button onClick={() => openStep(plan.id)} className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs transition-colors">
                    <Plus size={12} /> Agregar paso
                  </button>
                </div>
                {!tasks[plan.id] ? (
                  <p className="text-slate-500 text-sm">Cargando pasos...</p>
                ) : tasks[plan.id].length === 0 ? (
                  <p className="text-slate-500 text-sm">No hay pasos. Agrega el primero.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {tasks[plan.id].map((task, idx) => {
                      const Icon = STEP_TYPES.find((s) => s.key === task.category)?.icon || ClipboardList;
                      return (
                        <div key={task.id} className="flex items-center gap-3 bg-[#161b27] border border-[#2a3349] rounded-xl px-4 py-3">
                          <span className="text-slate-600 text-xs w-5 text-center shrink-0">{idx + 1}</span>
                          <Icon size={15} className="text-slate-400 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-slate-200 text-sm truncate">{task.title}</p>
                            <p className="text-slate-600 text-xs flex items-center gap-2">
                              <span className="flex items-center gap-1"><Clock size={11} /> {task.estimated_minutes} min</span>
                              {task.category === "documento" && task.document_name && <span className="text-cyan-400/80 truncate">📄 {task.document_name}</span>}
                              {task.category === "cuestionario" && <span className="text-fuchsia-400/80">{task.questions.length} pregunta{task.questions.length === 1 ? "" : "s"}</span>}
                            </p>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[task.category] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>{labelOf(task.category)}</span>
                          <button onClick={() => setDeleteTarget({ kind: "step", id: task.id, name: task.title, planId: plan.id })} className="text-slate-600 hover:text-red-400 transition-colors"><Trash2 size={14} /></button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* ─── MODAL PLAN ─── */}
      {planModal.open && (
        <Modal title={planModal.edit ? "Editar plan" : "Nuevo plan"} onClose={() => !saving && setPlanModal({ open: false, edit: null })}>
          <div className="flex flex-col gap-4">
            {error && <ErrBox msg={error} />}
            <Field label="Nombre *"><input className="input" value={planForm.name} onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })} placeholder="Ej. Onboarding Desarrollador Junior" /></Field>
            <Field label="Descripción"><input className="input" value={planForm.description} onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })} placeholder="Breve descripción" /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Cargo objetivo">
                <select className="input" value={planForm.target_role_id} onChange={(e) => setPlanForm({ ...planForm, target_role_id: e.target.value })}>
                  <option value="">— Cualquiera —</option>
                  {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              </Field>
              <Field label="Departamento objetivo">
                <select className="input" value={planForm.target_department_id} onChange={(e) => setPlanForm({ ...planForm, target_department_id: e.target.value })}>
                  <option value="">— Cualquiera —</option>
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Duración (días)"><input type="number" min={1} className="input" value={planForm.duration_days} onChange={(e) => setPlanForm({ ...planForm, duration_days: parseInt(e.target.value) || 1 })} /></Field>
              <Field label="Nota mínima para aprobar (%)"><input type="number" min={0} max={100} className="input" value={planForm.pass_threshold} onChange={(e) => setPlanForm({ ...planForm, pass_threshold: Math.max(0, Math.min(100, parseInt(e.target.value) || 0)) })} /></Field>
            </div>
            <label className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer bg-[#0f1117] border border-[#2a3349] rounded-xl px-3 py-2.5">
              <input type="checkbox" checked={planForm.auto_assign} onChange={(e) => setPlanForm({ ...planForm, auto_assign: e.target.checked })} className="accent-indigo-500 mt-0.5" />
              <span><span className="flex items-center gap-1.5"><Zap size={14} className="text-indigo-400" /> Asignar automáticamente</span>
                <span className="text-slate-500 text-xs block mt-0.5">Se asignará solo a los empleados nuevos cuyo cargo sea el objetivo.</span></span>
            </label>
          </div>
          <ModalFooter onCancel={() => setPlanModal({ open: false, edit: null })} onSave={savePlan} saving={saving} saveLabel={planModal.edit ? "Guardar" : "Crear plan"} />
        </Modal>
      )}

      {/* ─── MODAL PASO ─── */}
      {stepModal.open && (
        <Modal title="Nuevo paso" wide onClose={() => !saving && setStepModal({ open: false, planId: null })}>
          <div className="flex flex-col gap-4">
            {error && <ErrBox msg={error} />}
            <Field label="Tipo de paso">
              <div className="grid grid-cols-5 gap-2">
                {STEP_TYPES.map((t) => (
                  <button key={t.key} onClick={() => setStepForm({ ...stepForm, category: t.key })}
                    className={`flex flex-col items-center gap-1 py-2.5 rounded-xl border text-xs transition-colors
                      ${stepForm.category === t.key ? "bg-indigo-500/10 border-indigo-500/40 text-indigo-300" : "bg-[#0f1117] border-[#2a3349] text-slate-400 hover:text-slate-200"}`}>
                    <t.icon size={16} /> {t.label}
                  </button>
                ))}
              </div>
            </Field>
            <Field label="Título *"><input className="input" value={stepForm.title} onChange={(e) => setStepForm({ ...stepForm, title: e.target.value })} placeholder="Ej. Leer el manual de empleados" /></Field>
            <Field label="Descripción"><input className="input" value={stepForm.description} onChange={(e) => setStepForm({ ...stepForm, description: e.target.value })} placeholder="Instrucciones para el empleado" /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Día"><input type="number" min={1} className="input" value={stepForm.day_number} onChange={(e) => setStepForm({ ...stepForm, day_number: parseInt(e.target.value) || 1 })} /></Field>
              <Field label="Tiempo estimado (min)"><input type="number" min={1} className="input" value={stepForm.estimated_minutes} onChange={(e) => setStepForm({ ...stepForm, estimated_minutes: parseInt(e.target.value) || 1 })} /></Field>
            </div>

            {stepForm.category === "documento" && (
              <Field label="Documento enlazado *">
                <select className="input" value={stepForm.document_id} onChange={(e) => setStepForm({ ...stepForm, document_id: e.target.value })}>
                  <option value="">Selecciona un documento</option>
                  {documents.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
                {documents.length === 0 && <p className="text-amber-400 text-xs mt-1">No hay documentos. Súbelos en el módulo Documentos.</p>}
              </Field>
            )}

            {stepForm.category === "cuestionario" && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">Preguntas</p>
                  <button onClick={addQuestion} className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs"><Plus size={12} /> Agregar pregunta</button>
                </div>
                {stepForm.questions.length === 0 && <p className="text-slate-500 text-sm">Agrega la primera pregunta.</p>}
                {stepForm.questions.map((q: any, qi: number) => (
                  <div key={qi} className="bg-[#0f1117] border border-[#2a3349] rounded-xl p-3 flex flex-col gap-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 text-xs">P{qi + 1}</span>
                      <input className="input flex-1" value={q.text} onChange={(e) => updateQuestion(qi, { text: e.target.value })} placeholder="Enunciado de la pregunta" />
                      <button onClick={() => removeQuestion(qi)} className="text-slate-600 hover:text-red-400"><Trash2 size={14} /></button>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <select className="input !w-auto !py-1.5 text-xs" value={q.qtype}
                        onChange={(e) => {
                          const qtype = e.target.value;
                          // al pasar a 'single' deja solo la primera correcta
                          let options = q.options;
                          if (qtype === "single") {
                            let seen = false;
                            options = q.options.map((o: any) => {
                              if (o.is_correct && !seen) { seen = true; return o; }
                              return { ...o, is_correct: false };
                            });
                          }
                          updateQuestion(qi, { qtype, options });
                        }}>
                        <option value="single">Respuesta única</option>
                        <option value="multiple">Respuesta múltiple</option>
                      </select>
                      <select className="input !w-auto !py-1.5 text-xs" value={q.category || ""} onChange={(e) => updateQuestion(qi, { category: e.target.value })}>
                        <option value="">Categoría (opcional)</option>
                        {["procesos", "rol", "cultura", "herramientas", "relaciones"].map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      {q.options.map((o: any, oi: number) => (
                        <div key={oi} className="flex items-center gap-2">
                          <button onClick={() => setCorrect(qi, oi)} title="Marcar como correcta"
                            className={`w-5 h-5 ${q.qtype === "single" ? "rounded-full" : "rounded-md"} border flex items-center justify-center shrink-0 transition-colors
                              ${o.is_correct ? "bg-emerald-500 border-emerald-500 text-white" : "border-[#2a3349] text-transparent hover:border-emerald-500/50"}`}>
                            <Check size={12} />
                          </button>
                          <input className="input flex-1 !py-1.5" value={o.text} onChange={(e) => updateOption(qi, oi, { text: e.target.value })} placeholder={`Opción ${oi + 1}`} />
                          {q.options.length > 2 && <button onClick={() => removeOption(qi, oi)} className="text-slate-600 hover:text-red-400"><X size={14} /></button>}
                        </div>
                      ))}
                      <button onClick={() => addOption(qi)} className="flex items-center gap-1 text-slate-500 hover:text-slate-300 text-xs w-fit mt-0.5"><Plus size={11} /> Opción</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <ModalFooter onCancel={() => setStepModal({ open: false, planId: null })} onSave={saveStep} saving={saving} saveLabel="Agregar paso" />
        </Modal>
      )}

      {/* ─── MODAL ASIGNAR ─── */}
      {assignModal.open && (
        <Modal title={`Asignar “${assignModal.plan?.name}”`} onClose={() => !saving && setAssignModal({ open: false, plan: null })}>
          <div className="flex flex-col gap-4">
            {error && <ErrBox msg={error} />}
            <p className="text-slate-400 text-sm">El empleado pasará a estado <span className="text-white">onboarding</span> y deberá completar todos los pasos.</p>
            <Field label="Empleado">
              <select className="input" value={assignUser} onChange={(e) => setAssignUser(e.target.value)}>
                <option value="">Selecciona un empleado</option>
                {employees.map((u) => <option key={u.id} value={u.id}>{u.full_name} — {u.role_name || "sin cargo"}</option>)}
              </select>
            </Field>
          </div>
          <ModalFooter onCancel={() => setAssignModal({ open: false, plan: null })} onSave={doAssign} saving={saving} saveLabel="Asignar plan" />
        </Modal>
      )}

      {/* ─── CONFIRMAR BORRADO ─── */}
      {deleteTarget && (
        <Modal title={`Eliminar ${deleteTarget.kind === "plan" ? "plan" : "paso"}`} onClose={() => !saving && setDeleteTarget(null)}>
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-center shrink-0"><AlertTriangle size={18} className="text-red-400" /></div>
              <p className="text-slate-400 text-sm mt-1">¿Eliminar <span className="text-white">“{deleteTarget.name}”</span>? Esta acción no se puede deshacer.</p>
            </div>
            {error && <ErrBox msg={error} />}
          </div>
          <ModalFooter onCancel={() => setDeleteTarget(null)} onSave={confirmDelete} saving={saving} saveLabel="Eliminar" danger />
        </Modal>
      )}
    </div>
  );
}

// ─── Componentes auxiliares ──────────────────────────────────────────────────
function Field({ label, children }: any) {
  return <div className="flex flex-col gap-1.5"><label className="text-slate-400 text-xs">{label}</label>{children}</div>;
}
function ErrBox({ msg }: { msg: string }) {
  return <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{msg}</div>;
}
function Modal({ title, children, onClose, wide }: any) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div className={`bg-[#161b27] border border-[#2a3349] rounded-2xl w-full ${wide ? "max-w-2xl" : "max-w-lg"} max-h-[90vh] overflow-y-auto`} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349] sticky top-0 bg-[#161b27]">
          <h2 className="text-white text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200 transition-colors"><X size={18} /></button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
function ModalFooter({ onCancel, onSave, saving, saveLabel, danger }: any) {
  return (
    <div className="flex items-center justify-end gap-3 pt-5 mt-1">
      <button onClick={onCancel} disabled={saving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">Cancelar</button>
      <button onClick={onSave} disabled={saving} className={`${danger ? "bg-red-500 hover:bg-red-600" : "bg-indigo-500 hover:bg-indigo-600"} disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors`}>
        {saving ? "Guardando..." : saveLabel}
      </button>
    </div>
  );
}
