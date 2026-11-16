"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useWorkspace } from "./workspace-provider";
import { useWalkthrough } from "./walkthrough";
import { time } from "@/lib/client";
export function ActivityPage() {
  const w = useWorkspace(),
    tour = useWalkthrough(),
    [view, setView] = useState("runs"),
    [draft, setDraft] = useState(""),
    [applying, setApplying] = useState(false),
    [qualityOpen, setQualityOpen] = useState(false),
    [failedOnly, setFailedOnly] = useState(false);
  useEffect(() => {
    if (w.data?.daily.date && !draft) setDraft(w.data.daily.date);
  }, [w.data?.daily.date]);
  useEffect(() => {
    if (
      tour.active &&
      ["coverage", "exclusions", "refresh"].includes(tour.step.id)
    )
      setQualityOpen(true);
  }, [tour.active, tour.step.id]);
  useEffect(() => {
    if (tour.fillRequest?.stepId === "daily") {
      const latest = w.data?.runs[0];
      setDraft(
        latest
          ? new Date(latest.started_at).toLocaleDateString("en-CA", {
              timeZone: w.data?.daily.timezone || "Asia/Kolkata",
            })
          : w.data?.daily.date || "",
      );
    }
  }, [tour.fillRequest]);
  const d = w.data,
    raw = d?.total_tests ? (100 * d.resolved_tests) / d.total_tests : 0,
    eligible = d?.eligible_test_entries
      ? (100 * d.resolved_tests) / d.eligible_test_entries
      : 0;
  const files =
    d?.files.filter((f) => !failedOnly || f.status === "Failed") || [];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Activity</h1>
          <p>What was received, processed, or needs another look.</p>
        </div>
        <form
          data-tour="daily-filter"
          aria-label="Daily statistics filter"
          className="date-filter"
          onSubmit={async (e) => {
            e.preventDefault();
            setApplying(true);
            try {
              if (!(await w.refresh(draft))) return;
              w.setDay(draft);
              tour.signal("date-applied");
            } catch (error) {
              w.setError((error as Error).message);
            } finally {
              setApplying(false);
            }
          }}
        >
          <label className="sr-only" htmlFor="activity-date">
            Activity date
          </label>
          <input
            id="activity-date"
            type="date"
            required
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <Button variant="outline" size="sm" disabled={applying} type="submit">
            Apply
          </Button>
        </form>
      </div>
      <p className="supporting mb-3">
        Daily file attempts · {d?.daily.timezone || "Asia/Kolkata"} ·{" "}
        {d?.daily.date || "Loading…"}
      </p>
      <div className="activity-metrics">
        {[
          ["Received", d?.daily.received],
          ["Processed", d?.daily.processed],
          ["Failed", d?.daily.failed],
          ["Flagged", d?.daily.flagged_files],
        ].map(([label, count]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{count ?? "—"}</strong>
          </div>
        ))}
      </div>
      <details
        className="quality-details"
        open={qualityOpen}
        onToggle={(e) => setQualityOpen(e.currentTarget.open)}
      >
        <summary>Data quality & mapping coverage</summary>
        <section data-tour="coverage" className="quality-body">
          <div className="coverage-heading">
            <div>
              <h2>
                {raw.toFixed(1)}% <span>source names recognised</span>
              </h2>
              <p>
                {d?.resolved_tests || 0} of {d?.total_tests || 0} original
                source entries, before panel expansion.
              </p>
            </div>
            <div className="coverage-track">
              <span style={{ width: raw + "%" }} />
            </div>
          </div>
          <p className="supporting">
            Name matching and result validity are measured separately. A
            recognised name can still have missing or incompatible data.
          </p>
          {!!d?.non_test_entries && (
            <div className="mt-4">
              <p className="text-sm">
                {eligible.toFixed(1)}% excluding identified non-test rows (
                {d.resolved_tests}/{d.eligible_test_entries}).
              </p>
              <details
                data-tour="exclusions"
                className="mt-3 text-sm"
                onToggle={(e) => {
                  if (e.currentTarget.open) tour.signal("exclusions-opened");
                }}
              >
                <summary>View non-test rows ({d.non_test_entries})</summary>
                <p className="supporting mt-2">
                  These rows remain in raw coverage and source evidence.
                </p>
                {Object.entries(d.non_test_names).map(([name, count]) => (
                  <p key={name} className="mt-2 text-xs">
                    {name} ×{count}
                  </p>
                ))}
              </details>
            </div>
          )}
          <p className="supporting mt-4">
            {(d?.observation_count || 0) - (d?.analytics.Invalid || 0)} of{" "}
            {d?.observation_count || 0} output observations have a result
            classification.
          </p>
          {!!Object.keys(d?.unresolved_names || {}).length && (
            <details className="mt-4 text-sm">
              <summary>Unresolved source names</summary>
              <div className="max-h-60 overflow-auto">
                {Object.entries(d?.unresolved_names || {}).map(
                  ([name, count]) => (
                    <p key={name} className="mt-2 text-xs">
                      {name} ×{count}
                    </p>
                  ),
                )}
              </div>
            </details>
          )}
          {!!d?.outdated_records && (
            <>
              <p className="supporting mt-4">
                {d.outdated_records} reports use older processing rules.
                Refreshing archives the previous output and resets review.
              </p>
              <Button
                className="mt-3"
                variant="outline"
                size="sm"
                disabled={w.busy}
                onClick={() => w.process(undefined, true)}
              >
                Refresh {d.outdated_records} reports
              </Button>
            </>
          )}
        </section>
      </details>
      <div className="activity-section-heading">
        <div className="local-tabs" aria-label="Activity views">
          <button
            className={view === "runs" ? "selected" : ""}
            onClick={() => setView("runs")}
          >
            Processing runs
          </button>
          <button
            className={view === "files" ? "selected" : ""}
            onClick={() => setView("files")}
          >
            File outcomes
          </button>
        </div>
        {view === "files" && (
          <label className="text-xs text-neutral-500 flex items-center gap-2">
            <input
              type="checkbox"
              checked={failedOnly}
              onChange={(e) => setFailedOnly(e.target.checked)}
            />
            Failed only
          </label>
        )}
      </div>
      <p className="supporting mb-4">
        {view === "runs"
          ? "One row per batch. A batch may contain several files."
          : "One row per file attempt. A file may contain several reports."}
      </p>
      <div className="data-table-wrap">
        {view === "runs" ? (
          <table className="w-full">
            <thead>
              <tr>
                {[
                  "Started",
                  "Received",
                  "Processed",
                  "Failed",
                  "Duplicates",
                  "Duration",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {d?.runs.map((run) => (
                <tr key={run.id}>
                  <td>{time(run.started_at)}</td>
                  <td>{run.summary.received}</td>
                  <td>{run.summary.processed}</td>
                  <td>{run.summary.failed}</td>
                  <td>{run.summary.duplicates}</td>
                  <td>{run.summary.duration_seconds}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full">
            <thead>
              <tr>
                {[
                  "File",
                  "Source",
                  "Outcome",
                  "New reports",
                  "Duplicates",
                  "Reason",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.id}>
                  <td className="max-w-52 break-words">
                    {f.name.split("/").pop()}
                  </td>
                  <td>{f.clinic}</td>
                  <td>
                    <Badge
                      className={f.status === "Failed" ? "status-review" : ""}
                    >
                      {f.status}
                    </Badge>
                  </td>
                  <td>{f.records}</td>
                  <td>{f.duplicates}</td>
                  <td className="max-w-72">
                    {f.reason || "—"}
                    {f.status === "Failed" && (
                      <Link href="/system" className="text-link block mt-2">
                        Inspect in System tools
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!d ? (
          <p className="empty-state" role="status">
            Loading activity…
          </p>
        ) : (
          !(view === "runs" ? d.runs.length : files.length) && (
            <p className="empty-state">No activity to show.</p>
          )
        )}
      </div>
    </>
  );
}
