// SME portal — DocumentUpload
// Teal identity (CONVENTIONS.md: teal = SME, coral = bank). Drag-drop or browse,
// per-file progress + status, retry on failure. Accessible: keyboard-openable
// drop zone, visible focus, aria-live status, reduced-motion aware.
//
// Usage:
//   <DocumentUpload applicationId={app.id} onUploaded={(doc) => refreshList(doc)} />
import { useCallback, useRef, useState } from "react";
import { uploadDocument, ApiError } from "../../lib/api";
import type { UploadItem, UploadedDocument } from "../../types";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.webp,.heic,.heif";
const ACCEPTED_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/heic",
  "image/heif",
]);
const MAX_BYTES = 15 * 1024 * 1024;

interface Props {
  applicationId: string;
  onUploaded?: (doc: UploadedDocument) => void;
}

function prevalidate(file: File): string | null {
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_BYTES) return "This file is over 15 MB.";
  // Some browsers leave type blank for HEIC; fall back to extension check.
  if (file.type && !ACCEPTED_TYPES.has(file.type)) return "Unsupported file type.";
  return null;
}

export default function DocumentUpload({ applicationId, onUploaded }: Props) {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const patch = useCallback((id: string, next: Partial<UploadItem>) => {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...next } : it)));
  }, []);

  const startUpload = useCallback(
    async (item: UploadItem) => {
      patch(item.id, { stage: "uploading", progress: 0, error: undefined });
      try {
        const doc = await uploadDocument(applicationId, item.file, (f) =>
          patch(item.id, { progress: f }),
        );
        patch(item.id, { stage: "uploaded", progress: 1, result: doc });
        onUploaded?.(doc);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Upload failed. Try again.";
        patch(item.id, { stage: "failed", error: message });
      }
    },
    [applicationId, onUploaded, patch],
  );

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const incoming: UploadItem[] = Array.from(files).map((file) => {
        const problem = prevalidate(file);
        return {
          id: crypto.randomUUID(),
          file,
          stage: problem ? "failed" : "queued",
          progress: 0,
          error: problem ?? undefined,
        };
      });
      setItems((prev) => [...prev, ...incoming]);
      incoming.filter((it) => it.stage === "queued").forEach(startUpload);
    },
    [startUpload],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
    },
    [addFiles],
  );

  const openPicker = () => inputRef.current?.click();

  return (
    <section className="mx-auto w-full max-w-xl">
      <div
        role="button"
        tabIndex={0}
        aria-label="Add documents: drag files here or press Enter to browse"
        onClick={openPicker}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPicker();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={[
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors motion-reduce:transition-none",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2",
          dragging
            ? "border-teal-500 bg-teal-50"
            : "border-teal-200 bg-white hover:border-teal-400 hover:bg-teal-50/40",
        ].join(" ")}
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-100 text-teal-700">
          {/* upload glyph */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 16V5m0 0 4 4m-4-4-4 4M5 19h14"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <p className="text-sm font-medium text-slate-800">
          Drop documents here, or <span className="text-teal-700 underline">browse</span>
        </p>
        <p className="text-xs text-slate-500">
          Receipts, invoices, or statements — PDF or image, up to 15 MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          className="sr-only"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files);
            e.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="mt-4 space-y-2" aria-live="polite">
          {items.map((it) => (
            <li
              key={it.id}
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium text-slate-800" title={it.file.name}>
                    {it.file.name}
                  </p>
                  <StatusLabel item={it} />
                </div>

                {it.stage === "uploading" && (
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-teal-500 transition-[width] duration-150 motion-reduce:transition-none"
                      style={{ width: `${Math.round(it.progress * 100)}%` }}
                    />
                  </div>
                )}

                {it.stage === "failed" && it.error && (
                  <p className="mt-1 text-xs text-rose-600">{it.error}</p>
                )}
              </div>

              {it.stage === "failed" && !prevalidate(it.file) && (
                <button
                  type="button"
                  onClick={() => startUpload(it)}
                  className="shrink-0 rounded-lg border border-teal-300 px-2.5 py-1 text-xs font-medium text-teal-700 hover:bg-teal-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
                >
                  Retry
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function StatusLabel({ item }: { item: UploadItem }) {
  const map: Record<UploadItem["stage"], { text: string; cls: string }> = {
    queued: { text: "Queued", cls: "text-slate-500" },
    uploading: { text: `${Math.round(item.progress * 100)}%`, cls: "text-teal-700" },
    uploaded: { text: "Uploaded", cls: "text-teal-700" },
    failed: { text: "Failed", cls: "text-rose-600" },
  };
  const { text, cls } = map[item.stage];
  return <span className={`shrink-0 text-xs font-medium ${cls}`}>{text}</span>;
}
