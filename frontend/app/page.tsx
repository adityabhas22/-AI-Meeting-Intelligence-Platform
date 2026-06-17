"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { UploadZone } from "@/components/UploadZone";
import { api } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/format";
import { TERMINAL_STATUSES, type MeetingListItem } from "@/lib/types";

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setMeetings(await api.listMeetings());
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
    const processing = meetings.some((m) => !TERMINAL_STATUSES.includes(m.status));
    if (!processing) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [meetings, load]);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Meetings</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Upload a recording to get a speaker-labelled transcript, a structured summary, and action
          items.
        </p>
      </header>

      <div className="mb-10">
        <UploadZone onUploaded={load} />
      </div>

      {error && <p className="mb-4 text-sm text-red-600">Could not reach the API: {error}</p>}

      {loading ? (
        <p className="text-sm text-zinc-400">Loading meetings…</p>
      ) : meetings.length === 0 ? (
        <div className="rounded-xl border border-zinc-200 bg-white px-6 py-12 text-center">
          <p className="text-sm text-zinc-500">No meetings yet. Upload one above to get started.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {meetings.map((m) => (
            <li key={m.id}>
              <Link
                href={`/meetings/${m.id}`}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-5 py-4 transition-colors hover:border-zinc-300 hover:bg-zinc-50"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-zinc-900">{m.title}</p>
                  <p className="mt-0.5 text-xs text-zinc-400">
                    {formatDate(m.created_at)}
                    {m.duration_sec ? ` · ${formatDuration(m.duration_sec)}` : ""}
                    {m.action_item_count > 0 ? ` · ${m.action_item_count} action items` : ""}
                  </p>
                </div>
                <StatusBadge status={m.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
