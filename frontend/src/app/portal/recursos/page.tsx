"use client";

import { FileText, Search } from "lucide-react";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  procesos: "Procesos", rol: "Rol", cultura: "Cultura", herramientas: "Herramientas", relaciones: "Relaciones",
};
const categoryColors: Record<string, string> = {
  procesos: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  rol: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  cultura: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  herramientas: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  relaciones: "bg-pink-500/10 text-pink-400 border border-pink-500/20",
};

function fmtSize(kb?: number) {
  if (!kb) return "—";
  return kb < 1024 ? `${kb} KB` : `${(kb / 1024).toFixed(1)} MB`;
}

export default function RecursosPage() {
  const [docs, setDocs] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getDocuments(); // el backend ya filtra por rol/RBAC
        setDocs(data.filter((d: any) => d.status === "indexado"));
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const filtered = docs.filter((d) => d.name.toLowerCase().includes(search.toLowerCase()));

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="text-slate-400 text-sm">Cargando...</div></div>
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-white text-2xl font-semibold">Recursos</h1>
        <p className="text-slate-400 text-sm mt-1">Documentos disponibles para tu perfil</p>
      </div>

      <div className="relative max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Buscar documento..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-[#161e33] border border-[#2a3354] text-white placeholder-slate-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>

      {filtered.length === 0 ? (
        <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-10 text-center">
          <FileText size={28} className="text-slate-600 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">No hay documentos disponibles para tu perfil.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {filtered.map((doc) => (
            <div key={doc.id} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-5 hover:border-[#3a4a72] transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${doc.format === "pdf" ? "bg-red-500/10" : doc.format === "docx" ? "bg-blue-500/10" : "bg-slate-500/10"}`}>
                  <FileText size={18} className={doc.format === "pdf" ? "text-red-400" : doc.format === "docx" ? "text-blue-400" : "text-slate-400"} />
                </div>
                {doc.primary_category && (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[doc.primary_category] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>
                    {CATEGORY_LABELS[doc.primary_category] || doc.primary_category}
                  </span>
                )}
              </div>
              <p className="text-white text-sm font-medium mb-1 truncate">{doc.name}</p>
              <div className="flex items-center justify-between mt-2">
                <span className="text-slate-500 text-xs">{fmtSize(doc.size_kb)}</span>
                <span className="text-slate-500 text-xs uppercase">{doc.format}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
