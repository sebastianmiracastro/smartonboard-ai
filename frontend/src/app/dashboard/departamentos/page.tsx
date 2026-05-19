"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Building2, Users, Shield, Crown, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";

export default function DepartamentosPage() {
  const [departments, setDepartments] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getDepartments();
        setDepartments(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggle = (id: string) => setExpanded(expanded === id ? null : id);

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
        <button className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
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
    </div>
  );
}