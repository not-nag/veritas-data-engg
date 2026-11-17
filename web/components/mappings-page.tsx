"use client";
import { useEffect, useState } from "react";
import { api, time } from "@/lib/client";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { useWorkspace } from "./workspace-provider";
type Suggestion = {
  id: string;
  label: string;
  canonical: string | null;
  reason: string;
  model: string;
  status: string;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
};
type State = {
  enabled: boolean;
  automatic_enabled: boolean;
  automatic: { id: string; label: string; canonical: string | null; reason: string; model: string; status: string; created_at: string }[];
  model: string;
  daily_limit: number;
  calls_today: number;
  suggestions: Suggestion[];
  unresolved: { label: string; occurrences: number }[];
  aliases: { label: string; canonical: string }[];
};
export function MappingsPage() {
  const workspace = useWorkspace();
  const [confirmReplay, setConfirmReplay] = useState(false);
  const [notice, setNotice] = useState("");
  const [data, setData] = useState<State | null>(null);
  const [label, setLabel] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    api("mappings")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  async function act(body: unknown) {
    setBusy(true);
    setError("");
    try {
      setData(await api("mappings", body));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function replay() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await api("process", { mode: "stored", reprocess: true });
      await workspace.refresh();
      setData(await api("mappings"));
      setNotice(
        `${result.updated_records} reports updated. Previous output versions were retained; review the recalculated results.`,
      );
      setConfirmReplay(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>AI mappings</h1>
          <p>
            Unrecognised test names can be resolved by Gemini during processing.
            You can also request and review reusable aliases here.
          </p>
        </div>
      </div>
      <p className="supporting mb-5">
        Automatic ingestion mapping: {data?.automatic_enabled ? "On" : "Off"}.
        Only test labels are sent; results, units and reference ranges use existing rules.
      </p>
      {!!data?.automatic?.length && (
        <div className="data-table-wrap mb-6">
          <h2 className="p-4 font-semibold">Automatic processing decisions</h2>
          <table className="w-full">
            <thead><tr><th>Original name</th><th>Mapped name</th><th>Outcome</th><th>Reason</th></tr></thead>
            <tbody>{data.automatic.map((event) => (
              <tr key={event.id}>
                <td>{event.label}<p className="supporting">{time(event.created_at)}</p></td>
                <td>{event.canonical || "Unresolved"}</td>
                <td>{event.status}</td><td>{event.reason}<p className="supporting">{event.model}</p></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      <div className="mapping-form">
        {!!data?.unresolved?.length && (
          <div>
            <label htmlFor="unresolved-name">
              Unresolved names from your reports
            </label>
            <select
              id="unresolved-name"
              className="mt-2 w-full rounded-md border border-neutral-200 p-2"
              value=""
              onChange={(e) => {
                setLabel(e.target.value);
                setConsent(false);
              }}
            >
              <option value="">Choose a label to review…</option>
              {data.unresolved.map((item) => (
                <option key={item.label} value={item.label}>
                  {item.label} ({item.occurrences})
                </option>
              ))}
            </select>
            <p className="supporting mt-2">
              Damaged or missing names require the original report. Manual suggestions
              below require approval; automatic ingestion decisions are listed separately.
            </p>
          </div>
        )}
        <label htmlFor="test-label">Test name</label>
        <div className="flex gap-3">
          <Input
            id="test-label"
            maxLength={100}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. HGB concentration"
          />
          <Button
            disabled={
              busy ||
              !consent ||
              !label.trim() ||
              !data?.enabled ||
              data.calls_today >= data.daily_limit
            }
            onClick={() => act({ action: "suggest", label, labels_only: true })}
          >
            {busy ? "Working…" : "Ask Gemini"}
          </Button>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />{" "}
          This is a test name only, with no patient information.
        </label>
        <p className="supporting">
          Only this label is sent to Google. Use synthetic examples for the
          free-tier demo. Results, medicines and reference ranges are never
          generated by AI.
        </p>
        <p className="supporting">
          {data?.enabled
            ? `${data.calls_today} of ${data.daily_limit} daily requests used · ${data.model}`
            : "Gemini is not configured."}
        </p>
      </div>
      {error && (
        <div className="feedback feedback-error" role="alert">
          {error}
        </div>
      )}
      <p className="supporting my-5">
        Accepted aliases apply to future processing. Existing reports change
        only when explicitly reprocessed; previous outputs are retained.
      </p>
      {!!(data?.aliases.length || data?.automatic.length) && (
        <div className="my-5">
          {!confirmReplay ? (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => setConfirmReplay(true)}
            >
              Reprocess existing reports
            </Button>
          ) : (
            <div className="rounded-md border border-neutral-200 p-4">
              <p className="mb-3">
                Reprocess stored reports using current mappings and retry failed Gemini lookups? Previous
                outputs will be retained. Review acknowledgements reset for
                changed reports.
              </p>
              <div className="flex gap-2">
                <Button disabled={busy} onClick={replay}>
                  {busy ? "Reprocessing…" : "Reprocess reports"}
                </Button>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => setConfirmReplay(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
      {notice && (
        <p role="status" className="feedback mb-5">
          {notice}
        </p>
      )}
      <div className="data-table-wrap mapping-results">
        <table className="w-full">
          <thead>
            <tr>
              <th>Original name</th>
              <th>Suggested name</th>
              <th>Reason</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {!data?.suggestions.length && (
              <tr>
                <td colSpan={4}>
                  No suggestions yet. Enter a synthetic test label above to try
                  it.
                </td>
              </tr>
            )}
            {data?.suggestions.map((s) => (
              <tr key={s.id}>
                <td data-label="Original name">
                  {s.label}
                  <p className="supporting">{time(s.created_at)}</p>
                </td>
                <td data-label="Suggested name">
                  {s.canonical || "Unresolved"}
                </td>
                <td data-label="Reason">
                  {s.reason}
                  <details className="mt-2">
                    <summary>Audit details</summary>
                    <p>Model: {s.model}</p>
                    {s.reviewed_at && (
                      <p>
                        Reviewed by {s.reviewed_by} · {time(s.reviewed_at)}
                      </p>
                    )}
                  </details>
                </td>
                <td data-label="Review">
                  {s.status === "Pending" ? (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => act({ id: s.id, decision: "Accepted" })}
                      >
                        Accept
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => act({ id: s.id, decision: "Rejected" })}
                      >
                        Reject
                      </Button>
                    </div>
                  ) : (
                    s.status
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
