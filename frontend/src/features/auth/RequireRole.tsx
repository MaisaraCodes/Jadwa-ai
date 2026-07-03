// Route guards. RequireRole gates a subtree to one role; anyone signed in under
// the other role is bounced to their own home, and signed-out users go to /login.
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, type AppRole } from "./AuthProvider";

const HOME: Record<AppRole, string> = { sme: "/sme", bank: "/bank" };

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 motion-reduce:animate-none"
        role="status"
        aria-label="Loading"
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

// Used at "/" and "/login" to bounce an already-signed-in user to their home.
export function RedirectByRole() {
  const { session, role, loading } = useAuth();
  if (loading) return <FullPageSpinner />;
  if (!session || !role) return <Navigate to="/login" replace />;
  return <Navigate to={HOME[role]} replace />;
}
