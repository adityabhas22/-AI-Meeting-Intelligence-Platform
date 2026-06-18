"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Button, SectionLabel, Spinner } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import type { RetrievedChunk } from "@/lib/types";

interface Turn {
  question: string;
  answer?: string;
  sources?: RetrievedChunk[];
  error?: string;
}

const SUGGESTIONS = [
  "What decisions were made recently?",
  "What action items are still open?",
  "What did we say about deadlines?",
];

function SearchClient() {
  const params = useSearchParams();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const asked = useRef(false);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setTurns((prev) => [...prev, { question: q }]);
    try {
      const res = await api.ask(q, sessionId);
      setTurns((prev) =>
        prev.map((t, i) =>
          i === prev.length - 1 ? { ...t, answer: res.answer, sources: res.sources } : t,
        ),
      );
    } catch (e) {
      setTurns((prev) =>
        prev.map((t, i) => (i === prev.length - 1 ? { ...t, error: (e as Error).message } : t)),
      );
    } finally {
      setBusy(false);
    }
  }

  // Prefill + auto-ask when arriving from a topic chip (?q=...).
  useEffect(() => {
    const q = params.get("q");
    if (q && !asked.current) {
      asked.current = true;
      ask(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-8 py-12">
      <header className="rise mb-8">
        <SectionLabel>Ask the archive</SectionLabel>
        <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Search</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Ask anything across every meeting. Answers cite the meetings they came from.
        </p>
      </header>

      <div className="flex-1 space-y-6">
        {turns.length === 0 && (
          <div className="space-y-3">
            <SectionLabel>Try asking</SectionLabel>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-muted hover:border-accent hover:text-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="rise space-y-3">
            <p className="text-right">
              <span className="inline-block rounded-2xl rounded-br-sm bg-accent px-4 py-2 text-sm text-white">
                {turn.question}
              </span>
            </p>
            {turn.error ? (
              <p className="text-sm text-failed">{turn.error}</p>
            ) : turn.answer === undefined ? (
              <p className="flex items-center gap-2 text-sm text-muted">
                <Spinner /> Searching the archive…
              </p>
            ) : (
              <div className="rounded-2xl rounded-tl-sm border border-line bg-surface p-4">
                <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-ink">
                  {turn.answer}
                </p>
                {turn.sources && turn.sources.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-line pt-3">
                    <SectionLabel>Sources</SectionLabel>
                    {turn.sources.map((s) => (
                      <Link
                        key={s.chunk_id}
                        href={`/meetings/${s.meeting_id}`}
                        className="block rounded-lg bg-paper p-2.5 text-xs hover:bg-accent-soft/50"
                      >
                        <span className="font-medium text-ink">{s.meeting_title}</span>
                        <span className="ml-1 font-mono text-faint">
                          {formatTimestamp(s.start_sec)}
                        </span>
                        <span className="mt-1 block line-clamp-2 text-muted">{s.text}</span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="sticky bottom-6 mt-6 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          placeholder="Ask about your meetings…"
          className="flex-1 rounded-xl border border-line bg-surface px-4 py-3 text-sm shadow-sm outline-none focus:border-accent"
        />
        <Button onClick={() => ask(input)} disabled={busy || !input.trim()} className="px-5 py-3">
          Ask
        </Button>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="px-8 py-12 text-sm text-muted">Loading…</div>}>
      <SearchClient />
    </Suspense>
  );
}
