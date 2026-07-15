// Lifecycle status pill (DESIGN_SYSTEM.md §8.6/§9): quiet + neutral for every
// ApplicationStatus value. pass/review/flag are reserved for ForensicStatus
// only — never reused here, even for "approved"/"rejected". Shared by the SME
// dashboard list and the application detail header.
import { useLang } from "../i18n/LangProvider";
import type { StringKey } from "../i18n/strings";
import type { ApplicationStatus } from "../types";

export default function LifecycleStatusPill({ status }: { status: ApplicationStatus }) {
  const { t } = useLang();
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs font-medium text-text-2">
      {t(`sme.dashboard.status.${status}` as StringKey)}
    </span>
  );
}
