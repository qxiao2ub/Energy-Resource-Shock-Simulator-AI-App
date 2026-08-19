import { useEffect, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setLoading(false);
      if (_event === "SIGNED_IN" && next?.user) {
        const u = next.user;
        setTimeout(() => {
          void supabase.from("profiles").upsert(
            {
              id: u.id,
              display_name:
                (u.user_metadata?.["display_name"] as string | null) ?? u.email ?? null,
            },
            { onConflict: "id" },
          );
        }, 0);
      }
    });
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const user: User | null = session?.user ?? null;
  return { session, user, loading };
}
