import type {
  ActionItem,
  Analytics,
  AskResponse,
  MeetingDetail,
  MeetingListItem,
  MeetingStatus,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export const api = {
  listMeetings: () => http<MeetingListItem[]>("/meetings"),

  getMeeting: (id: string) => http<MeetingDetail>(`/meetings/${id}`),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http<{ id: string; status: MeetingStatus }>("/meetings", {
      method: "POST",
      body: form,
    });
  },

  renameSpeakers: (id: string, names: Record<number, string>) =>
    http<MeetingDetail>(`/meetings/${id}/speakers`, jsonInit("PATCH", { names })),

  updateActionItem: (itemId: string, patch: Partial<Pick<ActionItem, "completed" | "task" | "owner" | "due">>) =>
    http<ActionItem>(`/action-items/${itemId}`, jsonInit("PATCH", patch)),

  ask: (question: string, sessionId?: string) =>
    http<AskResponse>("/ask", jsonInit("POST", { question, session_id: sessionId })),

  analytics: () => http<Analytics>("/analytics"),
};
