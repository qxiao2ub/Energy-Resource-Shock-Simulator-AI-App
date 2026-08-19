import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export type Workspace = { id: string; name: string };

export const MAX_WORKSPACES = 3;

export function WorkspaceBar({
  workspaces,
  activeId,
  eventCounts,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: {
  workspaces: Workspace[];
  activeId: string | null;
  eventCounts: Record<string, number>;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [dismissedMax, setDismissedMax] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Workspace | null>(null);
  const atMax = workspaces.length >= MAX_WORKSPACES;

  const commit = (id: string) => {
    const name = draft.trim();
    if (name) onRename(id, name);
    setEditingId(null);
  };

  const requestDelete = (ws: Workspace) => {
    if ((eventCounts[ws.id] ?? 0) > 0) {
      setPendingDelete(ws);
      return;
    }
    onDelete(ws.id);
  };

  const pendingCount = pendingDelete ? (eventCounts[pendingDelete.id] ?? 0) : 0;

  return (
    <section className="border-b border-border bg-muted/40 px-6 py-4 sm:px-8">
      <div className="mx-auto flex w-full max-w-2xl flex-wrap items-center gap-2">
        <span className="mr-1 text-sm font-medium text-muted-foreground">Workspaces</span>
        {workspaces.map((ws) =>
          editingId === ws.id ? (
            <span key={ws.id} className="flex items-center gap-1">
              <Input
                autoFocus
                className="h-8 w-40"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => commit(ws.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commit(ws.id);
                  if (e.key === "Escape") setEditingId(null);
                }}
                aria-label="Workspace name"
              />
            </span>
          ) : (
            <span
              key={ws.id}
              className={`flex items-center gap-1 rounded-full px-3 py-1 text-sm ring-1 ${
                ws.id === activeId
                  ? "bg-primary text-primary-foreground ring-transparent"
                  : "bg-card text-card-foreground ring-border"
              }`}
            >
              <button type="button" onClick={() => onSelect(ws.id)} className="font-medium">
                {ws.name}
              </button>
              <button
                type="button"
                className="opacity-70 hover:opacity-100"
                aria-label={`Rename ${ws.name}`}
                onClick={() => {
                  setEditingId(ws.id);
                  setDraft(ws.name);
                }}
              >
                ✎
              </button>
              <button
                type="button"
                className="opacity-70 hover:opacity-100"
                aria-label={`Delete ${ws.name}`}
                onClick={() => requestDelete(ws)}
              >
                ✕
              </button>
            </span>
          ),
        )}
        {!atMax && (
          <Button size="sm" variant="outline" onClick={onCreate}>
            New workspace
          </Button>
        )}
        {atMax && !dismissedMax && (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            Maximum of 3 workspaces.
            <button
              type="button"
              className="rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-border hover:bg-accent"
              onClick={() => setDismissedMax(true)}
            >
              OK
            </button>
          </span>
        )}
      </div>

      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete workspace?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete?.name} has {pendingCount} {pendingCount === 1 ? "event" : "events"}. Are
              you sure you want to delete it? This action is not recoverable.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (pendingDelete) onDelete(pendingDelete.id);
                setPendingDelete(null);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
