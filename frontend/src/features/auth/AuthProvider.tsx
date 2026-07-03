// Auth state for the whole app. Wraps Supabase Auth (client-side — no custom
// login/signup endpoints, per CONVENTIONS.md). Exposes the current session, the
// derived role ("sme" | "bank"), and sign in / sign up / sign out.
//
// Role source: the JWT. Set at signup via user_metadata.role (the only metadata a
// client can write without admin keys). The backend reads app_metadata.role first,
// then falls back to user_metadata.role — so this stays consistent with auth.py.
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "../../lib/supabase";

export type AppRole = "sme" | "bank";

function roleFromUser(user: User | null): AppRole | null {
  const raw =
    (user?.app_metadata as Record<string, unknown> | undefined)?.role ??
    (user?.user_metadata as Record<string, unknown> | undefined)?.role;
  return raw === "sme" || raw === "bank" ? raw : null;
}

interface AuthValue {
  session: Session | null;
  user: User | null;
  role: AppRole | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, role: AppRole) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });
    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthValue>(() => {
    const user = session?.user ?? null;
    return {
      session,
      user,
      role: roleFromUser(user),
      loading,
      async signIn(email, password) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw new Error(error.message);
      },
      async signUp(email, password, role) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { role } },
        });
        if (error) throw new Error(error.message);
      },
      async signOut() {
        await supabase.auth.signOut();
      },
    };
  }, [session, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}
