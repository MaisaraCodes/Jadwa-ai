// SME portal — DocumentUpload
// Rendered inside the SME portal (data-portal="sme"), so bg-accent/text-accent
// resolve to oasis teal (DESIGN_SYSTEM.md §4, §11). Dropzone layout matches
// docs/mockups/sme_portal_arabic_rtl_light.html; copy follows the global
// language via i18n/strings.ts. Drag-drop or browse, per-file progress +
// status, retry on failure. Accessible: keyboard-openable drop zone, visible
// focus, aria-live status, reduced-motion aware.
//
// Usage:
//   <DocumentUpload applicationId={app.id} onUploaded={(doc) => refreshList(doc)} />
import { useCallback, useRef, useState } from "react";
import { IconCloudUpload } from "@tabler/icons-react";
import { uploadDocument, ApiError } from "../../lib/api";
import type { UploadItem, UploadedDocument } from "../../types";
import { useLang } from "../../i18n/LangProvider";
import type { Lang } from "../../i18n/LangProvider";
import { STRINGS } from "../../i18n/strings";

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

function prevalidate(file: File, lang: Lang): string | null {
  if (file.size === 0) return STRINGS["upload.errorEmpty"][lang];
  if (file.size > MAX_BYTES) return STRINGS["upload.errorTooLarge"][lang];
  // Some browsers leave type blank for HEIC; fall back to extension check.
  if (file.type && !ACCEPTED_TYPES.has(file.type)) return STRINGS["upload.errorUnsupportedType"][lang];
  return null;
}

export default function DocumentUpload({ applicationId, onUploaded }: Props) {
  const { t, lang } = useLang();
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
        const message = err instanceof ApiError ? err.message : t("upload.errorFailed");
        patch(item.id, { stage: "failed", error: message });
      }
    },
    [applicationId, onUploaded, patch, t],
  );

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const incoming: UploadItem[] = Array.from(files).map((file) => {
        const problem = prevalidate(file, lang);
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
    [startUpload, lang],
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
    <section className="h-full w-full">
      <div
        role="button"
        tabIndex={0}
        aria-label={t("upload.dropzoneAriaLabel")}
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
          "flex h-full cursor-pointer flex-col items-center justify-center rounded-xl border-[1.5px] border-dashed px-4 py-[22px] text-center transition-colors motion-reduce:transition-none",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
          dragging ? "border-accent bg-accent-soft" : "border-line-strong bg-surface",
        ].join(" ")}
      >
        <IconCloudUpload size={26} className="text-accent" aria-hidden="true" />
        <p className="mb-1 mt-2.5 text-[13px] font-medium text-ink">{t("upload.dropHere")}</p>
        <p className="mb-3 text-[11.5px] text-text-3">{t("upload.hint")}</p>
        <span className="rounded-lg bg-accent px-[18px] py-2 text-[12.5px] font-medium text-on-accent">
          {t("upload.browse")}
        </span>
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
              className="flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-medium text-ink" title={it.file.name}>
                    {it.file.name}
                  </p>
                  <StatusLabel item={it} />
                </div>

                {it.stage === "uploading" && (
                  <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full bg-accent transition-[width] duration-150 motion-reduce:transition-none"
                      style={{ width: `${Math.round(it.progress * 100)}%` }}
                    />
                  </div>
                )}

                {it.stage === "failed" && it.error && (
                  <p className="mt-1 text-xs text-flag">{it.error}</p>
                )}
              </div>

              {it.stage === "failed" && !prevalidate(it.file, lang) && (
                <button
                  type="button"
                  onClick={() => startUpload(it)}
                  className="shrink-0 rounded-lg border border-line-strong px-2.5 py-1 text-xs font-medium text-accent-strong hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {t("upload.retry")}
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
  const { t } = useLang();
  const map: Record<UploadItem["stage"], { text: string; cls: string }> = {
    queued: { text: t("upload.statusQueued"), cls: "text-text-3" },
    uploading: { text: `${Math.round(item.progress * 100)}%`, cls: "text-accent-strong" },
    uploaded: { text: t("upload.statusUploaded"), cls: "text-accent-strong" },
    failed: { text: t("upload.statusFailed"), cls: "text-flag" },
  };
  const { text, cls } = map[item.stage];
  return <span className={`shrink-0 text-xs font-medium ${cls}`}>{text}</span>;
}
