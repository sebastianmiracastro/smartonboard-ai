"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Mail, Calendar, Building2, Briefcase, CheckCircle2, Clock, Circle, AlertCircle } from "lucide-react";
import { mockEmployees } from "@/mock/data";

const categoryColors: Record<string, string> = {
  procesos: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  rol: "bg-violet-500/10 text-violet-400 border border-violet-500/20",
  cultura: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  herramientas: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  relaciones: "bg-pink-500/10 text-pink-400 border border-pink-500/20",
};

const categoryLabels: Record<string, string> = {
  procesos: "Procesos internos",
  rol: "Rol y funciones",
  cultura: "Cultura y políticas",
  herramientas: "Herramientas",
  relaciones: "Relaciones de equipo",
};

const mockScores = [
  { category: "cultura", score: 91, questions: 14, note: "Comprende bien las normas y beneficios" },
  { category: "procesos", score: 82, questions: 9, note: "Buen entendimiento del flujo de trabajo" },
  { category: "relaciones", score: 60, questions: 5, note: "Aún no identifica bien a quién escalar" },
  { category: "rol", score: 45, questions: 11, note: "Repite preguntas sobre sus responsabilidades" },
  { category: "herramientas", score: 30, questions: 8, note: "Mucha confusión con Jira y Git" },
];

const mockTasks = [
  { id: "t1", title: "Leer manual de empleados", category: "lectura", status: "completada", day: 1 },
  { id: "t2", title: "Reunión con Tech Lead", category: "reunion", status: "completada", day: 2 },
  { id: "t3", title: "Configurar entorno de desarrollo", category: "configuracion", status: "completada", day: 3 },
  { id: "t4", title: "Revisar política de seguridad IT", category: "lectura", status: "en_progreso", day: 4 },
  { id: "t5", title: "Primer PR de prueba", category: "entregable", status: "pendiente", day: 5 },
  { id: "t6", title: "Code review con el equipo", category: "reunion", status: "pendiente", day: 6 },
];

const taskStatusIcon = (status: string) => {
  if (status === "completada") return <CheckCircle2 size={16} className="text-emerald-400" />;
  if (status === "en_progreso") return <Clock size={16} className="text-amber-400" />;
  if (status === "bloqueada") return <AlertCircle size={16} className="text-red-400" />;
  return <Circle size={16} className="text-slate-500" />;
};

const scoreColor = (score: number) => {
  if (score >= 75) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
};

const scoreTextColor = (score: number) => {
  if (score >= 75) return "text-emerald-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
};

export default function EmpleadoDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const emp = mockEmployees.find((e) => e.id === id);

  if (!emp) return (
    <div className="text-slate-400 text-sm">Empleado no encontrado.</div>
  );

  const globalScore = Math.round(
    mockScores.reduce((a, s) => a + s.score, 0) / mockScores.length
  );

  return (
    <div className="flex flex-col gap-6">

      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors w-fit"
      >
        <ArrowLeft size={16} /> Volver a empleados
      </button>

      {/* Header empleado */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-6 flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-indigo-500/20 border border-indigo-500/20 rounded-2xl flex items-center justify-center">
            <span className="text-indigo-400 text-lg font-semibold">
              {emp.fullName.split(" ").map((n) => n[0]).join("").slice(0, 2)}
            </span>
          </div>
          <div>
            <h1 className="text-white text-xl font-semibold">{emp.fullName}</h1>
            <div className="flex items-center gap-4 mt-1.5">
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Mail size={12} /> {emp.email}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Building2 size={12} /> {emp.department}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Briefcase size={12} /> {emp.role}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                <Calendar size={12} /> Desde {emp.startDate}
              </span>
            </div>
          </div>
        </div>

        {/* Score global */}
        <div className="text-right">
          <p className="text-slate-500 text-xs mb-1">Score global</p>
          <p className={`text-3xl font-semibold ${scoreTextColor(globalScore)}`}>{globalScore}%</p>
          <p className="text-slate-500 text-xs">comprensión general</p>
        </div>
      </div>

      {/* Progreso onboarding */}
      <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-white font-medium">Progreso de onboarding</p>
          <span className="text-slate-400 text-sm">Día {emp.onboardingDay} de {emp.onboardingTotalDays}</span>
        </div>
        <div className="h-2 bg-[#2a3349] rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all"
            style={{ width: `${emp.progress}%` }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-slate-500 text-xs">Inicio</span>
          <span className="text-indigo-400 text-xs font-medium">{emp.progress}%</span>
          <span className="text-slate-500 text-xs">Meta</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">

        {/* Comprensión por categoría */}
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-4">Comprensión por categoría</h2>
          <div className="flex flex-col gap-4">
            {mockScores.map((s) => (
              <div key={s.category}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-300 text-sm">{categoryLabels[s.category]}</span>
                  <span className={`text-sm font-semibold ${scoreTextColor(s.score)}`}>{s.score}%</span>
                </div>
                <div className="h-1.5 bg-[#2a3349] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${scoreColor(s.score)}`}
                    style={{ width: `${s.score}%` }}
                  />
                </div>
                <p className="text-slate-600 text-xs mt-1">{s.questions} preguntas · {s.note}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Tareas */}
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-5">
          <h2 className="text-white font-semibold mb-4">Tareas del plan</h2>
          <div className="flex flex-col gap-2">
            {mockTasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center gap-3 p-3 bg-[#1e2536]/50 rounded-xl border border-[#2a3349]"
              >
                {taskStatusIcon(task.status)}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm truncate ${task.status === "completada" ? "text-slate-500 line-through" : "text-white"}`}>
                    {task.title}
                  </p>
                  <p className="text-slate-600 text-xs">Día {task.day}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${categoryColors[task.category] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                  {task.category}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}