// Supabase browser client — used for Auth (session + JWT). One instance per app.
// Env (frontend/.env, VITE_-prefixed so Vite exposes them to the client):
//   VITE_SUPABASE_URL
//   VITE_SUPABASE_ANON_KEY
import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!url || !anonKey) {
  // Fail loud in dev rather than silently 401-ing every request.
  console.warn("Supabase env vars missing: VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY");
}

export const supabase = createClient(url, anonKey);
