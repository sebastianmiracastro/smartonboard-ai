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

  // Departamentos
  getDepartments: () => request<any[]>("/api/departments/"),
  createDepartment: (data: any) =>
    request("/api/departments/", { method: "POST", body: JSON.stringify(data) }),

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
    request("/api/chat/conversations", { method: "POST" }),
  getMessages: (convId: string) =>
    request<any[]>(`/api/chat/conversations/${convId}/messages`),
  sendMessage: (convId: string, content: string) =>
    request(`/api/chat/conversations/${convId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
};