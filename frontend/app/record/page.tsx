"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button, SectionLabel, TextInput } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";
import { formatDuration } from "@/lib/format";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Phase = "idle" | "recording" | "paused" | "recorded" | "uploading";

export default function RecordPage() {
  const router = useRouter();
  const toast = useToast();
  const [phase, setPhase] = useState<Phase>("idle");
  const [seconds, setSeconds] = useState(0);
  const [level, setLevel] = useState(0);
  const [title, setTitle] = useState("");
  const [keyterms, setKeyterms] = useState("");
  const [progress, setProgress] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const blobRef = useRef<Blob | null>(null);
  const timerRef = useRef<number | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number | null>(null);

  const startTimer = () => {
    timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000);
  };
  const stopTimer = () => {
    if (timerRef.current) window.clearInterval(timerRef.current);
  };

  function teardown() {
    stopTimer();
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    ctxRef.current?.close().catch(() => {});
    setLevel(0);
  }

  // Stop the mic/timer/audio only when leaving the page.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => () => teardown(), []);

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ctx = new AudioContext();
      ctxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const avg = data.reduce((a, b) => a + b, 0) / data.length;
        setLevel(Math.min(avg / 130, 1));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();

      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        blobRef.current = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        setPhase("recorded");
      };
      recorder.start();
      recorderRef.current = recorder;
      setSeconds(0);
      startTimer();
      setPhase("recording");
    } catch {
      toast("Microphone access was denied", "error");
    }
  }

  function pause() {
    recorderRef.current?.pause();
    stopTimer();
    setPhase("paused");
  }
  function resume() {
    recorderRef.current?.resume();
    startTimer();
    setPhase("recording");
  }
  function stop() {
    recorderRef.current?.stop();
    teardown();
  }
  function discard() {
    blobRef.current = null;
    chunksRef.current = [];
    setSeconds(0);
    setTitle("");
    setKeyterms("");
    setPhase("idle");
  }

  function save() {
    if (!blobRef.current) return;
    const form = new FormData();
    form.append("file", blobRef.current, "live-recording.webm");
    if (title.trim()) form.append("title", title.trim());
    if (keyterms.trim()) form.append("keyterms", keyterms.trim());

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/meetings`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        toast("Recording saved. Processing has started.", "success");
        router.push(`/meetings/${JSON.parse(xhr.responseText).id}`);
      } else {
        toast("Upload failed", "error");
        setPhase("recorded");
      }
    };
    xhr.onerror = () => {
      toast("Could not reach the server", "error");
      setPhase("recorded");
    };
    setProgress(0);
    setPhase("uploading");
    xhr.send(form);
  }

  const live = phase === "recording" || phase === "paused";

  return (
    <div className="mx-auto max-w-2xl px-8 py-12">
      <header className="rise mb-10">
        <SectionLabel>Capture live</SectionLabel>
        <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Record a meeting</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Record straight from your microphone. When you stop, it runs through the same
          transcription and analysis pipeline as an upload.
        </p>
      </header>

      <div className="flex flex-col items-center rounded-xl border border-line bg-surface px-6 py-12">
        {phase !== "recorded" && phase !== "uploading" && (
          <>
            <div className="relative flex h-32 w-32 items-center justify-center">
              {live && (
                <span
                  className="absolute inset-0 rounded-full bg-accent/10 transition-transform duration-100"
                  style={{ transform: `scale(${1 + level * 0.5})` }}
                />
              )}
              <button
                onClick={phase === "idle" ? start : phase === "recording" ? pause : resume}
                className={cn(
                  "relative flex h-20 w-20 items-center justify-center rounded-full text-white transition-colors",
                  phase === "recording" ? "bg-failed" : "bg-accent hover:bg-accent-ink",
                )}
                aria-label={phase === "idle" ? "Start recording" : phase === "recording" ? "Pause" : "Resume"}
              >
                {phase === "idle" && <span className="h-6 w-6 rounded-full bg-white" />}
                {phase === "recording" && <span className="h-5 w-5 rounded-sm bg-white" />}
                {phase === "paused" && <span className="ml-1 h-0 w-0 border-y-8 border-l-[13px] border-y-transparent border-l-white" />}
              </button>
            </div>

            <p className="mt-6 font-mono text-2xl text-ink">{formatDuration(seconds)}</p>
            <p className="label mt-1">
              {phase === "idle" ? "Tap to start" : phase === "recording" ? "Recording" : "Paused"}
            </p>

            {live && (
              <Button variant="secondary" className="mt-6" onClick={stop}>
                Stop and review
              </Button>
            )}
          </>
        )}

        {phase === "recorded" && (
          <div className="w-full max-w-md">
            <p className="text-center font-display text-xl text-ink">
              Recorded {formatDuration(seconds)}
            </p>
            <div className="mt-6 space-y-3">
              <label className="block">
                <SectionLabel>Title (optional)</SectionLabel>
                <TextInput
                  className="mt-1"
                  placeholder="e.g. Weekly sync"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label className="block">
                <SectionLabel>Key terms (optional)</SectionLabel>
                <TextInput
                  className="mt-1"
                  placeholder="Names, technical terms"
                  value={keyterms}
                  onChange={(e) => setKeyterms(e.target.value)}
                />
              </label>
            </div>
            <div className="mt-6 flex gap-2">
              <Button onClick={save} className="flex-1">
                Save and transcribe
              </Button>
              <Button variant="ghost" onClick={discard}>
                Discard
              </Button>
            </div>
          </div>
        )}

        {phase === "uploading" && (
          <div className="w-full max-w-md text-center">
            <p className="font-display text-xl text-ink">Uploading…</p>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-line">
              <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="label mt-2">{progress < 100 ? `${progress}%` : "Processing on the server"}</p>
          </div>
        )}
      </div>
    </div>
  );
}
