"use client";

import { FileText, Download, Search } from "lucide-react";
import { useState } from "react";
import { mockDocuments } from "@/mock/data";

export default function RecursosPage() {
  const [search, setSearch] = useState("");

  const publicDocs = mockDocuments.filter(
    (d) => d.permissions.color === "green" && d.status === "indexado"
  );

  const filtered = publicDocs.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-6">

      <div>
        <h1 className="text-white text-2xl font-semibold">Recursos</h1>
        <p className="text-slate-400 text-sm mt-1">
          Documentos disponibles para tu perfil
        </p>
      </div>

      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Buscar documento..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-[#161b27] border border-[#2a3349] text-white placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {filtered.map((doc) => (
          <div
            key={doc.id}
            className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5 hover:border-[#3d4f6e] transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center
                ${doc.format === "pdf" ? "bg-red-500/10" : "bg-blue-500/10"}`}>
                <FileText size={18} className={doc.format === "pdf" ? "text-red-400" : "text-blue-400"} />
              </div>
              <button className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg">
                <Download size={14} />
              </button>
            </div>
            <p className="text-white text-sm font-medium mb-1">{doc.name}</p>
            <div className="flex items-center justify-between mt-2">
              <span className="text-slate-500 text-xs">{(doc.sizeKb / 1024).toFixed(1)} MB</span>
              <span className="text-slate-500 text-xs uppercase">{doc.format}</span>
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="col-span-2 text-center py-12">
            <p className="text-slate-500 text-sm">No se encontraron documentos</p>
          </div>
        )}
      </div>
    </div>
  );
}