import type { MeetingStatus } from "@/lib/types";
import { TERMINAL_STATUSES } from "@/lib/types";

const STYLES: Record<MeetingStatus, string> = {
  uploaded: "bg-zinc-100 text-zinc-600",
  transcribing: "bg-blue-50 text-blue-700",
  extracting: "bg-violet-50 text-violet-700",
  indexing: "bg-amber-50 text-amber-700",
  done: "bg-emerald-50 text-emerald-700",
  failed: "bg-red-50 text-red-700",
};

export function StatusBadge({ status }: { status: MeetingStatus }) {
  const processing = !TERMINAL_STATUSES.includes(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      {processing && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {status}
    </span>
  );
}
