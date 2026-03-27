// Typed fetch wrapper for the Borodach Mobile API

import { API_URL, PARTNER_ID } from "./config";
import type {
  PartnerProfile,
  Company,
  PeriodStats,
  Rating,
  StatsPeriod,
  RatingPeriod,
  Department,
  DepartmentButton,
  Task,
  TaskCreateRequest,
  AIResponse,
  ContactInfo,
  Poll,
} from "./types";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string): Promise<T> {
  const url = `${API_URL}/api/v1${path}`;
  const res = await fetch(url, {
    headers: {
      "X-Partner-ID": String(PARTNER_ID),
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

async function requestPost<T>(path: string, body: unknown): Promise<T> {
  const url = `${API_URL}/api/v1${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "X-Partner-ID": String(PARTNER_ID),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getProfile: () => request<PartnerProfile>("/me"),

  getCompanies: () => request<Company[]>("/companies"),

  getStats: (period: StatsPeriod) =>
    request<PeriodStats>(`/stats/${period}`),

  getRating: (period: RatingPeriod) =>
    request<Rating>(`/rating/${period}`),

  health: () => request<{ status: string; version: string }>("/health"),

  getDepartments: () => request<Department[]>("/useful/departments"),
  getDepartmentButtons: (deptKey: string) =>
    request<DepartmentButton[]>(`/useful/departments/${deptKey}/buttons`),

  getTaskDepartments: () => request<Department[]>("/tasks/departments"),
  getTasks: (activeOnly = true) =>
    request<Task[]>(`/tasks?active_only=${activeOnly}`),
  createTask: (data: TaskCreateRequest) =>
    requestPost<{ task_id: number }>("/tasks", data),
  cancelTask: (taskId: number) =>
    requestPost<{ success: boolean }>(`/tasks/${taskId}/cancel`, {}),

  askAI: (question: string, detailed = false) =>
    requestPost<AIResponse>("/ai/ask", { question, detailed }),

  getContactInfo: () => request<ContactInfo>("/contact-office"),

  getPolls: () => request<Poll[]>("/polls"),
  votePoll: (pollId: number, optionIds: number[]) =>
    requestPost<{ success: boolean }>(`/polls/${pollId}/vote`, {
      option_ids: optionIds,
    }),
};
