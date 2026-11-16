"use client";
import { useEffect, useState } from "react";
import { api, time } from "@/lib/client";
import { useWorkspace } from "./workspace-provider";
import { Button } from "./ui/button";
type State = {
  configured: boolean;
  bucket: string;
  prefix: string;
  automatic: boolean;
  objects: {
    bucket: string;
    name: string;
    generation: string;
    status: string;
    error: string | null;
    updated_at: string;
  }[];
};
export function CloudPanel() {
  const [data, setData] = useState<State | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const w = useWorkspace();
  useEffect(() => {
    api("cloud")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  async function sync(retry = false) {
    setBusy(true);
    setError("");
    try {
      setData(await api("cloud", { retry_failed: retry }));
      await w.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="cloud-section">
      <div className="page-heading">
        <div>
          <h2>Google Cloud Storage</h2>
          <p>
            {data?.configured
              ? `gs://${data.bucket}/${data.prefix} · ${data.automatic ? "Checks every 60 seconds" : "Manual sync"}`
              : "Not connected. A bucket and Google Cloud credentials are needed."}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={!data?.configured || busy}
            onClick={() => sync(true)}
          >
            Retry failed objects
          </Button>
          <Button disabled={!data?.configured || busy} onClick={() => sync()}>
            {busy ? "Syncing…" : "Sync now"}
          </Button>
        </div>
      </div>
      {!data?.configured && (
        <p className="supporting">
          Local uploads and folder ingestion still work. Cloud integration is
          ready to configure once a bucket is available.
        </p>
      )}
      {error && (
        <p role="alert" className="feedback feedback-error">
          {error}
        </p>
      )}
      {!!data?.objects.length && (
        <div className="data-table-wrap">
          <table className="w-full">
            <thead>
              <tr>
                <th>Object</th>
                <th>Generation</th>
                <th>Status</th>
                <th>Last checked</th>
              </tr>
            </thead>
            <tbody>
              {data.objects.map((o) => (
                <tr key={`${o.name}:${o.generation}`}>
                  <td>{o.name}</td>
                  <td>{o.generation}</td>
                  <td>
                    {o.status}
                    {o.error && <p>{o.error}</p>}
                  </td>
                  <td>{time(o.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
