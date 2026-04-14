"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Filter, ArrowRight, Plus } from "lucide-react";
import { mockEmployees } from "@/mock/data";

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

export default function EmpleadosPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("todos");

  const filtered = mockEmployees.filter((emp) => {
    const matchSearch =
      emp.fullName.toLowerCase().includes(search.toLowerCase()) ||
      emp.email.toLowerCase().includes(search.toLowerCase()) ||
      emp.department.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === "todos" || emp.status === filterStatus;
    return matchSearch && matchStatus;
  });

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Empleados</h1>
          <p className="text-slate-400 text-sm mt-1">
            {mockEmployees.length} empleados registrados
          </p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
          <Plus size={16} />
          Nuevo empleado
        </button>
      </div>

      {/* Filtros */}
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
              className={`px-3 py-2 rounded-xl text-xs font-medium transition-colors capitalize
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

      {/* Tabla */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">

        {/* Header */}
        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-[#2a3349] bg-[#1e2536]/50">
          <span className="col-span-3 text-slate-500 text-xs uppercase tracking-wider">Empleado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Departamento</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Rol</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Estado</span>
          <span className="col-span-2 text-slate-500 text-xs uppercase tracking-wider">Progreso</span>
          <span className="col-span-1"></span>
        </div>

        {/* Filas */}
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
              <div className="col-span-3 flex items-center gap-3">
                <div className="w-9 h-9 bg-indigo-500/20 border border-indigo-500/20 rounded-full flex items-center justify-center shrink-0">
                  <span className="text-indigo-400 text-xs font-semibold">
                    {emp.fullName.split(" ").map((n) => n[0]).join("").slice(0, 2)}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-white text-sm font-medium truncate">{emp.fullName}</p>
                  <p className="text-slate-500 text-xs truncate">{emp.email}</p>
                </div>
              </div>

              <div className="col-span-2">
                <p className="text-slate-300 text-sm">{emp.department}</p>
              </div>

              <div className="col-span-2">
                <p className="text-slate-300 text-sm truncate">{emp.role}</p>
              </div>

              <div className="col-span-2">
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[emp.status]}`}>
                  {statusLabels[emp.status]}
                </span>
              </div>

              <div className="col-span-2">
                {emp.status === "onboarding" ? (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-indigo-500"
                        style={{ width: `${emp.progress}%` }}
                      />
                    </div>
                    <span className="text-slate-400 text-xs">{emp.progress}%</span>
                  </div>
                ) : (
                  <span className="text-slate-500 text-xs">Completado</span>
                )}
              </div>

              <div className="col-span-1 flex justify-end">
                <button
                  onClick={() => router.push(`/dashboard/empleados/${emp.id}`)}
                  className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg"
                >
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}