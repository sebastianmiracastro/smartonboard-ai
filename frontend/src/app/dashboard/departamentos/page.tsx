"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Building2, Users, Shield, Crown, Plus, ChevronDown, ChevronUp, X } from "lucide-react";
import { api } from "@/lib/api";

const COLORS = ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#ef4444"];
const emptyDept = { name: "", description: "", color: "#6366f1", is_rrhh: false, is_gerencia: false };

export default function DepartamentosPage() {
  const [departments, setDepartments] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ ...emptyDept });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const loadDepartments = async () => {
    const data = await api.getDepartments();
    setDepartments(data);
  };

  useEffect(() => {
    const load = async () => {
      try {
        await loadDepartments();
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggle = (id: string) => setExpanded(expanded === id ? null : id);

  const openModal = () => {
    setForm({ ...emptyDept });
    setError("");
    setShowModal(true);
  };

  const handleCreate = async () => {
    setError("");
    if (!form.name.trim()) {
      setError("El nombre del departamento es obligatorio.");
      return;
    }
    setSaving(true);
    try {
      await api.createDepartment(form);
      setShowModal(false);
      await loadDepartments();
    } catch (err: any) {
      setError(err.message || "No se pudo crear el departamento.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Cargando...</div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Departamentos</h1>
          <p className="text-slate-400 text-sm mt-1">
            Estructura organizacional y control de acceso
          </p>
        </div>
        <button
          onClick={openModal}
          className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors"
        >
          <Plus size={16} />
          Nuevo departamento
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Departamentos", value: departments.length },
          { label: "Con acceso RR.HH.", value: departments.filter(d => d.is_rrhh).length },
          { label: "De gerencia", value: departments.filter(d => d.is_gerencia).length },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {departments.map((dept) => (
          <div key={dept.id} className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
            <div
              className="flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-[#1e2536]/50 transition-colors"
              onClick={() => toggle(dept.id)}
            >
              <div
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: dept.color || "#6366f1" }}
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
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
                {dept.description && (
                  <p className="text-slate-500 text-xs mt-0.5">{dept.description}</p>
                )}
              </div>
              <div className="text-slate-500">
                {expanded === dept.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </div>

            {expanded === dept.id && (
              <div className="border-t border-[#2a3349] px-6 py-4 bg-[#1e2536]/30">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">Información</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-[#161b27] border border-[#2a3349] rounded-xl p-3">
                    <p className="text-slate-500 text-xs mb-1">Acceso RR.HH.</p>
                    <p className={`text-sm font-medium ${dept.is_rrhh ? "text-emerald-400" : "text-slate-400"}`}>
                      {dept.is_rrhh ? "Sí" : "No"}
                    </p>
                  </div>
                  <div className="bg-[#161b27] border border-[#2a3349] rounded-xl p-3">
                    <p className="text-slate-500 text-xs mb-1">Gerencia</p>
                    <p className={`text-sm font-medium ${dept.is_gerencia ? "text-amber-400" : "text-slate-400"}`}>
                      {dept.is_gerencia ? "Sí" : "No"}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal nuevo departamento */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => !saving && setShowModal(false)}
        >
          <div
            className="bg-[#161b27] border border-[#2a3349] rounded-2xl w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3349]">
              <h2 className="text-white text-lg font-semibold">Nuevo departamento</h2>
              <button onClick={() => !saving && setShowModal(false)} className="text-slate-500 hover:text-slate-200 transition-colors">
                <X size={18} />
              </button>
            </div>

            <div className="px-6 py-5 flex flex-col gap-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{error}</div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Nombre *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Ej. Tecnología"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Descripción</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Breve descripción del área"
                  className="bg-[#0f1117] border border-[#2a3349] text-white placeholder-slate-600 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Color</label>
                <div className="flex gap-2">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={() => setForm({ ...form, color: c })}
                      className={`w-7 h-7 rounded-full transition-transform ${form.color === c ? "ring-2 ring-white ring-offset-2 ring-offset-[#161b27] scale-110" : ""}`}
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.is_rrhh} onChange={(e) => setForm({ ...form, is_rrhh: e.target.checked })} className="accent-indigo-500" />
                  <Shield size={14} className="text-violet-400" /> Acceso de RR.HH.
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.is_gerencia} onChange={(e) => setForm({ ...form, is_gerencia: e.target.checked })} className="accent-indigo-500" />
                  <Crown size={14} className="text-amber-400" /> Departamento de gerencia
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3349]">
              <button onClick={() => setShowModal(false)} disabled={saving} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl transition-colors disabled:opacity-40">
                Cancelar
              </button>
              <button onClick={handleCreate} disabled={saving} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                {saving ? "Creando..." : "Crear departamento"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}