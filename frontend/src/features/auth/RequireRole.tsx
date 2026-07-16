// Route guards. RequireRole gates a subtree to one role; anyone signed in under
// the other role is bounced to their own home, and signed-out users go to /login.
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, type AppRole } from "./AuthProvider";
import { useLang } from "../../i18n/LangProvider";
import LandingPage from "../landing/LandingPage";

const HOME: Record<AppRole, string> = { sme: "/sme", bank: "/bank" };

function FullPageSpinner() {
  const { t } = useLang();
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-line-strong border-t-ink motion-reduce:animate-none"
        role="status"
        aria-label={t("common.loading")}
      />
    </div>
  );
}

export function RequireRole({ role, children }: { role: AppRole; children: ReactNode }) {
  const { session, role: userRole, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullPageSpinner />;
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />;
  if (userRole !== role) {
    // Signed in, wrong portal — send them to the one that matches their role.
    return <Navigate to={userRole ? HOME[userRole] : "/login"} replace />;
  }
  return <>{children}</>;
}

// Used at the catch-all route ("*") to bounce an already-signed-in user to
// their home, or a signed-out one to /login.
export function RedirectByRole() {
  const { session, role, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!session || !role) return <Navigate to="/login" replace />;
  return <Navigate to={HOME[role]} replace />;
}

// Used at "/" — the public landing page for signed-out visitors. Preserves
// the same authed-redirect behavior as RedirectByRole (signed-in users still
// land on their portal), but signed-out visitors see the landing page
// instead of being bounced straight to /login.
export function LandingOrRedirect() {
  const { session, role, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (session && role) return <Navigate to={HOME[role]} replace />;
  return <LandingPage />;
}
