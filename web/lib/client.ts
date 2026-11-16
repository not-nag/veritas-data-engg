import { writeHeaders } from "./auth-client";
import type { Interval } from "./types";
export async function api(path: string, body?: unknown, signal?: AbortSignal) {
  const response = await fetch("/api/" + path, {
    signal,
    cache: "no-store",
    ...(body === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(await writeHeaders()),
          },
          body: JSON.stringify(body),
        }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}
export function intervalText(i: Interval) {
  if (i.low === null) return `${i.high_inclusive ? "≤" : "<"} ${i.high}`;
  if (i.high === null) return `${i.low_inclusive ? "≥" : ">"} ${i.low}`;
  return `${i.low_inclusive ? "" : ">"}${i.low}–${i.high_inclusive ? "" : "<"}${i.high}`;
}
export function time(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
export function reportTitle(type: string) {
  return type === "lab_report"
    ? "Laboratory report"
    : type === "discharge_summary"
      ? "Discharge summary"
      : "Medical report";
}
export function percent(value: number | null) {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}
