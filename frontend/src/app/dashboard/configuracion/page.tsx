"use client";

import { useState } from "react";
import { Bot, Save, RotateCcw, Shield, Sliders, MessageSquare } from "lucide-react";

export default function ConfiguracionPage() {
  const [config, setConfig] = useState({
    agentName: "Asistente de onboarding",
    welcomeMessage: "Hola 👋 Soy tu asistente de onboarding. Estoy aquí para ayudarte con cualquier duda sobre la empresa, tu rol, procesos o herramientas.",
    model: "gpt-4o-mini",
    temperature: 0.3,
    maxTokens: 1000,
    ragTopK: 5,
    requireSources: true,
    allowGeneralQuestions: true,
    blockSalaryQuestions: true,
    blockPersonalData: true,
  });

  const [saved, setSaved] = useState(false);

  const save = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex flex-col gap-6 max-w-3xl">

      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-semibold">Configuración del agente</h1>
        <p className="text-slate-400 text-sm mt-1">
          Personaliza el comportamiento del agente IA para tu empresa
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
              <option value="claude-sonnet">Claude Sonnet</option>
              <option value="llama-3-finetuned">Llama 3 (fine-tuned)</option>
            </select>
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

      {/* Acciones */}
      <div className="flex items-center gap-3">
        <button
          onClick={save}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-colors
            ${saved
              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
              : "bg-indigo-500 hover:bg-indigo-600 text-white"
            }`}
        >
          <Save size={16} />
          {saved ? "Guardado" : "Guardar cambios"}
        </button>
        <button className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium bg-[#161b27] border border-[#2a3349] text-slate-400 hover:text-slate-200 transition-colors">
          <RotateCcw size={16} />
          Restablecer
        </button>
      </div>
    </div>
  );
}