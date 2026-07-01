"use client";

import { useState, useEffect, useRef } from "react";
import { FileText, Upload, Trash2, Shield, Users, Crown, Briefcase, Building2, X, Tag, RotateCw, AlertTriangle, Eye } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";

const statusConfig: Record<string, { label: string; classes: string }> = {
  indexado: { label: "Indexado", classes: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
  procesando: { label: "Procesando", classes: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
  en_cola: { label: "En cola", classes: "bg-slate-500/10 text-slate-400 border border-slate-500/20" },
  error: { label: "Error", classes: "bg-red-500/10 text-red-400 border border-red-500/20" },
};

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

const emptyForm = {
  category: "", role_permission: "", dept_permission: "", min_seniority: "",
  require_rrhh: false, require_gerencia: false,
};

function fmtSize(kb: number) {
  if (!kb) return "—";
  return kb < 1024 ? `${kb} KB` : `${(kb / 1024).toFixed(1)} MB`;
}
function fmtDate(s?: string) {
  if (!s) return "";
  try { return new Date(s).toLocaleDateString(); } catch { return ""; }
}

export default function DocumentosPage() {
  const toast = useToast();
  const [docs, setDocs] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(true);

  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [myRole, setMyRole] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try { setMyRole(JSON.parse(localStorage.getItem("user") || "{}").system_role || ""); } catch {}
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [d, r, dp] = await Promise.all([
          api.getDocuments(),
          api.getRoles().catch(() => []),
          api.getDepartments().catch(() => []),
        ]);
        setDocs(d); setRoles(r); setDepartments(dp);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  const roleName = (id: string) => roles.find((r) => r.id === id)?.name;
  const deptName = (id: string) => departments.find((d) => d.id === id)?.name;

  const accessBadge = (doc: any) => {
    if (doc.require_gerencia) return { label: "Solo gerencia", icon: Crown, cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" };
    if (doc.require_rrhh) return { label: "Solo RR.HH.", icon: Shield, cls: "bg-violet-500/10 text-violet-400 border-violet-500/20" };
    if (doc.role_permission) return { label: roleName(doc.role_permission) || "Cargo", icon: Briefcase, cls: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" };
    if (doc.dept_permission) return { label: deptName(doc.dept_permission) || "Depto", icon: Building2, cls: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20" };
    return { label: "Todos", icon: Users, cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" };
  };

  const deleteDoc = async (id: string) => {
    try { await api.deleteDocument(id); setDocs(docs.filter((d) => d.id !== id)); toast.success("Documento eliminado"); }
    catch (e: any) { toast.error(e.message || "No se pudo eliminar el documento"); }
  };

  const openDoc = async (id: string) => {
    try { await api.openDocument(id); }
    catch (e: any) { toast.error(e.message || "No se pudo abrir el documento"); }
  };

  const retryDoc = async (id: string, name: string) => {
    const tid = toast.loading(`Reprocesando “${name}”…`);
    try {
      await api.retryDocument(id);
      setDocs((prev) => prev.map((d) => d.id === id ? { ...d, status: "en_cola", progress: 0, error_message: null } : d));
      pollDocumentStatus(id, tid);
    } catch (e: any) {
      toast.update(tid, { type: "error", message: e.message || "No se pudo reprocesar el documento" });
    }
  };

  // Selección de archivo (por botón o arrastre) → abre el modal de parámetros
  const pickFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "txt"].includes(ext || "")) { toast.error("Formato no soportado. Usa PDF, DOCX o TXT."); return; }
    setForm({ ...emptyForm }); setError(""); setPendingFile(file);
  };

  const doUpload = async () => {
    if (!pendingFile) return;
    setError(""); setUploading(true);
    const tid = toast.loading(`Subiendo “${pendingFile.name}”…`);
    try {
      const params = {
        category: form.category,
        role_permission: form.role_permission,
        dept_permission: form.dept_permission,
        min_seniority: form.min_seniority,
        require_rrhh: form.require_rrhh,
        require_gerencia: form.require_gerencia,
      };
      const data = await api.uploadDocument(pendingFile, params);
      setPendingFile(null);
      // Si el documento queda restringido POR ENCIMA de mi nivel, no lo veré en la
      // lista: confirmo la subida y no lo agrego ni hago polling (el índice sigue).
      const hiddenAfterUpload = form.require_gerencia && myRole !== "gerencia";
      if (hiddenAfterUpload) {
        toast.update(tid, {
          type: "success",
          message: `“${data.nombre}” subido y en indexación. Queda restringido a Gerencia, así que no aparece en tu lista.`,
        });
      } else {
        setDocs((prev) => [...prev, {
          id: data.id, name: data.nombre, format: data.nombre.split(".").pop(),
          size_kb: Math.round(pendingFile.size / 1024), status: "en_cola", progress: 0, chunk_count: 0,
          uploaded_at: new Date().toISOString(),
          require_rrhh: form.require_rrhh, require_gerencia: form.require_gerencia,
          role_permission: form.role_permission || null, dept_permission: form.dept_permission || null,
          primary_category: form.category || null,
        }]);
        toast.update(tid, { type: "info", message: "Procesando y extrayendo contextos…" });
        pollDocumentStatus(data.id, tid);
      }
    } catch (e: any) {
      setError(e.message || "No se pudo subir el documento.");
      toast.update(tid, { type: "error", message: e.message || "No se pudo subir el documento" });
    }
    finally { setUploading(false); }
  };

  const pollDocumentStatus = (docId: string, tid: number) => {
    const interval = setInterval(async () => {
      try {
        const data = await api.getDocuments();
        const doc = data.find((d: any) => d.id === docId);
        if (doc) {
          setDocs((prev) => prev.map((d) => d.id === docId ? { ...d, ...doc } : d));
          if (doc.status === "indexado") {
            toast.update(tid, { type: "success", message: `“${doc.name}” indexado y listo` });
            clearInterval(interval);
          } else if (doc.status === "error") {
            toast.update(tid, { type: "error", message: doc.error_message || `Error al procesar “${doc.name}”` });
            clearInterval(interval);
          }
        }
      } catch { clearInterval(interval); }
    }, 2000);
  };

  const totalChunks = docs.filter((d) => d.status === "indexado").reduce((a, d) => a + (d.chunk_count || 0), 0);

  if (loading) return (
    <div className="flex items-center justify-center h-64"><div className="text-slate-400 text-sm">Cargando...</div></div>
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-white text-2xl font-semibold">Base de conocimiento</h1>
          <p className="text-slate-400 text-sm mt-1">Documentos de los que el agente extrae contextos</p>
        </div>
        <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
          <Upload size={16} /> Subir documento
        </button>
        <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) pickFile(f); e.target.value = ""; }} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Documentos totales", value: docs.length },
          { label: "Contextos indexados", value: totalChunks.toLocaleString() },
          { label: "Indexados", value: docs.filter((d) => d.status === "indexado").length },
        ].map((s) => (
          <div key={s.label} className="bg-[#161e33] border border-[#2a3354] rounded-2xl p-4 text-center">
            <p className="text-white text-2xl font-semibold">{s.value}</p>
            <p className="text-slate-500 text-xs mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Zona de arrastre */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files?.[0]; if (f) pickFile(f); }}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors ${dragging ? "border-indigo-500 bg-indigo-500/5" : "border-[#2a3354] hover:border-[#3a4a72]"}`}
      >
        <Upload size={24} className="text-slate-500 mx-auto mb-3" />
        <p className="text-slate-300 text-sm font-medium mb-1">Arrastra un archivo aquí o usa “Subir documento”</p>
        <p className="text-slate-500 text-xs">PDF, DOCX, TXT — podrás categorizar y definir el acceso antes de subir</p>
      </div>

      {/* Lista */}
      <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#2a3354]"><h2 className="text-white font-semibold">Documentos cargados</h2></div>
        {docs.length === 0 ? (
          <div className="px-6 py-12 text-center text-slate-500 text-sm">Aún no hay documentos.</div>
        ) : (
          <div className="divide-y divide-[#2a3354]">
            {docs.map((doc) => {
              const acc = accessBadge(doc);
              const AccIcon = acc.icon;
              return (
                <div key={doc.id} className="px-6 py-4 flex items-center gap-4 hover:bg-[#1c2540]/50 transition-colors">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${doc.format === "pdf" ? "bg-red-500/10" : doc.format === "docx" ? "bg-blue-500/10" : "bg-slate-500/10"}`}>
                    <FileText size={18} className={doc.format === "pdf" ? "text-red-400" : doc.format === "docx" ? "text-blue-400" : "text-slate-400"} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-medium truncate">{doc.name}</p>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className="text-slate-500 text-xs">{fmtSize(doc.size_kb)}</span>
                      {doc.chunk_count ? <span className="text-slate-500 text-xs">{doc.chunk_count} contextos</span> : null}
                      {doc.uploaded_at && <span className="text-slate-500 text-xs">{fmtDate(doc.uploaded_at)}</span>}
                      {doc.primary_category && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${categoryColors[doc.primary_category] || "bg-slate-500/10 text-slate-400 border border-slate-500/20"}`}>
                          {CATEGORY_LABELS[doc.primary_category] || doc.primary_category}
                        </span>
                      )}
                    </div>
                    {doc.status === "procesando" && doc.progress ? (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="flex-1 h-1 bg-[#2a3354] rounded-full overflow-hidden">
                          <div className="h-full bg-amber-400 rounded-full transition-all" style={{ width: `${doc.progress}%` }} />
                        </div>
                        <span className="text-amber-400 text-xs">{doc.progress}%</span>
                      </div>
                    ) : null}
                    {doc.status === "error" && doc.error_message ? (
                      <p className="mt-1.5 text-red-400 text-xs">{doc.error_message}</p>
                    ) : null}
                  </div>
                  <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border ${acc.cls}`}>
                    <AccIcon size={11} /> {acc.label}
                  </span>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${statusConfig[doc.status]?.classes || statusConfig.en_cola.classes}`}>
                    {statusConfig[doc.status]?.label || doc.status}
                  </span>
                  <button onClick={() => openDoc(doc.id)} title="Ver / descargar el archivo original" className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg">
                    <Eye size={14} />
                  </button>
                  {doc.status === "error" && (
                    <button onClick={() => retryDoc(doc.id, doc.name)} title="Reintentar procesamiento" className="text-slate-500 hover:text-indigo-400 transition-colors p-1.5 hover:bg-indigo-500/10 rounded-lg">
                      <RotateCw size={14} />
                    </button>
                  )}
                  <button onClick={() => deleteDoc(doc.id)} className="text-slate-500 hover:text-red-400 transition-colors p-1.5 hover:bg-red-500/10 rounded-lg">
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal de parámetros de subida */}
      {pendingFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => !uploading && setPendingFile(null)}>
          <div className="bg-[#161e33] border border-[#2a3354] rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#2a3354]">
              <h2 className="text-white text-lg font-semibold">Subir documento</h2>
              <button onClick={() => !uploading && setPendingFile(null)} className="text-slate-500 hover:text-slate-200"><X size={18} /></button>
            </div>
            <div className="px-6 py-5 flex flex-col gap-4">
              {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg px-3 py-2">{error}</div>}
              <div className="flex items-center gap-2 bg-[#0f1629] border border-[#2a3354] rounded-xl px-3 py-2.5">
                <FileText size={16} className="text-indigo-400 shrink-0" />
                <span className="text-slate-300 text-sm truncate">{pendingFile.name}</span>
                <span className="text-slate-600 text-xs ml-auto shrink-0">{fmtSize(Math.round(pendingFile.size / 1024))}</span>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs flex items-center gap-1.5"><Tag size={12} /> Categoría</label>
                <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                  <option value="">Detectar automáticamente</option>
                  {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1.5">
                  <label className="text-slate-400 text-xs">Acceso por cargo</label>
                  <select className="input" value={form.role_permission} onChange={(e) => setForm({ ...form, role_permission: e.target.value })}>
                    <option value="">General (todos)</option>
                    {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-slate-400 text-xs">Departamento</label>
                  <select className="input" value={form.dept_permission} onChange={(e) => setForm({ ...form, dept_permission: e.target.value })}>
                    <option value="">General (todos)</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-slate-400 text-xs">Nivel mínimo (seniority)</label>
                <select className="input" value={form.min_seniority} onChange={(e) => setForm({ ...form, min_seniority: e.target.value })}>
                  <option value="">Cualquiera</option>
                  <option value="1">1 · Junior</option>
                  <option value="2">2 · Mid</option>
                  <option value="3">3 · Senior</option>
                  <option value="4">4 · Lead</option>
                </select>
              </div>

              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.require_rrhh} onChange={(e) => setForm({ ...form, require_rrhh: e.target.checked })} className="accent-indigo-500" />
                  <Shield size={14} className="text-violet-400" /> Confidencial — solo RR.HH./gerencia
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
                  <input type="checkbox" checked={form.require_gerencia} onChange={(e) => setForm({ ...form, require_gerencia: e.target.checked })} className="accent-indigo-500" />
                  <Crown size={14} className="text-amber-400" /> Solo gerencia
                </label>
                {form.require_gerencia && myRole !== "gerencia" && (
                  <p className="flex items-start gap-1.5 text-amber-400 text-xs bg-amber-500/10 border border-amber-500/20 rounded-lg px-2.5 py-2">
                    <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                    Este documento quedará visible <b className="font-semibold">solo para Gerencia</b>. Como {myRole === "rrhh" ? "RR.HH." : "tu perfil"}, no lo verás en tu lista después de subirlo.
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#2a3354]">
              <button onClick={() => setPendingFile(null)} disabled={uploading} className="text-slate-400 hover:text-slate-200 text-sm px-4 py-2.5 rounded-xl disabled:opacity-40">Cancelar</button>
              <button onClick={doUpload} disabled={uploading} className="bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors">
                {uploading ? "Subiendo..." : "Subir e indexar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
