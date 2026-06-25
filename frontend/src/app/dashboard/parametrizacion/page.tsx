"use client";

import { useState, useEffect } from "react";
import {
  Building2, Briefcase, Tags, Shield, Crown, Plus, ChevronDown, ChevronUp,
  X, Trash2, Users, Lock, AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";

const COLORS = ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#ef4444"];
const SENIORITY = [
  { level: 1, label: "Junior" },
  { level: 2, label: "Mid" },
  { level: 3, label: "Senior" },
  { level: 4, label: "Lead" },
];

const categoryColors: Record<string, string> = {
  procesos: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  rol: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  cultura: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  herramientas: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  relaciones: "bg-pink-500/10 text-pink-400 border border-pink-500/20",
};

const emptyDept = { name: "", description: "", color: "#6366f1", is_rrhh: false, is_gerencia: false };
const emptyRole = { name: "", department_id: "", description: "", seniority_level: 1, seniority_label: "Junior" };

type Tab = "departamentos" | "cargos" | "categorias";

export default function ParametrizacionPage() {
  const [tab, setTab] = useState<Tab>("departamentos");

  const [departments, setDepartments] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Modales de creación
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [deptForm, setDeptForm] = useState({ ...emptyDept });
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [roleForm, setRoleForm] = useState({ ...emptyRole });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  // Modal de borrado (reutilizable para departamentos y cargos)
  const [deleteTarget, setDeleteTarget] = useState<{ kind: "dept" | "role"; id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const loadAll = async () => {
    const [deps, rls, usrs, cats] = await Promise.all([
      api.getDepartments(),
      api.getRoles(),
      api.getUsers().catch(() => []),
      api.getCategories().catch(() => ({ categories: [] })),
    ]);
    setDepartments(deps);
    setRoles(rls);
    setUsers(usrs);
    setCategories(cats?.categories || []);
  };

  useEffect(() => {
    (async () => {
      try {
        await loadAll();
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Conteos derivados
  const rolesByDept = (deptId: string) => roles.filter((r) => r.department_id === deptId);
  const empCountByDept = (deptId: string) => users.filter((u) => u.department_id === deptId).length;
  const empCountByRole = (roleId: string) => users.filter((u) => u.role_id === roleId).length;
  const deptName = (deptId: string) => departments.find((d) => d.id === deptId)?.name || "—";

  // ─── Crear departamento ──────────────────────────────────────────────────
  const openDeptModal = () => {
    setDeptForm({ ...emptyDept });
    setFormError("");
    setShowDeptModal(true);
  };
  const createDept = async () => {
    setFormError("");
    if (!deptForm.name.trim()) {
      setFormError("El nombre del departamento es obligatorio.");
      return;
    }
    setSaving(true);
    try {
      await api.createDepartment(deptForm);
      setShowDeptModal(false);
      await loadAll();
    } catch (err: any) {
      setFormError(err.message || "No se pudo crear el departamento.");
    } finally {
      setSaving(false);
    }
  };

  // ─── Crear cargo ─────────────────────────────────────────────────────────
  const openRoleModal = () => {
    if (departments.length === 0) {
      setTab("departamentos");
      return;
    }
    setRoleForm({ ...emptyRole, department_id: departments[0].id });
    setFormError("");
    setShowRoleModal(true);
  };
  const createRole = async () => {
    setFormError("");
    if (!roleForm.name.trim()) {
      setFormError("El nombre del cargo es obligatorio.");
      return;
    }
    if (!roleForm.department_id) {
      setFormError("Selecciona un departamento.");
      return;
    }
    setSaving(true);
    try {
      await api.createRole(roleForm);
      setShowRoleModal(false);
      await loadAll();
    } catch (err: any) {
      setFormError(err.message || "No se pudo crear el cargo.");
    } finally {
      setSaving(false);
    }
  };

  // ─── Borrar (departamento o cargo) ───────────────────────────────────────
  const askDelete = (kind: "dept" | "role", id: string, name: string) => {
    setDeleteError("");
    setDeleteTarget({ kind, id, name });
  };
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError("");
    try {
      if (deleteTarget.kind === "dept") await api.deleteDepartment(deleteTarget.id);
      else await api.deleteRole(deleteTarget.id);
      setDeleteTarget(null);
      await loadAll();
    } catch (err: any) {
      setDeleteError(err.message || "No se pudo eliminar.");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando...</div>
    </div>
  );

  const tabs: { key: Tab; label: string; icon: any }[] = [
    { key: "departamentos", label: "Departamentos", icon: Building2 },
    { key: "cargos", label: "Cargos", icon: Briefcase },
    { key: "categorias", label: "Categorías", icon: Tags },
  ];

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Parametrización de empresa</h1>
          <p className="text-slate-400 text-sm mt-1">
            Define la estructura de tu organización: departamentos, cargos y categorías
          </p>
        </div>
        {tab === "departamentos" && (
          <button onClick={openDeptModal} className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
            <Plus size={16} /> Nuevo departamento
          </button>
        )}
        {tab === "cargos" && (
          <button onClick={openRoleModal} className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
            <Plus size={16} /> Nuevo cargo
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#161b27] border border-[#2a3349] rounded-xl p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors
              ${tab === t.key ? "bg-indigo-500/15 text-indigo-400" : "text-slate-400 hover:text-slate-200"}`}
          >
            <t.icon size={15} /> {t.label}
          </button>
        ))}
      </div>

      {/* ─── TAB DEPARTAMENTOS ─────────────────────────────────────────────── */}
      {tab === "departamentos" && (
        <div className="flex flex-col gap-3">
          {departments.length === 0 ? (
            <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-10 text-center">
              <Building2 size={28} className="text-slate-600 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">Aún no hay departamentos. Crea el primero.</p>
            </div>
          ) : (
            departments.map((dept) => {
              const deptRoles = rolesByDept(dept.id);
              return (
                <div key={dept.id} className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
                  <div className="flex items-center gap-4 px-6 py-4">
                    <div
                      className="flex items-center gap-4 flex-1 cursor-pointer"
                      onClick={() => setExpanded(expanded === dept.id ? null : dept.id)}
                    >
                      <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: dept.color || "#6366f1" }} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-white font-medium">{dept.name}</p>
                          {dept.is_rrhh && (
                            <span className="flex items-center gap-1 text-xs bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5 rounded-full">
                              <Shield size={10} /> RR.HH.
                            </span>
                          )}
                          {dept.is_gerencia && (
                            <span className="flex items-center gap-1 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
                              <Crown size={10} /> Gerencia
                            </span>
                          )}
                        </div>
                        {dept.description && <p className="text-slate-500 text-xs mt-0.5">{dept.description}</p>}
                      </div>
                    </div>
                    <span className="text-slate-500 text-xs flex items-center gap-1.5">
                      <Briefcase size={12} /> {deptRoles.length}
                      <Users size={12} className="ml-2" /> {empCountByDept(dept.id)}
                    </span>
                    <button
                      onClick={() => askDelete("dept", dept.id, dept.name)}
                      className="text-slate-500 hover:text-red-400 transition-colors"
                      title="Eliminar departamento"
                    >
                      <Trash2 size={16} />
                    </button>
                    <button
                      onClick={() => setExpanded(expanded === dept.id ? null : dept.id)}
                      className="text-slate-500"
                    >
                      {expanded === dept.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>

                  {expanded === dept.id && (
                    <div className="border-t border-[#2a3349] px-6 py-4 bg-[#1e2536]/30">
                      <p className="text-slate-400 text-xs uppercase tracking-wider mb-3">
                        Cargos del departamento
                      </p>
                      {deptRoles.length === 0 ? (
                        <p className="text-slate-500 text-sm">Sin cargos. Créalos en la pestaña “Cargos”.</p>
                      ) : (
                        <div className="flex flex-col gap-2">
                          {deptRoles.map((r) => (
                            <div key={r.id} className="flex items-center gap-3 bg-[#161b27] border border-[#2a3349] rounded-xl px-3 py-2">
                              <Briefcase size={14} className="text-indigo-400 shrink-0" />
                              <span className="text-white text-sm flex-1">{r.name}</span>
                              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/20">
                                {r.seniority_label}
                              </span>
                              <span className="text-slate-500 text-xs flex items-center gap-1">
                                <Users size={11} /> {empCountByRole(r.id)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* ─── TAB CARGOS ────────────────────────────────────────────────────── */}
      {tab === "cargos" && (
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
          {roles.length === 0 ? (
            <div className="p-10 text-center">
              <Briefcase size={28} className="text-slate-600 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">Aún no hay cargos definidos.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3349] bg-[#1e2536]/50">
                <span className="col-span-4 text-slate-500 text-xs uppercase tracking-wider">Cargo</span>
                <span className="col-span-3 text-slate-500 text-xs uppercase tracking-wider">Departamento</span>
                <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Seniority</span>
                <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Empleados</span>
                <span className="col-span-1"></span>
              </div>
              {roles.map((r) => (
                <div key={r.id} className="grid grid-cols-12 gap-4 px-6 py-3.5 border-b border-[#2a3349] last:border-0 items-center hover:bg-[#1e2536]/40 transition-colors">
                  <div className="col-span-4 min-w-0">
                    <p className="text-white text-sm font-medium truncate">{r.name}</p>
                    {r.description && <p className="text-slate-500 text-xs truncate">{r.description}</p>}
                  </div>
                  <div className="col-span-3 text-slate-300 text-sm truncate">{deptName(r.department_id)}</div>
                  <div className="col-span-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {r.seniority_label}
                    </span>
                  </div>
                  <div className="col-span-2 text-slate-400 text-sm flex items-center gap-1.5">
                    <Users size={13} /> {empCountByRole(r.id)}
                  </div>
                  <div className="col-span-1 flex justify-end">
                    <button
                      onClick={() => askDelete("role", r.id, r.name)}
                      className="text-slate-500 hover:text-red-400 transition-colors"
                      title="Eliminar cargo"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* ─── TAB CATEGORÍAS (taxonomía fija de referencia) ─────────────────── */}
      {tab === "categorias" && (
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-4">
            <Lock size={16} className="text-indigo-400 mt-0.5 shrink-0" />
            <p className="text-slate-300 text-sm leading-relaxed">
              Las categorías de conocimiento son <span className="text-white font-medium">fijas por diseño</span>.
              Con ellas se clasifican tanto los documentos como las preguntas, de modo que las métricas de
              comprensión y pérdida de conocimiento sean comparables entre cargos y a lo largo del tiempo.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.map((c) => (
              <div key={c.key} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4">
                <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[c.key] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>
                  {c.label}
                </span>
                <p className="text-slate-400 text-sm mt-2">{c.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── MODAL: nuevo departamento ─────────────────────────────────────── */}
      {showDeptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !saving && setShowDeptModal(false)}>
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
              <h2 className="text-white text-lg font-semibold">Nuevo departamento</h2>
              <button onClick={() => !saving && setShowDeptModal(false)} className="text-slate-500 hover:text-slate-200 transition-colors"><X size={18} /></button>
            </div>
            <div className="px-6 py-5 flex flex-col gap-4">
              {formError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{formError}</div>}
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Nombre *</label>
                <input value={deptForm.name} onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })} placeholder="Ej. Tecnología"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Descripción</label>
                <input value={deptForm.description} onChange={(e) => setDeptForm({ ...deptForm, description: e.target.value })} placeholder="Breve descripción del área"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Color</label>
                <div className="flex gap-2">
                  {COLORS.map((c) => (
                    <button key={c} onClick={() => setDeptForm({ ...deptForm, color: c })}
                      className={`w-7 h-7 rounded-full transition-transform ${deptForm.color === c ? "ring-2 ring-white ring-offset-2 ring-offset-[#161b27] scale-110" : ""}`}
                      style={{ backgroundColor: c }} />
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={deptForm.is_rrhh} onChange={(e) => setDeptForm({ ...deptForm, is_rrhh: e.target.checked })} className="accent-indigo-500" />
                  <Shield size={14} className="text-violet-400" /> Acceso de RR.HH.
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={deptForm.is_gerencia} onChange={(e) => setDeptForm({ ...deptForm, is_gerencia: e.target.checked })} className="accent-indigo-500" />
                  <Crown size={14} className="text-amber-400" /> Departamento de gerencia
                </label>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349]">
              <button onClick={() => setShowDeptModal(false)} disabled={saving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">Cancelar</button>
              <button onClick={createDept} disabled={saving} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                {saving ? "Creando..." : "Crear departamento"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── MODAL: nuevo cargo ────────────────────────────────────────────── */}
      {showRoleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !saving && setShowRoleModal(false)}>
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
              <h2 className="text-white text-lg font-semibold">Nuevo cargo</h2>
              <button onClick={() => !saving && setShowRoleModal(false)} className="text-slate-500 hover:text-slate-200 transition-colors"><X size={18} /></button>
            </div>
            <div className="px-6 py-5 flex flex-col gap-4">
              {formError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{formError}</div>}
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Nombre *</label>
                <input value={roleForm.name} onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })} placeholder="Ej. Desarrollador Backend"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Departamento *</label>
                <select value={roleForm.department_id} onChange={(e) => setRoleForm({ ...roleForm, department_id: e.target.value })}
                  className="bg-[#0f1117] border border-[#2a3349] text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors">
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-slate-400 text-xs">Nivel de seniority</label>
                  <select value={roleForm.seniority_level}
                    onChange={(e) => {
                      const lvl = parseInt(e.target.value);
                      setRoleForm({ ...roleForm, seniority_level: lvl, seniority_label: SENIORITY.find((s) => s.level === lvl)?.label || roleForm.seniority_label });
                    }}
                    className="bg-[#0f1117] border border-[#2a3349] text-white rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors">
                    {SENIORITY.map((s) => <option key={s.level} value={s.level}>{s.level} · {s.label}</option>)}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-slate-400 text-xs">Etiqueta</label>
                  <input value={roleForm.seniority_label} onChange={(e) => setRoleForm({ ...roleForm, seniority_label: e.target.value })} placeholder="Ej. Director"
                    className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Descripción</label>
                <input value={roleForm.description} onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })} placeholder="Responsabilidades del cargo"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors" />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349]">
              <button onClick={() => setShowRoleModal(false)} disabled={saving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">Cancelar</button>
              <button onClick={createRole} disabled={saving} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                {saving ? "Creando..." : "Crear cargo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── MODAL: confirmar borrado ──────────────────────────────────────── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-5 flex flex-col gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center justify-center shrink-0">
                  <AlertTriangle size={18} className="text-red-400" />
                </div>
                <div>
                  <h2 className="text-white font-semibold">
                    Eliminar {deleteTarget.kind === "dept" ? "departamento" : "cargo"}
                  </h2>
                  <p className="text-slate-400 text-sm mt-1">
                    ¿Seguro que quieres eliminar <span className="text-white">“{deleteTarget.name}”</span>? Esta acción no se puede deshacer.
                  </p>
                </div>
              </div>
              {deleteError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{deleteError}</div>}
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349]">
              <button onClick={() => setDeleteTarget(null)} disabled={deleting} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">Cancelar</button>
              <button onClick={confirmDelete} disabled={deleting} className="bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                {deleting ? "Eliminando..." : "Eliminar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
