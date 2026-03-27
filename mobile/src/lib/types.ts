// TypeScript types matching backend Pydantic schemas

export interface Company {
  id: number;
  yclients_id: string;
  name: string;
  city: string | null;
  region: string | null;
  is_active: boolean;
}

export interface PartnerProfile {
  id: number;
  full_name: string;
  phone_masked: string;
  status: string;
  is_owner: boolean;
  position: string | null;
  companies: Company[];
  has_pending_branch: boolean;
  pending_branch_text: string | null;
  created_at: string | null;
  verified_at: string | null;
}

export interface CompanyStats {
  name: string;
  yclients_id: string | null;
  revenue: number;
  completed_count: number;
  total_count: number;
  rank: number;
  total_companies: number;
  rank_change: number;
  avg_check: number;
  error: string | null;
}

export interface PeriodStats {
  period_type: string;
  period_label: string;
  date_from: string;
  date_to: string;
  companies: CompanyStats[];
  total_revenue: number;
  total_completed: number;
}

export interface RatingEntry {
  rank: number;
  yclients_company_id: string;
  company_name: string;
  location: string;
  region: string | null;
  revenue: number;
  avg_check: number;
  rank_change: number;
  is_partner: boolean;
}

export interface Rating {
  period_label: string;
  total_companies: number;
  entries: RatingEntry[];
  partner_ranks: number[];
}

export type StatsPeriod = "today" | "yesterday" | "current_month" | "prev_month";
export type RatingPeriod = "current" | "previous";

export interface Department {
  key: string;
  name: string;
}

export interface DepartmentButton {
  id: number;
  button_text: string;
  message_text: string;
}

export interface Task {
  id: number;
  title: string;
  barbershop: string | null;
  department_name: string;
  stage: string;
  stage_emoji: string;
  created_at: string;
  group_id: string;
}

export interface TaskCreateRequest {
  department_key: string;
  barbershop: string;
  title: string;
  description: string;
}

export interface AIResponse {
  answer: string;
}

export interface ContactInfo {
  text: string;
}

export interface PollOption {
  id: number;
  text: string;
  position: number;
}

export interface Poll {
  id: number;
  question: string;
  options: PollOption[];
  status: string;
  created_at: string;
}
