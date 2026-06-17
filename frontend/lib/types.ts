export type MeetingStatus =
  | "uploaded"
  | "transcribing"
  | "extracting"
  | "indexing"
  | "done"
  | "failed";

export interface MeetingListItem {
  id: string;
  title: string;
  filename: string;
  status: MeetingStatus;
  duration_sec: number | null;
  created_at: string;
  action_item_count: number;
}

export interface Speaker {
  label: number;
  display_name: string | null;
}

export interface Segment {
  idx: number;
  speaker_label: number;
  start_sec: number;
  end_sec: number;
  text: string;
}

export interface Summary {
  overview: string;
  attendees: string[];
  key_decisions: string[];
  discussion_points: string[];
  open_questions: string[];
  next_steps: string[];
}

export interface ActionItem {
  id: string;
  task: string;
  owner: string | null;
  due: string | null;
  completed: boolean;
}

export interface TalkTime {
  participant: string;
  seconds: number;
}

export interface MeetingDetail {
  id: string;
  title: string;
  filename: string;
  status: MeetingStatus;
  error: string | null;
  duration_sec: number | null;
  language: string | null;
  created_at: string;
  speakers: Speaker[];
  segments: Segment[];
  summary: Summary | null;
  action_items: ActionItem[];
  topics: string[];
  talk_time: TalkTime[];
}

export interface RetrievedChunk {
  chunk_id: string;
  meeting_id: string;
  meeting_title: string;
  text: string;
  start_sec: number;
  end_sec: number;
  score: number;
}

export interface AskResponse {
  answer: string;
  sources: RetrievedChunk[];
}

export interface Analytics {
  total_meetings: number;
  total_duration_sec: number;
  action_items: { total: number; completed: number; rate: number };
  meetings_per_week: { period: string; count: number }[];
  top_topics: { topic: string; count: number }[];
  talk_time: TalkTime[];
}

export const TERMINAL_STATUSES: MeetingStatus[] = ["done", "failed"];
