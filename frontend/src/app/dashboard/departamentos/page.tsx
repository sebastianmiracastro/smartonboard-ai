"use client";

import { useState } from "react";
import { Building2, Users, Shield, Crown, Plus, ChevronDown, ChevronUp } from "lucide-react";
import { mockDepartments } from "@/mock/data";

export default function DepartamentosPage() {
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggle = (id: string) => setExpanded(expanded === id ? null : id);

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
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

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Departamentos", value: mockDepartments.length },
          { label: "Empleados totales", value: mockDepartments.reduce((a, d) => a + d.employeeCount, 0) },
          { label: "Roles definidos", value: mockDepartments.reduce((a, d) => a + d.roleCount, 0) },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Lista departamentos */}
      <div className="flex flex-col gap-3">
        {mockDepartments.map((dept) => (
          <div key={dept.id} className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">

            {/* Fila principal */}
            <div
              className="flex items-center gap-4 px-6 py-4 cursor-pointer hover:bg-[#1e2536]/50 transition-colors"
              onClick={() => toggle(dept.id)}
            >
              {/* Color dot */}
              <div
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: dept.color }}
              />

              {/* Nombre */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-white font-medium">{dept.name}</p>
                  {dept.isRrhh && (
                    <span className="flex items-center gap-1 text-xs bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5 rounded-full">
                      <Shield size={10} /> RR.HH.
                    </span>
                  )}
                  {dept.isGerencia && (
                    <span className="flex items-center gap-1 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
                      <Crown size={10} /> Gerencia
                    </span>
                  )}
                </div>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-1.5 text-slate-400 text-sm">
                  <Users size={14} />
                  <span>{dept.employeeCount} empleados</span>
                </div>
                <div className="flex items-center gap-1.5 text-slate-400 text-sm">
                  <Building2 size={14} />
                  <span>{dept.roleCount} roles</span>
                </div>
              </div>

              {/* Expand */}
              <div className="text-slate-500">
                {expanded === dept.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
            </div>

            {/* Expanded — roles */}
            {expanded === dept.id && (
              <div className="border-t border-[#2a3349] px-6 py-4 bg-[#1e2536]/30">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">Roles</p>
                  <button className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs transition-colors">
                    <Plus size={12} /> Agregar rol
                  </button>
                </div>
                <div className="flex flex-col gap-2">
                  {[
                    { label: "Junior", seniority: 1 },
                    { label: "Mid", seniority: 2 },
                    { label: "Senior", seniority: 3 },
                    { label: "Lead", seniority: 4 },
                  ].slice(0, dept.roleCount).map((role) => (
                    <div
                      key={role.label}
                      className="flex items-center justify-between bg-[#161b27] border border-[#2a3349] rounded-xl px-4 py-3"
                    >
                      <div>
                        <p className="text-white text-sm">
                          {dept.name === "Recursos Humanos" ? "Analista" : dept.name === "Gerencia" ? "Director" : `Desarrollador`} {role.label}
                        </p>
                        <p className="text-slate-500 text-xs mt-0.5">Nivel {role.seniority} de seniority</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4].map((n) => (
                          <div
                            key={n}
                            className={`w-2 h-2 rounded-full ${n <= role.seniority ? "bg-indigo-400" : "bg-[#2a3349]"}`}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}