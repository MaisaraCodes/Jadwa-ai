// App router. Wraps everything in LangProvider + ThemeProvider (global,
// user-controlled) then AuthProvider, then routes by role:
//   /             → public landing page (signed-out) or the user's portal (signed-in)
//   /data         → public data-sources / credibility page
//   /login        → shared sign in / create account
//   /sme/*        → SME portal (role "sme")
//   /bank/*       → bank dashboard (role "bank")
//   *             → send the user to the right place for their role
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LangProvider } from "./i18n/LangProvider";
import { ThemeProvider } from "./lib/theme";
import { AuthProvider } from "./features/auth/AuthProvider";
import { RequireRole, RedirectByRole, LandingOrRedirect } from "./features/auth/RequireRole";
import DataSourcesPage from "./features/landing/DataSourcesPage";
import LoginPage from "./features/auth/LoginPage";
import SmePortalLayout from "./features/sme/SmePortalLayout";
import SmeDashboardPage from "./features/sme/pages/SmeDashboardPage";
import NewApplicationPage from "./features/sme/pages/NewApplicationPage";
import ApplicationDetailPage from "./features/sme/pages/ApplicationDetailPage";
import ReviewDocumentsPage from "./features/sme/pages/ReviewDocumentsPage";
import BankDashboardLayout from "./features/bank/BankDashboardLayout";
import BankQueuePage from "./features/bank/pages/BankQueuePage";
import BankApplicationDetailPage from "./features/bank/pages/BankApplicationDetailPage";

export default function App() {
  return (
    <LangProvider>
      <ThemeProvider>
        <div className="min-h-screen bg-bg font-sans text-ink antialiased">
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<LoginPage />} />

                <Route
                  path="/sme"
                  element={
                    <RequireRole role="sme">
                      <SmePortalLayout />
                    </RequireRole>
                  }
                >
                  <Route index element={<SmeDashboardPage />} />
                  <Route path="review" element={<ReviewDocumentsPage />} />
                  <Route path="review/:applicationId" element={<ReviewDocumentsPage />} />
                  <Route path="applications/new" element={<NewApplicationPage />} />
                  <Route path="applications/:applicationId" element={<ApplicationDetailPage />} />
                </Route>

                <Route
                  path="/bank"
                  element={
                    <RequireRole role="bank">
                      <BankDashboardLayout />
                    </RequireRole>
                  }
                >
                  <Route index element={<BankQueuePage />} />
                </Route>

                <Route
                  path="/bank/applications/:applicationId"
                  element={
                    <RequireRole role="bank">
                      <BankApplicationDetailPage />
                    </RequireRole>
                  }
                />

                <Route path="/" element={<LandingOrRedirect />} />
                <Route path="/data" element={<DataSourcesPage />} />
                <Route path="*" element={<RedirectByRole />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </div>
      </ThemeProvider>
    </LangProvider>
  );
}
