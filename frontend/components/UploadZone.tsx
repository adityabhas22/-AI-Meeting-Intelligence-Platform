import { useRef, useState } from "react";
import { api } from "@/lib/api";

export function UploadZone({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    try {
      await api.upload(file);
      onUploaded();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) upload(file);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? "border-indigo-400 bg-indigo-50"
            : "border-zinc-300 bg-white hover:border-zinc-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.m4a"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload(file);
            e.target.value = "";
          }}
        />
        {busy ? (
          <p className="text-sm font-medium text-zinc-700">Uploading and processing…</p>
        ) : (
          <>
            <p className="text-sm font-medium text-zinc-700">
              Drop a meeting recording, or click to choose
            </p>
            <p className="mt-1 text-xs text-zinc-400">wav, mp3, or m4a</p>
          </>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
