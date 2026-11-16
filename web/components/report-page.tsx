"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCheck,
  FileText,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { api, intervalText, reportTitle, time } from "@/lib/client";
import type { Detail, Obs } from "@/lib/types";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useWorkspace } from "./workspace-provider";
import { useWalkthrough } from "./walkthrough";
function resultText(o: Obs) {
  if (o.result_interval)
    return `${intervalText(o.result_interval)} ${o.unit_canonical || ""}`;
  if (o.result_value !== null && o.unit_canonical !== null)
    return `${o.result_value} ${o.unit_canonical}`;
  return `${String(o.result_text ?? "—")}${
    o.unit_original &&
    !String(o.result_text ?? "")
      .toLowerCase()
      .includes(o.unit_original.toLowerCase())
      ? " " + o.unit_original
      : ""
  }`;
}
function referenceText(o: Obs) {
  return o.range_low !== null || o.range_high !== null
    ? intervalText({
        low: o.range_low,
        high: o.range_high,
        low_inclusive: o.range_low_inclusive ?? true,
        high_inclusive: o.range_high_inclusive ?? true,
      })
    : o.range_text || "Not available";
}
function resultStatus(o: Obs) {
  if (o.reference_policy === "adult_bp_upper_threshold") {
    if (o.analytics === "Within Range") return "Below upper threshold";
    if (o.analytics === "Above Range") return "At/above threshold";
  }
  if (o.analytics === "Invalid")
    return o.issues.includes("No applicable reference range; cannot classify")
      ? "Reference unavailable"
      : "Check data";
  return (
    (
      {
        "Within Range": "Within range",
        "Above Range": "High",
        "Below Range": "Low",
        Outlier: "Check value",
      } as Record<string, string>
    )[o.analytics] || o.analytics
  );
}
export function ReportPage({ id }: { id: string }) {
  const w = useWorkspace(),
    tour = useWalkthrough();
  const [detail, setDetail] = useState<Detail | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [masked, setMasked] = useState(false),
    [reload, setReload] = useState(0);
  const lastMask = useRef(false);
  const [view, setView] = useState("results"),
    [filter, setFilter] = useState("All results"),
    [technical, setTechnical] = useState(false);
  useEffect(() => {
    setMasked(false);
    setTechnical(false);
    setFilter("All results");
  }, [id]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setDetail(null);
    void api(
      "record?id=" + encodeURIComponent(id) + (masked ? "&mask=1" : ""),
      undefined,
      controller.signal,
    )
      .then((result) => {
        if (controller.signal.aborted) return;
        setDetail(result);
        if (lastMask.current !== masked) {
          lastMask.current = masked;
          tour.signal("mask-changed");
        }
        setView(result.output.observations.length ? "results" : "medicines");
        if (tour.active && tour.step.detailTab)
          setView(
            tour.step.detailTab === "Medications" ? "medicines" : "results",
          );
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [id, masked, reload]);
  useEffect(() => {
    if (!tour.active) return;
    if (tour.step.detailTab)
      setView(tour.step.detailTab === "Medications" ? "medicines" : "results");
    if (["raw", "mask", "versions"].includes(tour.step.id)) setTechnical(true);
    if (tour.step.id === "provenance") setFilter("All results");
  }, [tour.active, tour.step.id]);
  useEffect(() => {
    if (tour.fillRequest?.stepId === "observation-filter") {
      setFilter("Invalid");
      tour.signal("observations-filtered");
    }
  }, [tour.fillRequest]);
  const stored = w.data?.records.find((r) => r.id === id),
    reviewed = stored?.review_status === "Reviewed";
  const results =
    detail?.output.observations.filter(
      (o) =>
        filter === "All results" ||
        (filter === "Needs checking" && o.issues.length > 0) ||
        (filter === "Unresolved names" && !o.test_name_canonical) ||
        (filter === "Missing results" && o.value_status === "Missing") ||
        (filter === "Derived components" && o.derived_from) ||
        o.analytics === filter,
    ) || [];
  if (loading)
    return (
      <>
        <Link href="/reports" className="back-link">
          <ArrowLeft className="size-4" />
          Reports
        </Link>
        <div role="status" className="empty-state">
          <Loader2 className="mx-auto mb-4 size-5 animate-spin" />
          Loading report…
        </div>
      </>
    );
  if (error || !detail)
    return (
      <>
        <Link href="/reports" className="back-link">
          <ArrowLeft className="size-4" />
          Reports
        </Link>
        <div role="alert" className="empty-state">
          <h1>Unable to open report</h1>
          <p>{error || "Report unavailable"}</p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => setReload((n) => n + 1)}
          >
            Try again
          </Button>
        </div>
      </>
    );
  const patient = detail.output.patient;
  return (
    <>
      <Link href="/reports" className="back-link">
        <ArrowLeft className="size-4" />
        Reports
      </Link>
      <article className="medical-report">
        <header className="medical-report-header">
          <div className="report-type-label">
            <FileText className="size-4" />
            {reportTitle(detail.output.record_type)}
          </div>
          <div className="report-title-row">
            <div>
              <h1>{patient.name || "Patient name unavailable"}</h1>
              <p className="patient-meta">
                {[
                  patient.age_structured
                    ? `${patient.age_structured.years} years`
                    : null,
                  patient.gender,
                  patient.report_date,
                ]
                  .filter(Boolean)
                  .join(" · ") || "Patient details not supplied"}
              </p>
            </div>
            <Badge
              className={
                reviewed
                  ? "status-reviewed"
                  : stored?.flagged
                    ? "status-review"
                    : ""
              }
            >
              {reviewed
                ? "Reviewed"
                : stored?.flagged
                  ? "Needs review"
                  : "No flags"}
            </Badge>
          </div>
          <div className="report-source-row">
            <span>{detail.output.clinic}</span>
            <span className="font-mono text-xs break-all">
              {detail.output.document_id}
            </span>
          </div>
        </header>
        {!!detail.output.issues.length && (
          <details className="report-data-notice">
            <summary>{detail.output.issues.length} report-level checks</summary>
            <ul>
              {detail.output.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          </details>
        )}
        <div className="results-toolbar">
          <div className="local-tabs" aria-label="Report content">
            {(detail.output.observations.length > 0 || tour.active) && (
              <button
                data-tour="detail-Observations"
                className={view === "results" ? "selected" : ""}
                onClick={() => {
                  setView("results");
                  tour.signal("detail:Observations");
                }}
              >
                Test results <span>{detail.output.observations.length}</span>
              </button>
            )}
            {detail.output.medications.length > 0 && (
              <button
                data-tour="detail-Medications"
                className={view === "medicines" ? "selected" : ""}
                onClick={() => {
                  setView("medicines");
                  tour.signal("detail:Medications");
                }}
              >
                Medicines <span>{detail.output.medications.length}</span>
              </button>
            )}
          </div>
          {view === "results" && (
            <select
              aria-label="Filter test results"
              data-tour="observation-filter"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                tour.signal("observations-filtered");
              }}
            >
              {[
                "All results",
                "Needs checking",
                "Within Range",
                "Above Range",
                "Below Range",
                "Invalid",
                "Outlier",
                "Unresolved names",
                "Missing results",
                "Derived components",
              ].map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          )}
        </div>
        {view === "results" ? (
          <div data-tour="observations">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Your result</th>
                  <th>Reference</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((o, i) => (
                  <tr key={i}>
                    <td data-label="Test">
                      <strong>
                        {o.test_name_canonical ||
                          o.test_name_original ||
                          "Unnamed test"}
                      </strong>
                      <details className="test-evidence">
                        <summary>
                          {o.issues.length
                            ? `${o.issues.length} ${o.issues.length === 1 ? "check" : "checks"} to review`
                            : "Source details"}
                        </summary>
                        {!!o.issues.length && (
                          <ul>
                            {o.issues.map((issue, j) => (
                              <li key={j}>{issue}</li>
                            ))}
                          </ul>
                        )}
                        <dl>
                          <dt>Original name</dt>
                          <dd>{o.test_name_original}</dd>
                          <dt>Original result</dt>
                          <dd>{String(o.result_text ?? "Not supplied")}</dd>
                          <dt>Original unit</dt>
                          <dd>{o.unit_original || "Not supplied"}</dd>
                          <dt>Matching</dt>
                          <dd>
                            {o.normalization_method} · similarity{" "}
                            {Math.round(o.normalization_confidence * 100)}%
                          </dd>
                          <dt>Page</dt>
                          <dd>{o.page ?? "Not supplied"}</dd>
                          {o.derived_from && (
                            <>
                              <dt>Split from</dt>
                              <dd>
                                {o.derived_from.test_name}:{" "}
                                {o.derived_from.result_text}
                              </dd>
                            </>
                          )}
                          {o.unit_provenance && (
                            <>
                              <dt>Unit source</dt>
                              <dd>{o.unit_provenance}</dd>
                            </>
                          )}
                        </dl>
                      </details>
                    </td>
                    <td data-label="Your result" className="result-value">
                      {resultText(o)}
                    </td>
                    <td data-label="Reference">
                      {referenceText(o)}
                      {o.range_source && (
                        <details className="test-evidence">
                          <summary>Reference source</summary>
                          {/^https:\/\//.test(o.range_source) ? (
                            <a
                              className="text-link"
                              href={o.range_source}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {o.reference_policy === "adult_bp_upper_threshold"
                                ? "AHA · configured adult BP threshold"
                                : o.range_source}
                            </a>
                          ) : (
                            <p>{o.range_source}</p>
                          )}
                          {o.reference_note && (
                            <p className="mt-2">{o.reference_note}</p>
                          )}
                        </details>
                      )}
                    </td>
                    <td data-label="Status">
                      <Badge
                        className={
                          o.analytics === "Within Range"
                            ? "status-neutral"
                            : o.analytics === "Invalid" ||
                                o.analytics === "Outlier"
                              ? "status-review"
                              : "status-outside"
                        }
                      >
                        {resultStatus(o)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!results.length && (
              <p className="empty-state">No results match this view.</p>
            )}
          </div>
        ) : (
          <div data-tour="medications">
            <table className="results-table medicines-table">
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Generic name</th>
                  <th>Dose / frequency</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {detail.output.medications.map((m, i) => (
                  <tr key={i}>
                    <td data-label="Medicine">
                      <strong>{m.original}</strong>
                      {m.mapping_source && (
                        <details className="test-evidence">
                          <summary>Mapping source</summary>
                          <a
                            className="text-link"
                            href={m.mapping_source}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Reference
                          </a>
                          {!!m.ingredients?.length && (
                            <p className="mt-2">{m.ingredients.join(", ")}</p>
                          )}
                        </details>
                      )}
                    </td>
                    <td data-label="Generic name">
                      {m.generic || "Not mapped"}
                    </td>
                    <td data-label="Dose / frequency">
                      {m.dose || "Dose not supplied"}
                      <p className="mt-1 text-xs text-neutral-500">
                        {m.frequency || "Frequency not supplied"}
                      </p>
                    </td>
                    <td data-label="Status">
                      <Badge
                        className={
                          m.status === "Unresolved"
                            ? "status-review"
                            : "status-neutral"
                        }
                      >
                        {m.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!detail.output.medications.length && (
              <p className="empty-state">No medicines in this report.</p>
            )}
          </div>
        )}
        <div className="report-review-bar">
          <p>
            {reviewed
              ? "This report has been reviewed."
              : "Checked the results and any data issues?"}
          </p>
          <Button
            data-tour="mark-reviewed"
            disabled={reviewed || w.busy}
            onClick={() => w.review(id)}
          >
            <CheckCheck />
            {reviewed ? "Reviewed" : "Mark reviewed"}
          </Button>
        </div>
      </article>
      <p className="list-footnote">
        Review status records a data check. Original results and flags are
        retained.
      </p>
      <details
        className="technical-details"
        open={technical}
        onToggle={(e) => setTechnical(e.currentTarget.open)}
      >
        <summary>Technical details</summary>
        <div className="technical-body">
          <div className="technical-toolbar">
            <label data-tour="mask">
              <input
                type="checkbox"
                checked={masked}
                onChange={(e) => {
                  setMasked(e.target.checked);
                }}
              />{" "}
              Mask identifiers and source data
            </label>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setReload((n) => n + 1)}
            >
              <RotateCcw />
              Reload
            </Button>
          </div>
          <dl className="source-metadata">
            <dt>Source file</dt>
            <dd className="break-all">{detail.source}</dd>
            <dt>First processed</dt>
            <dd>{time(detail.ingested_at)}</dd>
            <dt>Configuration</dt>
            <dd>{detail.output.config_version}</dd>
          </dl>
          <details
            className="json-comparison"
            onToggle={(e) => {
              if (e.currentTarget.open)
                tour.signal("detail:Raw & standardised");
            }}
          >
            <summary data-tour="detail-Raw & standardised">
              Original & transformed data
            </summary>
            <div className="json-columns">
              {[
                ["Original JSON", detail.raw],
                ["Transformed output", detail.output],
              ].map(([title, value]) => (
                <section key={String(title)}>
                  <h3>{String(title)}</h3>
                  <pre>{JSON.stringify(value, null, 2)}</pre>
                </section>
              ))}
            </div>
          </details>
          <details
            data-tour="versions"
            onToggle={(e) => {
              if (e.currentTarget.open) tour.signal("versions-opened");
            }}
            className="version-history"
          >
            <summary>
              Previous output versions ({detail.versions.length})
            </summary>
            {detail.versions.length ? (
              <>
                <p className="supporting my-3">
                  Saved before reprocessing. These are processing versions, not
                  separate medical tests.
                </p>
                {detail.versions.map((version, i) => (
                  <details key={i}>
                    <summary>
                      {time(version.archived_at)} · {version.config_version}
                    </summary>
                    <pre>
                      {JSON.stringify(
                        { output: version.output, review: version.review },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                ))}
              </>
            ) : (
              <p className="supporting mt-3">
                No previous versions. The report has not been reprocessed with
                changed rules.
              </p>
            )}
          </details>
        </div>
      </details>
    </>
  );
}
