"use client";

import { useEffect, useState } from "react";
import { Card, SectionLabel, Skeleton } from "@/components/ui/primitives";
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

  return (
    <div className="mx-auto max-w-5xl px-8 py-12">
      <header className="rise mb-8">
        <SectionLabel>Across the archive</SectionLabel>
        <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Analytics</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Patterns in how the team meets, decides, and follows through.
        </p>
      </header>

      {error && <p className="text-sm text-failed">Could not load analytics: {error}</p>}

      {!data ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <Loaded data={data} />
      )}
    </div>
  );
}

function Loaded({ data }: { data: Analytics }) {
  const completion = Math.round(data.action_items.rate * 100);
  const maxTalk = Math.max(...data.talk_time.map((t) => t.seconds), 1);
  const maxWeek = Math.max(...data.meetings_per_week.map((w) => w.count), 1);
  const maxTopic = Math.max(...data.top_topics.map((t) => t.count), 1);

  return (
    <>
      <div className="rise grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Meetings" value={String(data.total_meetings)} />
        <Stat label="Total recorded" value={formatDuration(data.total_duration_sec)} />
        <Stat
          label="Action items done"
          value={`${completion}%`}
          sub={`${data.action_items.completed} of ${data.action_items.total}`}
        />
      </div>

      <div className="rise mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel title="Speaking time by participant">
          {data.talk_time.length === 0 ? (
            <Empty />
          ) : (
            <div className="space-y-3">
              {data.talk_time.map((t) => (
                <div key={t.participant}>
                  <div className="flex justify-between text-xs text-muted">
                    <span>{t.participant}</span>
                    <span className="font-mono">{formatDuration(t.seconds)}</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-line">
                    <div
                      className="h-2 rounded-full bg-accent"
                      style={{ width: `${(t.seconds / maxTalk) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Recurring topics">
          {data.top_topics.length === 0 ? (
            <Empty />
          ) : (
            <div className="flex flex-wrap gap-2">
              {data.top_topics.map((t) => (
                <span
                  key={t.topic}
                  className="rounded-full bg-accent-soft px-3 py-1 font-mono text-accent-ink"
                  style={{ fontSize: `${0.75 + (t.count / maxTopic) * 0.45}rem` }}
                >
                  {t.topic} <span className="text-accent/60">{t.count}</span>
                </span>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Meeting frequency">
          {data.meetings_per_week.length === 0 ? (
            <Empty />
          ) : (
            <div className="flex h-32 items-end gap-2">
              {data.meetings_per_week.map((w) => (
                <div key={w.period} className="flex flex-1 flex-col items-center gap-1">
                  <div
                    className="w-full rounded-t bg-accent"
                    style={{ height: `${Math.max((w.count / maxWeek) * 100, 6)}%` }}
                    title={`${w.count} meetings`}
                  />
                  <span className="font-mono text-[10px] text-faint">{w.period.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <Card className="p-5">
      <SectionLabel>{label}</SectionLabel>
      <p className="mt-1 font-display text-3xl text-ink">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </Card>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <SectionLabel className="mb-4">{title}</SectionLabel>
      {children}
    </Card>
  );
}

function Empty() {
  return <p className="text-sm text-faint">No data yet.</p>;
}
