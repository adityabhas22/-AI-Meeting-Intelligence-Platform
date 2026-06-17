"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import type { Analytics } from "@/lib/types";

export default function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .analytics()
      .then(setData)
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error) return <Shell>Could not load analytics: {error}</Shell>;
  if (!data) return <Shell>Loading…</Shell>;

  const completion = Math.round(data.action_items.rate * 100);
  const maxTalk = Math.max(...data.talk_time.map((t) => t.seconds), 1);
  const maxWeek = Math.max(...data.meetings_per_week.map((w) => w.count), 1);
  const maxTopic = Math.max(...data.top_topics.map((t) => t.count), 1);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Analytics</h1>
        <p className="mt-1 text-sm text-zinc-500">Trends across the whole meeting archive.</p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Meetings" value={String(data.total_meetings)} />
        <Stat label="Total recorded" value={formatDuration(data.total_duration_sec)} />
        <Stat
          label="Action items done"
          value={`${completion}%`}
          sub={`${data.action_items.completed} of ${data.action_items.total}`}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Speaking time by participant">
          {data.talk_time.length === 0 ? (
            <Empty />
          ) : (
            <div className="space-y-3">
              {data.talk_time.map((t) => (
                <div key={t.participant}>
                  <div className="flex justify-between text-xs text-zinc-500">
                    <span>{t.participant}</span>
                    <span className="font-mono">{formatDuration(t.seconds)}</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-zinc-100">
                    <div
                      className="h-2 rounded-full bg-indigo-500"
                      style={{ width: `${(t.seconds / maxTalk) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Recurring topics">
          {data.top_topics.length === 0 ? (
            <Empty />
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.top_topics.map((t) => (
                <span
                  key={t.topic}
                  className="rounded-full bg-indigo-50 px-3 py-1 text-sm text-indigo-700"
                  style={{ fontSize: `${0.8 + (t.count / maxTopic) * 0.5}rem` }}
                >
                  {t.topic} <span className="text-indigo-400">{t.count}</span>
                </span>
              ))}
            </div>
          )}
        </Card>

        <Card title="Meeting frequency">
          {data.meetings_per_week.length === 0 ? (
            <Empty />
          ) : (
            <div className="flex h-32 items-end gap-2">
              {data.meetings_per_week.map((w) => (
                <div key={w.period} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t bg-indigo-500"
                    style={{ height: `${(w.count / maxWeek) * 100}%` }}
                    title={`${w.count} meetings`}
                  />
                  <span className="text-[10px] text-zinc-400">{w.period.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="px-8 py-10 text-sm text-zinc-400">{children}</div>;
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-zinc-900">{value}</p>
      {sub && <p className="text-xs text-zinc-400">{sub}</p>}
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold tracking-tight text-zinc-900">{title}</h2>
      {children}
    </section>
  );
}

function Empty() {
  return <p className="text-sm text-zinc-400">No data yet.</p>;
}
