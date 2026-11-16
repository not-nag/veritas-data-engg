"use client";
import Link from "next/link";
import {
  ArrowDownToLine,
  ChevronRight,
  FileText,
  Search,
  Upload,
} from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { useWorkspace } from "./workspace-provider";
import { useWalkthrough } from "./walkthrough";
import { reportTitle } from "@/lib/client";
export function ReportsPage() {
  const w = useWorkspace(),
    tour = useWalkthrough(),
    pending =
      w.data?.records.filter((r) => r.flagged && r.review_status !== "Reviewed")
        .length || 0;
  const records =
    w.data?.records.filter(
      (r) =>
        (w.clinic === "All clinics" || r.clinic === w.clinic) &&
        (w.quality !== "Needs review" ||
          (r.flagged && r.review_status !== "Reviewed")) &&
        (w.quality !== "Reviewed" || r.review_status === "Reviewed") &&
        (w.quality !== "No flags" || !r.flagged) &&
        `${r.document_id} ${r.clinic} ${r.patient.name || ""} ${r.record_type}`
          .toLowerCase()
          .includes(w.query.toLowerCase()),
    ) || [];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Reports</h1>
          <p>Your medical reports, with standardised results ready to check.</p>
        </div>
        <div className="page-actions">
          <Button
            variant="outline"
            disabled={!w.data?.records.length}
            onClick={() => w.setExportOpen(true)}
          >
            <ArrowDownToLine />
            Export
          </Button>
          <Button onClick={() => w.setUploadOpen(true)}>
            <Upload />
            Upload reports
          </Button>
        </div>
      </div>
      <div className="report-toolbar">
        <div className="local-tabs" aria-label="Report views">
          <button
            className={w.quality !== "Needs review" ? "selected" : ""}
            onClick={() => w.setQuality("All reports")}
          >
            All reports <span>{w.data?.records.length || 0}</span>
          </button>
          <button
            data-tour="nav-Review queue"
            className={w.quality === "Needs review" ? "selected" : ""}
            onClick={() => {
              w.setQuality("Needs review");
              tour.signal("nav:Review queue");
            }}
          >
            Needs review <span>{pending}</span>
          </button>
        </div>
        <div className="report-filters">
          <div className="search-field">
            <Search className="size-4" />
            <Input
              aria-label="Search reports"
              data-tour="search"
              placeholder="Search reports…"
              value={w.query}
              onChange={(e) => {
                w.setQuery(e.target.value);
                if (e.target.value.trim()) tour.signal("records-searched");
              }}
            />
          </div>
          <select
            aria-label="Filter by source"
            data-tour="clinic-filter"
            value={w.clinic}
            onChange={(e) => {
              w.setClinic(e.target.value);
              tour.signal("clinic-filtered");
            }}
          >
            <option>All clinics</option>
            {w.data?.clinics.map((c) => (
              <option key={c.clinic}>{c.clinic}</option>
            ))}
          </select>
          <select
            aria-label="Filter by review status"
            data-tour="quality-filter"
            value={w.quality}
            onChange={(e) => {
              w.setQuality(e.target.value);
              tour.signal("quality-filtered");
            }}
          >
            {["All reports", "Needs review", "Reviewed", "No flags"].map(
              (q) => (
                <option key={q}>{q}</option>
              ),
            )}
          </select>
        </div>
      </div>
      <section className="reports-list" aria-label="Reports">
        {!w.data && !w.error ? (
          <p className="empty-state" role="status">
            Loading reports…
          </p>
        ) : !records.length ? (
          <div className="empty-state">
            <FileText className="mx-auto mb-3 size-7 text-neutral-300" />
            <h2>
              {w.data?.records.length
                ? "No matching reports"
                : "No reports yet"}
            </h2>
            <p>
              {w.data?.records.length
                ? "Clear your search or adjust the filters."
                : "Upload a JSON report or try the sample data."}
            </p>
            {w.data?.records.length ? (
              <Button
                className="mt-4"
                variant="outline"
                onClick={() => {
                  w.setQuery("");
                  w.setClinic("All clinics");
                  w.setQuality("All reports");
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Button className="mt-4" onClick={() => w.setUploadOpen(true)}>
                Upload your first report
              </Button>
            )}
          </div>
        ) : (
          <ul>
            {records.map((r) => (
              <li key={r.id}>
                <Link
                  className="report-list-link"
                  href={"/reports/" + r.id}
                  data-tour={
                    w.quality === "Needs review"
                      ? "inspect-review"
                      : r.tests
                        ? "inspect-lab"
                        : "inspect-discharge"
                  }
                  onClick={() => w.remember(r)}
                >
                  <span className="report-file-icon">
                    <FileText className="size-5" />
                  </span>
                  <div className="report-list-copy">
                    <h2>{reportTitle(r.record_type)}</h2>
                    <p>{r.patient.name || "Patient name unavailable"}</p>
                    <div className="report-list-meta">
                      <span>{r.clinic}</span>
                      <span>{r.patient.report_date || "Date unavailable"}</span>
                      {r.tests > 0 && <span>{r.tests} results</span>}
                    </div>
                    <span className="report-document-id">{r.document_id}</span>
                  </div>
                  <Badge
                    className={
                      r.review_status === "Reviewed"
                        ? "status-reviewed"
                        : r.flagged
                          ? "status-review"
                          : ""
                    }
                  >
                    {r.review_status === "Reviewed"
                      ? "Reviewed"
                      : r.flagged
                        ? "Needs review"
                        : "No flags"}
                  </Badge>
                  <ChevronRight className="report-chevron size-4" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="list-footnote">
        “Needs review” refers to data quality checks. Open a report to see the
        details.
      </p>
    </>
  );
}
