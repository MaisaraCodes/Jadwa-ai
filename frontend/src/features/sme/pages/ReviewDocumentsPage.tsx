// SME portal — DocumentReviewPanel + ReviewDocumentsPage.
// Lets the SME confirm or correct what Node 1 (document_intelligence_node)
// extracted from each uploaded document, before the forensic accountant
// reconciles it against the ledger. Low confidence_score documents are
// pre-flagged so the SME's attention goes where the LLM is least sure.
//
// GET /applications/:id/extracted and PATCH /applications/:id/documents/:id
// are both real endpoints (routers/applications.py).
//
// DocumentReviewPanel is the reusable core (list + edit + confirm + progress
// bar) — ReviewDocumentsPage wraps it with page chrome for the standalone
// /sme/review route; ApplicationDetailPage embeds the panel directly for the
// analysis-done phase, passing its own onContinue ("Submit application")
// instead of the panel's default "back to dashboard" behavior.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { IconAlertTriangle, IconCheck, IconPencil } from "@tabler/icons-react";
import { useLang } from "../../../i18n/LangProvider";
import type { StringKey } from "../../../i18n/strings";
import { ApiError, getExtractedDocuments, patchExtractedDocument } from "../../../lib/api";
import type { DocumentJSON, DocumentType } from "../../../types";
import BackButton from "../../../components/BackButton";
import Skeleton from "../../../components/Skeleton";

const LOW_CONFIDENCE_THRESHOLD = 0.85;
const DOCUMENT_TYPES: DocumentType[] = ["zatca_receipt", "invoice", "bank_statement", "contract", "other"];

interface DraftFields {
  vendor: string;
  extracted_amount: string;
  date: string;
  type: DocumentType;
}

function toDraft(doc: DocumentJSON): DraftFields {
  return {
    vendor: doc.vendor ?? "",
    extracted_amount: String(doc.extracted_amount),
    date: doc.date,
    type: doc.type,
  };
}

export interface DocumentReviewPanelProps {
  applicationId: string;
  /** Fires whenever the confirmed count changes — lets a host page (e.g. the
   * detail page's "Submit application" button) gate on full confirmation
   * without duplicating the confirm-tracking logic. */
  onAllConfirmedChange?: (info: { allConfirmed: boolean; confirmedCount: number; total: number }) => void;
  /** If provided, renders a trailing continue button with this handler.
   * Omit to let the host page provide its own action bar instead. */
  onContinue?: () => void;
  continueLabel?: string;
}

export function DocumentReviewPanel({
  applicationId,
  onAllConfirmedChange,
  onContinue,
  continueLabel,
}: DocumentReviewPanelProps) {
  const { t } = useLang();

  const [documents, setDocuments] = useState<DocumentJSON[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [confirmedIds, setConfirmedIds] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftFields | null>(null);
  const [rowError, setRowError] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    setDocuments(null);
    try {
      const { documents: docs } = await getExtractedDocuments(applicationId);
      setDocuments(docs);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : t("review.loadError"));
    }
  }, [applicationId, t]);

  useEffect(() => {
    load();
  }, [load]);

  const startEdit = (doc: DocumentJSON) => {
    setEditingId(doc.document_id);
    setDraft(toDraft(doc));
    setRowError((prev) => ({ ...prev, [doc.document_id]: "" }));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setDraft(null);
  };

  const saveEdit = async (doc: DocumentJSON) => {
    if (!draft) return;
    const amount = Number(draft.extracted_amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setRowError((prev) => ({ ...prev, [doc.document_id]: t("review.amountValidation") }));
      return;
    }

    setSavingId(doc.document_id);
    setRowError((prev) => ({ ...prev, [doc.document_id]: "" }));
    try {
      const updated = await patchExtractedDocument(applicationId, doc.document_id, {
        vendor: draft.vendor,
        extracted_amount: amount,
        date: draft.date,
        type: draft.type,
      });
      setDocuments((prev) => prev?.map((d) => (d.document_id === doc.document_id ? updated : d)) ?? prev);
      // Editing implies it wasn't right as extracted — re-confirm on save.
      setConfirmedIds((prev) => new Set(prev).add(doc.document_id));
      setEditingId(null);
      setDraft(null);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t("review.saveError");
      setRowError((prev) => ({ ...prev, [doc.document_id]: message }));
    } finally {
      setSavingId(null);
    }
  };

  const confirm = (doc: DocumentJSON) => {
    setConfirmedIds((prev) => new Set(prev).add(doc.document_id));
  };

  const allConfirmed = useMemo(
    () => documents !== null && documents.length > 0 && documents.every((d) => confirmedIds.has(d.document_id)),
    [documents, confirmedIds],
  );

  useEffect(() => {
    if (!onAllConfirmedChange || documents === null) return;
    onAllConfirmedChange({
      allConfirmed,
      confirmedCount: documents.filter((d) => confirmedIds.has(d.document_id)).length,
      total: documents.length,
    });
    // onAllConfirmedChange is expected to be referentially stable (or the
    // host memoizes it); only re-fire on data changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents, confirmedIds, allConfirmed]);

  return (
    <>
      {documents === null && !loadError && (
        <div className="space-y-2.5" role="status">
          <span className="sr-only">{t("review.loading")}</span>
          {[0, 1, 2].map((i) => (
            <div key={i} className="rounded-xl border border-line bg-surface px-4 py-3.5" aria-hidden="true">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 space-y-2">
                  <Skeleton className="h-3.5 w-28" />
                  <Skeleton className="h-3 w-40" />
                </div>
                <Skeleton className="h-5 w-24 shrink-0 rounded-full" />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <Skeleton className="h-7 w-20" />
                <Skeleton className="h-7 w-16" />
              </div>
            </div>
          ))}
        </div>
      )}

      {loadError && (
        <div className="rounded-xl border border-line bg-surface px-4 py-6 text-center">
          <p className="mb-2.5 text-[13px] text-flag">{loadError}</p>
          <button
            type="button"
            onClick={load}
            className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-accent-strong hover:bg-accent-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {t("review.retry")}
          </button>
        </div>
      )}

      {documents !== null && documents.length === 0 && (
        <p className="rounded-xl border border-line bg-surface px-4 py-6 text-center text-[13px] text-text-2">
          {t("review.empty")}
        </p>
      )}

      {documents !== null && documents.length > 0 && (
        <>
          <ul className="space-y-2.5">
            {documents.map((doc) => {
              const isEditing = editingId === doc.document_id;
              const isConfirmed = confirmedIds.has(doc.document_id);
              const lowConfidence = doc.confidence_score < LOW_CONFIDENCE_THRESHOLD;
              const error = rowError[doc.document_id];

              return (
                <li key={doc.document_id} className="rounded-xl border border-line bg-surface px-4 py-3.5">
                  {!isEditing && (
                    <>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-1.5 text-[12.5px] font-semibold text-ink">
                            {t(`review.type.${doc.type}` as StringKey)}
                            {lowConfidence && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-review-bg px-2 py-0.5 text-[11px] font-medium text-review">
                                <IconAlertTriangle size={11} aria-hidden="true" />
                                {t("review.lowConfidence")}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[12.5px] text-text-2">
                            {doc.vendor && <span>{doc.vendor} · </span>}
                            <span dir="ltr" className="tabular-nums">
                              {doc.currency} {doc.extracted_amount.toLocaleString("en-US")}
                            </span>
                            {" · "}
                            <span dir="ltr" className="tabular-nums">
                              {doc.date}
                            </span>
                          </p>
                        </div>

                        <span
                          className={[
                            "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px] font-medium",
                            isConfirmed ? "bg-pass-bg text-pass" : "bg-review-bg text-review",
                          ].join(" ")}
                        >
                          <span className={`h-1.5 w-1.5 rounded-full ${isConfirmed ? "bg-pass" : "bg-review"}`} />
                          {isConfirmed ? t("review.confirmed") : t("review.needsConfirmation")}
                        </span>
                      </div>

                      <div className="mt-3 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => confirm(doc)}
                          disabled={isConfirmed}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-on-accent disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                        >
                          <IconCheck size={13} aria-hidden="true" />
                          {t("review.confirm")}
                        </button>
                        <button
                          type="button"
                          onClick={() => startEdit(doc)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        >
                          <IconPencil size={13} aria-hidden="true" />
                          {t("review.edit")}
                        </button>
                      </div>
                    </>
                  )}

                  {isEditing && draft && (
                    <div className="space-y-2.5">
                      <label className="block text-[12px] font-medium text-text-2">
                        {t("review.field.vendor")}
                        <input
                          type="text"
                          value={draft.vendor}
                          onChange={(e) => setDraft({ ...draft, vendor: e.target.value })}
                          className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        />
                      </label>
                      <div className="grid grid-cols-2 gap-2.5">
                        <label className="block text-[12px] font-medium text-text-2">
                          {t("review.field.amount")}
                          <input
                            type="number"
                            step="0.01"
                            dir="ltr"
                            value={draft.extracted_amount}
                            onChange={(e) => setDraft({ ...draft, extracted_amount: e.target.value })}
                            className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] tabular-nums text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                          />
                        </label>
                        <label className="block text-[12px] font-medium text-text-2">
                          {t("review.field.date")}
                          <input
                            type="date"
                            dir="ltr"
                            value={draft.date}
                            onChange={(e) => setDraft({ ...draft, date: e.target.value })}
                            className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] tabular-nums text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                          />
                        </label>
                      </div>
                      <label className="block text-[12px] font-medium text-text-2">
                        {t("review.field.type")}
                        <select
                          value={draft.type}
                          onChange={(e) => setDraft({ ...draft, type: e.target.value as DocumentType })}
                          className="mt-1 w-full rounded-lg border border-line-strong bg-bg px-2.5 py-1.5 text-[13px] text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        >
                          {DOCUMENT_TYPES.map((docType) => (
                            <option key={docType} value={docType}>
                              {t(`review.type.${docType}` as StringKey)}
                            </option>
                          ))}
                        </select>
                      </label>

                      {error && <p className="text-xs text-flag">{error}</p>}

                      <div className="flex items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => saveEdit(doc)}
                          disabled={savingId === doc.document_id}
                          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-on-accent disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                        >
                          {savingId === doc.document_id ? t("review.saving") : t("review.save")}
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          disabled={savingId === doc.document_id}
                          className="rounded-lg border border-line-strong px-3 py-1.5 text-xs font-medium text-ink hover:bg-surface-2 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                        >
                          {t("review.cancel")}
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex items-center justify-between rounded-xl border border-line bg-surface px-4 py-3">
            <span className="text-[12.5px] text-text-2">
              {allConfirmed
                ? t("review.allConfirmedTitle")
                : t("review.progress", {
                    done: documents.filter((d) => confirmedIds.has(d.document_id)).length,
                    total: documents.length,
                  })}
            </span>
            {onContinue && (
              <button
                type="button"
                onClick={onContinue}
                disabled={!allConfirmed}
                className="rounded-lg bg-accent px-4 py-1.5 text-xs font-medium text-on-accent disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
              >
                {continueLabel ?? t("review.continue")}
              </button>
            )}
          </div>
        </>
      )}
    </>
  );
}

export default function ReviewDocumentsPage() {
  const { applicationId: routeApplicationId } = useParams();
  const applicationId = routeApplicationId ?? "JDW-2026-0147"; // demo fallback, mirrors SmeHomePage's APP_REF
  const { t } = useLang();
  const navigate = useNavigate();

  return (
    <section>
      <BackButton to="/sme" label={t("common.back.dashboard")} />

      <h1 className="font-display text-2xl font-extrabold text-ink">{t("review.title")}</h1>
      <p className="mb-4 mt-0.5 max-w-xl text-[13px] text-text-2">{t("review.subtitle")}</p>

      <DocumentReviewPanel applicationId={applicationId} onContinue={() => navigate("/sme")} />
    </section>
  );
}
