export type EventStatus = "active" | "upcoming" | "ended" | "inactive";

const DAY = 86400000;
const WINDOW_DAYS = 7;

function parse(date: string): number | null {
  if (!date) return null;
  const t = Date.parse(`${date}T00:00:00Z`);
  return Number.isFinite(t) ? t : null;
}

export function getEventStatus(
  now: number,
  startDate: string,
  endDate: string,
): EventStatus {
  const start = parse(startDate);
  const end = parse(endDate) ?? start;
  if (start === null || end === null) return "inactive";
  if (now >= start && now <= end + DAY - 1) return "active";
  if (start > now && start - now <= WINDOW_DAYS * DAY) return "upcoming";
  if (now > end && now - end <= WINDOW_DAYS * DAY) return "ended";
  return "inactive";
}

export const STATUS_LABEL: Record<EventStatus, string> = {
  active: "Happening now",
  upcoming: "About to happen",
  ended: "Just ended",
  inactive: "Inactive",
};

export const STATUS_MARKER_COLOR: Record<EventStatus, string> = {
  active: "var(--destructive)",
  upcoming: "var(--chart-3, var(--primary))",
  ended: "var(--muted-foreground)",
  inactive: "var(--primary)",
};

export function toDateInput(ms: number) {
  return new Date(ms).toISOString().slice(0, 10);
}

export function toTimeInput(ms: number) {
  return new Date(ms).toISOString().slice(11, 16);
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(isoDate: string) {
  if (!isoDate) return "";
  const [year, month, day] = isoDate.split("-");
  if (!year || !month || !day) return isoDate;
  const monthIndex = Number(month) - 1;
  if (monthIndex < 0 || monthIndex > 11) return isoDate;
  return `${day} ${MONTHS[monthIndex]} ${year}`;
}
