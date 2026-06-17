"use client";

import { useState, useRef, useEffect } from "react";
import { Send, FileText, Bot, Plus, Trash2, MessageSquare } from "lucide-react";
import { api } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: { name: string; page?: number }[];
}

interface Conversation {
  id: string;
  title: string | null;
  created_at?: string;
}

const suggestions = [
  "¿Cuáles son mis responsabilidades?",
  "¿Cómo solicito vacaciones?",
  "¿Cómo muevo un ticket en Jira?",
  "¿A quién le reporto?",
];

const WELCOME: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hola 👋 Soy tu asistente de onboarding. Estoy aquí para ayudarte con cualquier duda sobre la empresa, tu rol, procesos o herramientas. ¿En qué te puedo ayudar hoy?",
};

function parseSources(raw?: string | null): Message["sources"] {
  if (!raw) return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = async (): Promise<Conversation[]> => {
    const convs = await api.getConversations();
    setConversations(convs || []);
    return convs || [];
  };

  const loadMessages = async (id: string) => {
    const history = await api.getMessages(id);
    const restored: Message[] = history.map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      sources: parseSources(m.sources),
    }));
    setMessages([WELCOME, ...restored]);
  };

  useEffect(() => {
    const init = async () => {
      try {
        const convs = await loadConversations();
        let active: Conversation;
        if (convs.length > 0) {
          active = convs[0];
        } else {
          active = await api.createConversation();
          setConversations([active]);
        }
        setConvId(active.id);
        await loadMessages(active.id);
      } catch (err) {
        console.error(err);
        setMessages([WELCOME]);
      } finally {
        setInitializing(false);
      }
    };
    init();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selectConversation = async (id: string) => {
    if (id === convId || loading) return;
    setConvId(id);
    setMessages([WELCOME]);
    try {
      await loadMessages(id);
    } catch (err) {
      console.error(err);
    }
  };

  const newConversation = async () => {
    if (loading) return;
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setConvId(conv.id);
      setMessages([WELCOME]);
    } catch (err) {
      console.error(err);
    }
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (id === convId) {
        if (remaining.length > 0) {
          await selectConversation(remaining[0].id);
        } else {
          await newConversation();
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const sendMessage = async (text?: string) => {
    const content = text || input.trim();
    if (!content || loading || !convId) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await api.sendMessage(convId, content);
      const assistantMsg: Message = {
        id: response.id,
        role: "assistant",
        content: response.content,
        sources: parseSources(response.sources),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      // Refrescar la lista para reflejar el título automático generado
      loadConversations().catch(() => {});
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: "Ocurrió un error al procesar tu pregunta. Por favor intenta de nuevo.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (initializing)
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 text-sm">Iniciando conversación...</div>
      </div>
    );

  return (
    <div className="flex gap-4 h-[calc(100vh-48px)]">
      {/* Panel de conversaciones */}
      <aside className="w-64 shrink-0 flex flex-col bg-[#161b27] border border-[#2a3349] rounded-2xl overflow-hidden">
        <div className="p-3 border-b border-[#2a3349]">
          <button
            onClick={newConversation}
            className="w-full flex items-center justify-center gap-2 bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium rounded-xl px-3 py-2.5 transition-colors"
          >
            <Plus size={16} />
            Nueva conversación
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
          {conversations.length === 0 && (
            <p className="text-slate-500 text-xs text-center px-3 py-6">
              Aún no tienes conversaciones.
            </p>
          )}
          {conversations.map((conv) => {
            const active = conv.id === convId;
            return (
              <div
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-colors
                  ${active
                    ? "bg-indigo-500/10 text-indigo-300"
                    : "text-slate-400 hover:text-slate-200 hover:bg-[#1e2536]"
                  }`}
              >
                <MessageSquare size={15} className="shrink-0" />
                <span className="flex-1 text-sm truncate">
                  {conv.title || "Nueva conversación"}
                </span>
                <button
                  onClick={(e) => deleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-opacity shrink-0"
                  title="Eliminar conversación"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
        </div>
      </aside>

      {/* Chat */}
      <div className="flex-1 flex flex-col min-w-0">
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
              <div className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-semibold
                ${msg.role === "user"
                  ? "bg-indigo-500/20 border border-indigo-500/20 text-indigo-400"
                  : "bg-[#1e2536] border border-[#2a3349] text-slate-400"
                }`}
              >
                {msg.role === "user" ? "CM" : "IA"}
              </div>

              <div className={`max-w-[75%] flex flex-col gap-2 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap
                  ${msg.role === "user"
                    ? "bg-indigo-500 text-white rounded-tr-sm"
                    : "bg-[#161b27] border border-[#2a3349] text-slate-200 rounded-tl-sm"
                  }`}
                >
                  {msg.content}
                </div>

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
    </div>
  );
}
