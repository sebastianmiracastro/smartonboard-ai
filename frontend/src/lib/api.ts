const BASE_URL = "http://localhost:8000";

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
  getUserHistory: (id: string) => request<any[]>(`/api/users/${id}/history`),

  // Departamentos
  getDepartments: () => request<any[]>("/api/departments/"),
  createDepartment: (data: any) =>
    request("/api/departments/", { method: "POST", body: JSON.stringify(data) }),

  // Roles
  getRoles: () => request<any[]>("/api/roles/"),

  // Documentos
  getDocuments: () => request<any[]>("/api/documents/"),
  deleteDocument: (id: string) =>
    request(`/api/documents/${id}`, { method: "DELETE" }),

  // Planes
  getPlans: () => request<any[]>("/api/plans/"),
  getPlanTasks: (planId: string) => request<any[]>(`/api/plans/${planId}/tasks`),

  // Tareas
  getMyTasks: () => request<any[]>("/api/tasks/my"),
  getUserTasks: (userId: string) => request<any[]>(`/api/tasks/user/${userId}`),
  completeTask: (id: string) =>
    request(`/api/tasks/${id}/complete`, { method: "PATCH" }),

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