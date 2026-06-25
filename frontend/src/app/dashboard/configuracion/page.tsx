"use client";

import { useEffect, useState } from "react";
import {
  Bot, Save, RotateCcw, Shield, Sliders, MessageSquare,
  KeyRound, Eye, EyeOff, CheckCircle2, AlertTriangle, Trash2, Loader2,
} from "lucide-react";
import { api } from "@/lib/api";

export default function ConfiguracionPage() {
  const [config, setConfig] = useState({
    agentName: "Sara",
    welcomeMessage: "Hola 👋 Soy tu asistente de onboarding. Estoy aquí para ayudarte con cualquier duda sobre la empresa, tu rol, procesos o herramientas.",
    model: "gpt-4o-mini",
    temperature: 0.4,
    ragTopK: 5,
    requireSources: true,
    allowGeneralQuestions: true,
    blockSalaryQuestions: true,
    blockPersonalData: true,
  });

  // Estado de la clave de IA
  const [hasApiKey, setHasApiKey] = useState(false);
  const [apiKeyPreview, setApiKeyPreview] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");   // clave nueva escrita por el usuario
  const [showKey, setShowKey] = useState(false);
  const [removeKey, setRemoveKey] = useState(false);    // marcar la clave para borrarla al guardar

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  // Cargar la configuración real de la empresa
  useEffect(() => {
    (async () => {
      try {
        const c = await api.getAgentConfig();
        setConfig((prev) => ({
          ...prev,
          agentName: c.agent_name ?? prev.agentName,
          welcomeMessage: c.welcome_message ?? prev.welcomeMessage,
          model: c.ai_model ?? prev.model,
          temperature: c.ai_temperature ?? prev.temperature,
          ragTopK: c.rag_top_k ?? prev.ragTopK,
        }));
        setHasApiKey(!!c.has_api_key);
        setApiKeyPreview(c.api_key_preview ?? null);
      } catch (e: any) {
        setError(e.message || "No se pudo cargar la configuración");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload: any = {
        agent_name: config.agentName,
        welcome_message: config.welcomeMessage,
        ai_model: config.model,
        ai_temperature: config.temperature,
        rag_top_k: config.ragTopK,
      };
      // Solo tocamos la clave si el usuario escribió una nueva o pidió borrarla
      if (apiKeyInput.trim() !== "") payload.openai_api_key = apiKeyInput.trim();
      else if (removeKey) payload.openai_api_key = "";

      const c = await api.updateAgentConfig(payload);
      setHasApiKey(!!c.has_api_key);
      setApiKeyPreview(c.api_key_preview ?? null);
      setApiKeyInput("");
      setRemoveKey(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(e.message || "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  };

  // Estado efectivo de la conexión tras una eventual edición sin guardar
  const keyActive = (hasApiKey && !removeKey) || apiKeyInput.trim() !== "";

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm p-6">
        <Loader2 size={16} className="animate-spin" />
        Cargando configuración…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-3xl">

      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-semibold">Configuración del agente</h1>
        <p className="text-slate-400 text-sm mt-1">
          Personaliza el comportamiento del agente IA para tu empresa
        </p>
      </div>

      {/* Conexión con IA (API Key) */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <KeyRound size={18} className="text-indigo-400" />
            <h2 className="text-white font-semibold">Conexión con IA</h2>
          </div>
          {keyActive ? (
            <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1">
              <CheckCircle2 size={13} /> Conectada
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-full px-3 py-1">
              <AlertTriangle size={13} /> Modo demo
            </span>
          )}
        </div>

        <p className="text-slate-400 text-sm mb-4 leading-relaxed">
          Pega tu clave de OpenAI para que el agente genere respuestas inteligentes
          a partir de la información de los documentos que subes. Sin una clave, el
          agente responde en modo demostración con respuestas predefinidas.
        </p>

        <label className="text-slate-300 text-sm font-medium mb-1.5 block">
          OpenAI API Key
        </label>
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              type={showKey ? "text" : "password"}
              value={apiKeyInput}
              onChange={(e) => { setApiKeyInput(e.target.value); setRemoveKey(false); }}
              placeholder={hasApiKey && !removeKey ? `Clave configurada (${apiKeyPreview ?? "•••• "})` : "sk-..."}
              autoComplete="off"
              className="w-full bg-[#1e2536] border border-[#2a3349] text-white rounded-xl pl-4 pr-10 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {hasApiKey && !removeKey && (
            <button
              type="button"
              onClick={() => { setRemoveKey(true); setApiKeyInput(""); }}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors shrink-0"
            >
              <Trash2 size={15} /> Quitar
            </button>
          )}
        </div>

        {removeKey && (
          <p className="text-amber-400 text-xs mt-2">
            La clave se eliminará al guardar. El agente volverá al modo demostración.
          </p>
        )}
        <p className="text-slate-500 text-xs mt-3">
          La clave se almacena de forma segura en el servidor y nunca se muestra
          completa. Obtén la tuya en{" "}
          <a
            href="https://platform.openai.com/api-keys"
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-400 hover:underline"
          >
            platform.openai.com/api-keys
          </a>.
        </p>
      </div>

      {/* Identidad */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bot size={18} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Identidad del agente</h2>
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <label className="text-slate-300 text-sm font-medium mb-1.5 block">
              Nombre del agente
            </label>
            <input
              type="text"
              value={config.agentName}
              onChange={(e) => setConfig({ ...config, agentName: e.target.value })}
              className="w-full bg-[#1e2536] border border-[#2a3349] text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <div>
            <label className="text-slate-300 text-sm font-medium mb-1.5 block">
              Mensaje de bienvenida
            </label>
            <textarea
              value={config.welcomeMessage}
              onChange={(e) => setConfig({ ...config, welcomeMessage: e.target.value })}
              rows={3}
              className="w-full bg-[#1e2536] border border-[#2a3349] text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors resize-none"
            />
          </div>
        </div>
      </div>

      {/* Modelo */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sliders size={18} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Parámetros del modelo</h2>
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <label className="text-slate-300 text-sm font-medium mb-1.5 block">
              Modelo LLM
            </label>
            <select
              value={config.model}
              onChange={(e) => setConfig({ ...config, model: e.target.value })}
              className="w-full bg-[#1e2536] border border-[#2a3349] text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="gpt-4o-mini">GPT-4o Mini (recomendado)</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4-turbo">GPT-4 Turbo</option>
              <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
            </select>
            <p className="text-slate-500 text-xs mt-1.5">
              Debe ser un modelo compatible con la clave de OpenAI configurada arriba.
            </p>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-slate-300 text-sm font-medium">
                Temperatura
              </label>
              <span className="text-indigo-400 text-sm">{config.temperature}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={config.temperature}
              onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between mt-1">
              <span className="text-slate-600 text-xs">Preciso</span>
              <span className="text-slate-600 text-xs">Creativo</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-slate-300 text-sm font-medium">
                Documentos a recuperar (RAG Top-K)
              </label>
              <span className="text-indigo-400 text-sm">{config.ragTopK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={config.ragTopK}
              onChange={(e) => setConfig({ ...config, ragTopK: parseInt(e.target.value) })}
              className="w-full accent-indigo-500"
            />
            <div className="flex justify-between mt-1">
              <span className="text-slate-600 text-xs">1 doc</span>
              <span className="text-slate-600 text-xs">10 docs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Permisos del agente */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield size={18} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Control de respuestas</h2>
        </div>

        <div className="flex flex-col gap-3">
          {[
            { key: "requireSources", label: "Requerir fuentes en respuestas", sub: "El agente siempre cita el documento del que obtuvo la información" },
            { key: "allowGeneralQuestions", label: "Permitir preguntas generales", sub: "El agente puede responder preguntas que no están en los documentos" },
            { key: "blockSalaryQuestions", label: "Bloquear preguntas de salarios", sub: "El agente no responde sobre compensación a empleados sin acceso" },
            { key: "blockPersonalData", label: "Bloquear datos personales", sub: "El agente no revela información personal de otros empleados" },
          ].map((item) => (
            <div
              key={item.key}
              className="flex items-start justify-between gap-4 p-4 bg-[#1e2536]/50 rounded-xl border border-[#2a3349]"
            >
              <div className="flex-1">
                <p className="text-white text-sm font-medium">{item.label}</p>
                <p className="text-slate-500 text-xs mt-0.5">{item.sub}</p>
              </div>
              <button
                onClick={() => setConfig({ ...config, [item.key]: !config[item.key as keyof typeof config] })}
                className={`relative w-11 h-6 rounded-full transition-colors shrink-0 mt-0.5
                  ${config[item.key as keyof typeof config] ? "bg-indigo-500" : "bg-[#2a3349]"}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform
                  ${config[item.key as keyof typeof config] ? "translate-x-5" : "translate-x-0.5"}`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Preview mensaje */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare size={18} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Vista previa</h2>
        </div>
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 bg-[#1e2536] border border-[#2a3349] rounded-full flex items-center justify-center text-xs text-slate-400 shrink-0">
            IA
          </div>
          <div className="bg-[#1e2536] border border-[#2a3349] rounded-2xl rounded-tl-sm px-4 py-3 text-slate-200 text-sm leading-relaxed">
            {config.welcomeMessage}
          </div>
        </div>
      </div>

      {error && (
        <p className="text-rose-400 text-sm">{error}</p>
      )}

      {/* Acciones */}
      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-colors disabled:opacity-60
            ${saved
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-indigo-500 hover:bg-indigo-600 text-white"
            }`}
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {saved ? "Guardado" : saving ? "Guardando…" : "Guardar cambios"}
        </button>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-[#161b27] border border-[#2a3349] text-slate-400 hover:text-slate-200 transition-colors"
        >
          <RotateCcw size={16} />
          Restablecer
        </button>
      </div>
    </div>
  );
}
