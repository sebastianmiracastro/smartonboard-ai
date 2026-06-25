const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    throw new Error("Sesión expirada");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Error desconocido" }));
    throw new Error(error.detail || "Error en la petición");
  }

  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  // Usuarios
  getMe: () => request<any>("/api/users/me"),
  getUsers: () => request<any[]>("/api/users/"),
  getUser: (id: string) => request<any>(`/api/users/${id}`),
  createUser: (data: any) =>
    request<any>("/api/users/", { method: "POST", body: JSON.stringify(data) }),
  updateUser: (id: string, data: any) =>
    request<any>(`/api/users/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  changeUserPassword: (id: string, password: string) =>
    request<any>(`/api/users/${id}/password`, { method: "PATCH", body: JSON.stringify({ password }) }),
  getUserHistory: (id: string) => request<any[]>(`/api/users/${id}/history`),

  // Departamentos
  getDepartments: () => request<any[]>("/api/departments/"),
  createDepartment: (data: any) =>
    request<any>("/api/departments/", { method: "POST", body: JSON.stringify(data) }),
  deleteDepartment: (id: string) =>
    request(`/api/departments/${id}`, { method: "DELETE" }),

  // Roles / Cargos
  getRoles: () => request<any[]>("/api/roles/"),
  createRole: (data: any) =>
    request<any>("/api/roles/", { method: "POST", body: JSON.stringify(data) }),
  deleteRole: (id: string) =>
    request(`/api/roles/${id}`, { method: "DELETE" }),

  // Categorías de conocimiento (taxonomía fija de referencia)
  getCategories: () => request<any>("/api/config/categories"),

  // Documentos
  getDocuments: () => request<any[]>("/api/documents/"),
  deleteDocument: (id: string) =>
    request(`/api/documents/${id}`, { method: "DELETE" }),
  uploadDocument: async (file: File, params: Record<string, any> = {}) => {
    const token = getToken();
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") fd.append(k, String(v));
    });
    const res = await fetch(`${BASE_URL}/api/documents/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (res.status === 401) {
      if (typeof window !== "undefined") { localStorage.removeItem("token"); window.location.href = "/login"; }
      throw new Error("Sesión expirada");
    }
    if (!res.ok) {
      const e = await res.json().catch(() => ({ detail: "Error" }));
      throw new Error(e.detail || "Error al subir el documento");
    }
    return res.json();
  },

  // Planes de onboarding
  getPlans: () => request<any[]>("/api/plans/"),
  createPlan: (data: any) =>
    request<any>("/api/plans/", { method: "POST", body: JSON.stringify(data) }),
  updatePlan: (id: string, data: any) =>
    request<any>(`/api/plans/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deletePlan: (id: string) =>
    request(`/api/plans/${id}`, { method: "DELETE" }),
  getPlanTasks: (planId: string) => request<any[]>(`/api/plans/${planId}/tasks`),
  createPlanTask: (planId: string, data: any) =>
    request<any>(`/api/plans/${planId}/tasks`, { method: "POST", body: JSON.stringify(data) }),
  updatePlanTask: (taskId: string, data: any) =>
    request<any>(`/api/plans/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deletePlanTask: (taskId: string) =>
    request(`/api/plans/tasks/${taskId}`, { method: "DELETE" }),
  assignPlan: (planId: string, userId: string) =>
    request<any>(`/api/plans/${planId}/assign`, { method: "POST", body: JSON.stringify({ user_id: userId }) }),
  getUserAssignments: (userId: string) =>
    request<any[]>(`/api/plans/assignments/user/${userId}`),

  // Tareas
  getMyTasks: () => request<any[]>("/api/tasks/my"),
  getUserTasks: (userId: string) => request<any[]>(`/api/tasks/user/${userId}`),
  completeTask: (id: string) =>
    request(`/api/tasks/${id}/complete`, { method: "PATCH" }),

  // Ejecución del plan (portal del empleado)
  getMyPlans: () => request<any[]>("/api/tasks/my-plans"),
  startStep: (id: string) => request<any>(`/api/tasks/steps/${id}/start`, { method: "POST" }),
  pauseStep: (id: string) => request<any>(`/api/tasks/steps/${id}/pause`, { method: "POST" }),
  completeStep: (id: string) => request<any>(`/api/tasks/steps/${id}/complete`, { method: "POST" }),
  getStepQuiz: (id: string) => request<any>(`/api/tasks/steps/${id}/quiz`),
  submitQuiz: (id: string, answers: any[]) =>
    request<any>(`/api/tasks/steps/${id}/quiz`, { method: "POST", body: JSON.stringify({ answers }) }),

  // Chat
  getConversations: () => request<any[]>("/api/chat/conversations"),
  createConversation: () =>
    request<any>("/api/chat/conversations", { method: "POST" }),
  deleteConversation: (convId: string) =>
    request(`/api/chat/conversations/${convId}`, { method: "DELETE" }),
  getMessages: (convId: string) =>
    request<any[]>(`/api/chat/conversations/${convId}/messages`),
  sendMessage: (convId: string, content: string) =>
    request<any>(`/api/chat/conversations/${convId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  // Configuración del agente IA
  getAgentConfig: () => request<any>("/api/config/agent"),
  updateAgentConfig: (data: any) =>
    request<any>("/api/config/agent", { method: "PUT", body: JSON.stringify(data) }),

  // Evaluación / Analítica
  getCompanySummary: () => request<any>("/api/evaluation/company/summary"),
  getCompanyAnalytics: () => request<any>("/api/evaluation/company/analytics"),
  getUserStats: (userId: string) => request<any>(`/api/evaluation/stats/${userId}`),
  getUserInsights: (userId: string) =>
    request<any>(`/api/evaluation/insights/${userId}`),
  // Métricas de conocimiento (cobertura, comprensión, pérdida de conocimiento)
  getUserKnowledge: (userId: string) =>
    request<any>(`/api/evaluation/knowledge/${userId}`),
  getCompanyKnowledgeMap: () =>
    request<any>("/api/evaluation/company/knowledge-map"),
  getUserOnboarding: (userId: string) =>
    request<any>(`/api/evaluation/onboarding/${userId}`),
  getAlerts: () => request<any>("/api/evaluation/alerts"),
  resolveAlert: (alertId: string) =>
    request(`/api/evaluation/alerts/${alertId}/resolve`, { method: "PATCH" }),

  // Nómina
  getPayrollMetrics: () => request<any>("/api/payroll/metrics"),
  getConcepts: () => request<any[]>("/api/payroll/concepts"),
  createConcept: (data: any) =>
    request<any>("/api/payroll/concepts", { method: "POST", body: JSON.stringify(data) }),
  updateConcept: (id: string, data: any) =>
    request<any>(`/api/payroll/concepts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteConcept: (id: string) =>
    request(`/api/payroll/concepts/${id}`, { method: "DELETE" }),
  getPeriods: () => request<any[]>("/api/payroll/periods"),
  getPeriod: (id: string) => request<any>(`/api/payroll/periods/${id}`),
  createPeriod: (data: any) =>
    request<any>("/api/payroll/periods", { method: "POST", body: JSON.stringify(data) }),
  createSettlement: (data: any) =>
    request<any>("/api/payroll/settlement", { method: "POST", body: JSON.stringify(data) }),
  payPeriod: (id: string) =>
    request<any>(`/api/payroll/periods/${id}/pay`, { method: "PATCH" }),
  deletePeriod: (id: string) =>
    request(`/api/payroll/periods/${id}`, { method: "DELETE" }),
  getMonthlySummary: () => request<any[]>("/api/payroll/monthly-summary"),
  getEmployeePayslips: (userId: string) =>
    request<any[]>(`/api/payroll/employees/${userId}/payslips`),
  getNovelties: (onlyPending = false) =>
    request<any[]>(`/api/payroll/novelties${onlyPending ? "?only_pending=true" : ""}`),
  createNovelty: (data: any) =>
    request<any>("/api/payroll/novelties", { method: "POST", body: JSON.stringify(data) }),
  deleteNovelty: (id: string) =>
    request(`/api/payroll/novelties/${id}`, { method: "DELETE" }),
};