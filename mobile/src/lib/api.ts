// Typed fetch wrapper for the Borodach Mobile API

import { API_URL, PARTNER_ID } from "./config";
import type {
  PartnerProfile,
  Company,
  PeriodStats,
  Rating,
  StatsPeriod,
  RatingPeriod,
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

export const api = {
  getProfile: () => request<PartnerProfile>("/me"),

  getCompanies: () => request<Company[]>("/companies"),

  getStats: (period: StatsPeriod) =>
    request<PeriodStats>(`/stats/${period}`),

  getRating: (period: RatingPeriod) =>
    request<Rating>(`/rating/${period}`),

  health: () => request<{ status: string; version: string }>("/health"),
};
