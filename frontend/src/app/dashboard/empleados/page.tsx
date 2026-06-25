"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Plus, X, Pencil, History, KeyRound, Power, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";

function fmtDate(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleString("es-CO", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

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

const inputCls = "bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors w-full";
const labelCls = "text-slate-400 text-xs";

const emptyForm = {
  full_name: "",
  email: "",
  password: "",
  department_id: "",
  role_id: "",
  system_role: "empleado",
  status: "onboarding",
  start_date: "",
  onboarding_total_days: 15,
  // Datos de RR.HH.
  document_id: "",
  gender: "",
  birth_date: "",
  phone: "",
  address: "",
  marital_status: "",
  num_children: 0,
  contract_type: "",
  base_salary: 0,
  bank_name: "",
  bank_account: "",
};

export default function EmpleadosPage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("todos");
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [departments, setDepartments] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<any[]>([]);

  // Acciones rápidas de la tabla
  const [pwdTarget, setPwdTarget] = useState<any | null>(null);
  const [pwdValue, setPwdValue] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdDone, setPwdDone] = useState(false);
  const [pwdError, setPwdError] = useState("");
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const openPwd = (emp: any) => {
    setPwdTarget(emp); setPwdValue(""); setShowPwd(false); setPwdError(""); setPwdDone(false);
  };
  const savePwd = async () => {
    if (pwdValue.trim().length < 6) { setPwdError("La contraseña debe tener al menos 6 caracteres."); return; }
    setPwdSaving(true); setPwdError("");
    try {
      await api.changeUserPassword(pwdTarget.id, pwdValue.trim());
      setPwdDone(true);
      setTimeout(() => setPwdTarget(null), 1200);
    } catch (e: any) {
      setPwdError(e.message || "No se pudo cambiar la contraseña.");
    } finally {
      setPwdSaving(false);
    }
  };
  const toggleStatus = async (emp: any) => {
    const next = emp.status === "inactivo" ? "activo" : "inactivo";
    setTogglingId(emp.id);
    try {
      const updated = await api.updateUser(emp.id, { status: next });
      setEmployees((prev) => prev.map((e) => (e.id === emp.id ? { ...e, ...updated } : e)));
    } catch (e) { console.error(e); }
    finally { setTogglingId(null); }
  };

  const loadEmployees = async () => {
    const data = await api.getUsers();
    setEmployees(data);
  };

  useEffect(() => {
    const load = async () => {
      try {
        await loadEmployees();
      } catch {
        router.push("/login");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const loadCatalogs = async () => {
    try {
      const [depts, rls] = await Promise.all([api.getDepartments(), api.getRoles()]);
      setDepartments(depts);
      setRoles(rls);
    } catch {
      // si falla la carga de catálogos, el modal sigue usable sin selects poblados
    }
  };

  const openCreate = async () => {
    setMode("create");
    setEditingId(null);
    setHistory([]);
    setForm({ ...emptyForm });
    setError("");
    setShowModal(true);
    await loadCatalogs();
  };

  const openEdit = async (emp: any) => {
    setMode("edit");
    setEditingId(emp.id);
    setHistory([]);
    api.getUserHistory(emp.id).then(setHistory).catch(() => setHistory([]));
    setForm({
      ...emptyForm,
      full_name: emp.full_name ?? "",
      email: emp.email ?? "",
      password: "",
      department_id: emp.department_id ?? "",
      role_id: emp.role_id ?? "",
      system_role: emp.system_role ?? "empleado",
      status: emp.status ?? "onboarding",
      start_date: emp.start_date ?? "",
      onboarding_total_days: emp.onboarding_total_days ?? 15,
      document_id: emp.document_id ?? "",
      gender: emp.gender ?? "",
      birth_date: emp.birth_date ?? "",
      phone: emp.phone ?? "",
      address: emp.address ?? "",
      marital_status: emp.marital_status ?? "",
      num_children: emp.num_children ?? 0,
      contract_type: emp.contract_type ?? "",
      base_salary: emp.base_salary ?? 0,
      bank_name: emp.bank_name ?? "",
      bank_account: emp.bank_account ?? "",
    });
    setError("");
    setShowModal(true);
    await loadCatalogs();
  };

  const handleSave = async () => {
    setError("");
    if (!form.full_name.trim()) {
      setError("El nombre es obligatorio.");
      return;
    }
    if (mode === "create" && (!form.email.trim() || !form.password.trim())) {
      setError("Correo y contraseña son obligatorios.");
      return;
    }
    setSaving(true);

    const payload: any = {
      full_name: form.full_name,
      department_id: form.department_id || null,
      role_id: form.role_id || null,
      system_role: form.system_role,
      start_date: form.start_date || null,
      onboarding_total_days: Number(form.onboarding_total_days) || 15,
      document_id: form.document_id || null,
      gender: form.gender || null,
      birth_date: form.birth_date || null,
      phone: form.phone || null,
      address: form.address || null,
      marital_status: form.marital_status || null,
      num_children: Number(form.num_children) || 0,
      contract_type: form.contract_type || null,
      base_salary: Number(form.base_salary) || 0,
      bank_name: form.bank_name || null,
      bank_account: form.bank_account || null,
    };

    try {
      if (mode === "create") {
        await api.createUser({ ...payload, email: form.email, password: form.password });
      } else if (editingId) {
        await api.updateUser(editingId, { ...payload, status: form.status });
      }
      setShowModal(false);
      await loadEmployees();
    } catch (err: any) {
      setError(err.message || "No se pudo guardar el empleado.");
    } finally {
      setSaving(false);
    }
  };

  const filteredRoles = form.department_id
    ? roles.filter((r) => r.department_id === form.department_id)
    : roles;

  const filtered = employees.filter((emp) => {
    const matchSearch =
      emp.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      emp.email?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === "todos" || emp.status === filterStatus;
    return matchSearch && matchStatus;
  });

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Empleados</h1>
          <p className="text-slate-400 text-sm mt-1">
            {employees.length} empleados registrados
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
        >
          <Plus size={16} />
          Nuevo empleado
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Buscar empleado..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#161b27] border border-[#2a3349] text-white placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div className="flex items-center gap-2">
          {["todos", "onboarding", "activo", "inactivo"].map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors
                ${filterStatus === s
                  ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  : "bg-[#161b27] border border-[#2a3349] text-slate-400 hover:text-slate-200"
                }`}
            >
              {s === "todos" ? "Todos" : statusLabels[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3349] bg-[#1e2536]/50">
          <span className="col-span-4 text-slate-500 text-xs uppercase tracking-wider">Empleado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Rol sistema</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Estado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Progreso</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider text-right">Acciones</span>
        </div>

        {filtered.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-slate-500 text-sm">No se encontraron empleados</p>
          </div>
        ) : (
          filtered.map((emp) => (
            <div
              key={emp.id}
              className="grid grid-cols-12 gap-4 px-6 py-4 border-b border-[#2a3349] last:border-0 hover:bg-[#1e2536]/50 transition-colors items-center"
            >
              <div className="col-span-4 flex items-center gap-3">
                <div className="w-9 h-9 bg-indigo-500/20 border border-indigo-500/20 rounded-full flex items-center justify-center shrink-0">
                  <span className="text-indigo-400 text-xs font-semibold">
                    {emp.full_name?.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium truncate">{emp.full_name}</p>
                  <p className="text-slate-500 text-xs truncate">{emp.email}</p>
                </div>
              </div>

              <div className="col-span-2">
                <p className="text-slate-300 text-sm capitalize">{emp.system_role}</p>
              </div>

              <div className="col-span-2">
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[emp.status] || statusColors.inactivo}`}>
                  {statusLabels[emp.status] || emp.status}
                </span>
              </div>

              <div className="col-span-2">
                {emp.status === "onboarding" ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-indigo-500"
                        style={{
                          width: `${Math.round((emp.onboarding_day / emp.onboarding_total_days) * 100)}%`
                        }}
                      />
                    </div>
                    <span className="text-slate-400 text-xs">
                      {Math.round((emp.onboarding_day / emp.onboarding_total_days) * 100)}%
                    </span>
                  </div>
                ) : (
                  <span className="text-slate-500 text-xs">Completado</span>
                )}
              </div>

              <div className="col-span-2 flex justify-end gap-1">
                <button
                  onClick={() => openPwd(emp)}
                  title="Restablecer contraseña"
                  className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg"
                >
                  <KeyRound size={15} />
                </button>
                <button
                  onClick={() => toggleStatus(emp)}
                  disabled={togglingId === emp.id}
                  title={emp.status === "inactivo" ? "Activar empleado" : "Inactivar empleado"}
                  className={`p-1.5 rounded-lg transition-colors disabled:opacity-40 ${
                    emp.status === "inactivo"
                      ? "text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10"
                      : "text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                  }`}
                >
                  <Power size={15} />
                </button>
                <button
                  onClick={() => openEdit(emp)}
                  title="Editar empleado"
                  className="text-slate-500 hover:text-amber-400 transition-colors p-1.5 hover:bg-amber-500/10 rounded-lg"
                >
                  <Pencil size={15} />
                </button>
                <button
                  onClick={() => router.push(`/dashboard/empleados/${emp.id}`)}
                  title="Ver detalle"
                  className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg"
                >
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal crear / editar empleado */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => !saving && setShowModal(false)}
        >
          <div
            className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349] sticky top-0 bg-[#161b27] z-10">
              <h2 className="text-white text-lg font-semibold">
                {mode === "create" ? "Nuevo empleado" : "Editar empleado"}
              </h2>
              <button
                onClick={() => !saving && setShowModal(false)}
                className="text-slate-500 hover:text-slate-200 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <div className="px-6 py-5 flex flex-col gap-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">
                  {error}
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className={labelCls}>Nombre completo *</label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Ej. María González"
                  className={inputCls}
                />
              </div>

              {mode === "create" ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className={labelCls}>Correo *</label>
                    <input
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      placeholder="correo@empresa.co"
                      className={inputCls}
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className={labelCls}>Contraseña *</label>
                    <input
                      type="text"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="Contraseña temporal"
                      className={inputCls}
                    />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className={labelCls}>Correo</label>
                    <input type="email" value={form.email} disabled className={`${inputCls} opacity-60 cursor-not-allowed`} />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className={labelCls}>Estado</label>
                    <select
                      value={form.status}
                      onChange={(e) => setForm({ ...form, status: e.target.value })}
                      className={inputCls}
                    >
                      <option value="onboarding">En onboarding</option>
                      <option value="activo">Activo</option>
                      <option value="inactivo">Inactivo</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Departamento</label>
                  <select
                    value={form.department_id}
                    onChange={(e) => setForm({ ...form, department_id: e.target.value, role_id: "" })}
                    className={inputCls}
                  >
                    <option value="">Sin asignar</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Cargo / Rol</label>
                  <select
                    value={form.role_id}
                    onChange={(e) => setForm({ ...form, role_id: e.target.value })}
                    className={inputCls}
                  >
                    <option value="">Sin asignar</option>
                    {filteredRoles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Rol del sistema</label>
                  <select
                    value={form.system_role}
                    onChange={(e) => setForm({ ...form, system_role: e.target.value })}
                    className={inputCls}
                  >
                    <option value="empleado">Empleado</option>
                    <option value="rrhh">RR.HH.</option>
                    <option value="gerencia">Gerencia</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Fecha de ingreso</label>
                  <input
                    type="date"
                    value={form.start_date}
                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                    className={inputCls}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Días onboarding</label>
                  <input
                    type="number"
                    min={1}
                    value={form.onboarding_total_days}
                    onChange={(e) => setForm({ ...form, onboarding_total_days: Number(e.target.value) })}
                    className={inputCls}
                  />
                </div>
              </div>

              {/* ── Datos de RR.HH. ── */}
              <p className="text-slate-500 text-xs uppercase tracking-wider mt-2 pt-2 border-t border-[#2a3349]">
                Información de RR.HH.
              </p>

              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Cédula / Documento</label>
                  <input value={form.document_id} onChange={(e) => setForm({ ...form, document_id: e.target.value })} className={inputCls} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Género</label>
                  <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} className={inputCls}>
                    <option value="">Sin definir</option>
                    <option value="masculino">Masculino</option>
                    <option value="femenino">Femenino</option>
                    <option value="otro">Otro</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Fecha de nacimiento</label>
                  <input type="date" value={form.birth_date} onChange={(e) => setForm({ ...form, birth_date: e.target.value })} className={inputCls} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Estado civil</label>
                  <select value={form.marital_status} onChange={(e) => setForm({ ...form, marital_status: e.target.value })} className={inputCls}>
                    <option value="">Sin definir</option>
                    <option value="soltero">Soltero</option>
                    <option value="casado">Casado</option>
                    <option value="union_libre">Unión libre</option>
                    <option value="divorciado">Divorciado</option>
                    <option value="viudo">Viudo</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>N° de hijos</label>
                  <input type="number" min={0} value={form.num_children} onChange={(e) => setForm({ ...form, num_children: Number(e.target.value) })} className={inputCls} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Tipo de contrato</label>
                  <select value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })} className={inputCls}>
                    <option value="">Sin definir</option>
                    <option value="indefinido">Indefinido</option>
                    <option value="fijo">Término fijo</option>
                    <option value="obra_labor">Obra o labor</option>
                    <option value="prestacion_servicios">Prestación de servicios</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Teléfono</label>
                  <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className={inputCls} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Salario base (COP)</label>
                  <input type="number" min={0} value={form.base_salary} onChange={(e) => setForm({ ...form, base_salary: Number(e.target.value) })} className={inputCls} />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className={labelCls}>Dirección</label>
                <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className={inputCls} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>Banco</label>
                  <input value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} className={inputCls} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className={labelCls}>N° de cuenta</label>
                  <input value={form.bank_account} onChange={(e) => setForm({ ...form, bank_account: e.target.value })} className={inputCls} />
                </div>
              </div>

              {/* ── Historial de cambios (auditoría) ── */}
              {mode === "edit" && (
                <div className="mt-2 pt-3 border-t border-[#2a3349]">
                  <div className="flex items-center gap-2 mb-3">
                    <History size={14} className="text-slate-400" />
                    <p className="text-slate-500 text-xs uppercase tracking-wider">
                      Historial de modificaciones
                    </p>
                  </div>
                  {history.length === 0 ? (
                    <p className="text-slate-600 text-xs">Sin modificaciones registradas.</p>
                  ) : (
                    <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                      {history.map((h) => (
                        <div key={h.id} className="bg-[#0f1117] border border-[#2a3349] rounded-lg px-3 py-2 text-xs">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-slate-300 font-medium">{h.field_label || h.field}</span>
                            <span className="text-slate-600">{fmtDate(h.created_at)}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <span className="text-red-400/80 line-through">{h.old_value ?? "—"}</span>
                            <span className="text-slate-600">→</span>
                            <span className="text-emerald-400">{h.new_value ?? "—"}</span>
                          </div>
                          {h.changed_by_name && (
                            <p className="text-slate-600 mt-0.5">por {h.changed_by_name}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349] sticky bottom-0 bg-[#161b27]">
              <button
                onClick={() => setShowModal(false)}
                disabled={saving}
                className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
              >
                {saving ? "Guardando..." : mode === "create" ? "Crear empleado" : "Guardar cambios"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal restablecer contraseña */}
      {pwdTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !pwdSaving && setPwdTarget(null)}>
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
              <h2 className="text-white text-lg font-semibold flex items-center gap-2">
                <KeyRound size={18} className="text-indigo-400" /> Restablecer contraseña
              </h2>
              <button onClick={() => !pwdSaving && setPwdTarget(null)} className="text-slate-500 hover:text-slate-200"><X size={18} /></button>
            </div>
            <div className="px-6 py-5 flex flex-col gap-3">
              <p className="text-slate-400 text-sm">
                Nueva contraseña para <span className="text-white">{pwdTarget.full_name}</span>.
              </p>
              {pwdError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{pwdError}</div>}
              {pwdDone ? (
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg px-3 py-2">Contraseña actualizada ✓</div>
              ) : (
                <div className="relative">
                  <input
                    type={showPwd ? "text" : "password"}
                    value={pwdValue}
                    onChange={(e) => setPwdValue(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                    autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") savePwd(); }}
                    className="w-full bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl pl-3 pr-10 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                  <button type="button" onClick={() => setShowPwd((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              )}
            </div>
            {!pwdDone && (
              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349]">
                <button onClick={() => setPwdTarget(null)} disabled={pwdSaving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl disabled:opacity-40">Cancelar</button>
                <button onClick={savePwd} disabled={pwdSaving} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                  {pwdSaving ? "Guardando..." : "Restablecer"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}