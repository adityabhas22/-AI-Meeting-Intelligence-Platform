"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { cn } from "@/lib/cn";

type Kind = "success" | "error" | "info";
interface ToastAction {
  label: string;
  onClick: () => void;
}
interface Toast {
  id: number;
  message: string;
  kind: Kind;
  action?: ToastAction;
}

type Notify = (message: string, kind?: Kind, action?: ToastAction) => void;

const ToastContext = createContext<Notify>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

let counter = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback<Notify>(
    (message, kind = "info", action) => {
      const id = ++counter;
      setToasts((prev) => [...prev, { id, message, kind, action }]);
      setTimeout(() => dismiss(id), action ? 6000 : 3200);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col items-end gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "rise pointer-events-auto flex items-center gap-3 rounded-lg border bg-surface px-3.5 py-2.5 text-sm shadow-[0_8px_30px_rgba(29,27,22,0.12)]",
              t.kind === "success" && "border-done/30 text-done",
              t.kind === "error" && "border-failed/30 text-failed",
              t.kind === "info" && "border-line text-ink",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                t.kind === "success" && "bg-done",
                t.kind === "error" && "bg-failed",
                t.kind === "info" && "bg-accent",
              )}
            />
            <span>{t.message}</span>
            {t.action && (
              <button
                onClick={() => {
                  t.action!.onClick();
                  dismiss(t.id);
                }}
                className="font-mono text-xs font-medium text-accent underline underline-offset-2 hover:text-accent-ink"
              >
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
