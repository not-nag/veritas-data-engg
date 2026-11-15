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
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  ChevronUp,
  Pause,
  RotateCcw,
  WandSparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  walkthroughSteps,
  type WalkthroughStep,
} from "@/lib/walkthrough-steps";
import {
  canContinue,
  completeFromEvent,
  readProgress,
} from "@/lib/walkthrough-state.mjs";

const STORAGE_KEY = "veritas.walkthrough.v1";
type FillRequest = { stepId: string; sequence: number } | null;
type Context = {
  active: boolean;
  step: WalkthroughStep;
  index: number;
  completed: string[];
  saved: boolean;
  open: (resume?: boolean) => void;
  pause: () => void;
  go: (index: number) => void;
  finish: () => void;
  signal: (event: string) => void;
  fillRequest: FillRequest;
  requestFill: () => void;
  watcherPaused: boolean;
  reportWatcher: (enabled: boolean) => void;
};
const WalkthroughContext = createContext<Context | null>(null);
export function useWalkthrough() {
  const value = useContext(WalkthroughContext);
  if (!value) throw new Error("WalkthroughProvider is required");
  return value;
}
export function WalkthroughProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false),
    [index, setIndex] = useState(0),
    [completed, setCompleted] = useState<string[]>([]),
    [saved, setSaved] = useState(false),
    [ready, setReady] = useState(false),
    [fillRequest, setFillRequest] = useState<FillRequest>(null),
    [watcherPaused, setWatcherPaused] = useState(false);
  const step = walkthroughSteps[index];
  useEffect(() => {
    let progress = null;
    try {
      progress = readProgress(
        localStorage.getItem(STORAGE_KEY),
        walkthroughSteps.map((s) => s.id),
      );
    } catch {
      /* Memory-only guide when storage is unavailable. */
    }
    if (progress) {
      setIndex(walkthroughSteps.findIndex((s) => s.id === progress.stepId));
      setCompleted(progress.completed);
      setSaved(true);
    }
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready || !saved) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ version: 1, stepId: step.id, completed }),
      );
    } catch {
      /* Progress still works for this session. */
    }
  }, [ready, saved, step.id, completed]);
  const signal = useCallback(
    (event: string) => {
      if (event === "watcher-paused") setWatcherPaused(true);
      if (event === "watcher-running") setWatcherPaused(false);
      if (active)
        setCompleted((previous) => completeFromEvent(previous, step, event));
    },
    [active, step],
  );
  const reportWatcher = useCallback(
    (enabled: boolean) => setWatcherPaused(!enabled),
    [],
  );
  function open(resume = false) {
    if (!resume) {
      setIndex(0);
      setCompleted([]);
    }
    setFillRequest(null);
    setSaved(true);
    setActive(true);
  }
  function go(next: number) {
    setFillRequest(null);
    setIndex(Math.max(0, Math.min(walkthroughSteps.length - 1, next)));
  }
  function finish() {
    setActive(false);
    setSaved(false);
    setFillRequest(null);
    setCompleted([]);
    setIndex(0);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* No persistent progress to remove. */
    }
  }
  return (
    <WalkthroughContext.Provider
      value={{
        active,
        step,
        index,
        completed,
        saved,
        open,
        pause: () => setActive(false),
        go,
        finish,
        signal,
        fillRequest,
        requestFill: () =>
          setFillRequest({ stepId: step.id, sequence: Date.now() }),
        watcherPaused,
        reportWatcher,
      }}
    >
      {children}
    </WalkthroughContext.Provider>
  );
}
export function WalkthroughLauncher() {
  const { active, saved, open, pause } = useWalkthrough();
  return (
    <Button
      size="sm"
      variant="outline"
      onClick={() => (active ? pause() : open(saved))}
      aria-expanded={active}
      aria-controls="walkthrough-guide"
    >
      <BookOpen />
      {active
        ? "Pause walkthrough"
        : saved
          ? "Resume walkthrough"
          : "Walkthrough"}
    </Button>
  );
}
export function WalkthroughGuide({ onFinish }: { onFinish: () => void }) {
  const {
    active,
    step,
    index,
    completed,
    go,
    pause,
    open,
    finish,
    requestFill,
    watcherPaused,
  } = useWalkthrough();
  const [found, setFound] = useState(false),
    [collapsed, setCollapsed] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (!active) return;
    setCollapsed(false);
    let highlighted: HTMLElement | null = null;
    let frame = 0;
    function locate() {
      const target =
        Array.from(document.querySelectorAll<HTMLElement>("[data-tour]")).find(
          (el) =>
            el.dataset.tour === step.target && el.getClientRects().length > 0,
        ) || null;
      setFound(!!target);
      if (target === highlighted) return;
      highlighted?.classList.remove("walkthrough-target");
      highlighted = target;
      if (target) {
        target.classList.add("walkthrough-target");
        frame = requestAnimationFrame(() =>
          target.scrollIntoView({
            block: "center",
            behavior: window.matchMedia("(prefers-reduced-motion: reduce)")
              .matches
              ? "auto"
              : "smooth",
          }),
        );
      }
    }
    heading.current?.focus({ preventScroll: true });
    const observer = new MutationObserver(locate);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["data-tour", "hidden"],
    });
    const resize = new ResizeObserver(locate);
    resize.observe(document.body);
    locate();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      resize.disconnect();
      highlighted?.classList.remove("walkthrough-target");
    };
  }, [active, step]);
  if (!active) return null;
  const done = canContinue(step, completed);
  const last = index === walkthroughSteps.length - 1;
  return (
    <aside
      id="walkthrough-guide"
      className="walkthrough-guide"
      aria-label="Interactive walkthrough"
    >
      <div className="walkthrough-toolbar">
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs">
          <BookOpen className="size-4" />
          <span className="font-medium">Walkthrough</span>
          <span className="text-neutral-500">
            {index + 1} / {walkthroughSteps.length}
          </span>
          <label className="sr-only" htmlFor="walkthrough-step">
            Jump to walkthrough step
          </label>
          <select
            id="walkthrough-step"
            className="walkthrough-select"
            value={index}
            onChange={(e) => go(Number(e.target.value))}
          >
            {walkthroughSteps.map((s, i) => (
              <option key={s.id} value={i}>
                {i + 1}. {s.chapter} · {s.title}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <Button
            size="icon"
            variant="ghost"
            aria-label={
              collapsed ? "Expand walkthrough" : "Minimise walkthrough"
            }
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? <ChevronDown /> : <ChevronUp />}
          </Button>
          <Button size="sm" variant="ghost" onClick={pause}>
            <Pause />
            Pause
          </Button>
        </div>
      </div>
      {!collapsed && (
        <div className="walkthrough-body">
          <div className="min-w-0">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-neutral-500">
              {step.chapter}
              {step.optional ? " · Optional action" : ""}
            </p>
            <h2
              ref={heading}
              tabIndex={-1}
              className="text-base font-semibold outline-none"
            >
              {step.title}
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-neutral-600">
              {step.description}
            </p>
            <p className="mt-2 text-xs font-medium leading-relaxed">
              {step.instruction}
            </p>
            {step.effect && (
              <p className="mt-2 text-[11px] leading-relaxed text-neutral-500">
                <span className="font-medium">Workspace effect: </span>
                {step.effect}
              </p>
            )}
            {!found && (
              <p role="status" className="mt-2 text-xs text-neutral-600">
                {step.unavailable ||
                  "Waiting for this control. If you navigated away, use Back then Continue to return, or skip this step."}
              </p>
            )}
            {watcherPaused && (
              <p
                role="status"
                className="mt-2 text-xs font-medium text-amber-800"
              >
                Folder ingestion is paused. Resume it in Operations; closing the
                guide will not resume it.
              </p>
            )}
          </div>
          <div className="walkthrough-actions">
            {step.fill && (
              <Button
                size="sm"
                variant="outline"
                disabled={!found}
                onClick={requestFill}
              >
                <WandSparkles />
                Fill example
              </Button>
            )}
            {step.download && (
              <Button size="sm" variant="outline" asChild>
                <a
                  href={
                    step.download === "valid"
                      ? "/walkthrough-example.json"
                      : "/walkthrough-invalid.json"
                  }
                  download
                >
                  {step.download === "valid"
                    ? "Download valid example"
                    : "Download invalid example"}
                </a>
              </Button>
            )}
            <p
              className="flex items-center gap-1.5 text-[11px] text-neutral-500"
              role="status"
              aria-live="polite"
            >
              {step.event ? (
                done ? (
                  <>
                    <Check className="size-3.5" />
                    Action completed
                  </>
                ) : (
                  "Complete the action to continue, or skip."
                )
              ) : (
                "Continue when you are ready."
              )}
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={index === 0}
                onClick={() => go(index - 1)}
              >
                <ArrowLeft />
                Back
              </Button>
              <Button
                size="sm"
                disabled={!done}
                onClick={() => {
                  if (last) {
                    finish();
                    onFinish();
                  } else go(index + 1);
                }}
              >
                {last ? "Finish" : "Continue"}
                <ArrowRight />
              </Button>
            </div>
            <div className="flex flex-wrap gap-3 text-[11px]">
              {!last && (
                <button
                  className="underline underline-offset-4"
                  onClick={() => go(index + 1)}
                >
                  Skip step
                </button>
              )}
              <button
                className="flex items-center gap-1 underline underline-offset-4"
                onClick={() => open(false)}
              >
                <RotateCcw className="size-3" />
                Restart
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
