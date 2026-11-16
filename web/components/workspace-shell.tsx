"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowDownToLine,
  ChevronDown,
  Files,
  Loader2,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { SignIn } from "./sign-in";
import { Button } from "./ui/button";
import {
  WalkthroughProvider,
  WalkthroughLauncher,
  WalkthroughGuide,
  useWalkthrough,
} from "./walkthrough";
import { WorkspaceProvider, useWorkspace } from "./workspace-provider";
export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (open && !el?.open) el?.showModal();
    else if (!open && el?.open) el.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="app-dialog"
      aria-label={title}
      onCancel={onClose}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          const box = e.currentTarget.getBoundingClientRect();
          if (
            e.clientX < box.left ||
            e.clientX > box.right ||
            e.clientY < box.top ||
            e.clientY > box.bottom
          )
            onClose();
        }
      }}
    >
      <div className="dialog-heading">
        <h2>{title}</h2>
        <button aria-label={`Close ${title}`} onClick={onClose}>
          <X className="size-5" />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function WorkspaceShell({ children }: { children: ReactNode }) {
  return (
    <WalkthroughProvider>
      <WorkspaceProvider>
        <Shell>{children}</Shell>
      </WorkspaceProvider>
    </WalkthroughProvider>
  );
}
function Shell({ children }: { children: ReactNode }) {
  const w = useWorkspace(),
    tour = useWalkthrough(),
    path = usePathname(),
    input = useRef<HTMLInputElement>(null),
    [help, setHelp] = useState(false);
  const pending =
    w.data?.records.filter((r) => r.flagged && r.review_status !== "Reviewed")
      .length || 0;
  function closeMenu(e: React.MouseEvent) {
    e.currentTarget.closest("details")?.removeAttribute("open");
  }
  return (
    <>
      <header className="app-header">
        <div className="app-header-inner">
          <Link className="app-brand" href="/reports">
            <ShieldCheck className="size-5" />
            veritas
          </Link>
          <nav
            aria-label="Main navigation"
            data-tour="navigation"
            className="app-nav"
          >
            <Link
              href="/reports"
              data-tour="nav-Records"
              aria-current={path.startsWith("/reports") ? "page" : undefined}
              onClick={() => tour.signal("nav:Records")}
            >
              Reports
            </Link>
            <Link
              href="/activity"
              data-tour="nav-Activity"
              aria-current={path === "/activity" ? "page" : undefined}
              onClick={() => tour.signal("nav:Activity")}
            >
              Activity
            </Link>
            <details
              className="header-menu"
              open={
                tour.active && ["clinics", "operations"].includes(tour.step.id)
              }
            >
              <summary
                className={
                  ["/system", "/sources"].includes(path) ? "active" : ""
                }
              >
                More <ChevronDown className="size-3.5" />
              </summary>
              <div className="menu-content">
                <Link
                  href="/sources"
                  data-tour="nav-Clinics"
                  onClick={(e) => {
                    tour.signal("nav:Clinics");
                    closeMenu(e);
                  }}
                >
                  Sources
                </Link>
                <Link href="/mappings" onClick={closeMenu}>
                  AI mappings
                </Link>
                <Link
                  href="/system"
                  data-tour="nav-Operations"
                  onClick={(e) => {
                    tour.signal("nav:Operations");
                    closeMenu(e);
                  }}
                >
                  System tools
                </Link>
                <button
                  onClick={(e) => {
                    w.setExportOpen(true);
                    closeMenu(e);
                  }}
                >
                  Export CSV
                </button>
                <button
                  onClick={(e) => {
                    setHelp(true);
                    closeMenu(e);
                  }}
                >
                  Help & walkthrough
                </button>
              </div>
            </details>
          </nav>
          <SignIn />
        </div>
      </header>
      <div className="app-container">
        <WalkthroughGuide
          onFinish={() =>
            w.setNotice("Walkthrough complete. Restart it from More → Help.")
          }
        />
        {w.error && (
          <div role="alert" className="feedback feedback-error">
            <span>{w.error}</span>
            <Button size="sm" variant="outline" onClick={() => w.refresh()}>
              Retry
            </Button>
          </div>
        )}
        {w.notice && (
          <div role="status" className="feedback">
            <span>{w.notice}</span>
            <button
              aria-label="Dismiss notification"
              onClick={() => w.setNotice("")}
            >
              <X className="size-4" />
            </button>
          </div>
        )}
        <main className="app-main" id="main-content">
          {children}
        </main>
        <footer className="app-footer">
          Veritas · Medical report standardisation
        </footer>
      </div>
      <Dialog
        open={w.uploadOpen}
        onClose={() => w.setUploadOpen(false)}
        title="Upload reports"
      >
        <p className="supporting">
          Choose medical-report JSON files in a supported format. Results appear
          in Reports after processing.
        </p>
        <div className="file-drop">
          <Upload className="size-7" />
          <p>One or more JSON files</p>
          <span>Up to 9.5 MB per upload</span>
          <Button
            data-tour="upload"
            disabled={w.busy}
            onClick={() => input.current?.click()}
          >
            {w.busy ? <Loader2 className="animate-spin" /> : <Upload />}Choose
            files
          </Button>
        </div>
        <input
          ref={input}
          type="file"
          aria-label="Upload JSON reports"
          accept=".json,application/json"
          multiple
          className="hidden"
          onChange={(e) => {
            const files = e.target.files;
            if (files?.length) void w.process(files);
            e.target.value = "";
          }}
        />
        <div className="sample-option">
          <div>
            <p>Just exploring?</p>
            <a href="/walkthrough-example.json" download>
              Download an example JSON
            </a>
          </div>
          <Button
            data-tour="samples"
            variant="outline"
            disabled={w.busy}
            onClick={() => w.process()}
          >
            <Files />
            Use sample data
          </Button>
        </div>
        {w.busy && (
          <p role="status" className="supporting mt-4">
            Processing files. Please keep this window open.
          </p>
        )}
        {w.error && (
          <p role="alert" className="mt-4 text-sm text-red-700">
            {w.error}
          </p>
        )}
        {w.notice && (
          <p role="status" className="mt-4 text-sm">
            {w.notice}
          </p>
        )}
      </Dialog>
      <Dialog
        open={w.exportOpen}
        onClose={() => w.setExportOpen(false)}
        title="Export results"
      >
        <p className="supporting">
          Download standardised tests, results, references, units, and result
          statuses.
        </p>
        <p className="export-summary">
          {w.data?.records.length || 0} reports · {pending} awaiting review
        </p>
        <p className="supporting mb-6">
          The CSV includes all stored reports, including reports awaiting
          review. Search and filters do not change the export.
        </p>
        {w.data?.records.length ? (
          <Button asChild>
            <a
              href="/api/export"
              data-tour="export"
              onClick={() => {
                tour.signal("export-requested");
                w.setExportOpen(false);
              }}
            >
              <ArrowDownToLine />
              Download CSV
            </a>
          </Button>
        ) : (
          <p className="supporting">Upload a report before exporting.</p>
        )}
      </Dialog>
      <Dialog open={help} onClose={() => setHelp(false)} title="Using Veritas">
        <p className="supporting">
          Upload a JSON report, check its standardised results, then mark it as
          reviewed. Export the results when you are ready.
        </p>
        <div className="mt-6" onClick={() => setHelp(false)}>
          <WalkthroughLauncher />
        </div>
        <div className="help-links">
          <a href="/walkthrough-example.json" download>
            Download valid example
          </a>
          <a href="/walkthrough-invalid.json" download>
            Download failed-file example
          </a>
        </div>
        <p className="supporting mt-5">
          Review flags identify data that needs checking. Marking reviewed
          records your acknowledgement; it does not correct results or remove
          flags.
        </p>
      </Dialog>
    </>
  );
}
