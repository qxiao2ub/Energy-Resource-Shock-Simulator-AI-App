import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";

export function AuthBar({ email }: { email: string | null }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const signOut = async () => {
    await queryClient.cancelQueries();
    queryClient.clear();
    await supabase.auth.signOut();
    navigate({ to: "/auth", replace: true });
  };

  return (
    <div className="pointer-events-auto flex items-center gap-2 rounded-xl bg-card/90 px-3 py-2 shadow-lg ring-1 ring-border/50 backdrop-blur-sm">
      {email ? (
        <div className="relative">
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="block max-w-[10rem] truncate text-xs text-muted-foreground hover:text-foreground"
          >
            {email}
          </button>
          {open && (
            <div className="absolute right-0 top-full z-50 mt-2 rounded-lg bg-card p-2 shadow-lg ring-1 ring-border">
              <Button size="sm" variant="outline" onClick={signOut}>
                Sign out
              </Button>
            </div>
          )}
        </div>
      ) : (
        <Button size="sm" asChild>
          <Link to="/auth">Sign in</Link>
        </Button>
      )}
    </div>
  );
}
