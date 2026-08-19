import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { toDateInput, toTimeInput } from "@/lib/event-status";

const DAY = 86400000;
const HOUR = 3600000;

export function TimeBar({
  now,
  running,
  speed,
  onToggle,
  onSetDate,
  onStep,
  onSpeedChange,
  onReset,
}: {
  now: number;
  running: boolean;
  /** Simulated hours advanced per real second. */
  speed: number;
  onToggle: () => void;
  onSetDate: (ms: number) => void;
  onStep: (days: number) => void;
  onSpeedChange: (speed: number) => void;
  onReset: () => void;
}) {
  const dateValue = toDateInput(now);
  const timeValue = toTimeInput(now);

  const setDateTime = (date: string, time: string) => {
    const t = Date.parse(`${date}T${time || "00:00"}:00Z`);
    if (Number.isFinite(t)) onSetDate(t);
  };

  return (
    <section className="border-b border-border bg-card/60 px-6 py-4 sm:px-8">
      <div className="mx-auto flex w-full max-w-4xl flex-wrap items-end gap-4">
        <div className="flex items-center gap-2">
          <Button onClick={onToggle} className="min-w-24">
            {running ? "Pause" : "Start time"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => onStep(-1)}>
            -1d
          </Button>
          <Button variant="outline" size="sm" onClick={() => onStep(1)}>
            +1d
          </Button>
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="sim-date">Current date</Label>
          <Input
            id="sim-date"
            type="date"
            className="w-44"
            value={dateValue}
            onChange={(e) => setDateTime(e.target.value, timeValue)}
          />
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="sim-time">Time (24h)</Label>
          <Input
            id="sim-time"
            type="time"
            step={60}
            className="w-32"
            value={timeValue}
            onChange={(e) => setDateTime(dateValue, e.target.value)}
          />
        </div>

        <div className="grid min-w-52 flex-1 gap-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="sim-speed">Speed</Label>
            <span className="font-mono text-xs text-muted-foreground">
              {speed} hour{speed === 1 ? "" : "s"}/sec
            </span>
          </div>
          <Slider
            id="sim-speed"
            min={0.5}
            max={72}
            step={0.5}
            value={[speed]}
            onValueChange={(v) => onSpeedChange(v[0] ?? 1)}
          />
        </div>

        <Button variant="ghost" size="sm" onClick={onReset}>
          Now
        </Button>
      </div>
    </section>
  );
}

export const MS_PER_DAY = DAY;
export const MS_PER_HOUR = HOUR;
