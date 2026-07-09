// App router. Wraps everything in LangProvider + ThemeProvider (global,
// user-controlled) then AuthProvider, then routes by role:
//   /login        → shared sign in / create account
//   /sme/*        → SME portal (role "sme")
//   /bank/*       → bank dashboard (role "bank")
//   /  and  *     → send the user to the right place for their role
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LangProvider } from "./i18n/LangProvider";
import { ThemeProvider } from "./lib/theme";
import { AuthProvider } from "./features/auth/AuthProvider";
import { RequireRole, RedirectByRole } from "./features/auth/RequireRole";
import LoginPage from "./features/auth/LoginPage";
import SmePortalLayout from "./features/sme/SmePortalLayout";
import SmeHomePage from "./features/sme/pages/SmeHomePage";
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
                  <Route index element={<SmeHomePage />} />
                  <Route path="review" element={<ReviewDocumentsPage />} />
                  <Route path="review/:applicationId" element={<ReviewDocumentsPage />} />
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
                  path="/bank/applications/demo"
                  element={
                    <RequireRole role="bank">
                      <BankApplicationDetailPage />
                    </RequireRole>
                  }
                />

                <Route path="/" element={<RedirectByRole />} />
                <Route path="*" element={<RedirectByRole />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </div>
      </ThemeProvider>
    </LangProvider>
  );
}
