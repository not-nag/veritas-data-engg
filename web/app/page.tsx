"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronRight,
  Files,
  Loader2,
  Search,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { OperationsPanel } from "@/components/operations-panel";
type Patient = {
  name?: string;
  gender?: string;
  age_structured?: { years: number };
  report_date?: string;
};
type Rec = {
  id: string;
  document_id: string;
  record_type: string;
  clinic: string;
  patient: Patient;
  tests: number;
  issues: number;
  flagged: number;
  review_status: string;
  source_file: string;
};
type Interval = {
  low: number | null;
  high: number | null;
  low_inclusive: boolean;
  high_inclusive: boolean;
};
type Obs = {
  result_interval?: Interval | null;
  range_low_inclusive?: boolean;
  range_high_inclusive?: boolean;
  value_status?: string;
  derived_from?: { test_name: string; result_text: string; rule: string };
  unit_provenance?: string;
  test_name_original: string;
  test_name_canonical: string | null;
  result_text: unknown;
  result_value: number | null;
  unit_original: string;
  unit_canonical: string | null;
  range_text: string;
  range_low: number | null;
  range_high: number | null;
  range_source: string;
  analytics: string;
  issues: string[];
  normalization_method: string;
  normalization_confidence: number;
  page: number;
};
type Run = {
  id: string;
  started_at: string;
  summary: {
    received: number;
    processed: number;
    failed: number;
    duplicates: number;
    records: number;
    flagged: number;
    updated_records?: number;
    duration_seconds: number;
  };
};
type Data = {
  records: Rec[];
  runs: Run[];
  files: {
    id: number;
    name: string;
    status: string;
    reason: string;
    records: number;
    duplicates: number;
    clinic: string;
  }[];
  clinics: {
    clinic: string;
    files: number;
    records: number;
    duplicates: number;
    flagged: number;
    failed: number;
    record_occurrences: number;
    duplicate_rate: number | null;
    error_rate: number | null;
    missing_field_rate: number | null;
    missing_fields: number | null;
    expected_fields: number | null;
  }[];
  analytics: Record<string, number>;
  daily: {
    date: string;
    timezone: string;
    received: number;
    processed: number;
    failed: number;
    flagged_files: number;
  };
  outdated_records: number;
  observation_count: number;
  coverage_kinds: Record<string, number>;
  eligible_test_entries: number;
  non_test_entries: number;
  non_test_names: Record<string, number>;
  unresolved_names: Record<string, number>;
  total_tests: number;
  resolved_tests: number;
  config: { tests: number; profiles: number };
};
type Detail = {
  versions: {
    config_version: string;
    archived_at: string;
    output: unknown;
    review: unknown;
  }[];
  raw: unknown;
  output: {
    id: string;
    clinic: string;
    document_id: string;
    record_type: string;
    patient: Patient;
    observations: Obs[];
    medications: {
      original: string;
      generic: string;
      dose: string;
      frequency: string;
      status: string;
      mapping_source?: string;
      ingredients?: string[];
    }[];
    issues: string[];
    config_version: string;
  };
  source: string;
  ingested_at: string;
};
function intervalText(i: Interval): string {
  if (i.low === null) return `${i.high_inclusive ? "≤" : "<"} ${i.high}`;
  if (i.high === null) return `${i.low_inclusive ? "≥" : ">"} ${i.low}`;
  return `${i.low_inclusive ? "[" : "("}${i.low} – ${i.high}${i.high_inclusive ? "]" : ")"}`;
}
function percent(value: number | null) {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}
const tabs = [
  "Overview",
  "Records",
  "Review queue",
  "Clinics",
  "Activity",
  "Operations",
];
function Status({ value }: { value: string }) {
  return (
    <Badge
      className={
        value === "Within Range" ||
        value === "Processed" ||
        value === "Reviewed"
          ? "bg-neutral-50 text-neutral-600"
          : value === "Outlier" || value === "Failed"
            ? "border-red-200 bg-red-50 text-red-700"
            : value === "Invalid"
              ? "border-amber-200 bg-amber-50 text-amber-800"
              : ""
      }
    >
      {value}
    </Badge>
  );
}
function Empty({ title, description }: { title: string; description: string }) {
  return (
    <div className="py-20 text-center">
      <Files className="mx-auto mb-4 size-7 text-neutral-300" />
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-xs text-neutral-500">{description}</p>
    </div>
  );
}
function time(s: string) {
  return new Date(s).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
async function api(path: string, body?: unknown) {
  const r = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}
export default function Home() {
  const [data, setData] = useState<Data | null>(null),
    [tab, setTab] = useState("Overview"),
    [query, setQuery] = useState(""),
    [clinic, setClinic] = useState("All clinics"),
    [classification, setClassification] = useState("All records"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [detail, setDetail] = useState<Detail | null>(null),
    [loadingDetail, setLoadingDetail] = useState(false),
    [detailTab, setDetailTab] = useState("Observations"),
    [selectedDay, setSelectedDay] = useState(""),
    [observationFilter, setObservationFilter] = useState("All observations"),
    [masked, setMasked] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const refresh = useCallback(async () => {
    try {
      setData(
        await api("dashboard" + (selectedDay ? "?day=" + selectedDay : "")),
      );
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [selectedDay]);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => clearInterval(timer);
  }, [refresh]);
  async function process(files?: FileList, reprocess = false) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      let payload: unknown = reprocess
        ? { mode: "stored", reprocess: true }
        : { mode: "samples" };
      if (files) {
        if (
          Array.from(files).some((f) => !f.name.toLowerCase().endsWith(".json"))
        )
          throw new Error("Please select JSON files only.");
        if (Array.from(files).reduce((n, f) => n + f.size, 0) > 9_500_000)
          throw new Error("Please keep uploads below 9.5 MB.");
        payload = {
          files: await Promise.all(
            Array.from(files).map(async (f) => ({
              name: f.name,
              content: await f.text(),
            })),
          ),
        };
      }
      const r = await api("process", payload);
      await refresh();
      setNotice(
        `${r.processed} files processed · ${r.records} new records${r.updated_records ? ` · ${r.updated_records} refreshed` : ""} · ${r.duplicates} duplicates suppressed${r.failed ? ` · ${r.failed} failed` : ""}`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  async function inspect(id: string) {
    setLoadingDetail(true);
    setError("");
    try {
      setDetail(
        await api(
          "record?id=" + encodeURIComponent(id) + (masked ? "&mask=1" : ""),
        ),
      );
      setDetailTab("Observations");
      setObservationFilter("All observations");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  }
  async function review(id: string) {
    try {
      await api("review", { id, status: "Reviewed" });
      await refresh();
      setNotice("Record marked as reviewed. Source flags are retained.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const filteredObservations = (detail?.output.observations || []).filter(
    (o) =>
      observationFilter === "All observations" ||
      (observationFilter === "Unresolved names"
        ? !o.test_name_canonical
        : observationFilter === "Missing results"
          ? o.value_status === "Missing"
          : observationFilter === "Derived components"
            ? !!o.derived_from
            : o.analytics === observationFilter),
  );
  const latest = data?.runs[0];
  const records = (data?.records || []).filter(
    (r) =>
      (tab !== "Review queue" ||
        (r.flagged && r.review_status !== "Reviewed")) &&
      (clinic === "All clinics" || r.clinic === clinic) &&
      (classification === "All records" ||
        (classification === "Flagged" ? r.flagged : !r.flagged)) &&
      `${r.document_id} ${r.clinic} ${r.patient.name} ${r.record_type}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const pending =
    data?.records.filter((r) => r.flagged && r.review_status !== "Reviewed")
      .length || 0;
  return (
    <div className="min-h-screen">
      <header className="border-b border-neutral-200">
        <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-5 md:px-10">
          <a
            href="/"
            className="flex items-center gap-2.5 font-semibold tracking-tight"
          >
            <span className="flex size-7 items-center justify-center rounded-md bg-neutral-900 text-white">
              <ShieldCheck className="size-4" />
            </span>
            veritas
            <span className="mx-3 h-5 border-l border-neutral-200" />
            <span className="text-xs font-normal text-neutral-500">
              Claims operations
            </span>
          </a>
          <span className="flex items-center gap-2 text-[11px] text-neutral-500">
            <span
              className={`size-1.5 rounded-full ${data ? "bg-emerald-500" : "bg-neutral-300"}`}
            />
            {data ? "Local workspace" : "Connecting"}
          </span>
        </div>
      </header>
      <div className="mx-auto max-w-[1400px] px-5 md:px-10">
        <nav
          aria-label="Main navigation"
          className="veritas-nav flex gap-1 overflow-x-auto"
        >
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => {
                setTab(t);
                setDetail(null);
                setQuery("");
              }}
              aria-current={tab === t ? "page" : undefined}
              className={`flex h-9 items-center gap-2 whitespace-nowrap rounded-md px-3 text-xs ${tab === t ? "bg-[#512439] font-medium text-white" : "text-[#f2dce5] hover:bg-[#401b2d] hover:text-white"}`}
            >
              {t}
              {t === "Review queue" && pending > 0 && (
                <span className="rounded bg-white/15 px-1.5 py-0.5 text-[10px]">
                  {pending}
                </span>
              )}
            </button>
          ))}
        </nav>
        <main className="pb-12 pt-9">
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-2 text-[10px] font-medium uppercase tracking-[.15em] text-neutral-400">
                Data standardisation
              </div>
              <h1 className="text-2xl font-semibold tracking-tight">
                {detail
                  ? "Record inspector"
                  : tab === "Overview"
                    ? "Pipeline overview"
                    : tab}
              </h1>
              <p className="mt-2 text-xs text-neutral-500">
                {detail
                  ? "Trace each transformation back to its source."
                  : tab === "Overview"
                    ? "A clear view of incoming reports and the quality of your data."
                    : tab === "Review queue"
                      ? "Review unresolved mappings, unusual results, and source inconsistencies."
                      : tab === "Clinics"
                        ? "Monitor data quality across your source systems."
                        : tab === "Activity"
                          ? "File outcomes and processing history."
                          : tab === "Operations"
                            ? "Monitor intake, recover failed files, and review pipeline alerts."
                            : "Search reports and inspect standardised results."}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => input.current?.click()}
                disabled={busy}
              >
                <Upload />
                Upload JSON
              </Button>
              <Button onClick={() => process()} disabled={busy}>
                {busy ? <Loader2 className="animate-spin" /> : <Activity />}
                {busy ? "Processing…" : "Run sample data"}
              </Button>
              <input
                ref={input}
                type="file"
                accept=".json,application/json"
                multiple
                className="hidden"
                aria-label="Upload JSON reports"
                onChange={(e) => {
                  if (e.target.files?.length) void process(e.target.files);
                }}
              />
            </div>
          </div>
          {error && (
            <div
              role="alert"
              className="mb-5 flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800"
            >
              {error}
              <Button variant="ghost" size="sm" onClick={() => refresh()}>
                Retry
              </Button>
            </div>
          )}
          {notice && (
            <div
              role="status"
              className="mb-5 flex items-center justify-between rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3 text-xs"
            >
              <span className="flex items-center gap-2">
                <Check className="size-3.5" />
                {notice}
              </span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X className="size-3.5" />
              </button>
            </div>
          )}
          {loadingDetail && (
            <p role="status" className="mb-4 text-xs text-neutral-500">
              Loading record…
            </p>
          )}
          {!data && !error ? (
            <div className="py-28 text-center text-neutral-400">
              <Loader2 className="mx-auto mb-3 size-5 animate-spin" />
              Loading workspace…
            </div>
          ) : detail ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                className="mb-5 -ml-3"
                onClick={() => setDetail(null)}
              >
                <ArrowLeft />
                Back to {tab.toLowerCase()}
              </Button>
              <label className="mb-4 flex items-center gap-2 text-xs text-neutral-500">
                <input
                  type="checkbox"
                  checked={masked}
                  onChange={async (e) => {
                    const value = e.target.checked;
                    setMasked(value);
                    try {
                      setDetail(
                        await api(
                          "record?id=" +
                            encodeURIComponent(detail.output.id) +
                            (value ? "&mask=1" : ""),
                        ),
                      );
                    } catch (error) {
                      setError((error as Error).message);
                    }
                  }}
                />
                Mask patient identifiers and raw source
              </label>
              <div className="mb-6 rounded-lg border border-neutral-200 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="mb-2 font-mono text-xs">
                      {detail.output.document_id}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {detail.output.clinic} ·{" "}
                      {detail.output.record_type.replaceAll("_", " ")} ·{" "}
                      {time(detail.ingested_at)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={
                      data?.records.find((r) => r.id === detail.output.id)
                        ?.review_status === "Reviewed"
                    }
                    onClick={() => review(detail.output.id)}
                  >
                    <CheckCheck />
                    {data?.records.find((r) => r.id === detail.output.id)
                      ?.review_status === "Reviewed"
                      ? "Reviewed"
                      : "Mark reviewed"}
                  </Button>
                </div>
                <p className="mt-4 break-all text-[11px] text-neutral-400">
                  Source: {detail.source}
                </p>
                <p className="mt-1 text-[11px] text-neutral-400">
                  Configuration: {detail.output.config_version}
                </p>
              </div>
              {!!detail.versions?.length && (
                <details className="mb-5 rounded-md border border-neutral-200 p-4 text-xs">
                  <summary>
                    Previous output versions ({detail.versions.length})
                  </summary>
                  <p className="mt-3 text-neutral-500">
                    Earlier outputs and review state are retained. Refreshed
                    records return to the review queue.
                  </p>
                  {detail.versions.map((version, i) => (
                    <details key={i} className="mt-3">
                      <summary>
                        {version.config_version} · Archived{" "}
                        {time(version.archived_at)}
                      </summary>
                      <pre className="mt-3 max-h-72 overflow-auto">
                        {JSON.stringify(
                          { output: version.output, review: version.review },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  ))}
                </details>
              )}
              <div className="mb-5 flex flex-wrap gap-2">
                {["Observations", "Medications", "Raw & standardised"].map(
                  (t) => (
                    <Button
                      key={t}
                      variant={detailTab === t ? "default" : "outline"}
                      size="sm"
                      onClick={() => setDetailTab(t)}
                    >
                      {t}
                    </Button>
                  ),
                )}
              </div>
              {detailTab === "Observations" ? (
                <div className="overflow-x-auto rounded-lg border border-neutral-200">
                  <div className="flex items-center justify-between gap-3 border-b border-neutral-100 px-4 py-3">
                    <span className="text-xs text-neutral-500">
                      {filteredObservations.length} of{" "}
                      {detail.output.observations.length} observations
                    </span>
                    <select
                      aria-label="Filter observations"
                      value={observationFilter}
                      onChange={(e) => setObservationFilter(e.target.value)}
                      className="h-8 rounded-md border border-neutral-200 px-2 text-xs"
                    >
                      {[
                        "All observations",
                        "Unresolved names",
                        "Missing results",
                        "Derived components",
                        "Invalid",
                        "Outlier",
                        "Above Range",
                        "Below Range",
                        "Within Range",
                      ].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  </div>
                  {filteredObservations.length ? (
                    <table className="w-full">
                      <thead className="bg-neutral-50/70">
                        <tr>
                          {[
                            "Test / source label",
                            "Result",
                            "Reference",
                            "Classification",
                            "Transformation notes",
                          ].map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {filteredObservations.map((o, i) => (
                          <tr key={i}>
                            <td className="min-w-44 max-w-64">
                              <p className="font-medium">
                                {o.test_name_canonical || "Unresolved test"}
                              </p>
                              <p className="mt-1 text-[11px] text-neutral-500">
                                {o.test_name_original}
                              </p>
                              {o.derived_from && (
                                <p className="mt-1 text-[10px] text-neutral-400">
                                  Split from {o.derived_from.test_name}
                                </p>
                              )}
                              <p className="mt-1 text-[10px] text-neutral-400">
                                Page {o.page ?? "—"} · {o.normalization_method}{" "}
                                · {Math.round(o.normalization_confidence * 100)}
                                %
                              </p>
                            </td>
                            <td className="max-w-64">
                              <p>
                                {o.result_interval
                                  ? `${intervalText(o.result_interval)} ${o.unit_canonical ?? ""}`
                                  : o.result_value !== null &&
                                      o.unit_canonical !== null
                                    ? `${o.result_value} ${o.unit_canonical}`
                                    : String(o.result_text ?? "—")}
                              </p>
                              {o.result_value !== null && o.unit_canonical && (
                                <p className="mt-1 text-[10px] text-neutral-400">
                                  Source: {String(o.result_text)}{" "}
                                  {o.unit_original}
                                </p>
                              )}
                            </td>
                            <td className="max-w-44">
                              <p>
                                {o.range_low !== null || o.range_high !== null
                                  ? intervalText({
                                      low: o.range_low,
                                      high: o.range_high,
                                      low_inclusive:
                                        o.range_low_inclusive ?? true,
                                      high_inclusive:
                                        o.range_high_inclusive ?? true,
                                    })
                                  : o.range_text || "—"}
                              </p>
                              <p className="mt-1 text-[10px] text-neutral-400">
                                {o.range_source}
                              </p>
                            </td>
                            <td>
                              <Status value={o.analytics} />
                            </td>
                            <td className="min-w-48 max-w-72 text-[11px] text-neutral-500">
                              {o.issues.length
                                ? o.issues.join(" · ")
                                : "Validated"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <Empty
                      title="No laboratory observations"
                      description="This record is a discharge summary. Inspect its medications or original data."
                    />
                  )}
                </div>
              ) : detailTab === "Medications" ? (
                <div className="overflow-x-auto rounded-lg border border-neutral-200">
                  {detail.output.medications.length ? (
                    <table className="w-full">
                      <thead className="bg-neutral-50">
                        <tr>
                          {[
                            "Source medication",
                            "Generic equivalent",
                            "Dose",
                            "Frequency",
                            "Status",
                          ].map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {detail.output.medications.map((m, i) => (
                          <tr key={i}>
                            <td>{m.original}</td>
                            <td>
                              <p>{m.generic || "—"}</p>
                              {m.mapping_source && (
                                <a
                                  className="mt-1 block text-[10px] text-neutral-500 underline underline-offset-2"
                                  href={m.mapping_source}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Mapping reference
                                </a>
                              )}
                            </td>
                            <td>{m.dose || "—"}</td>
                            <td>{m.frequency || "—"}</td>
                            <td>
                              <Badge>{m.status}</Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <Empty
                      title="No medications"
                      description="There are no discharge medications in this record."
                    />
                  )}
                </div>
              ) : (
                <div className="grid gap-5 lg:grid-cols-2">
                  {[
                    ["Original JSON", detail.raw],
                    ["Standardised output", detail.output],
                  ].map(([label, value]) => (
                    <div
                      key={String(label)}
                      className="min-w-0 rounded-lg border border-neutral-200"
                    >
                      <h2 className="border-b border-neutral-200 px-4 py-3 text-xs font-medium">
                        {String(label)}
                      </h2>
                      <pre className="max-h-[650px] overflow-auto p-4 text-neutral-600">
                        {JSON.stringify(value, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <>
              {tab === "Operations" && <OperationsPanel />}
              {tab === "Overview" && (
                <>
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3 text-xs text-neutral-500">
                    <span>
                      Daily ingestion · {data?.daily.timezone || "Asia/Kolkata"}
                    </span>
                    <form
                      aria-label="Daily statistics filter"
                      className="flex gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        setSelectedDay(
                          String(
                            new FormData(e.currentTarget).get("day") || "",
                          ),
                        );
                      }}
                    >
                      <Input
                        key={data?.daily.date}
                        name="day"
                        required
                        type="date"
                        aria-label="Daily statistics date"
                        defaultValue={selectedDay || data?.daily.date || ""}
                        className="h-8 text-xs"
                      />
                      <Button type="submit" variant="outline" size="sm">
                        Apply
                      </Button>
                    </form>
                  </div>
                  <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
                    {[
                      [
                        "Files received",
                        data?.daily.received ?? 0,
                        "File attempts on selected day",
                      ],
                      [
                        "Processed",
                        data?.daily.processed ?? 0,
                        "Completed file attempts",
                      ],
                      [
                        "Failed",
                        data?.daily.failed ?? 0,
                        "Retained for investigation",
                      ],
                      [
                        "Flagged files",
                        data?.daily.flagged_files ?? 0,
                        "Files containing review flags",
                      ],
                    ].map(([label, value, note]) => (
                      <div
                        className="rounded-lg border border-neutral-200 p-5"
                        key={label}
                      >
                        <p className="text-xs text-neutral-500">{label}</p>
                        <p className="mb-2 mt-4 text-3xl font-semibold tracking-tight tabular-nums">
                          {value}
                        </p>
                        <p className="text-[11px] text-neutral-400">{note}</p>
                      </div>
                    ))}
                  </div>
                  <p className="mb-8 text-[11px] text-neutral-400">
                    All time: {data?.records.length ?? 0} stored records ·{" "}
                    {data?.observation_count ?? 0} observations · {pending}{" "}
                    awaiting review
                  </p>
                  <div className="mb-8 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
                    <section className="rounded-lg border border-neutral-200">
                      <div className="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
                        <h2 className="text-sm font-medium">Latest run</h2>
                        {latest && (
                          <span className="text-[11px] text-neutral-400">
                            {time(latest.started_at)}
                          </span>
                        )}
                      </div>
                      {latest ? (
                        <div className="p-5">
                          <div className="mb-5 flex items-center gap-3">
                            <span className="flex size-9 items-center justify-center rounded-full bg-neutral-100">
                              <Check className="size-4" />
                            </span>
                            <div>
                              <p className="text-sm font-medium">
                                {latest.summary.failed
                                  ? "Completed with errors"
                                  : "Processing complete"}
                              </p>
                              <p className="mt-1 text-[11px] text-neutral-500">
                                {latest.summary.received} files ·{" "}
                                {latest.summary.duration_seconds}s elapsed
                              </p>
                            </div>
                          </div>
                          <div className="grid grid-cols-3 gap-4 border-t border-neutral-100 pt-4">
                            {[
                              [
                                "New / refreshed",
                                `${latest.summary.records} / ${latest.summary.updated_records ?? 0}`,
                              ],
                              ["Duplicates", latest.summary.duplicates],
                              ["Flagged records", latest.summary.flagged],
                            ].map(([k, v]) => (
                              <div key={k}>
                                <p className="text-[11px] text-neutral-500">
                                  {k}
                                </p>
                                <p className="mt-2 text-lg font-medium">{v}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <Empty
                          title="Ready for your first run"
                          description="Run the supplied samples or upload JSON reports."
                        />
                      )}
                    </section>
                    <section className="rounded-lg border border-neutral-200">
                      <div className="border-b border-neutral-100 px-5 py-4">
                        <h2 className="text-sm font-medium">
                          Standardisation coverage
                        </h2>
                      </div>
                      <div className="p-5">
                        <div className="flex items-end justify-between">
                          <p className="text-3xl font-semibold tracking-tight">
                            {data?.total_tests
                              ? (
                                  (data.resolved_tests / data.total_tests) *
                                  100
                                ).toFixed(1)
                              : 0}
                            <span className="text-lg text-neutral-400">%</span>
                          </p>
                          <span className="text-[11px] text-neutral-400">
                            Name resolution
                          </span>
                        </div>
                        <div className="mb-3 mt-4 h-1.5 overflow-hidden rounded-full bg-neutral-100">
                          <div
                            className="h-full rounded-full bg-neutral-800"
                            style={{
                              width: `${data?.total_tests ? (data.resolved_tests / data.total_tests) * 100 : 0}%`,
                            }}
                          />
                        </div>
                        <p className="text-[11px] leading-relaxed text-neutral-500">
                          {data?.resolved_tests || 0} of{" "}
                          {data?.total_tests || 0} original source entries
                          mapped, before panel expansion. Matching includes
                          named panels and findings; result validity is assessed
                          separately.
                        </p>
                        {!!data?.non_test_entries && (
                          <div className="mt-4 rounded-md bg-neutral-50 p-3 text-[11px] text-neutral-600">
                            <p className="font-medium">
                              {(
                                (data.resolved_tests /
                                  data.eligible_test_entries) *
                                100
                              ).toFixed(1)}
                              % excluding identified non-test rows
                            </p>
                            <p className="mt-1">
                              {data.resolved_tests} of{" "}
                              {data.eligible_test_entries} eligible entries. All{" "}
                              {data.non_test_entries} excluded rows remain in
                              the raw metric above and in the source evidence.
                              Uncertain rows remain eligible.
                            </p>
                            <details className="mt-2">
                              <summary>View non-test rows</summary>
                              {Object.entries(data.non_test_names).map(
                                ([name, count]) => (
                                  <p key={name} className="mt-1">
                                    {name} ×{count}
                                  </p>
                                ),
                              )}
                            </details>
                          </div>
                        )}
                        <p className="mt-2 text-[11px] text-neutral-400">
                          {(data?.observation_count ?? 0) -
                            (data?.analytics.Invalid ?? 0)}{" "}
                          of {data?.observation_count ?? 0} output observations
                          have a result classification.
                        </p>
                        {!!Object.keys(data?.unresolved_names || {}).length && (
                          <details className="mt-4 text-[11px] text-neutral-500">
                            <summary>Unresolved source names</summary>
                            <div className="mt-2 max-h-40 overflow-auto">
                              {Object.entries(data?.unresolved_names || {}).map(
                                ([name, count]) => (
                                  <p key={name} className="py-1">
                                    {name}{" "}
                                    <span className="text-neutral-400">
                                      ×{count}
                                    </span>
                                  </p>
                                ),
                              )}
                            </div>
                          </details>
                        )}
                        {!!data?.outdated_records && (
                          <Button
                            className="mt-4"
                            variant="outline"
                            size="sm"
                            disabled={busy}
                            onClick={() => process(undefined, true)}
                          >
                            {busy ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Activity />
                            )}
                            Refresh {data.outdated_records} records with latest
                            mappings
                          </Button>
                        )}
                      </div>
                    </section>
                  </div>
                </>
              )}
              {(tab === "Overview" ||
                tab === "Records" ||
                tab === "Review queue") && (
                <section className="overflow-hidden rounded-lg border border-neutral-200">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-100 px-5 py-4">
                    <h2 className="flex items-center gap-2 text-sm font-medium">
                      {tab === "Overview"
                        ? "Recent records"
                        : tab === "Review queue"
                          ? "Open reviews"
                          : "All records"}
                      <span className="text-xs font-normal text-neutral-400">
                        {records.length}
                      </span>
                    </h2>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 size-3.5 text-neutral-400" />
                        <Input
                          aria-label="Search records"
                          placeholder="Search records…"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          className="h-8 w-44 pl-8 text-xs"
                        />
                      </div>
                      <select
                        aria-label="Filter by clinic"
                        value={clinic}
                        onChange={(e) => setClinic(e.target.value)}
                        className="h-8 rounded-md border border-neutral-200 px-2 text-xs"
                      >
                        <option>All clinics</option>
                        {data?.clinics.map((c) => (
                          <option key={c.clinic}>{c.clinic}</option>
                        ))}
                      </select>
                      {tab === "Records" && (
                        <select
                          aria-label="Filter quality"
                          value={classification}
                          onChange={(e) => setClassification(e.target.value)}
                          className="h-8 rounded-md border border-neutral-200 px-2 text-xs"
                        >
                          <option>All records</option>
                          <option>Flagged</option>
                          <option>Clear</option>
                        </select>
                      )}
                      <Button size="sm" variant="outline" asChild>
                        <a href="/api/export">
                          <ArrowDownToLine />
                          Export
                        </a>
                      </Button>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    {records.length ? (
                      <table className="w-full">
                        <thead className="bg-neutral-50/60">
                          <tr>
                            {[
                              "Document",
                              "Source",
                              "Record type",
                              "Tests",
                              "Quality",
                              "",
                            ].map((h, i) => (
                              <th key={i}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {records
                            .slice(0, tab === "Overview" ? 6 : 500)
                            .map((r) => (
                              <tr key={r.id} className="hover:bg-neutral-50/60">
                                <td>
                                  <button
                                    className="text-left font-mono text-[11px] underline-offset-4 hover:underline"
                                    onClick={() => inspect(r.id)}
                                  >
                                    {r.document_id.length > 27
                                      ? r.document_id.slice(0, 27) + "…"
                                      : r.document_id}
                                  </button>
                                  <p className="mt-1 text-[10px] text-neutral-400">
                                    {r.patient.report_date ||
                                      "Date unavailable"}
                                  </p>
                                </td>
                                <td>{r.clinic}</td>
                                <td className="text-neutral-500">
                                  {r.record_type.replaceAll("_", " ")}
                                </td>
                                <td className="tabular-nums">
                                  {r.tests || "—"}
                                </td>
                                <td>
                                  <Badge
                                    className={
                                      r.review_status === "Reviewed"
                                        ? "bg-neutral-50 text-neutral-500"
                                        : r.flagged
                                          ? "border-amber-200 bg-amber-50 text-amber-800"
                                          : ""
                                    }
                                  >
                                    {r.review_status === "Reviewed"
                                      ? "Reviewed"
                                      : r.flagged
                                        ? `${r.issues} flags`
                                        : "Clear"}
                                  </Badge>
                                </td>
                                <td>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    aria-label={`Inspect ${r.document_id}`}
                                    onClick={() => inspect(r.id)}
                                  >
                                    <ArrowUpRight />
                                  </Button>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    ) : (
                      <Empty
                        title={
                          tab === "Review queue"
                            ? "No open reviews"
                            : "No records found"
                        }
                        description={
                          query || clinic !== "All clinics"
                            ? "Try adjusting your search or filters."
                            : "Run sample data or upload reports to get started."
                        }
                      />
                    )}
                  </div>
                  {tab === "Overview" && records.length > 6 && (
                    <div className="flex justify-end border-t border-neutral-100 px-4 py-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setTab("Records")}
                      >
                        View all records
                        <ChevronRight />
                      </Button>
                    </div>
                  )}
                </section>
              )}
              {tab === "Clinics" && (
                <section className="overflow-x-auto rounded-lg border border-neutral-200">
                  {data?.clinics.length ? (
                    <table className="w-full">
                      <thead className="bg-neutral-50">
                        <tr>
                          {[
                            "Source system",
                            "File attempts",
                            "Records added",
                            "Duplicates",
                            "Duplicate rate",
                            "Failed files",
                            "Error rate",
                            "Missing required fields",
                          ].map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.clinics.map((c) => (
                          <tr key={c.clinic}>
                            <td className="font-medium">{c.clinic}</td>
                            <td>{c.files}</td>
                            <td>{c.records}</td>
                            <td>{c.duplicates}</td>
                            <td>
                              <p>{percent(c.duplicate_rate)}</p>
                              <p className="mt-1 text-[10px] text-neutral-400">
                                {c.duplicates} / {c.record_occurrences}{" "}
                                occurrences
                              </p>
                            </td>
                            <td>{c.failed}</td>
                            <td>{percent(c.error_rate)}</td>
                            <td>
                              <p>{percent(c.missing_field_rate)}</p>
                              <p className="mt-1 text-[10px] text-neutral-400">
                                {c.missing_fields ?? 0} /{" "}
                                {c.expected_fields ?? 0} fields
                              </p>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <Empty
                      title="No clinic activity"
                      description="Source metrics appear after processing reports."
                    />
                  )}
                  <p className="border-t border-neutral-100 p-4 text-[11px] text-neutral-400">
                    Rates include reruns: duplicates / record occurrences,
                    failed files / file attempts, and missing / expected
                    required demographic fields. Redacted values count as
                    missing. Historical attempts without quality contracts are
                    excluded from the missing-field rate. Source system is the
                    sample clinic proxy.
                  </p>
                </section>
              )}
              {tab === "Activity" && (
                <div className="space-y-6">
                  <section className="overflow-x-auto rounded-lg border border-neutral-200">
                    <h2 className="border-b border-neutral-100 px-5 py-4 text-sm font-medium">
                      Processing runs
                    </h2>
                    {data?.runs.length ? (
                      <table className="w-full">
                        <thead className="bg-neutral-50">
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
                          {data.runs.map((r) => (
                            <tr key={r.id}>
                              <td>{time(r.started_at)}</td>
                              <td>{r.summary.received ?? "Running"}</td>
                              <td>{r.summary.processed ?? "—"}</td>
                              <td>{r.summary.failed ?? "—"}</td>
                              <td>{r.summary.duplicates ?? "—"}</td>
                              <td>{r.summary.duration_seconds ?? "—"}s</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <Empty
                        title="No processing runs"
                        description="Run history will appear here."
                      />
                    )}
                  </section>
                  <section className="overflow-x-auto rounded-lg border border-neutral-200">
                    <h2 className="border-b border-neutral-100 px-5 py-4 text-sm font-medium">
                      File outcomes
                    </h2>
                    <table className="w-full">
                      <thead className="bg-neutral-50">
                        <tr>
                          {[
                            "File",
                            "Source",
                            "Status",
                            "New records",
                            "Duplicates",
                            "Error detail",
                          ].map((h) => (
                            <th key={h}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data?.files.map((f) => (
                          <tr key={f.id}>
                            <td>{f.name.split("/").pop()}</td>
                            <td>{f.clinic}</td>
                            <td>
                              <Status value={f.status} />
                            </td>
                            <td>{f.records}</td>
                            <td>{f.duplicates}</td>
                            <td className="max-w-72 text-neutral-500">
                              {f.reason || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                </div>
              )}
            </>
          )}
        </main>
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 py-5 text-[10px] text-neutral-400">
          <span>Veritas Claims · Operations workspace</span>
          <span>
            {data?.config.tests || 0} dictionary entries · Local SQLite ·
            Prototype
          </span>
        </footer>
      </div>
    </div>
  );
}
