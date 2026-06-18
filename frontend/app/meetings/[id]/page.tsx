"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ConfirmDialog } from "@/components/ui/Dialog";
import {
  Button,
  Card,
  SectionLabel,
  Spinner,
  StatusPill,
  TextInput,
} from "@/components/ui/primitives";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDate, formatDuration, formatTimestamp, speakerName } from "@/lib/format";
import { type MeetingDetail, TERMINAL_STATUSES } from "@/lib/types";

const SPEAKER_COLORS = [
  "text-accent",
  "text-[#8a5a1c]",
  "text-[#7b2d8e]",
  "text-[#2a6f97]",
  "text-[#9c3848]",
  "text-[#3d6b35]",
];

const STAGES = ["transcribing", "extracting", "indexing"] as const;
const STAGE_COPY: Record<string, string> = {
  transcribing: "Transcribing and identifying speakers",
  extracting: "Extracting summary and action items",
  indexing: "Indexing for search",
};

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState(false);
  const [confirm, setConfirm] = useState(false);

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

  async function archive() {
    if (!meeting) return;
    setArchiving(true);
    try {
      await api.deleteMeeting(meeting.id);
      toast("Meeting archived", "success", {
        label: "Undo",
        onClick: async () => {
          await api.restoreMeeting(meeting.id);
          toast("Meeting restored", "success");
        },
      });
      router.push("/");
    } catch (e) {
      toast((e as Error).message, "error");
      setArchiving(false);
      setConfirm(false);
    }
  }

  if (error) return <Centered>Could not load meeting: {error}</Centered>;
  if (!meeting) return <Centered><Spinner className="h-5 w-5" /></Centered>;

  const nameOf = (label: number) =>
    speakerName(label, meeting.speakers.find((s) => s.label === label)?.display_name);

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <div className="rise flex items-center justify-between">
        <Link href="/" className="label hover:text-ink">
          ← Archive
        </Link>
        <Button variant="danger" size="sm" onClick={() => setConfirm(true)}>
          Archive
        </Button>
      </div>

      <header className="rise mt-4">
        <TitleEditor meeting={meeting} onChange={setMeeting} />
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          <StatusPill status={meeting.status} />
          <span className="label normal-case tracking-normal">
            {formatDate(meeting.created_at)}
            {meeting.duration_sec ? ` · ${formatDuration(meeting.duration_sec)}` : ""}
            {meeting.speakers.length ? ` · ${meeting.speakers.length} speakers` : ""}
          </span>
        </div>
        {meeting.topics.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {meeting.topics.map((t) => (
              <Link
                key={t}
                href={`/search?q=${encodeURIComponent(t)}`}
                className="rounded-full border border-line bg-paper px-2.5 py-1 font-mono text-xs text-muted hover:border-accent hover:text-accent"
              >
                {t}
              </Link>
            ))}
          </div>
        )}
      </header>

      {meeting.status === "failed" && (
        <Card className="mt-6 border-failed/30 bg-failed/5 p-5 text-sm text-failed">
          Processing failed: {meeting.error}
        </Card>
      )}

      {!TERMINAL_STATUSES.includes(meeting.status) ? (
        <Stepper status={meeting.status} />
      ) : meeting.status === "done" ? (
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-3">
            {meeting.summary && <SummaryCard meeting={meeting} />}
            <TranscriptCard meeting={meeting} nameOf={nameOf} />
          </div>
          <div className="space-y-6 lg:col-span-2">
            <ActionItemsCard meeting={meeting} onChange={setMeeting} />
            <SpeakersCard meeting={meeting} onChange={setMeeting} />
            <TalkTimeCard meeting={meeting} />
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={confirm}
        title="Archive this meeting?"
        body="It will be removed from your archive. You can restore it from the toast."
        confirmLabel="Archive"
        danger
        busy={archiving}
        onConfirm={archive}
        onCancel={() => setConfirm(false)}
      />
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center text-sm text-muted">{children}</div>;
}

function TitleEditor({
  meeting,
  onChange,
}: {
  meeting: MeetingDetail;
  onChange: (m: MeetingDetail) => void;
}) {
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(meeting.title);

  async function save() {
    setEditing(false);
    if (draft.trim() === meeting.title || !draft.trim()) return;
    try {
      onChange(await api.renameMeeting(meeting.id, draft.trim()));
      toast("Title updated", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  if (editing) {
    return (
      <TextInput
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => e.key === "Enter" && save()}
        className="max-w-xl font-display text-2xl"
      />
    );
  }
  return (
    <button
      onClick={() => {
        setDraft(meeting.title);
        setEditing(true);
      }}
      className="text-left font-display text-3xl tracking-tight text-ink hover:text-accent-ink"
      title="Click to rename"
    >
      {meeting.title}
    </button>
  );
}

function Stepper({ status }: { status: string }) {
  const current = STAGES.indexOf(status as (typeof STAGES)[number]);
  return (
    <Card className="mt-8 p-8">
      <div className="mx-auto max-w-md space-y-4">
        {STAGES.map((stage, i) => {
          const done = current > i;
          const active = current === i;
          return (
            <div key={stage} className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full text-xs",
                  done && "bg-accent text-white",
                  active && "border-2 border-accent text-accent",
                  !done && !active && "border border-line text-faint",
                )}
              >
                {done ? "✓" : i + 1}
              </span>
              <span className={cn("text-sm", active ? "text-ink" : done ? "text-muted" : "text-faint")}>
                {STAGE_COPY[stage]}
              </span>
              {active && <Spinner className="ml-auto h-4 w-4" />}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function CardShell({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <SectionLabel>{title}</SectionLabel>
        {action}
      </div>
      {children}
    </Card>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="font-mono text-xs font-medium text-ink">{title}</h3>
      <ul className="mt-1.5 space-y-1 text-sm text-muted">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-accent">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SummaryCard({ meeting }: { meeting: MeetingDetail }) {
  const toast = useToast();
  const s = meeting.summary!;

  function exportMarkdown() {
    const out: string[] = [`# ${meeting.title}`, "", s.overview, ""];
    const block = (t: string, items: string[]) =>
      items.length ? out.push(`## ${t}`, ...items.map((i) => `- ${i}`), "") : 0;
    block("Attendees", s.attendees);
    block("Key decisions", s.key_decisions);
    block("Discussion points", s.discussion_points);
    block("Open questions", s.open_questions);
    block("Next steps", s.next_steps);
    if (meeting.action_items.length) {
      out.push("## Action items");
      meeting.action_items.forEach((a) =>
        out.push(
          `- [${a.completed ? "x" : " "}] ${a.task}${a.owner ? ` (${a.owner})` : ""}${a.due ? ` (due ${a.due})` : ""}`,
        ),
      );
    }
    navigator.clipboard.writeText(out.join("\n"));
    toast("Summary copied as Markdown", "success");
  }

  return (
    <CardShell
      title="Summary"
      action={
        <Button variant="ghost" size="sm" onClick={exportMarkdown}>
          Copy as Markdown
        </Button>
      }
    >
      <p className="text-[15px] leading-relaxed text-ink">{s.overview}</p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <Section title="Attendees" items={s.attendees} />
        <Section title="Key decisions" items={s.key_decisions} />
        <Section title="Discussion points" items={s.discussion_points} />
        <Section title="Open questions" items={s.open_questions} />
        <Section title="Next steps" items={s.next_steps} />
      </div>
    </CardShell>
  );
}

function TranscriptCard({
  meeting,
  nameOf,
}: {
  meeting: MeetingDetail;
  nameOf: (label: number) => string;
}) {
  const [query, setQuery] = useState("");
  const segments = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? meeting.segments.filter((s) => s.text.toLowerCase().includes(q)) : meeting.segments;
  }, [meeting.segments, query]);

  return (
    <CardShell
      title="Transcript"
      action={
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search transcript…"
          className="w-40 rounded-md border border-line bg-paper px-2.5 py-1 text-xs outline-none focus:border-accent"
        />
      }
    >
      <div className="scroll-slim max-h-[30rem] space-y-4 overflow-y-auto pr-2">
        {segments.length === 0 ? (
          <p className="text-sm text-faint">No lines match.</p>
        ) : (
          segments.map((seg) => (
            <div key={seg.idx} className="flex gap-3">
              <span className="mt-1 w-9 shrink-0 font-mono text-[11px] text-faint">
                {formatTimestamp(seg.start_sec)}
              </span>
              <div className="min-w-0">
                <span
                  className={cn(
                    "font-mono text-[11px] font-medium",
                    SPEAKER_COLORS[seg.speaker_label % SPEAKER_COLORS.length],
                  )}
                >
                  {nameOf(seg.speaker_label)}
                </span>
                <p className="text-sm leading-relaxed text-ink">{seg.text}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </CardShell>
  );
}

function ActionItemsCard({
  meeting,
  onChange,
}: {
  meeting: MeetingDetail;
  onChange: (m: MeetingDetail) => void;
}) {
  const toast = useToast();
  const [task, setTask] = useState("");
  const [owner, setOwner] = useState("");

  function patch(items: MeetingDetail["action_items"]) {
    onChange({ ...meeting, action_items: items });
  }

  async function toggle(itemId: string, completed: boolean) {
    patch(meeting.action_items.map((a) => (a.id === itemId ? { ...a, completed } : a)));
    try {
      await api.updateActionItem(itemId, { completed });
    } catch (e) {
      patch(meeting.action_items); // revert
      toast((e as Error).message, "error");
    }
  }

  async function remove(itemId: string) {
    const prev = meeting.action_items;
    patch(prev.filter((a) => a.id !== itemId));
    try {
      await api.deleteActionItem(itemId);
    } catch (e) {
      patch(prev);
      toast((e as Error).message, "error");
    }
  }

  async function add() {
    if (!task.trim()) return;
    try {
      const created = await api.addActionItem(meeting.id, {
        task: task.trim(),
        owner: owner.trim() || null,
      });
      patch([...meeting.action_items, created]);
      setTask("");
      setOwner("");
    } catch (e) {
      toast((e as Error).message, "error");
    }
  }

  return (
    <CardShell title={`Action items · ${meeting.action_items.length}`}>
      {meeting.action_items.length === 0 ? (
        <p className="text-sm text-faint">None extracted.</p>
      ) : (
        <ul className="space-y-2.5">
          {meeting.action_items.map((item) => (
            <li key={item.id} className="group flex items-start gap-2.5">
              <input
                type="checkbox"
                checked={item.completed}
                onChange={(e) => toggle(item.id, e.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-accent"
              />
              <div className="min-w-0 flex-1">
                <p className={cn("text-sm", item.completed ? "text-faint line-through" : "text-ink")}>
                  {item.task}
                </p>
                {(item.owner || item.due) && (
                  <p className="label mt-0.5 normal-case tracking-normal">
                    {item.owner ?? "Unassigned"}
                    {item.due ? ` · due ${item.due}` : ""}
                  </p>
                )}
              </div>
              <button
                onClick={() => remove(item.id)}
                className="text-faint opacity-0 transition-opacity hover:text-failed group-hover:opacity-100"
                aria-label="Delete action item"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 flex gap-2 border-t border-line pt-4">
        <input
          value={task}
          onChange={(e) => setTask(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="Add an action item…"
          className="min-w-0 flex-1 rounded-md border border-line bg-paper px-2.5 py-1.5 text-sm outline-none focus:border-accent"
        />
        <Button variant="secondary" size="sm" onClick={add}>
          Add
        </Button>
      </div>
    </CardShell>
  );
}

function SpeakersCard({
  meeting,
  onChange,
}: {
  meeting: MeetingDetail;
  onChange: (m: MeetingDetail) => void;
}) {
  const toast = useToast();
  const [names, setNames] = useState<Record<number, string>>(() =>
    Object.fromEntries(meeting.speakers.map((s) => [s.label, s.display_name ?? ""])),
  );
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(names).map(([k, v]) => [Number(k), v.trim()]),
      );
      onChange(await api.renameSpeakers(meeting.id, payload));
      toast("Speaker names saved", "success");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <CardShell title="Speakers">
      <div className="space-y-2">
        {meeting.speakers.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="w-16 shrink-0 font-mono text-[11px] text-faint">Speaker {s.label}</span>
            <input
              value={names[s.label] ?? ""}
              onChange={(e) => setNames({ ...names, [s.label]: e.target.value })}
              placeholder="Add a name"
              className="min-w-0 flex-1 rounded-md border border-line bg-paper px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            />
          </div>
        ))}
      </div>
      <Button variant="secondary" size="sm" className="mt-3" onClick={save} disabled={saving}>
        {saving ? "Saving…" : "Save names"}
      </Button>
    </CardShell>
  );
}

function TalkTimeCard({ meeting }: { meeting: MeetingDetail }) {
  if (meeting.talk_time.length === 0) return null;
  const max = Math.max(...meeting.talk_time.map((t) => t.seconds), 1);
  return (
    <CardShell title="Speaking time">
      <div className="space-y-2.5">
        {meeting.talk_time.map((t) => (
          <div key={t.participant}>
            <div className="flex justify-between text-xs text-muted">
              <span>{t.participant}</span>
              <span className="font-mono">{formatDuration(t.seconds)}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-line">
              <div
                className="h-1.5 rounded-full bg-accent"
                style={{ width: `${(t.seconds / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </CardShell>
  );
}
