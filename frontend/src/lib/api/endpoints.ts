// One function per backend endpoint (docs/API.md §10). Keep endpoints.ts
// as the ONLY place that calls apiRequest directly — components/hooks call
// these functions, never fetch()/apiRequest() inline. This is what keeps
// the frontend/backend contract in one auditable place — see RULES.md.

import { apiRequest } from "./client";
import type {
  AnnouncementPage,
  AnnouncementPublic,
  ClassPreview,
  ClassPublic,
  LifeBlockPublic,
  MembershipPublic,
  RegenerateBlockResponse,
  RoutinePublic,
  StudyBlockPublic,
  TimetableEntryPublic,
  TokenPairResponse,
  UsageStatusResponse,
  UserPublic,
} from "./types";

// --- auth ---

export function register(input: { email: string; password: string; display_name: string }) {
  return apiRequest<TokenPairResponse & { user: UserPublic }>("/v1/auth/register", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export function login(input: { email: string; password: string }) {
  return apiRequest<TokenPairResponse & { user: UserPublic }>("/v1/auth/login", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export function googleAuth(idToken: string) {
  return apiRequest<TokenPairResponse & { user: UserPublic }>("/v1/auth/google", {
    method: "POST",
    body: { id_token: idToken },
    auth: false,
  });
}

export function logout(refreshToken: string) {
  return apiRequest<void>("/v1/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    auth: false,
  });
}

// --- users ---

export function getMe() {
  return apiRequest<UserPublic>("/v1/users/me");
}

// --- classes ---

export function createClass(name: string) {
  return apiRequest<ClassPublic>("/v1/classes", { method: "POST", body: { name } });
}

export function previewClass(joinCode: string) {
  return apiRequest<ClassPreview>(`/v1/classes/preview?join_code=${encodeURIComponent(joinCode)}`);
}

export function joinClass(joinCode: string) {
  return apiRequest<MembershipPublic>("/v1/classes/join", {
    method: "POST",
    body: { join_code: joinCode },
  });
}

export function getClass(classId: string) {
  return apiRequest<ClassPublic>(`/v1/classes/${classId}`);
}

// --- timetable ---

export interface TimetableEntryInput {
  subject: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  location?: string | null;
  recurrence?: string | null;
}

export function listMyTimetable() {
  return apiRequest<TimetableEntryPublic[]>("/v1/timetable");
}

export function createMyTimetableEntry(input: TimetableEntryInput) {
  return apiRequest<TimetableEntryPublic>("/v1/timetable", { method: "POST", body: input });
}

export function updateMyTimetableEntry(entryId: string, input: Partial<TimetableEntryInput>) {
  return apiRequest<TimetableEntryPublic>(`/v1/timetable/${entryId}`, {
    method: "PATCH",
    body: input,
  });
}

export function deleteMyTimetableEntry(entryId: string) {
  return apiRequest<void>(`/v1/timetable/${entryId}`, { method: "DELETE" });
}

export function listClassTimetable(classId: string) {
  return apiRequest<TimetableEntryPublic[]>(`/v1/timetable/class/${classId}`);
}

export function createClassTimetableEntry(classId: string, input: TimetableEntryInput) {
  return apiRequest<TimetableEntryPublic>(`/v1/timetable/class/${classId}`, {
    method: "POST",
    body: input,
  });
}

// --- announcements ---

export function listAnnouncements(classId: string, cursor?: string) {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return apiRequest<AnnouncementPage>(`/v1/classes/${classId}/announcements${query}`);
}

export function postAnnouncement(classId: string, content: string) {
  return apiRequest<AnnouncementPublic>(`/v1/classes/${classId}/announcements`, {
    method: "POST",
    body: { content },
  });
}

export function updateAnnouncement(
  classId: string,
  announcementId: string,
  input: { content?: string; pinned?: boolean },
) {
  return apiRequest<AnnouncementPublic>(`/v1/classes/${classId}/announcements/${announcementId}`, {
    method: "PATCH",
    body: input,
  });
}

// --- litheral: study (Premium+) ---

export interface SubjectInput {
  subject: string;
  priority?: number | null;
  exam_date?: string | null;
}

export function generateStudyPlan(subjects: SubjectInput[] = []) {
  return apiRequest<StudyBlockPublic[]>("/v1/litheral/study/generate", {
    method: "POST",
    body: { subjects },
  });
}

export function listStudyPlan() {
  return apiRequest<StudyBlockPublic[]>("/v1/litheral/study");
}

export function regenerateStudyBlock(blockId: string) {
  return apiRequest<RegenerateBlockResponse>(`/v1/litheral/study/${blockId}/regenerate`, {
    method: "POST",
  });
}

// --- litheral: routines + life (Pro) ---

export interface RoutineInput {
  label: RoutinePublic["label"];
  days: number[];
  start_time: string;
  end_time: string;
  is_flexible?: boolean;
}

export function listRoutines() {
  return apiRequest<RoutinePublic[]>("/v1/litheral/routines");
}

export function createRoutine(input: RoutineInput) {
  return apiRequest<RoutinePublic>("/v1/litheral/routines", { method: "POST", body: input });
}

export function updateRoutine(routineId: string, input: Partial<RoutineInput>) {
  return apiRequest<RoutinePublic>(`/v1/litheral/routines/${routineId}`, {
    method: "PATCH",
    body: input,
  });
}

export function deleteRoutine(routineId: string) {
  return apiRequest<void>(`/v1/litheral/routines/${routineId}`, { method: "DELETE" });
}

export function generateLifeSchedule() {
  return apiRequest<LifeBlockPublic[]>("/v1/litheral/life/generate", { method: "POST" });
}

export function listLifeSchedule() {
  return apiRequest<LifeBlockPublic[]>("/v1/litheral/life");
}

export function adjustLifeSchedule() {
  return apiRequest<LifeBlockPublic[]>("/v1/litheral/life/adjust", { method: "POST" });
}

// --- usage ---

export function getAiUsage() {
  return apiRequest<UsageStatusResponse>("/v1/usage/ai");
}
