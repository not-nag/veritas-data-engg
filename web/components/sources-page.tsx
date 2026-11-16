"use client";
import { useWorkspace } from "./workspace-provider";
import { percent } from "@/lib/client";
export function SourcesPage() {
  const { data } = useWorkspace();
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Sources</h1>
          <p>
            Data quality by the clinic or source system identified in each file.
          </p>
        </div>
      </div>
      <div className="data-table-wrap">
        <table className="w-full">
          <thead>
            <tr>
              {[
                "Source",
                "Files received",
                "Reports added",
                "Duplicate rate",
                "File error rate",
                "Missing required fields",
              ].map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.clinics.map((c) => (
              <tr key={c.clinic}>
                <td className="font-medium">{c.clinic}</td>
                <td>{c.files}</td>
                <td>{c.records}</td>
                <td>
                  {percent(c.duplicate_rate)}
                  <p className="table-note">
                    {c.duplicates}/{c.record_occurrences} report occurrences
                  </p>
                </td>
                <td>
                  {percent(c.error_rate)}
                  <p className="table-note">
                    {c.failed}/{c.files} file attempts
                  </p>
                </td>
                <td>
                  {percent(c.missing_field_rate)}
                  <p className="table-note">
                    {c.missing_fields ?? 0}/{c.expected_fields ?? 0} expected
                    fields
                  </p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data ? (
          <p role="status" className="empty-state">
            Loading sources…
          </p>
        ) : (
          !data.clinics.length && (
            <p className="empty-state">
              Sources appear after reports are processed.
            </p>
          )
        )}
      </div>
      <p className="list-footnote">
        Rates include reruns. Missing-field rates exclude historical attempts
        without a quality contract; redacted values count as missing.
      </p>
    </>
  );
}
