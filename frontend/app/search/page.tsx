"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { formatTimestamp } from "@/lib/format";
import type { RetrievedChunk } from "@/lib/types";

interface Turn {
  question: string;
  answer?: string;
  sources?: RetrievedChunk[];
  error?: string;
}

export default function SearchPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  async function ask() {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setTurns((prev) => [...prev, { question }]);
    try {
      const res = await api.ask(question, sessionId);
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

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-8 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">Search the archive</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Ask anything across every meeting. Answers cite the meetings they came from.
        </p>
      </header>

      <div className="flex-1 space-y-6">
        {turns.length === 0 && (
          <div className="rounded-xl border border-zinc-200 bg-white px-6 py-12 text-center text-sm text-zinc-400">
            Try “What did we decide about pricing?” or “What are the open action items?”
          </div>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="space-y-3">
            <p className="text-right">
              <span className="inline-block rounded-2xl bg-indigo-600 px-4 py-2 text-sm text-white">
                {turn.question}
              </span>
            </p>
            {turn.error ? (
              <p className="text-sm text-red-600">{turn.error}</p>
            ) : turn.answer === undefined ? (
              <p className="text-sm text-zinc-400">Thinking…</p>
            ) : (
              <div className="rounded-xl border border-zinc-200 bg-white p-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-800">
                  {turn.answer}
                </p>
                {turn.sources && turn.sources.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-zinc-100 pt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
                      Sources
                    </p>
                    {turn.sources.map((s) => (
                      <Link
                        key={s.chunk_id}
                        href={`/meetings/${s.meeting_id}`}
                        className="block rounded-lg bg-zinc-50 p-2.5 text-xs hover:bg-zinc-100"
                      >
                        <span className="font-medium text-zinc-700">{s.meeting_title}</span>
                        <span className="ml-1 font-mono text-zinc-400">
                          {formatTimestamp(s.start_sec)}
                        </span>
                        <span className="mt-1 block line-clamp-2 text-zinc-500">{s.text}</span>
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
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask about your meetings…"
          className="flex-1 rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-indigo-400"
        />
        <button
          onClick={ask}
          disabled={busy || !input.trim()}
          className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Ask
        </button>
      </div>
    </div>
  );
}
