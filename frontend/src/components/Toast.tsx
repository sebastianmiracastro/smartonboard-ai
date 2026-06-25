"use client";

import { createContext, useContext, useState, useCallback, useRef } from "react";
import { CheckCircle2, AlertTriangle, Info, Loader2, X } from "lucide-react";

type ToastType = "success" | "error" | "info" | "loading";
interface ToastItem { id: number; type: ToastType; message: string; }

interface ToastApi {
  success: (m: string) => number;
  error: (m: string) => number;
  info: (m: string) => number;
  loading: (m: string) => number;
  update: (id: number, t: { type: ToastType; message: string }) => void;
  dismiss: (id: number) => void;
}

const ToastCtx = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast debe usarse dentro de <ToastProvider>");
  return ctx;
}

const CONFIG: Record<ToastType, { icon: any; cls: string; ring: string }> = {
  success: { icon: CheckCircle2, cls: "text-emerald-400", ring: "border-l-emerald-400" },
  error: { icon: AlertTriangle, cls: "text-rose-400", ring: "border-l-rose-400" },
  info: { icon: Info, cls: "text-sky-400", ring: "border-l-sky-400" },
  loading: { icon: Loader2, cls: "text-violet-400", ring: "border-l-violet-400" },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const idRef = useRef(0);
  const timers = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const remove = useCallback((id: number) => {
    setToasts((p) => p.filter((t) => t.id !== id));
    if (timers.current[id]) { clearTimeout(timers.current[id]); delete timers.current[id]; }
  }, []);

  const schedule = useCallback((id: number, type: ToastType) => {
    if (timers.current[id]) clearTimeout(timers.current[id]);
    if (type !== "loading") {
      timers.current[id] = setTimeout(() => remove(id), type === "error" ? 5000 : 3500);
    }
  }, [remove]);

  const push = useCallback((type: ToastType, message: string) => {
    const id = ++idRef.current;
    setToasts((p) => [...p, { id, type, message }]);
    schedule(id, type);
    return id;
  }, [schedule]);

  const update = useCallback((id: number, t: { type: ToastType; message: string }) => {
    setToasts((p) => p.map((x) => (x.id === id ? { ...x, ...t } : x)));
    schedule(id, t.type);
  }, [schedule]);

  const api: ToastApi = {
    success: (m) => push("success", m),
    error: (m) => push("error", m),
    info: (m) => push("info", m),
    loading: (m) => push("loading", m),
    update,
    dismiss: remove,
  };

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80 max-w-[calc(100vw-2rem)]">
        {toasts.map((t) => {
          const c = CONFIG[t.type];
          const Icon = c.icon;
          return (
            <div
              key={t.id}
              style={{ animation: "toastIn .18s ease" }}
              className={`bg-[#161e33] border border-[#2a3354] border-l-2 ${c.ring} rounded-xl shadow-lg shadow-black/30 px-4 py-3 flex items-start gap-3`}
            >
              <Icon size={18} className={`${c.cls} shrink-0 mt-0.5 ${t.type === "loading" ? "animate-spin" : ""}`} />
              <p className="text-slate-200 text-sm flex-1 leading-snug">{t.message}</p>
              <button onClick={() => remove(t.id)} className="text-slate-500 hover:text-slate-300 shrink-0">
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastCtx.Provider>
  );
}
