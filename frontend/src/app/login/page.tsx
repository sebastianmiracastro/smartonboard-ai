"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Zap } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Simulamos autenticación con mock data
    await new Promise((r) => setTimeout(r, 800));
    if (email.includes("rrhh") || email === "andrea.salcedo@techcorp.co") {
      router.push("/dashboard");
    } else {
      router.push("/portal/inicio");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#0f1117] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-10 h-10 bg-indigo-500 rounded-xl flex items-center justify-center">
            <Zap size={20} className="text-white" />
          </div>
          <span className="text-white text-xl font-semibold tracking-tight">
            SmartOnboard <span className="text-indigo-400">AI</span>
          </span>
        </div>

        {/* Card */}
        <div className="bg-[#161b27] border border-[#2a3349] rounded-2xl p-8">
          <h1 className="text-white text-2xl font-semibold mb-1">
            Bienvenido
          </h1>
          <p className="text-slate-400 text-sm mb-6">
            Inicia sesión en tu cuenta
          </p>

          <form onSubmit={handleLogin} className="flex flex-col gap-4">
            <div>
              <label className="text-slate-300 text-sm font-medium mb-1.5 block">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@empresa.com"
                required
                className="w-full bg-[#1e2536] border border-[#2a3349] text-white placeholder-slate-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div>
              <label className="text-slate-300 text-sm font-medium mb-1.5 block">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-[#1e2536] border border-[#2a3349] text-white placeholder-slate-500 rounded-xl px-4 py-3 pr-11 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="flex justify-end">
              <button type="button" className="text-indigo-400 text-sm hover:text-indigo-300 transition-colors">
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-500 hover:bg-indigo-600 disabled:opacity-60 text-white font-medium py-3 rounded-xl text-sm transition-colors mt-1"
            >
              {loading ? "Ingresando..." : "Iniciar sesión"}
            </button>
          </form>

          {/* Accesos rápidos para demo */}
          <div className="mt-6 pt-6 border-t border-[#2a3349]">
            <p className="text-slate-500 text-xs text-center mb-3">
              Accesos rápidos (demo)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => { setEmail("andrea.salcedo@techcorp.co"); setPassword("demo123"); }}
                className="flex-1 bg-[#1e2536] hover:bg-[#2a3349] border border-[#2a3349] text-slate-300 text-xs py-2 rounded-lg transition-colors"
              >
                Panel RR.HH.
              </button>
              <button
                onClick={() => { setEmail("carlos.mejia@techcorp.co"); setPassword("demo123"); }}
                className="flex-1 bg-[#1e2536] hover:bg-[#2a3349] border border-[#2a3349] text-slate-300 text-xs py-2 rounded-lg transition-colors"
              >
                Portal Empleado
              </button>
            </div>
          </div>
        </div>

        <p className="text-slate-600 text-xs text-center mt-6">
          © 2026 SmartOnboard AI · Politécnico Grancolombiano
        </p>
      </div>
    </div>
  );
}