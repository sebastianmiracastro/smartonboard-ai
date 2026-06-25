"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// El módulo de Departamentos se integró en "Parametrización de empresa".
// Se mantiene esta ruta como redirección para no romper enlaces guardados.
export default function DepartamentosRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard/parametrizacion");
  }, [router]);
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-slate-400 text-sm">Redirigiendo a Parametrización…</div>
    </div>
  );
}
