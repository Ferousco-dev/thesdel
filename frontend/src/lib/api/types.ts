// Mirrors the backend Pydantic response/request models exactly. Keep this
// file in sync with the backend when either side changes a shape — see
// RULES.md #3 in this frontend's own rules file. Source of truth: the
// backend repo's app/*/schemas.py and docs/API.md.

export type Tier = "free" | "premium" | "pro";

export interface UserPublic {
  id: string;
  email: string;
  display_name: string;
  tier: Tier;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface ClassPublic {
  id: string;
  name: string;
  join_code: string;
  member_count: number;
  created_by: string;
}

export interface ClassPreview {
  id: string;
  name: string;
  member_count: number;
}

export interface MembershipPublic {
  class_id: string;
  role: "rep" | "member";
}

export interface TimetableEntryPublic {
  id: string;
  owner_type: "user" | "class";
  owner_id: string;
  subject: string;
  day_of_week: number; // 0-6
  start_time: string; // "HH:MM"
  end_time: string;
  location: string | null;
  recurrence: string | null;
}

export interface AnnouncementPublic {
  id: string;
  class_id: string;
  posted_by: string;
  content: string;
  pinned: boolean;
  created_at: string; // ISO 8601
}

export interface AnnouncementPage {
  items: AnnouncementPublic[];
  next_cursor: string | null;
}

export interface StudyBlockPublic {
  id: string;
  subject: string;
  priority: number | null;
  exam_date: string | null; // "YYYY-MM-DD"
  day_of_week: number;
  start_time: string;
  end_time: string;
  generated_at: string;
}

export interface RegenerateBlockResponse {
  block: StudyBlockPublic;
  remaining_regenerations: number;
}

export interface RoutinePublic {
  id: string;
  label: "Church" | "Gym" | "Work" | "Sleep" | "Meals" | "Personal";
  days: number[];
  start_time: string;
  end_time: string;
  is_flexible: boolean;
}

export interface LifeBlockPublic {
  id: string;
  source_type: "class" | "study" | "routine";
  source_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  conflict_flag: boolean;
  generated_at: string;
}

export interface FeatureCapStatus {
  feature: string;
  used: number;
  limit: number;
  remaining: number;
  resets_at: string;
}

export interface UsageStatusResponse {
  caps: FeatureCapStatus[];
}
