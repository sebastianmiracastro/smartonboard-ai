"use client";

import { useState, useRef, useEffect } from "react";
import { Send, FileText, Bot } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { name: string; page?: number }[];
}

const mockResponses: Record<string, { content: string; sources?: { name: string; page?: number }[] }> = {
  default: {
    content: "Entiendo tu pregunta. Basándome en los documentos disponibles de TechCorp, puedo ayudarte con información sobre procesos internos, tu rol, políticas de la empresa y herramientas. ¿Puedes ser más específico sobre lo que necesitas?",
  },
  vacaciones: {
    content: "Para solicitar vacaciones debes: (1) ingresar al portal de RR.HH. con al menos 15 días de anticipación, (2) diligenciar el formulario de solicitud, (3) esperar aprobación de tu líder directo. El proceso completo tarda máximo 3 días hábiles.",
    sources: [{ name: "Manual de empleados 2026.pdf", page: 14 }],
  },
  responsabilidades: {
    content: "Como Desarrollador Junior tus responsabilidades principales son: implementar y mantener endpoints REST, escribir pruebas unitarias con cobertura mínima del 80%, participar en code reviews, y documentar todos los cambios en el repositorio.",
    sources: [{ name: "Manual de Roles.pdf", page: 12 }],
  },
  jira: {
    content: "Para mover un ticket en Jira: (1) abre el ticket desde tu tablero, (2) arrastra la tarjeta a la columna correspondiente o usa el botón de transición dentro del ticket. Los estados disponibles son: To Do, In Progress, In Review y Done.",
    sources: [{ name: "Guía de herramientas.pdf", page: 3 }],
  },
  salario: {
    content: "No tengo acceso a información sobre salarios en los documentos disponibles para tu perfil. Para consultas sobre compensación te recomiendo contactar directamente a RR.HH.",
  },
};

function getResponse(message: string) {
  const lower = message.toLowerCase();
  if (lower.includes("vacacion") || lower.includes("vacaciones")) return mockResponses.vacaciones;
  if (lower.includes("responsabilidad") || lower.includes("rol") || lower.includes("función")) return mockResponses.responsabilidades;
  if (lower.includes("jira") || lower.includes("ticket") || lower.includes("tarea")) return mockResponses.jira;
  if (lower.includes("salario") || lower.includes("sueldo") || lower.includes("pago")) return mockResponses.salario;
  return mockResponses.default;
}

const suggestions = [
  "¿Cuáles son mis responsabilidades?",
  "¿Cómo solicito vacaciones?",
  "¿Cómo muevo un ticket en Jira?",
  "¿A quién le reporto?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hola Carlos 👋 Soy tu asistente de onboarding. Estoy aquí para ayudarte con cualquier duda sobre la empresa, tu rol, procesos o herramientas. ¿En qué te puedo ayudar hoy?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const content = text || input.trim();
    if (!content || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    // Simular delay del backend
    await new Promise((r) => setTimeout(r, 1000));

    const response = getResponse(content);
    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: response.content,
      sources: response.sources,
    };

    setMessages((prev) => [...prev, assistantMsg]);
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">

      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-[#2a3349] mb-4">
        <div className="w-9 h-9 bg-indigo-500/20 border border-indigo-500/20 rounded-xl flex items-center justify-center">
          <Bot size={18} className="text-indigo-400" />
        </div>
        <div>
          <p className="text-white font-semibold text-sm">Asistente de onboarding</p>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
            <span className="text-emerald-400 text-xs">En línea</span>
          </div>
        </div>
      </div>

      {/* Mensajes */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-4 pb-4">

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>

            {/* Avatar */}
            <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-semibold
              ${msg.role === "user"
                ? "bg-indigo-500/20 border border-indigo-500/20 text-indigo-400"
                : "bg-[#1e2536] border border-[#2a3349] text-slate-400"
              }`}
            >
              {msg.role === "user" ? "CM" : "IA"}
            </div>

            <div className={`max-w-[75%] flex flex-col gap-2 ${msg.role === "user" ? "items-end" : "items-start"}`}>
              {/* Burbuja */}
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
                ${msg.role === "user"
                  ? "bg-indigo-500 text-white rounded-tr-sm"
                  : "bg-[#161b27] border border-[#2a3349] text-slate-200 rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>

              {/* Fuentes */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {msg.sources.map((src, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-1.5 bg-[#1e2536] border border-[#2a3349] rounded-lg px-2.5 py-1"
                    >
                      <FileText size={10} className="text-slate-500" />
                      <span className="text-slate-400 text-xs">
                        {src.name}{src.page ? ` — pág. ${src.page}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-[#1e2536] border border-[#2a3349] flex items-center justify-center text-xs text-slate-400 shrink-0">
              IA
            </div>
            <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Sugerencias */}
      {messages.length === 1 && (
        <div className="flex flex-wrap gap-2 pb-3">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="bg-[#161b27] border border-[#2a3349] hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 text-xs px-3 py-2 rounded-xl transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-3 pt-3 border-t border-[#2a3349]">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Escribe tu pregunta..."
          className="flex-1 bg-[#161b27] border border-[#2a3349] text-white placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <button
          onClick={() => sendMessage()}
          disabled={!input.trim() || loading}
          className="w-11 h-11 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-40 rounded-xl flex items-center justify-center transition-colors shrink-0"
        >
          <Send size={16} className="text-white" />
        </button>
      </div>
    </div>
  );
}