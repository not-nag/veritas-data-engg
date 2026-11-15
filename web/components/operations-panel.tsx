"use client";
import { useCallback, useEffect, useState } from "react";
import { Activity, Check, Loader2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useWalkthrough } from "@/components/walkthrough";
import example from "@/public/walkthrough-example.json";
type Failure = {
  id: string;
  source: string;
  reason: string;
  status: string;
  retry_count: number;
  updated_at: string;
};
type State = {
  watcher: {
    enabled: boolean;
    folder: string;
    poll_seconds: number;
    last_scan: string | null;
    last_error: string | null;
  };
  health: {
    file_attempts: number;
    error_rate: number;
    throughput_files_per_second: number;
    p95_file_latency_seconds: number | null;
    oldest_pending_seconds: number;
    pending_files: number;
    window_seconds: number;
  };
  alerts: {
    code: string;
    status: string;
    message: string;
    acknowledged_at: string | null;
  }[];
  dead_letters: Failure[];
  intake: {
    id: string;
    source: string;
    status: string;
    reason: string | null;
    seen_at: string;
  }[];
  alert_events: {
    code: string;
    status: string;
    message: string;
    created_at: string;
  }[];
};
async function request(path: string, body?: unknown) {
  const response = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : { cache: "no-store" },
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}
function stamp(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Not yet scanned";
}
export function OperationsPanel({ refreshKey }: { refreshKey?: string }) {
  const tour = useWalkthrough();
  const { reportWatcher } = tour;
  const [data, setData] = useState<State | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<Failure | null>(null),
    [content, setContent] = useState("");
  const refresh = useCallback(async () => {
    try {
      const value = await request("operations");
      setData(value);
      reportWatcher(value.watcher.enabled);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [reportWatcher]);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => clearInterval(timer);
  }, [refresh, refreshKey]);
  useEffect(() => {
    if (tour.fillRequest?.stepId === "repair" && selected)
      setContent(JSON.stringify(example, null, 2));
  }, [tour.fillRequest]);
  async function action(body: {
    action: string;
    enabled?: boolean;
    code?: string;
  }) {
    setBusy(true);
    setError("");
    try {
      await request("operations", body);
      if (body.action === "watcher")
        tour.signal(body.enabled ? "watcher-running" : "watcher-paused");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function inspect(item: Failure) {
    setError("");
    try {
      const value = await request(
        "dead-letter?id=" + encodeURIComponent(item.id),
      );
      setSelected(item);
      setContent(value.content);
      setNotice("");
      tour.signal("failure-inspected");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function retry(corrected: boolean) {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const result = await request("process", {
        mode: "retry",
        id: selected.id,
        ...(corrected ? { content } : {}),
      });
      setNotice(
        result.failed
          ? "Retry failed. The original entry and attempt history were retained."
          : `Retry completed: ${result.records} new, ${result.updated_records} refreshed, ${result.duplicates} duplicates.`,
      );
      await refresh();
      if (!result.failed) {
        setSelected(null);
        tour.signal("retry-succeeded");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return (
      <p role="status" className="py-12 text-center text-xs text-neutral-500">
        {error || "Loading operations…"}
      </p>
    );
  return (
    <div className="space-y-6">
      {error && (
        <p
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800"
        >
          {error}
        </p>
      )}
      {notice && (
        <p
          role="status"
          className="rounded-md border border-neutral-200 bg-neutral-50 p-3 text-xs"
        >
          {notice}
        </p>
      )}
      <section
        data-tour="watcher"
        className="rounded-lg border border-neutral-200 p-5"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-medium">
              <Activity className="size-4" />
              Folder ingestion
              <Badge>{data.watcher.enabled ? "Running" : "Paused"}</Badge>
            </h2>
            <p className="mt-3 break-all font-mono text-[11px] text-neutral-500">
              {data.watcher.folder}
            </p>
            <p className="mt-2 text-[11px] text-neutral-400">
              Checks every {data.watcher.poll_seconds ?? "—"}s ·{" "}
              {data.health.pending_files} pending · Last scan{" "}
              {stamp(data.watcher.last_scan)}
            </p>
            <p className="mt-2 text-[11px] text-neutral-500">
              Drop a JSON file here. Stable files are retained and processed
              automatically.
            </p>
            {data.watcher.last_error && (
              <p className="mt-2 text-xs text-red-700">
                {data.watcher.last_error}
              </p>
            )}
          </div>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() =>
              action({ action: "watcher", enabled: !data.watcher.enabled })
            }
          >
            {data.watcher.enabled ? "Pause ingestion" : "Resume ingestion"}
          </Button>
        </div>
      </section>
      <div data-tour="health" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          [
            "Error rate",
            `${(data.health.error_rate * 100).toFixed(1)}%`,
            `${data.health.file_attempts} attempts in monitoring window`,
          ],
          [
            "Throughput",
            `${(data.health.throughput_files_per_second * 3600).toFixed(1)}/h`,
            "Completed files, window average",
          ],
          [
            "Observed p95",
            data.health.p95_file_latency_seconds === null
              ? "—"
              : `${data.health.p95_file_latency_seconds.toFixed(2)}s`,
            "Local discovery to DB completion",
          ],
          [
            "Oldest pending",
            `${data.health.oldest_pending_seconds.toFixed(1)}s`,
            "Settling, queued, or processing",
          ],
        ].map(([label, value, description]) => (
          <div key={label} className="rounded-lg border border-neutral-200 p-5">
            <p className="text-xs text-neutral-500">{label}</p>
            <p className="mt-3 text-2xl font-semibold tracking-tight">
              {value}
            </p>
            <p className="mt-2 text-[10px] text-neutral-400">{description}</p>
          </div>
        ))}
      </div>
      <section
        data-tour="alerts"
        className="overflow-hidden rounded-lg border border-neutral-200"
      >
        <h2 className="border-b border-neutral-100 px-5 py-4 text-sm font-medium">
          Monitoring alerts
        </h2>
        {data.alerts.length ? (
          <div className="divide-y divide-neutral-100">
            {data.alerts.map((alert) => (
              <div
                key={alert.code}
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Badge
                      className={
                        alert.status === "Active"
                          ? "border-amber-200 bg-amber-50 text-amber-800"
                          : ""
                      }
                    >
                      {alert.status}
                    </Badge>
                    <span className="text-xs">
                      {alert.code.replaceAll("_", " ")}
                    </span>
                  </div>
                  <p className="mt-2 text-[11px] text-neutral-500">
                    {alert.message}
                  </p>
                </div>
                {alert.status === "Active" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy || !!alert.acknowledged_at}
                    onClick={() =>
                      action({ action: "acknowledge", code: alert.code })
                    }
                  >
                    <Check />
                    {alert.acknowledged_at ? "Acknowledged" : "Acknowledge"}
                  </Button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="p-5 text-xs text-neutral-500">
            No threshold breaches. Alerts are retained here and in the local
            alert log.
          </p>
        )}
        <p className="border-t border-neutral-100 px-5 py-3 text-[10px] text-neutral-400">
          Acknowledgement records review; it does not clear an active condition.
          Unchanged conditions do not create repeated alerts.
        </p>
      </section>
      <section className="overflow-x-auto rounded-lg border border-neutral-200">
        <h2 className="border-b border-neutral-100 px-5 py-4 text-sm font-medium">
          Failed-file review
        </h2>
        {data.dead_letters.length ? (
          <table className="w-full">
            <thead className="bg-neutral-50">
              <tr>
                {["Source", "Failure reason", "Status", "Retries", ""].map(
                  (h, i) => (
                    <th key={i}>{h}</th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {data.dead_letters.map((item) => (
                <tr key={item.id}>
                  <td className="max-w-52 break-all">
                    {item.source.split("/").pop()}
                  </td>
                  <td className="max-w-96 text-neutral-500">{item.reason}</td>
                  <td>
                    <Badge>{item.status}</Badge>
                  </td>
                  <td>{item.retry_count}</td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      data-tour="failure-inspect"
                      onClick={() => inspect(item)}
                    >
                      Inspect / retry
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="p-5 text-xs text-neutral-500">
            No failed files. Malformed and unsupported inputs will appear here.
          </p>
        )}
      </section>
      {selected && (
        <section
          data-tour="repair"
          className="rounded-lg border border-neutral-200 p-5"
        >
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-sm font-medium">Repair failed input</h2>
            <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
              Close
            </Button>
          </div>
          <p className="mb-3 text-xs text-neutral-500">
            The original payload is retained. Each retry stores its submitted
            content and outcome.
          </p>
          <label
            htmlFor="corrected-json"
            className="mb-2 block text-xs font-medium"
          >
            JSON content
          </label>
          <textarea
            id="corrected-json"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            spellCheck={false}
            className="h-72 w-full rounded-md border border-neutral-200 p-3 font-mono text-xs outline-none focus:ring-2 focus:ring-neutral-300"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button disabled={busy} onClick={() => retry(true)}>
              {busy ? <Loader2 className="animate-spin" /> : <RotateCcw />}Retry
              edited JSON
            </Button>
            <Button
              disabled={busy}
              variant="outline"
              onClick={() => retry(false)}
            >
              Retry original
            </Button>
          </div>
        </section>
      )}
      <section className="overflow-x-auto rounded-lg border border-neutral-200">
        <h2 className="border-b border-neutral-100 px-5 py-4 text-sm font-medium">
          Folder queue
        </h2>
        {data.intake.length ? (
          <table className="w-full">
            <thead className="bg-neutral-50">
              <tr>
                {["File", "Status", "First observed", "Details"].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.intake.map((item) => (
                <tr key={item.id}>
                  <td>{item.source.split("/").pop()}</td>
                  <td>
                    <Badge>{item.status}</Badge>
                  </td>
                  <td>{stamp(item.seen_at)}</td>
                  <td className="text-neutral-500">{item.reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="p-5 text-xs text-neutral-500">The inbox is empty.</p>
        )}
      </section>
    </div>
  );
}
