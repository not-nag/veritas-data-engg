"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/client";
import type { Data, Rec } from "@/lib/types";
import { processingEvent } from "@/lib/walkthrough-state.mjs";
import { useWalkthrough } from "./walkthrough";
type Workspace = {
  data: Data | null;
  error: string;
  notice: string;
  busy: boolean;
  uploadOpen: boolean;
  exportOpen: boolean;
  setUploadOpen: (v: boolean) => void;
  setExportOpen: (v: boolean) => void;
  setNotice: (v: string) => void;
  setError: (v: string) => void;
  refresh: (dayOverride?: string) => Promise<boolean>;
  process: (files?: FileList, reprocess?: boolean) => Promise<void>;
  review: (id: string) => Promise<void>;
  day: string;
  setDay: (v: string) => void;
  query: string;
  setQuery: (v: string) => void;
  clinic: string;
  setClinic: (v: string) => void;
  quality: string;
  setQuality: (v: string) => void;
  remember: (record: Rec) => void;
};
const Context = createContext<Workspace | null>(null);
export function useWorkspace() {
  const value = useContext(Context);
  if (!value) throw new Error("WorkspaceProvider is required");
  return value;
}
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const tour = useWalkthrough(),
    router = useRouter(),
    pathname = usePathname();
  const [data, setData] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [uploadOpen, setUploadOpenState] = useState(false),
    [exportOpen, setExportOpen] = useState(false),
    [day, setDay] = useState("");
  const [query, setQuery] = useState(""),
    [clinic, setClinic] = useState("All clinics"),
    [quality, setQuality] = useState("All reports");
  const setUploadOpen = useCallback((value: boolean) => {
    if (value) {
      setError("");
      setNotice("");
    }
    setUploadOpenState(value);
  }, []);
  const remembered = useRef<Record<string, string>>({});
  const refresh = useCallback(
    async (dayOverride?: string) => {
      try {
        const chosenDay = dayOverride ?? day;
        setData(
          await api(
            "dashboard" +
              (chosenDay ? "?day=" + encodeURIComponent(chosenDay) : ""),
          ),
        );
        setError("");
        return true;
      } catch (e) {
        setError((e as Error).message);
        return false;
      }
    },
    [day],
  );
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 10000);
    return () => clearInterval(timer);
  }, [refresh]);
  const prepared = useRef("");
  useEffect(() => {
    if (!tour.active) {
      prepared.current = "";
      return;
    }
    const step = tour.step;
    if (prepared.current === step.id) return;
    if (step.record && !data) return;
    prepared.current = step.id;
    setQuery("");
    setClinic("All clinics");
    setQuality(step.screen === "Review queue" ? "Needs review" : "All reports");
    setUploadOpen(["samples", "upload", "failed-upload"].includes(step.id));
    setExportOpen(step.id === "export");
    let target =
      step.screen === "Activity"
        ? "/activity"
        : step.screen === "Clinics"
          ? "/sources"
          : step.screen === "Operations"
            ? "/system"
            : "/reports";
    if (["daily", "coverage", "exclusions", "refresh"].includes(step.id))
      target = "/activity";
    if (step.id === "records") target = "/activity";
    if (step.record) {
      const chosen =
        data?.records.find((r) => r.id === remembered.current[step.record!]) ||
        data?.records.find((r) =>
          step.record === "lab"
            ? r.tests > 0
            : step.record === "discharge"
              ? r.record_type === "discharge_summary"
              : r.flagged && r.review_status !== "Reviewed",
        );
      if (chosen) target = "/reports/" + chosen.id;
    }
    if (pathname !== target) router.push(target);
  }, [tour.active, tour.step.id, data?.records.length, pathname, router]);
  useEffect(() => {
    const request = tour.fillRequest;
    if (!request) return;
    if (request.stepId === "search") {
      setQuery("lab_report");
      tour.signal("records-searched");
    }
    if (request.stepId === "clinic-filter") {
      const name = data?.records.find((r) => r.tests > 0)?.clinic;
      if (name) {
        setClinic(name);
        tour.signal("clinic-filtered");
      }
    }
    if (request.stepId === "quality-filter") {
      setQuality("Needs review");
      tour.signal("quality-filtered");
    }
  }, [tour.fillRequest]);
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
          throw new Error("Choose JSON files only.");
        if (Array.from(files).reduce((n, f) => n + f.size, 0) > 9500000)
          throw new Error("Keep uploads below 9.5 MB.");
        payload = {
          files: await Promise.all(
            Array.from(files).map(async (f) => ({
              name: f.name,
              content: await f.text(),
            })),
          ),
        };
      }
      const result = await api("process", payload);
      await refresh();
      const event = processingEvent({
        upload: !!files,
        reprocess,
        processed: result.processed,
        failed: result.failed,
      });
      if (event) tour.signal(event);
      setNotice(
        `${result.processed} files processed · ${result.records} new reports · ${result.duplicates} duplicates skipped${result.updated_records ? ` · ${result.updated_records} refreshed` : ""}${result.failed ? ` · ${result.failed} failed — see System tools` : ""}`,
      );
      setUploadOpen(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function review(id: string) {
    setBusy(true);
    try {
      await api("review", { id, status: "Reviewed" });
      await refresh();
      setNotice(
        "Report marked as reviewed. Original data and flags are retained.",
      );
      tour.signal("record-reviewed");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function remember(record: Rec) {
    if (record.tests) {
      remembered.current.lab = record.id;
      tour.signal("inspect:lab");
    }
    if (record.record_type === "discharge_summary") {
      remembered.current.discharge = record.id;
      tour.signal("inspect:discharge");
    }
    if (record.flagged && record.review_status !== "Reviewed") {
      remembered.current.review = record.id;
      tour.signal("inspect:review");
    }
  }
  return (
    <Context.Provider
      value={{
        data,
        error,
        notice,
        busy,
        uploadOpen,
        exportOpen,
        setUploadOpen,
        setExportOpen,
        setNotice,
        setError,
        refresh,
        process,
        review,
        day,
        setDay,
        query,
        setQuery,
        clinic,
        setClinic,
        quality,
        setQuality,
        remember,
      }}
    >
      {children}
    </Context.Provider>
  );
}
