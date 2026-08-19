import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { AuthBar } from "@/components/AuthBar";
import { WorkspaceBar, MAX_WORKSPACES, type Workspace } from "@/components/WorkspaceBar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { TimeBar, MS_PER_DAY, MS_PER_HOUR } from "@/components/TimeBar";
import {
  getEventStatus,
  STATUS_LABEL,
  STATUS_MARKER_COLOR,
  formatDate,
  type EventStatus,
} from "@/lib/event-status";

const TYPE_COLOR: Record<string, string> = {
  war: "#dc2626",
  earthquake: "#a16207",
  hurricane: "#0891b2",
  port_closure: "#1d4ed8",
  pipeline_failure: "#ea580c",
  cyberattack: "#7c3aed",
  labor_strike: "#db2777",
  sanctions: "#0f172a",
  mine_accident: "#78350f",
  drought: "#ca8a04",
  shipping_chokepoint: "#0d9488",
  pandemic: "#16a34a",
};

const DEFAULT_FLAG_COLOR = "#64748b";
const CURSOR_FLAG_COLOR = "#dc2626";

function flagSvg(color: string, w: number, h: number) {
  return `%3Csvg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}' viewBox='0 0 20 24'%3E%3Cpath d='M4 23V2' stroke='%23111' stroke-width='1.8' stroke-linecap='round'/%3E%3Cpath d='M4.9 2.6h10.4l-2.6 3.9 2.6 3.9H4.9z' fill='${encodeURIComponent(color)}' stroke='%23111' stroke-width='1' stroke-linejoin='round'/%3E%3C/svg%3E`;
}

function flagCursor(color: string) {
  return `url("data:image/svg+xml;utf8,${flagSvg(color, 20, 24)}") 4 23, crosshair`;
}

const EVENT_TYPES = [
  "war",
  "earthquake",
  "hurricane",
  "port_closure",
  "pipeline_failure",
  "cyberattack",
  "labor_strike",
  "sanctions",
  "mine_accident",
  "drought",
  "shipping_chokepoint",
  "pandemic",
] as const;

type EventType = (typeof EVENT_TYPES)[number];

function formatType(type: string) {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function contrastColor(hex: string) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "#0f172a" : "#ffffff";
}

function parseCoord(value: string, limit: number) {
  const n = Number(value);
  if (value.trim() === "" || !Number.isFinite(n) || n < -limit || n > limit) return null;
  return Math.round(n * 10) / 10;
}

type MapEvent = {
  id: string;
  name: string;
  type: EventType | "";
  severity: string;
  startDate: string;
  endDate: string;
  notes: string;
  lat: number;
  lng: number;
};

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Energy Resource Shock Simulator" },
      { name: "description", content: "Map energy supply shocks — wars, storms, port closures and more — and model their impact on global resource flows." },
      { property: "og:title", content: "Energy Resource Shock Simulator" },
      { property: "og:description", content: "Map energy supply shocks — wars, storms, port closures and more — and model their impact on global resource flows." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const [guestEvents, setGuestEvents] = useState<MapEvent[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(1);

  useEffect(() => {
    if (!running) return;
    const tickMs = 100;
    const id = window.setInterval(() => {
      setNow((t) => t + (speed * MS_PER_HOUR * tickMs) / 1000);
    }, tickMs);
    return () => window.clearInterval(id);
  }, [running, speed]);

  const workspacesQuery = useQuery({
    queryKey: ["workspaces", user?.id],
    enabled: !!user,
    queryFn: async (): Promise<Workspace[]> => {
      const { data, error: err } = await supabase
        .from("workspaces")
        .select("id, name")
        .order("created_at", { ascending: true });
      if (err) throw err;
      return data ?? [];
    },
  });

  const workspaces = workspacesQuery.data ?? [];

  useEffect(() => {
    if (!workspaces.length) {
      setActiveId(null);
      return;
    }
    if (!activeId || !workspaces.some((w) => w.id === activeId)) {
      setActiveId(workspaces[0]!.id);
    }
  }, [workspaces, activeId]);

  const eventsQuery = useQuery({
    queryKey: ["events", activeId],
    enabled: !!activeId,
    queryFn: async (): Promise<MapEvent[]> => {
      const { data, error: err } = await supabase
        .from("events")
        .select("id, name, type, severity, start_date, end_date, notes, lat, lng")
        .eq("workspace_id", activeId!)
        .order("created_at", { ascending: true });
      if (err) throw err;
      return (data ?? []).map((row) => ({
        id: row.id,
        name: row.name,
        type: (row.type ?? "") as EventType | "",
        severity: row.severity === null ? "" : Number(row.severity).toFixed(1),
        startDate: row.start_date ?? "",
        endDate: row.end_date ?? "",
        notes: row.notes ?? "",
        lat: row.lat,
        lng: row.lng,
      }));
    },
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["workspaces", user?.id] });
    queryClient.invalidateQueries({ queryKey: ["events"] });
    queryClient.invalidateQueries({ queryKey: ["event-counts", user?.id] });
  };

  const eventCountsQuery = useQuery({
    queryKey: ["event-counts", user?.id],
    enabled: !!user,
    queryFn: async (): Promise<Record<string, number>> => {
      const { data, error: err } = await supabase.from("events").select("workspace_id");
      if (err) throw err;
      const counts: Record<string, number> = {};
      for (const row of data ?? []) {
        counts[row.workspace_id] = (counts[row.workspace_id] ?? 0) + 1;
      }
      return counts;
    },
  });

  const run = async (fn: () => Promise<void>) => {
    setError(null);
    try {
      await fn();
      invalidate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  const events = user ? (eventsQuery.data ?? []) : guestEvents;

  const addEvent = (event: MapEvent) => {
    if (!user) {
      setGuestEvents((p) => [...p, event]);
      return;
    }
    if (!activeId) {
      setError("Create a workspace before adding events.");
      return;
    }
    void run(async () => {
      const { error: err } = await supabase.from("events").insert({
        workspace_id: activeId,
        name: event.name,
        type: event.type || null,
        severity: event.severity === "" ? null : Number(event.severity),
        start_date: event.startDate || null,
        end_date: event.endDate || null,
        notes: event.notes || null,
        lat: event.lat,
        lng: event.lng,
      });
      if (err) throw err;
    });
  };

  const removeEvent = (id: string) => {
    if (!user) {
      setGuestEvents((p) => p.filter((e) => e.id !== id));
      return;
    }
    void run(async () => {
      const { error: err } = await supabase.from("events").delete().eq("id", id);
      if (err) throw err;
    });
  };

  return (
    <main className="w-full bg-background">
      <MapSection
        events={events}
        onAddEvent={addEvent}
        now={now}
        accountSlot={<AuthBar email={loading ? null : (user?.email ?? null)} />}
      />

      <TimeBar
        now={now}
        running={running}
        speed={speed}
        onToggle={() => setRunning((r) => !r)}
        onSetDate={setNow}
        onStep={(days) => setNow((t) => t + days * MS_PER_DAY)}
        onSpeedChange={setSpeed}
        onReset={() => setNow(Date.now())}
      />

      {user && (
        <WorkspaceBar
          workspaces={workspaces}
          activeId={activeId}
          eventCounts={eventCountsQuery.data ?? {}}
          onSelect={setActiveId}
          onCreate={() =>
            void run(async () => {
              if (workspaces.length >= MAX_WORKSPACES) {
                throw new Error("You can have at most 3 workspaces.");
              }
              const taken = new Set(workspaces.map((w) => w.name.trim().toLowerCase()));
              let n = workspaces.length + 1;
              while (taken.has(`workspace ${n}`.toLowerCase())) n += 1;
              const { data, error: err } = await supabase
                .from("workspaces")
                .insert({ user_id: user.id, name: `Workspace ${n}` })
                .select("id")
                .single();
              if (err) throw err;
              setActiveId(data.id);
            })
          }
          onRename={(id, name) =>
            void run(async () => {
              if (
                workspaces.some(
                  (w) => w.id !== id && w.name.trim().toLowerCase() === name.trim().toLowerCase(),
                )
              ) {
                throw new Error("You already have a workspace with that name.");
              }
              const { error: err } = await supabase
                .from("workspaces")
                .update({ name })
                .eq("id", id);
              if (err) {
                throw err.code === "23505"
                  ? new Error("You already have a workspace with that name.")
                  : err;
              }
            })
          }
          onDelete={(id) =>
            void run(async () => {
              const { error: err } = await supabase.from("workspaces").delete().eq("id", id);
              if (err) throw err;
            })
          }
        />
      )}

      {error && (
        <p className="px-6 pt-4 text-center text-sm text-destructive sm:px-8">{error}</p>
      )}

      <EventsSection
        events={events}
        onRemove={removeEvent}
        now={now}
        emptyHint={
          !user
            ? "No events yet — click the map to add one. Sign in to save events into workspaces."
            : !activeId
              ? "Create a workspace above to start saving events."
              : "No events yet — click a spot on the map above to add your first one."
        }
      />
      <InfoSection />
    </main>
  );
}

function MapSection({
  events,
  onAddEvent,
  now,
  accountSlot,
}: {
  events: MapEvent[];
  onAddEvent: (event: MapEvent) => void;
  now: number;
  accountSlot?: React.ReactNode;
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<import("leaflet").Map | null>(null);
  const leafletRef = useRef<typeof import("leaflet") | null>(null);
  const markerLayer = useRef<import("leaflet").LayerGroup | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [hover, setHover] = useState<{ lat: number; lng: number } | null>(null);
  const [pending, setPending] = useState<{ lat: number; lng: number } | null>(null);
  const [name, setName] = useState("");
  const [type, setType] = useState<EventType | "">("");
  const [severity, setSeverity] = useState(5);
  const [latText, setLatText] = useState("");
  const [lngText, setLngText] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    let map: import("leaflet").Map | null = null;
    let cancelled = false;

    const init = async () => {
      if (!mapRef.current || cancelled) return;

      const L = await import("leaflet");
      if (cancelled || !mapRef.current) return;
      if (mapInstance.current) return;

      // Inject Leaflet CSS on the client only.
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      link.integrity = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
      link.crossOrigin = "";
      document.head.appendChild(link);

      map = L.map(mapRef.current, {
        center: [20, 0],
        zoom: 2,
        zoomControl: false,
        attributionControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map);

      L.control.zoom({ position: "bottomright" }).addTo(map);

      map.on("click", (e: import("leaflet").LeafletMouseEvent) => {
        setPending({ lat: e.latlng.lat, lng: e.latlng.lng });
        setLatText(e.latlng.lat.toFixed(1));
        setLngText(e.latlng.lng.toFixed(1));
      });

      map.on("mousemove", (e: import("leaflet").LeafletMouseEvent) => {
        setHover({ lat: e.latlng.lat, lng: e.latlng.lng });
      });
      map.on("mouseout", () => setHover(null));

      markerLayer.current = L.layerGroup().addTo(map);

      leafletRef.current = L;
      mapInstance.current = map;
      setIsReady(true);
    };

    init();

    return () => {
      cancelled = true;
      if (map) {
        map.remove();
      }
      mapInstance.current = null;
      markerLayer.current = null;
    };
  }, []);

  useEffect(() => {
    const L = leafletRef.current;
    const layer = markerLayer.current;
    if (!L || !layer) return;
    layer.clearLayers();
    for (const ev of events) {
      const status = getEventStatus(now, ev.startDate, ev.endDate);
      const color = TYPE_COLOR[ev.type] ?? DEFAULT_FLAG_COLOR;
      const w = status === "active" ? 24 : 20;
      const h = Math.round(w * 1.2);
      const halo =
        status === "inactive"
          ? "filter:drop-shadow(0 1px 2px rgba(0,0,0,.45));"
          : `filter:drop-shadow(0 0 3px ${STATUS_MARKER_COLOR[status]}) drop-shadow(0 0 6px ${STATUS_MARKER_COLOR[status]});`;
      L.marker([ev.lat, ev.lng], {
        icon: L.divIcon({
          className: "",
          html: `<img src="data:image/svg+xml;utf8,${flagSvg(color, w, h)}" width="${w}" height="${h}" style="display:block;${halo}" />`,
          iconSize: [w, h],
          iconAnchor: [Math.round(w * 0.2), h - 1],
        }),
      })
        .addTo(layer)
        .bindTooltip(
          `<strong>${escapeHtml(ev.name)}</strong><br/><em>${escapeHtml(STATUS_LABEL[status])}</em>${
            ev.type ? `<br/><em>${escapeHtml(formatType(ev.type))}</em>` : ""
          }${ev.severity ? `<br/>Severity: ${escapeHtml(ev.severity)}/10` : ""}${
            ev.startDate
              ? `<br/>${escapeHtml(formatDate(ev.startDate))}${ev.endDate ? ` → ${escapeHtml(formatDate(ev.endDate))}` : ""}`
              : ""
          }${ev.notes ? `<br/>${escapeHtml(ev.notes)}` : ""}`,
          { direction: "top", offset: [0, -4] },
        );
    }
  }, [events, isReady, now]);

  const closeDialog = () => {
    setPending(null);
    setName("");
    setSeverity(5);
    setLatText("");
    setLngText("");
    setStartDate("");
    setEndDate("");
    setNotes("");
  };

  const trimmedName = name.trim();
  const isDuplicateName = events.some(
    (e) => e.name.toLowerCase() === trimmedName.toLowerCase(),
  );

  const save = () => {
    const lat = parseCoord(latText, 90);
    const lng = parseCoord(lngText, 180);
    if (!pending || !trimmedName || isDuplicateName || lat === null || lng === null) return;
    onAddEvent({
      id: crypto.randomUUID(),
      name: trimmedName,
      type,
      severity: severity.toFixed(1),
      startDate,
      endDate,
      notes: notes.trim(),
      lat,
      lng,
    });
    closeDialog();
  };

  return (
    <section className="relative z-0 h-[70vh] w-full overflow-hidden border-b-4 border-border">
      <div
        ref={mapRef}
        className="absolute inset-0 z-0"
        style={{ cursor: flagCursor(CURSOR_FLAG_COLOR) }}
        aria-label="Interactive world map"
        role="img"
      />

      {!isReady && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-muted">
          <div className="flex flex-col items-center gap-3 text-muted-foreground">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-current border-t-transparent" />
            <p className="text-sm font-medium">Loading map…</p>
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute inset-0 z-20 flex items-start justify-between gap-4 p-6 sm:p-8">
        <header className="pointer-events-auto self-start">
          <div className="rounded-xl bg-card/90 px-5 py-4 shadow-lg ring-1 ring-border/50 backdrop-blur-sm">
            <h1 className="text-lg font-semibold tracking-tight text-card-foreground sm:text-xl">
              Energy Resource Shock Simulator
            </h1>
            <p className="mt-0.5 text-xs text-muted-foreground sm:text-sm">
              Click anywhere on the map to add a supply shock event
            </p>
          </div>
        </header>
        {accountSlot}
      </div>

      {hover && (
        <div className="pointer-events-none absolute bottom-4 left-4 z-20 rounded-lg bg-card/90 px-3 py-1.5 font-mono text-xs text-card-foreground shadow-md ring-1 ring-border/50 backdrop-blur-sm">
          {hover.lat.toFixed(1)}°, {hover.lng.toFixed(1)}°
        </div>
      )}

      <Dialog open={pending !== null} onOpenChange={(o) => !o && closeDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add an event</DialogTitle>
            <DialogDescription>
              Describe the shock and adjust its coordinates if needed.
            </DialogDescription>
          </DialogHeader>
          <div className="grid max-h-[60vh] gap-4 overflow-y-auto pr-1">
            <div className="grid gap-2">
              <Label htmlFor="event-name">Name</Label>
              <Input
                id="event-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Suez Canal blockage"
              />
              {isDuplicateName && (
                <p className="text-xs text-destructive">An event with this name already exists.</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-type">Type</Label>
              <Select value={type} onValueChange={(v) => setType(v as EventType)}>
                <SelectTrigger id="event-type">
                  <SelectValue placeholder="Select a type" />
                </SelectTrigger>
                <SelectContent>
                  {EVENT_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {formatType(t)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="event-severity">Severity</Label>
                <span className="font-mono text-sm text-muted-foreground">
                  {severity.toFixed(1)}
                </span>
              </div>
              <Slider
                id="event-severity"
                min={0}
                max={10}
                step={0.1}
                value={[severity]}
                onValueChange={(v) => setSeverity(v[0] ?? 0)}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label htmlFor="event-start">Start date</Label>
                <Input
                  id="event-start"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="event-end">End date</Label>
                <Input
                  id="event-end"
                  type="date"
                  value={endDate}
                  min={startDate || undefined}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label htmlFor="event-lat">Latitude</Label>
                <Input
                  id="event-lat"
                  type="number"
                  inputMode="decimal"
                  min={-90}
                  max={90}
                  step="any"
                  value={latText}
                  onChange={(e) => setLatText(e.target.value)}
                />
                {parseCoord(latText, 90) === null && (
                  <p className="text-xs text-destructive">Enter a value between -90 and 90.</p>
                )}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="event-lng">Longitude</Label>
                <Input
                  id="event-lng"
                  type="number"
                  inputMode="decimal"
                  min={-180}
                  max={180}
                  step="any"
                  value={lngText}
                  onChange={(e) => setLngText(e.target.value)}
                />
                {parseCoord(lngText, 180) === null && (
                  <p className="text-xs text-destructive">Enter a value between -180 and 180.</p>
                )}
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="event-notes">Description</Label>
              <Textarea
                id="event-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What is happening here?"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeDialog}>
              Cancel
            </Button>
            <Button
              onClick={save}
              disabled={
                !trimmedName ||
                isDuplicateName ||
                parseCoord(latText, 90) === null ||
                parseCoord(lngText, 180) === null
              }
            >
              Add event
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function EventsSection({
  events,
  onRemove,
  now,
  emptyHint,
}: {
  events: MapEvent[];
  onRemove: (id: string) => void;
  now: number;
  emptyHint: string;
}) {
  const [sortBy, setSortBy] = useState<"created" | "startDate" | "severity" | "type">("created");

  const statusClass: Record<EventStatus, string> = {
    active: "ring-2 ring-destructive bg-destructive/5",
    upcoming: "ring-2 ring-primary bg-primary/5",
    ended: "ring-2 ring-muted-foreground/40 opacity-90",
    inactive: "ring-1 ring-border/50 opacity-70",
  };

  const sortedEvents = [...events].sort((a, b) => {
    switch (sortBy) {
      case "startDate":
        if (!a.startDate && !b.startDate) return 0;
        if (!a.startDate) return 1;
        if (!b.startDate) return -1;
        return new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
      case "severity":
        return Number(b.severity || 0) - Number(a.severity || 0);
      case "type":
        return a.type.localeCompare(b.type);
      case "created":
      default:
        return 0;
    }
  });

  return (
    <section className="px-6 pt-16 sm:px-8">
      <div className="mx-auto w-full max-w-2xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            Your events
          </h2>
          <div className="flex items-center gap-2">
            <Label htmlFor="event-sort" className="text-sm text-muted-foreground">Sort by</Label>
            <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
              <SelectTrigger id="event-sort" className="w-[10rem]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="created">Time created</SelectItem>
                <SelectItem value="startDate">Start date</SelectItem>
                <SelectItem value="severity">Severity</SelectItem>
                <SelectItem value="type">Type</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        {events.length === 0 ? (
          <p className="mt-4 text-base text-muted-foreground">
            {emptyHint}
          </p>
        ) : (
          <ul className="mt-6 space-y-4">
            {sortedEvents.map((ev) => {
              const status = getEventStatus(now, ev.startDate, ev.endDate);
              return (
              <li
                key={ev.id}
                className={`flex items-start justify-between gap-4 rounded-xl bg-card p-5 shadow-sm transition-colors ${statusClass[status]}`}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-card-foreground">{ev.name}</h3>
                    <Badge
                      variant={
                        status === "active"
                          ? "destructive"
                          : status === "upcoming"
                            ? "default"
                            : "secondary"
                      }
                    >
                      {STATUS_LABEL[status]}
                    </Badge>
                    {ev.type && (
                      <Badge
                        variant="secondary"
                        style={{
                          backgroundColor: TYPE_COLOR[ev.type] ?? DEFAULT_FLAG_COLOR,
                          color: contrastColor(TYPE_COLOR[ev.type] ?? DEFAULT_FLAG_COLOR),
                          borderColor: "transparent",
                        }}
                      >
                        {formatType(ev.type)}
                      </Badge>
                    )}
                    {ev.severity && <Badge variant="outline">Severity {ev.severity}/10</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Lat: {ev.lat.toFixed(1)}° · Lng: {ev.lng.toFixed(1)}°
                  </p>
                  {ev.startDate && (
                    <p className="mt-1 text-xs font-medium text-foreground">
                      {formatDate(ev.startDate)}
                      {ev.endDate ? ` → ${formatDate(ev.endDate)}` : " (ongoing)"}
                    </p>
                  )}
                  {ev.notes && (
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {ev.notes}
                    </p>
                  )}
                </div>
                <Button variant="ghost" size="sm" onClick={() => onRemove(ev.id)}>
                  Remove
                </Button>
              </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

function InfoSection() {
  return (
    <section className="relative z-10 min-h-[60vh] px-6 py-16 sm:px-8">
      <div className="mx-auto w-full max-w-2xl rounded-2xl bg-card p-8 shadow-xl ring-1 ring-border/50 sm:p-12">
        <h2 className="text-2xl font-semibold tracking-tight text-card-foreground sm:text-3xl">
          About this place
        </h2>
        <p className="mt-6 text-base leading-relaxed text-muted-foreground sm:text-lg">
          This is placeholder text for the section below the map. Scroll down to
          read more details, stories, or information about the locations shown
          above.
        </p>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
          You can replace this copy with anything you like: travel notes,
          project descriptions, itineraries, or curated highlights from around
          the world.
        </p>
      </div>
    </section>
  );
}
