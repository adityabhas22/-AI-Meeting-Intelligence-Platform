"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ConfirmDialog } from "@/components/ui/Dialog";
import { Button, EmptyState, SectionLabel, Skeleton, StatusPill } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import { type Analytics, type MeetingListItem, TERMINAL_STATUSES } from "@/lib/types";

export default function MeetingsPage() {
  const toast = useToast();
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [stats, setStats] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<MeetingListItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [m, s] = await Promise.all([api.listMeetings(), api.analytics()]);
      setMeetings(m);
      setStats(s);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!meetings.some((m) => !TERMINAL_STATUSES.includes(m.status))) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [meetings, load]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setDeleting(true);
    try {
      await api.deleteMeeting(target.id);
      setMeetings((prev) => prev.filter((m) => m.id !== target.id));
      toast("Meeting archived", "success", {
        label: "Undo",
        onClick: async () => {
          await api.restoreMeeting(target.id);
          load();
          toast("Meeting restored", "success");
        },
      });
      load();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-12">
      <header className="rise mb-8">
        <SectionLabel>Meeting Intelligence</SectionLabel>
        <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Meetings</h1>
        <p className="mt-2 max-w-prose text-sm leading-relaxed text-muted">
          Every recording becomes a speaker-labelled transcript, a structured summary, and a
          checkable set of decisions and action items.
        </p>
      </header>

      {stats && stats.total_meetings > 0 && (
        <div className="rise mb-8 grid grid-cols-3 divide-x divide-line rounded-xl border border-line bg-surface">
          <Stat label="Meetings" value={String(stats.total_meetings)} />
          <Stat label="Recorded" value={formatDuration(stats.total_duration_sec)} />
          <Stat label="Actions done" value={`${Math.round(stats.action_items.rate * 100)}%`} />
        </div>
      )}

      <div className="rise mb-10">
        <UploadZone onUploaded={load} />
      </div>

      <SectionLabel className="mb-3">Archive</SectionLabel>
      {error && <p className="text-sm text-failed">Could not reach the API: {error}</p>}

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : meetings.length === 0 ? (
        <EmptyState title="No meetings yet" hint="Upload a recording above to get started." />
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {meetings.map((m) => (
            <li key={m.id} className="group flex items-center gap-3 px-5 py-4 hover:bg-paper/60">
              <Link href={`/meetings/${m.id}`} className="min-w-0 flex-1">
                <p className="truncate font-medium text-ink group-hover:text-accent-ink">
                  {m.title}
                </p>
                <p className="label mt-1 normal-case tracking-normal">
                  {formatDate(m.created_at)}
                  {m.duration_sec ? ` · ${formatDuration(m.duration_sec)}` : ""}
                  {m.action_item_count > 0 ? ` · ${m.action_item_count} actions` : ""}
                </p>
              </Link>
              <StatusPill status={m.status} />
              <Button
                variant="ghost"
                size="sm"
                className="opacity-0 group-hover:opacity-100"
                onClick={() => setPendingDelete(m)}
                aria-label="Archive meeting"
              >
                Archive
              </Button>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Archive this meeting?"
        body={`"${pendingDelete?.title}" will be removed from your archive. You can restore it later.`}
        confirmLabel="Archive"
        danger
        busy={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-5 py-4">
      <SectionLabel>{label}</SectionLabel>
      <p className="mt-1 font-display text-2xl text-ink">{value}</p>
    </div>
  );
}
