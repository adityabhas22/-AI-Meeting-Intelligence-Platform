import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { TERMINAL_STATUSES, type MeetingStatus } from "@/lib/types";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-ink",
  secondary: "border border-line bg-surface text-ink hover:border-ink/30",
  ghost: "text-muted hover:bg-ink/5 hover:text-ink",
  danger: "border border-failed/30 text-failed hover:bg-failed/10",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors",
        "disabled:pointer-events-none disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm",
        VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cn("rounded-xl border border-line bg-surface", className)}>{children}</section>
  );
}

export function SectionLabel({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("label", className)}>{children}</p>;
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink outline-none",
        "placeholder:text-faint focus:border-accent",
        className,
      )}
      {...props}
    />
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block animate-spin rounded-full border-2 border-line border-t-accent",
        className ?? "h-4 w-4",
      )}
    />
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded bg-line/70", className)} />;
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface/50 px-6 py-14 text-center">
      <p className="font-display text-lg text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}

const STATUS: Record<MeetingStatus, { label: string; dot: string; text: string }> = {
  uploaded: { label: "Queued", dot: "bg-faint", text: "text-muted" },
  transcribing: { label: "Transcribing", dot: "bg-processing", text: "text-processing" },
  extracting: { label: "Extracting", dot: "bg-processing", text: "text-processing" },
  indexing: { label: "Indexing", dot: "bg-processing", text: "text-processing" },
  done: { label: "Ready", dot: "bg-done", text: "text-done" },
  failed: { label: "Failed", dot: "bg-failed", text: "text-failed" },
};

export function StatusPill({ status }: { status: MeetingStatus }) {
  const s = STATUS[status];
  const processing = !TERMINAL_STATUSES.includes(status);
  return (
    <span className={cn("label inline-flex items-center gap-1.5", s.text)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot, processing && "animate-pulse")} />
      {s.label}
    </span>
  );
}
