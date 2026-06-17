"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { formatDuration, formatTimestamp, speakerName } from "@/lib/format";
import { TERMINAL_STATUSES, type MeetingDetail } from "@/lib/types";

const SPEAKER_COLORS = [
  "text-indigo-600",
  "text-emerald-600",
  "text-amber-600",
  "text-rose-600",
  "text-sky-600",
  "text-violet-600",
];

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setMeeting(await api.getMeeting(id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!meeting || TERMINAL_STATUSES.includes(meeting.status)) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [meeting, load]);

  if (error) return <Centered>Could not load meeting: {error}</Centered>;
  if (!meeting) return <Centered>Loading…</Centered>;

  const nameOf = (label: number) =>
    speakerName(label, meeting.speakers.find((s) => s.label === label)?.display_name);

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800">
        ← All meetings
      </Link>

      <header className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">{meeting.title}</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {meeting.duration_sec ? formatDuration(meeting.duration_sec) : "—"}
            {meeting.language ? ` · ${meeting.language}` : ""}
            {` · ${meeting.speakers.length} speakers`}
          </p>
        </div>
        <StatusBadge status={meeting.status} />
      </header>

      {meeting.topics.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {meeting.topics.map((t) => (
            <span key={t} className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-600">
              {t}
            </span>
          ))}
        </div>
      )}

      {meeting.status === "failed" && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          Processing failed: {meeting.error}
        </div>
      )}

      {!TERMINAL_STATUSES.includes(meeting.status) ? (
        <ProcessingState status={meeting.status} />
      ) : meeting.status === "done" ? (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            {meeting.summary && <SummaryCard summary={meeting.summary} />}
            <TranscriptCard meeting={meeting} nameOf={nameOf} />
          </div>
          <div className="space-y-6">
            <ActionItemsCard meeting={meeting} onChange={setMeeting} />
            <SpeakersCard meeting={meeting} onChange={setMeeting} />
            <TalkTimeCard meeting={meeting} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-8 text-sm text-zinc-400">
      {children}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold tracking-tight text-zinc-900">{title}</h2>
      {children}
    </section>
  );
}

function ProcessingState({ status }: { status: string }) {
  const message: Record<string, string> = {
    uploaded: "Queued for processing…",
    transcribing: "Transcribing audio and identifying speakers…",
    extracting: "Extracting the summary and action items…",
    indexing: "Indexing the transcript for search…",
  };
  return (
    <div className="mt-6 rounded-xl border border-zinc-200 bg-white px-6 py-12 text-center">
      <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-zinc-200 border-t-indigo-600" />
      <p className="text-sm text-zinc-600">{message[status] ?? "Processing…"}</p>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-zinc-400">{title}</h3>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-zinc-700">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function SummaryCard({ summary }: { summary: NonNullable<MeetingDetail["summary"]> }) {
  return (
    <Card title="Summary">
      <p className="text-sm leading-relaxed text-zinc-700">{summary.overview}</p>
      <div className="mt-4 space-y-4">
        <Section title="Attendees" items={summary.attendees} />
        <Section title="Key decisions" items={summary.key_decisions} />
        <Section title="Discussion points" items={summary.discussion_points} />
        <Section title="Open questions" items={summary.open_questions} />
        <Section title="Next steps" items={summary.next_steps} />
      </div>
    </Card>
  );
}

function TranscriptCard({
  meeting,
  nameOf,
}: {
  meeting: MeetingDetail;
  nameOf: (label: number) => string;
}) {
  return (
    <Card title="Transcript">
      <div className="scroll-slim max-h-[32rem] space-y-4 overflow-y-auto pr-2">
        {meeting.segments.map((seg) => (
          <div key={seg.idx} className="flex gap-3">
            <span className="mt-0.5 w-10 shrink-0 font-mono text-xs text-zinc-400">
              {formatTimestamp(seg.start_sec)}
            </span>
            <div className="min-w-0">
              <span
                className={`text-xs font-semibold ${
                  SPEAKER_COLORS[seg.speaker_label % SPEAKER_COLORS.length]
                }`}
              >
                {nameOf(seg.speaker_label)}
              </span>
              <p className="text-sm leading-relaxed text-zinc-700">{seg.text}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ActionItemsCard({
  meeting,
  onChange,
}: {
  meeting: MeetingDetail;
  onChange: (m: MeetingDetail) => void;
}) {
  async function toggle(itemId: string, completed: boolean) {
    const updated = await api.updateActionItem(itemId, { completed });
    onChange({
      ...meeting,
      action_items: meeting.action_items.map((a) => (a.id === itemId ? updated : a)),
    });
  }

  return (
    <Card title={`Action items (${meeting.action_items.length})`}>
      {meeting.action_items.length === 0 ? (
        <p className="text-sm text-zinc-400">None found.</p>
      ) : (
        <ul className="space-y-2.5">
          {meeting.action_items.map((item) => (
            <li key={item.id} className="flex items-start gap-2.5">
              <input
                type="checkbox"
                checked={item.completed}
                onChange={(e) => toggle(item.id, e.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-indigo-600"
              />
              <div className="min-w-0">
                <p
                  className={`text-sm ${
                    item.completed ? "text-zinc-400 line-through" : "text-zinc-700"
                  }`}
                >
                  {item.task}
                </p>
                {(item.owner || item.due) && (
                  <p className="text-xs text-zinc-400">
                    {item.owner ?? "Unassigned"}
                    {item.due ? ` · due ${item.due}` : ""}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SpeakersCard({
  meeting,
  onChange,
}: {
  meeting: MeetingDetail;
  onChange: (m: MeetingDetail) => void;
}) {
  const [names, setNames] = useState<Record<number, string>>(() =>
    Object.fromEntries(meeting.speakers.map((s) => [s.label, s.display_name ?? ""])),
  );
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const filled = Object.fromEntries(
        Object.entries(names).filter(([, v]) => v.trim()).map(([k, v]) => [Number(k), v.trim()]),
      );
      const updated = await api.renameSpeakers(meeting.id, filled);
      onChange(updated);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card title="Speakers">
      <div className="space-y-2">
        {meeting.speakers.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="w-16 shrink-0 text-xs text-zinc-400">Speaker {s.label}</span>
            <input
              value={names[s.label] ?? ""}
              onChange={(e) => setNames({ ...names, [s.label]: e.target.value })}
              placeholder="Add a name"
              className="min-w-0 flex-1 rounded-md border border-zinc-200 px-2 py-1 text-sm outline-none focus:border-indigo-400"
            />
          </div>
        ))}
      </div>
      <button
        onClick={save}
        disabled={saving}
        className="mt-3 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save names"}
      </button>
    </Card>
  );
}

function TalkTimeCard({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.talk_time.length === 0) return null;
  const max = Math.max(...meeting.talk_time.map((t) => t.seconds), 1);
  return (
    <Card title="Speaking time">
      <div className="space-y-2.5">
        {meeting.talk_time.map((t) => (
          <div key={t.participant}>
            <div className="flex justify-between text-xs text-zinc-500">
              <span>{t.participant}</span>
              <span className="font-mono">{formatDuration(t.seconds)}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-zinc-100">
              <div
                className="h-1.5 rounded-full bg-indigo-500"
                style={{ width: `${(t.seconds / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
