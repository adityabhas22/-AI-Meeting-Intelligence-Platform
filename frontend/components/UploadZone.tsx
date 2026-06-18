import { useRef, useState } from "react";
import { Button, SectionLabel, TextInput } from "@/components/ui/primitives";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function humanSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function UploadZone({ onUploaded }: { onUploaded: () => void }) {
  const toast = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [keyterms, setKeyterms] = useState("");
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);

  function reset() {
    setFile(null);
    setTitle("");
    setKeyterms("");
    setProgress(null);
  }

  function upload() {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    if (title.trim()) form.append("title", title.trim());
    if (keyterms.trim()) form.append("keyterms", keyterms.trim());

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/meetings`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        toast("Uploaded. Processing has started.", "success");
        reset();
        onUploaded();
      } else {
        let detail = "Upload failed";
        try {
          detail = JSON.parse(xhr.responseText).detail ?? detail;
        } catch {
          /* keep default */
        }
        toast(detail, "error");
        setProgress(null);
      }
    };
    xhr.onerror = () => {
      toast("Could not reach the server", "error");
      setProgress(null);
    };
    setProgress(0);
    xhr.send(form);
  }

  const uploading = progress !== null;

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files?.[0];
        if (dropped) setFile(dropped);
      }}
      className={cn(
        "rounded-xl border bg-surface transition-colors",
        dragging ? "border-accent bg-accent-soft/40" : "border-line",
      )}
    >
      {!file ? (
        <button
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center justify-center gap-1 px-6 py-12 text-center"
        >
          <span className="font-display text-lg text-ink">Drop a recording to begin</span>
          <span className="text-sm text-muted">or click to choose a file</span>
          <span className="label mt-2">wav · mp3 · m4a · webm</span>
        </button>
      ) : (
        <div className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{file.name}</p>
              <p className="label mt-0.5">{humanSize(file.size)}</p>
            </div>
            {!uploading && (
              <Button variant="ghost" size="sm" onClick={reset}>
                Change
              </Button>
            )}
          </div>

          {uploading ? (
            <div className="mt-4">
              <div className="h-1.5 overflow-hidden rounded-full bg-line">
                <div
                  className="h-full rounded-full bg-accent transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="label mt-2">
                {progress! < 100 ? `Uploading ${progress}%` : "Processing on the server"}
              </p>
            </div>
          ) : (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <label className="block">
                <SectionLabel>Title (optional)</SectionLabel>
                <TextInput
                  className="mt-1"
                  placeholder="e.g. Q3 Planning"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
              <label className="block">
                <SectionLabel>Key terms (optional)</SectionLabel>
                <TextInput
                  className="mt-1"
                  placeholder="Kubernetes, OAuth, pgvector"
                  value={keyterms}
                  onChange={(e) => setKeyterms(e.target.value)}
                />
              </label>
              <div className="sm:col-span-2">
                <Button onClick={upload} className="w-full sm:w-auto">
                  Transcribe meeting
                </Button>
                <p className="mt-2 text-xs text-muted">
                  Key terms sharpen transcription of names and technical vocabulary.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="audio/*,video/*,.wav,.mp3,.m4a,.webm"
        className="hidden"
        onChange={(e) => {
          const chosen = e.target.files?.[0];
          if (chosen) setFile(chosen);
          e.target.value = "";
        }}
      />
    </div>
  );
}
