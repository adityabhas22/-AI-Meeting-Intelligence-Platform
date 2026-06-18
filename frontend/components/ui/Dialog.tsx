import { Button } from "./primitives";

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button className="absolute inset-0 bg-ink/30" aria-label="Close" onClick={onCancel} />
      <div className="rise relative w-full max-w-sm rounded-xl border border-line bg-surface p-6 shadow-[0_20px_60px_rgba(29,27,22,0.2)]">
        <h2 className="font-display text-xl text-ink">{title}</h2>
        {body && <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
