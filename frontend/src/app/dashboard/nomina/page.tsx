"use client";

import { useState, useEffect } from "react";
import {
  Wallet, Users, TrendingUp, Baby, Plus, Trash2, X, FileText, CheckCircle2, Calendar, AlertTriangle, LogOut,
} from "lucide-react";
import { api } from "@/lib/api";

const COP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

// Días y proporción a pagar según el rango de fechas (mes = 30 días)
function dayInfo(start?: string, end?: string): string {
  if (!start || !end) return "Sin fechas: se paga el mes completo (30 días).";
  const d1 = new Date(start);
  const d2 = new Date(end);
  if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return "";
  let days = Math.round((d2.getTime() - d1.getTime()) / 86400000) + 1;
  if (days <= 0) days = 1;
  const pct = Math.round((days / 30) * 100);
  return `Se pagarán ${days} de 30 días (${pct}% del salario base).`;
}

const typeLabels: Record<string, string> = {
  devengado: "Devengado",
  deduccion: "Deducción",
  aporte_patronal: "Aporte patronal",
  provision: "Provisión",
};

const typeColors: Record<string, string> = {
  devengado: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  deduccion: "bg-red-500/10 text-red-400 border border-red-500/20",
  aporte_patronal: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  provision: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20",
};

const periodStatusColors: Record<string, string> = {
  borrador: "bg-slate-500/10 text-slate-400 border border-slate-500/20",
  procesada: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20",
  pagada: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
};

export default function NominaPage() {
  const [tab, setTab] = useState<"resumen" | "conceptos" | "novedades" | "periodos">("resumen");
  const [loading, setLoading] = useState(true);

  const [metrics, setMetrics] = useState<any>(null);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [monthly, setMonthly] = useState<any[]>([]);
  const [novelties, setNovelties] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);

  const [showConceptModal, setShowConceptModal] = useState(false);
  const [conceptForm, setConceptForm] = useState({ name: "", type: "devengado", calc_type: "fijo", value: 0, description: "" });

  const [showPeriodModal, setShowPeriodModal] = useState(false);
  const [periodForm, setPeriodForm] = useState({ name: "", period_start: "", period_end: "" });
  const [savingPeriod, setSavingPeriod] = useState(false);
  const [periodError, setPeriodError] = useState("");

  const [showSettlementModal, setShowSettlementModal] = useState(false);
  const [settlementForm, setSettlementForm] = useState({ user_id: "", name: "", period_start: "", period_end: "" });
  const [savingSettlement, setSavingSettlement] = useState(false);
  const [settlementError, setSettlementError] = useState("");

  const [showNoveltyModal, setShowNoveltyModal] = useState(false);
  const [noveltyForm, setNoveltyForm] = useState({ user_id: "", concept_name: "", type: "devengado", amount: 0, description: "" });
  const [noveltyError, setNoveltyError] = useState("");

  const [openPeriod, setOpenPeriod] = useState<any>(null);
  const [loadError, setLoadError] = useState("");

  // Carga tolerante: un endpoint que falle (ej. backend sin reiniciar) no rompe la página
  const safe = async <T,>(p: Promise<T>, fallback: T): Promise<T> => {
    try { return await p; } catch { return fallback; }
  };

  const loadAll = async () => {
    const [m, c, p, ms, nv, emps] = await Promise.all([
      safe(api.getPayrollMetrics(), null),
      safe(api.getConcepts(), []),
      safe(api.getPeriods(), []),
      safe(api.getMonthlySummary(), []),
      safe(api.getNovelties(), []),
      safe(api.getUsers(), []),
    ]);
    setMetrics(m);
    setConcepts(c);
    setPeriods(p);
    setMonthly(ms);
    setNovelties(nv);
    setEmployees((emps || []).filter((e: any) => e.status !== "inactivo"));
    if (!m && (!c || c.length === 0) && (!p || p.length === 0)) {
      setLoadError("No se pudo cargar la información de nómina. Verifica que el backend esté actualizado y reiniciado.");
    } else {
      setLoadError("");
    }
  };

  useEffect(() => {
    (async () => {
      try {
        await loadAll();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // ── Conceptos ──
  const saveConcept = async () => {
    if (!conceptForm.name.trim()) return;
    await api.createConcept({ ...conceptForm, value: Number(conceptForm.value) || 0 });
    setShowConceptModal(false);
    setConceptForm({ name: "", type: "devengado", calc_type: "fijo", value: 0, description: "" });
    setConcepts(await api.getConcepts());
  };

  const removeConcept = async (id: string) => {
    await api.deleteConcept(id);
    setConcepts(await api.getConcepts());
  };

  // ── Períodos ──
  const createPeriod = async () => {
    setPeriodError("");
    if (!periodForm.name.trim()) {
      setPeriodError("El nombre del período es obligatorio.");
      return;
    }
    setSavingPeriod(true);
    try {
      const month_key = periodForm.period_start ? periodForm.period_start.slice(0, 7) : undefined;
      await api.createPeriod({ ...periodForm, month_key });
      setShowPeriodModal(false);
      setPeriodForm({ name: "", period_start: "", period_end: "" });
      await loadAll();
    } catch (err: any) {
      setPeriodError(err.message || "No se pudo liquidar la nómina.");
    } finally {
      setSavingPeriod(false);
    }
  };

  // ── Liquidación por terminación (1 colaborador) ──
  const createSettlement = async () => {
    setSettlementError("");
    if (!settlementForm.user_id) {
      setSettlementError("Selecciona al colaborador a liquidar.");
      return;
    }
    setSavingSettlement(true);
    try {
      const month_key = settlementForm.period_start ? settlementForm.period_start.slice(0, 7) : undefined;
      await api.createSettlement({ ...settlementForm, month_key });
      setShowSettlementModal(false);
      setSettlementForm({ user_id: "", name: "", period_start: "", period_end: "" });
      await loadAll();
    } catch (err: any) {
      setSettlementError(err.message || "No se pudo liquidar la terminación.");
    } finally {
      setSavingSettlement(false);
    }
  };

  // ── Novedades ──
  const saveNovelty = async () => {
    setNoveltyError("");
    if (!noveltyForm.user_id) {
      setNoveltyError("Selecciona un colaborador.");
      return;
    }
    if (!noveltyForm.concept_name.trim()) {
      setNoveltyError("Indica el concepto de la novedad.");
      return;
    }
    try {
      await api.createNovelty({ ...noveltyForm, amount: Number(noveltyForm.amount) || 0 });
      setShowNoveltyModal(false);
      setNoveltyForm({ user_id: "", concept_name: "", type: "devengado", amount: 0, description: "" });
      setNovelties(await api.getNovelties());
    } catch (err: any) {
      setNoveltyError(err.message || "No se pudo registrar la novedad.");
    }
  };

  const removeNovelty = async (id: string) => {
    await api.deleteNovelty(id);
    setNovelties(await api.getNovelties());
  };

  const removePeriod = async (id: string) => {
    await api.deletePeriod(id);
    if (openPeriod?.id === id) setOpenPeriod(null);
    await loadAll();
  };

  const payPeriod = async (id: string) => {
    await api.payPeriod(id);
    await loadAll();
    if (openPeriod?.id === id) setOpenPeriod(await api.getPeriod(id));
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando nómina...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold flex items-center gap-2">
            <Wallet size={22} className="text-indigo-400" /> Nómina y RR.HH.
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Gestión de salarios, conceptos y liquidación de nómina
          </p>
        </div>
      </div>

      {loadError && (
        <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm rounded-xl px-4 py-3">
          <AlertTriangle size={16} className="shrink-0" />
          {loadError}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#2a3354]">
        {([
          ["resumen", "Resumen"],
          ["conceptos", "Conceptos"],
          ["novedades", "Novedades"],
          ["periodos", "Períodos"],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors
              ${tab === key
                ? "border-indigo-500 text-indigo-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── RESUMEN ── */}
      {tab === "resumen" && metrics && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard icon={Users} label="Empleados activos" value={metrics.headcount} color="text-indigo-400" />
            <MetricCard icon={Wallet} label="Costo nómina (base)" value={COP.format(metrics.total_payroll)} color="text-emerald-400" />
            <MetricCard icon={TrendingUp} label="Salario promedio" value={COP.format(metrics.avg_salary)} color="text-amber-400" />
            <MetricCard icon={Baby} label="Hijos (beneficiarios)" value={metrics.total_children} color="text-pink-400" />
          </div>

          {/* Nómina liquidada por mes (agrupa quincenas) */}
          <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <Calendar size={16} className="text-indigo-400" />
              <p className="text-white text-sm font-medium">Nómina liquidada por mes</p>
            </div>
            {monthly.length === 0 ? (
              <p className="text-slate-500 text-xs">Aún no hay períodos liquidados.</p>
            ) : (
              <div className="overflow-hidden rounded-xl border border-[#2a3354]">
                <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-[#1c2540]/50 text-slate-500 text-xs uppercase tracking-wider">
                  <span className="col-span-3">Mes</span>
                  <span className="col-span-2 text-center">Liquidaciones</span>
                  <span className="col-span-2 text-right">Devengado</span>
                  <span className="col-span-2 text-right">Deducciones</span>
                  <span className="col-span-3 text-right">Neto del mes</span>
                </div>
                {monthly.map((m) => (
                  <div key={m.month} className="grid grid-cols-12 gap-2 px-4 py-2.5 border-t border-[#2a3354] text-sm items-center">
                    <span className="col-span-3 text-white font-medium">{m.month}</span>
                    <span className="col-span-2 text-center text-slate-400">{m.periods}</span>
                    <span className="col-span-2 text-right text-emerald-400">{COP.format(m.total_devengado)}</span>
                    <span className="col-span-2 text-right text-red-400">{COP.format(m.total_deduccion)}</span>
                    <span className="col-span-3 text-right text-white font-semibold">{COP.format(m.total_neto)}</span>
                  </div>
                ))}
              </div>
            )}
            <p className="text-slate-600 text-xs mt-3">
              Si pagas por quincena, cada mes suma sus dos liquidaciones para mostrar el total mensual real.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <DistroCard title="Por departamento" data={metrics.by_department} />
            <DistroCard title="Por género" data={metrics.by_gender} />
            <DistroCard title="Por tipo de contrato" data={metrics.by_contract} />
            <DistroCard title="Por estado" data={metrics.by_status} />
          </div>
        </div>
      )}

      {/* ── CONCEPTOS ── */}
      {tab === "conceptos" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <p className="text-slate-400 text-sm">{concepts.length} conceptos definidos</p>
            <button
              onClick={() => setShowConceptModal(true)}
              className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
            >
              <Plus size={16} /> Nuevo concepto
            </button>
          </div>

          <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl overflow-hidden">
            <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3354] bg-[#1c2540]/50 text-slate-500 text-xs uppercase tracking-wider">
              <span className="col-span-4">Concepto</span>
              <span className="col-span-3">Tipo</span>
              <span className="col-span-3">Cálculo</span>
              <span className="col-span-2 text-right">Acciones</span>
            </div>
            {concepts.length === 0 ? (
              <div className="px-6 py-12 text-center text-slate-500 text-sm">
                Aún no has definido conceptos de nómina.
              </div>
            ) : (
              concepts.map((c) => (
                <div key={c.id} className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3354] last:border-0 items-center">
                  <div className="col-span-4">
                    <p className="text-white text-sm font-medium">{c.name}</p>
                    {c.description && <p className="text-slate-500 text-xs truncate">{c.description}</p>}
                  </div>
                  <div className="col-span-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${typeColors[c.type]}`}>
                      {typeLabels[c.type]}
                    </span>
                  </div>
                  <div className="col-span-3 text-slate-300 text-sm">
                    {c.calc_type === "porcentaje" ? `${c.value}% del salario` : COP.format(c.value)}
                  </div>
                  <div className="col-span-2 flex justify-end">
                    <button
                      onClick={() => removeConcept(c.id)}
                      className="text-slate-500 hover:text-red-400 p-1.5 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── NOVEDADES ── */}
      {tab === "novedades" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <p className="text-slate-400 text-sm">
              Ajustes individuales por colaborador que se aplican en la próxima liquidación
            </p>
            <button
              onClick={() => { setNoveltyError(""); setShowNoveltyModal(true); }}
              className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
            >
              <Plus size={16} /> Nueva novedad
            </button>
          </div>

          {novelties.length === 0 ? (
            <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl px-6 py-12 text-center text-slate-500 text-sm">
              No hay novedades registradas.
            </div>
          ) : (
            <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl overflow-hidden">
              <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3354] bg-[#1c2540]/50 text-slate-500 text-xs uppercase tracking-wider">
                <span className="col-span-3">Colaborador</span>
                <span className="col-span-3">Concepto</span>
                <span className="col-span-2">Tipo</span>
                <span className="col-span-2 text-right">Monto</span>
                <span className="col-span-2 text-right">Estado</span>
              </div>
              {novelties.map((n) => (
                <div key={n.id} className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3354] last:border-0 items-center">
                  <div className="col-span-3">
                    <p className="text-white text-sm">{n.employee_name}</p>
                  </div>
                  <div className="col-span-3">
                    <p className="text-slate-300 text-sm">{n.concept_name}</p>
                    {n.description && <p className="text-slate-500 text-xs truncate">{n.description}</p>}
                  </div>
                  <div className="col-span-2">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      n.type === "deduccion" ? "bg-red-500/10 text-red-400 border border-red-500/20"
                      : n.type === "retiro" ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    }`}>
                      {n.type === "deduccion" ? "Deducción" : n.type === "retiro" ? "Retiro" : "Devengado"}
                    </span>
                  </div>
                  <div className="col-span-2 text-right text-slate-300 text-sm">{COP.format(n.amount)}</div>
                  <div className="col-span-2 flex items-center justify-end gap-2">
                    {n.applied ? (
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <CheckCircle2 size={13} className="text-emerald-400" /> Aplicada
                      </span>
                    ) : (
                      <>
                        <span className="text-xs text-amber-400">Pendiente</span>
                        <button onClick={() => removeNovelty(n.id)} className="text-slate-500 hover:text-red-400 p-1 transition-colors">
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── PERÍODOS ── */}
      {tab === "periodos" && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <p className="text-slate-400 text-sm">{periods.length} períodos liquidados</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setSettlementError(""); setShowSettlementModal(true); }}
                className="flex items-center gap-2 bg-orange-500/10 border border-orange-500/30 hover:bg-orange-500/20 text-orange-400 text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
              >
                <LogOut size={16} /> Liquidar terminación
              </button>
              <button
                onClick={() => { setPeriodError(""); setShowPeriodModal(true); }}
                className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
              >
                <Plus size={16} /> Liquidar nómina
              </button>
            </div>
          </div>

          {periods.length === 0 ? (
            <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl px-6 py-12 text-center text-slate-500 text-sm">
              No hay períodos de nómina. Crea uno para liquidar a los empleados.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {periods.map((p) => (
                <div key={p.id} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5 flex flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-white font-semibold">{p.name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          p.kind === "terminacion"
                            ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                            : "bg-[#2a3354] text-slate-400"
                        }`}>
                          {p.kind === "terminacion" ? "Terminación" : "Nómina"}
                        </span>
                      </div>
                      <p className="text-slate-500 text-xs">
                        {p.employee_count} {p.employee_count === 1 ? "empleado" : "empleados"} · {p.days ?? 30} días · {p.period_start || "—"} a {p.period_end || "—"}
                      </p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${periodStatusColors[p.status]}`}>
                      {p.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <Stat label="Devengado" value={COP.format(p.total_devengado)} className="text-emerald-400" />
                    <Stat label="Deducciones" value={COP.format(p.total_deduccion)} className="text-red-400" />
                    <Stat label="Aportes/Prov." value={COP.format(p.total_aportes)} className="text-amber-400" />
                    <Stat label="Neto a pagar" value={COP.format(p.total_neto)} className="text-white font-semibold" />
                  </div>
                  <div className="flex items-center gap-2 pt-2 border-t border-[#2a3354]">
                    <button
                      onClick={async () => setOpenPeriod(await api.getPeriod(p.id))}
                      className="flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 text-xs font-medium"
                    >
                      <FileText size={14} /> Ver comprobantes
                    </button>
                    <div className="flex-1" />
                    {p.status !== "pagada" && (
                      <button
                        onClick={() => payPeriod(p.id)}
                        className="flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 text-xs font-medium"
                      >
                        <CheckCircle2 size={14} /> Marcar pagada
                      </button>
                    )}
                    <button
                      onClick={() => removePeriod(p.id)}
                      className="text-slate-500 hover:text-red-400 p-1 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal concepto */}
      {showConceptModal && (
        <Modal title="Nuevo concepto" onClose={() => setShowConceptModal(false)}>
          <div className="flex flex-col gap-4">
            <Field label="Nombre del concepto">
              <input
                value={conceptForm.name}
                onChange={(e) => setConceptForm({ ...conceptForm, name: e.target.value })}
                placeholder="Ej. Auxilio de transporte"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo">
                <select value={conceptForm.type} onChange={(e) => setConceptForm({ ...conceptForm, type: e.target.value })} className="input">
                  <option value="devengado">Devengado (suma)</option>
                  <option value="deduccion">Deducción (resta)</option>
                  <option value="aporte_patronal">Aporte patronal</option>
                  <option value="provision">Provisión</option>
                </select>
              </Field>
              <Field label="Cálculo">
                <select value={conceptForm.calc_type} onChange={(e) => setConceptForm({ ...conceptForm, calc_type: e.target.value })} className="input">
                  <option value="fijo">Monto fijo</option>
                  <option value="porcentaje">% del salario</option>
                </select>
              </Field>
            </div>
            <Field label={conceptForm.calc_type === "porcentaje" ? "Porcentaje (%)" : "Monto (COP)"}>
              <input
                type="number"
                value={conceptForm.value}
                onChange={(e) => setConceptForm({ ...conceptForm, value: Number(e.target.value) })}
                className="input"
              />
            </Field>
            <Field label="Descripción (opcional)">
              <input
                value={conceptForm.description}
                onChange={(e) => setConceptForm({ ...conceptForm, description: e.target.value })}
                className="input"
              />
            </Field>
          </div>
          <ModalFooter onCancel={() => setShowConceptModal(false)} onSave={saveConcept} saveLabel="Crear concepto" />
        </Modal>
      )}

      {/* Modal liquidar período */}
      {showPeriodModal && (
        <Modal title="Liquidar nómina" onClose={() => setShowPeriodModal(false)}>
          <div className="flex flex-col gap-4">
            {periodError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{periodError}</div>
            )}
            <p className="text-slate-400 text-xs">
              Se generará un comprobante para cada empleado activo con salario asignado,
              aplicando los conceptos activos y las novedades pendientes.
            </p>
            <Field label="Nombre del período">
              <input
                value={periodForm.name}
                onChange={(e) => setPeriodForm({ ...periodForm, name: e.target.value })}
                placeholder="Ej. Junio 2026 — 1ª quincena"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Desde">
                <input type="date" value={periodForm.period_start} onChange={(e) => setPeriodForm({ ...periodForm, period_start: e.target.value })} className="input" />
              </Field>
              <Field label="Hasta">
                <input type="date" value={periodForm.period_end} onChange={(e) => setPeriodForm({ ...periodForm, period_end: e.target.value })} className="input" />
              </Field>
            </div>
            <p className="text-slate-500 text-xs -mt-1">
              {dayInfo(periodForm.period_start, periodForm.period_end)}
            </p>
          </div>
          <ModalFooter onCancel={() => setShowPeriodModal(false)} onSave={createPeriod} saveLabel={savingPeriod ? "Liquidando..." : "Liquidar"} saving={savingPeriod} />
        </Modal>
      )}

      {/* Modal liquidación por terminación */}
      {showSettlementModal && (
        <Modal title="Liquidación por terminación" onClose={() => setShowSettlementModal(false)}>
          <div className="flex flex-col gap-4">
            {settlementError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{settlementError}</div>
            )}
            <div className="flex items-start gap-2 bg-orange-500/10 border border-orange-500/20 text-orange-400 text-xs rounded-lg px-3 py-2">
              <LogOut size={14} className="shrink-0 mt-0.5" />
              <span>Se liquidará solo a este colaborador y quedará <b>inactivo</b> automáticamente.</span>
            </div>
            <Field label="Colaborador">
              <select
                value={settlementForm.user_id}
                onChange={(e) => setSettlementForm({ ...settlementForm, user_id: e.target.value })}
                className="input"
              >
                <option value="">Selecciona un empleado</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>{e.full_name}</option>
                ))}
              </select>
            </Field>
            <Field label="Nombre de la liquidación (opcional)">
              <input
                value={settlementForm.name}
                onChange={(e) => setSettlementForm({ ...settlementForm, name: e.target.value })}
                placeholder="Ej. Liquidación final"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Desde">
                <input type="date" value={settlementForm.period_start} onChange={(e) => setSettlementForm({ ...settlementForm, period_start: e.target.value })} className="input" />
              </Field>
              <Field label="Hasta">
                <input type="date" value={settlementForm.period_end} onChange={(e) => setSettlementForm({ ...settlementForm, period_end: e.target.value })} className="input" />
              </Field>
            </div>
            <p className="text-slate-500 text-xs -mt-1">
              {dayInfo(settlementForm.period_start, settlementForm.period_end)} Para pagar un solo día, usa la misma fecha en ambos campos.
            </p>
          </div>
          <ModalFooter onCancel={() => setShowSettlementModal(false)} onSave={createSettlement} saveLabel={savingSettlement ? "Liquidando..." : "Liquidar y retirar"} saving={savingSettlement} />
        </Modal>
      )}

      {/* Modal nueva novedad */}
      {showNoveltyModal && (
        <Modal title="Nueva novedad individual" onClose={() => setShowNoveltyModal(false)}>
          <div className="flex flex-col gap-4">
            {noveltyError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{noveltyError}</div>
            )}
            <Field label="Colaborador">
              <select
                value={noveltyForm.user_id}
                onChange={(e) => setNoveltyForm({ ...noveltyForm, user_id: e.target.value })}
                className="input"
              >
                <option value="">Selecciona un empleado</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>{e.full_name}</option>
                ))}
              </select>
            </Field>
            <Field label="Concepto">
              <input
                value={noveltyForm.concept_name}
                onChange={(e) => setNoveltyForm({ ...noveltyForm, concept_name: e.target.value })}
                placeholder="Ej. Bonificación extra, Descuento préstamo, Liquidación"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo">
                <select
                  value={noveltyForm.type}
                  onChange={(e) => setNoveltyForm({ ...noveltyForm, type: e.target.value })}
                  className="input"
                >
                  <option value="devengado">Devengado (suma)</option>
                  <option value="deduccion">Deducción (resta)</option>
                  <option value="retiro">Retiro (liquidación + inactiva)</option>
                </select>
              </Field>
              <Field label="Monto (COP)">
                <input
                  type="number"
                  value={noveltyForm.amount}
                  onChange={(e) => setNoveltyForm({ ...noveltyForm, amount: Number(e.target.value) })}
                  className="input"
                />
              </Field>
            </div>
            {noveltyForm.type === "retiro" && (
              <p className="text-orange-400/80 text-xs -mt-2">
                El retiro paga el monto como liquidación final y marca al colaborador como inactivo
                tras la próxima liquidación.
              </p>
            )}
            <Field label="Descripción (opcional)">
              <input
                value={noveltyForm.description}
                onChange={(e) => setNoveltyForm({ ...noveltyForm, description: e.target.value })}
                className="input"
              />
            </Field>
          </div>
          <ModalFooter onCancel={() => setShowNoveltyModal(false)} onSave={saveNovelty} saveLabel="Registrar novedad" />
        </Modal>
      )}

      {/* Modal detalle período (comprobantes individuales) */}
      {openPeriod && (
        <Modal title={`Comprobantes — ${openPeriod.name}`} wide onClose={() => setOpenPeriod(null)}>
          <div className="flex items-center gap-2 mb-3 text-xs">
            <span className={`px-2 py-0.5 rounded-full ${
              openPeriod.kind === "terminacion"
                ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                : "bg-[#2a3354] text-slate-400"
            }`}>
              {openPeriod.kind === "terminacion" ? "Terminación" : "Nómina"}
            </span>
            <span className="text-slate-500">
              {openPeriod.days ?? 30} días liquidados · {openPeriod.period_start || "—"} a {openPeriod.period_end || "—"}
            </span>
          </div>
          <div className="flex flex-col gap-3 max-h-[60vh] overflow-y-auto">
            {(openPeriod.payslips || []).map((s: any) => (
              <div key={s.id} className="bg-[#0f1629] border border-[#2a3354] rounded-xl p-4">
                <div className="flex items-start justify-between mb-1">
                  <div>
                    <p className="text-white text-sm font-medium">{s.employee_name}</p>
                    <p className="text-slate-500 text-xs">
                      {[s.employee_role, s.employee_document].filter(Boolean).join(" · ") || "—"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-white text-sm font-semibold">{COP.format(s.net_pay)}</p>
                    <p className="text-slate-500 text-xs">neto a pagar</p>
                  </div>
                </div>

                {s.days != null && s.monthly_salary ? (
                  <p className="text-slate-500 text-xs mb-2">
                    Salario mensual {COP.format(s.monthly_salary)} · liquidado {s.days}/30 días = {COP.format(s.base_salary)}
                  </p>
                ) : null}

                <div className="flex flex-col gap-1 pt-2 border-t border-[#2a3354]">
                  {(s.items || []).map((it: any) => (
                    <div key={it.id} className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          it.type === "deduccion" ? "bg-red-400" :
                          it.type === "devengado" ? "bg-emerald-400" :
                          it.type === "aporte_patronal" ? "bg-amber-400" : "bg-indigo-400"
                        }`} />
                        {it.concept_name}
                      </span>
                      <span className={it.type === "deduccion" ? "text-red-400" : "text-slate-300"}>
                        {it.type === "deduccion" ? "-" : ""}{COP.format(it.amount)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between gap-4 mt-2 pt-2 border-t border-[#2a3354] text-xs">
                  <span className="text-emerald-400">Devengado {COP.format(s.total_devengado)}</span>
                  <span className="text-red-400">Deducciones {COP.format(s.total_deduccion)}</span>
                  <span className="text-amber-400">Aportes {COP.format(s.total_aportes)}</span>
                </div>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  );
}

// ─── Subcomponentes ─────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, color }: any) {
  return (
    <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={16} className={color} />
        <span className="text-slate-400 text-xs">{label}</span>
      </div>
      <p className="text-white text-xl font-semibold">{value}</p>
    </div>
  );
}

function DistroCard({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data || {});
  const total = entries.reduce((a, [, v]) => a + v, 0) || 1;
  return (
    <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5">
      <p className="text-white text-sm font-medium mb-4">{title}</p>
      <div className="flex flex-col gap-3">
        {entries.length === 0 && <p className="text-slate-500 text-xs">Sin datos</p>}
        {entries.map(([k, v]) => (
          <div key={k}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400 capitalize">{k.replace(/_/g, " ")}</span>
              <span className="text-slate-300">{v}</span>
            </div>
            <div className="h-1.5 bg-[#2a3354] rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(v / total) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value, className = "" }: any) {
  return (
    <div>
      <p className="text-slate-500 text-xs">{label}</p>
      <p className={`text-sm ${className}`}>{value}</p>
    </div>
  );
}

function Field({ label, children }: any) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-slate-400 text-xs">{label}</label>
      {children}
    </div>
  );
}

function Modal({ title, children, onClose, wide }: any) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div
        className={`bg-[#161e33] border border-[#2a3354] rounded-2xl w-full ${wide ? "max-w-2xl" : "max-w-lg"} max-h-[90vh] overflow-y-auto`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3354]">
          <h2 className="text-white text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function ModalFooter({ onCancel, onSave, saveLabel, saving }: any) {
  return (
    <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-[#2a3354]">
      <button onClick={onCancel} disabled={saving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">
        Cancelar
      </button>
      <button onClick={onSave} disabled={saving} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
        {saveLabel}
      </button>
    </div>
  );
}
