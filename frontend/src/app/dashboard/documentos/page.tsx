"use client";

import { useState } from "react";
import { FileText, Upload, RefreshCw, Trash2, Shield, Users } from "lucide-react";
import { mockDocuments } from "@/mock/data";

const statusConfig: Record<string, { label: string; classes: string }> = {
  indexado: { label: "Indexado", classes: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
  procesando: { label: "Procesando", classes: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
  en_cola: { label: "En cola", classes: "bg-slate-500/10 text-slate-400 border border-slate-500/20" },
  error: { label: "Error", classes: "bg-red-500/10 text-red-400 border border-red-500/20" },
};

const permissionConfig: Record<string, { label: string; classes: string }> = {
  green: { label: "Todos", classes: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
  purple: { label: "Solo RR.HH.", classes: "bg-violet-500/10 text-violet-400 border border-violet-500/20" },
};

export default function DocumentosPage() {
  const [docs, setDocs] = useState(mockDocuments);
  const [dragging, setDragging] = useState(false);

  const totalChunks = docs
    .filter(d => d.status === "indexado")
    .reduce((acc, d) => acc + (d.chunkCount || 0), 0);

  return (
    <div className="flex flex-col gap-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Base de conocimiento</h1>
          <p className="text-slate-400 text-sm mt-1">
            Documentos que entrena al agente IA
          </p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
          <Upload size={16} />
          Subir documento
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Documentos totales", value: docs.length },
          { label: "Chunks indexados", value: totalChunks.toLocaleString() },
          { label: "Indexados", value: docs.filter(d => d.status === "indexado").length },
        ].map((s) => (
          <div key={s.label} className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors
          ${dragging ? "border-indigo-500 bg-indigo-500/5" : "border-[#2a3349] hover:border-[#3d4f6e]"}`}
      >
        <Upload size={24} className="text-slate-500 mx-auto mb-3" />
        <p className="text-slate-300 text-sm font-medium mb-1">Arrastra archivos aquí</p>
        <p className="text-slate-500 text-xs">PDF, DOCX, TXT — máx. 50MB por archivo</p>
        <button className="mt-4 border border-[#2a3349] hover:border-[#3d4f6e] text-slate-400 hover:text-slate-200 text-xs px-4 py-2 rounded-lg transition-colors">
          Seleccionar archivos
        </button>
      </div>

      {/* Lista documentos */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#2a3349]">
          <h2 className="text-white font-semibold">Documentos cargados</h2>
        </div>

        <div className="divide-y divide-[#2a3349]">
          {docs.map((doc) => (
            <div key={doc.id} className="px-6 py-4 flex items-center gap-4 hover:bg-[#1e2536]/50 transition-colors">

              {/* Icono formato */}
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0
                ${doc.format === "pdf" ? "bg-red-500/10" : doc.format === "docx" ? "bg-blue-500/10" : "bg-slate-500/10"}`}>
                <FileText size={18} className={
                  doc.format === "pdf" ? "text-red-400" : doc.format === "docx" ? "text-blue-400" : "text-slate-400"
                } />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-medium truncate">{doc.name}</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-slate-500 text-xs">
                    {(doc.sizeKb / 1024).toFixed(1)} MB
                  </span>
                  {doc.chunkCount && (
                    <span className="text-slate-500 text-xs">{doc.chunkCount} chunks</span>
                  )}
                  <span className="text-slate-500 text-xs">{doc.uploadedAt}</span>
                </div>

                {/* Barra progreso si está procesando */}
                {doc.status === "procesando" && doc.progress && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 h-1 bg-[#2a3349] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-400 rounded-full transition-all"
                        style={{ width: `${doc.progress}%` }}
                      />
                    </div>
                    <span className="text-amber-400 text-xs">{doc.progress}%</span>
                  </div>
                )}
              </div>

              {/* Permisos */}
              <div className="flex items-center gap-2">
                {doc.permissions.color === "purple" ? (
                  <Shield size={12} className="text-violet-400" />
                ) : (
                  <Users size={12} className="text-emerald-400" />
                )}
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium border
                  ${permissionConfig[doc.permissions.color].classes}`}>
                  {permissionConfig[doc.permissions.color].label}
                </span>
              </div>

              {/* Estado */}
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium border
                ${statusConfig[doc.status].classes}`}>
                {statusConfig[doc.status].label}
              </span>

              {/* Acciones */}
              <div className="flex items-center gap-2">
                <button className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg">
                  <RefreshCw size={14} />
                </button>
                <button
                  onClick={() => setDocs(docs.filter(d => d.id !== doc.id))}
                  className="text-slate-500 hover:text-red-400 transition-colors p-1.5 hover:bg-red-500/10 rounded-lg"
                >
                  <Trash2 size={14} />
                </button>
              </div>

            </div>
          ))}
        </div>
      </div>
    </div>
  );
}