export type WalkthroughStep = {
  id: string;
  chapter: string;
  title: string;
  description: string;
  instruction: string;
  target: string;
  screen: string;
  event?: string;
  record?: "lab" | "discharge" | "review";
  detailTab?: string;
  fill?: string;
  download?: "valid" | "invalid";
  optional?: boolean;
  effect?: string;
  unavailable?: string;
};

export const walkthroughSteps: WalkthroughStep[] = [
  {
    id: "welcome",
    chapter: "Getting started",
    title: "Your workspace, one step at a time",
    description:
      "Veritas reads medical-report JSON, standardises supported data, and keeps uncertain results available for review. This guide uses the real interface.",
    instruction:
      "Continue to begin. You control every action; the guide never submits, processes, retries, or reviews a record for you.",
    target: "navigation",
    screen: "Overview",
  },
  {
    id: "samples",
    chapter: "Getting started",
    title: "Load the supplied reports",
    description:
      "Sample reports give you records to explore. Repeating a run demonstrates duplicate suppression.",
    instruction: "Click Run sample data, wait for the result, then Continue.",
    target: "samples",
    screen: "Overview",
    event: "samples-processed",
    effect:
      "Processes the supplied files in this workspace and records a new run. Existing records are deduplicated.",
  },
  {
    id: "daily",
    chapter: "Dashboard",
    title: "Look at a day's activity",
    description:
      "These figures count file attempts on the chosen date: received, processed, failed, and flagged. Reruns count as new attempts.",
    instruction:
      "Choose a date and click Apply. Fill example uses the date of your latest run.",
    target: "daily-filter",
    screen: "Overview",
    event: "date-applied",
    fill: "date",
  },
  {
    id: "coverage",
    chapter: "Dashboard",
    title: "Understand what was mapped",
    description:
      "Name resolution measures recognised source labels. A recognised name can still have an invalid result. The result-classification count is shown separately.",
    instruction:
      "Compare raw coverage, coverage excluding identified non-test rows, and classified observations.",
    target: "coverage",
    screen: "Overview",
  },
  {
    id: "exclusions",
    chapter: "Dashboard",
    title: "See exactly what was excluded",
    description:
      "Headings and comments remain in the raw metric and source evidence. The eligible metric excludes only the listed non-test rows.",
    instruction:
      "Expand View non-test rows, then Continue. If your data has none, skip this step.",
    target: "exclusions",
    screen: "Overview",
    event: "exclusions-opened",
    optional: true,
    unavailable: "No identified non-test rows are present in this dataset.",
  },
  {
    id: "records",
    chapter: "Find records",
    title: "Open the records list",
    description:
      "Records contains the stored reports, including their source, record type, observation count, and review status.",
    instruction: "Click Records in the navigation.",
    target: "nav-Records",
    screen: "Overview",
    event: "nav:Records",
  },
  {
    id: "search",
    chapter: "Find records",
    title: "Search your reports",
    description:
      "Search matches document IDs, clinic names, patient names, and record types. Results update as you type.",
    instruction:
      "Type a search, or click Fill example to search for lab_report.",
    target: "search",
    screen: "Records",
    event: "records-searched",
    fill: "search",
  },
  {
    id: "clinic-filter",
    chapter: "Find records",
    title: "Filter by source clinic",
    description:
      "Use the clinic filter to narrow the list to one source. This affects the visible list, not the stored records.",
    instruction: "Choose a clinic, or use Fill example.",
    target: "clinic-filter",
    screen: "Records",
    event: "clinic-filtered",
    fill: "clinic",
  },
  {
    id: "quality-filter",
    chapter: "Find records",
    title: "Find flagged records",
    description:
      "Flagged records need attention. A flag may mean an unresolved name, missing unit, inconsistent value, or out-of-range result.",
    instruction: "Select Flagged in the quality filter, or use Fill example.",
    target: "quality-filter",
    screen: "Records",
    event: "quality-filtered",
    fill: "quality",
  },
  {
    id: "inspect-lab",
    chapter: "Inspect a report",
    title: "Open a laboratory report",
    description:
      "The inspector connects the standardised results to their source evidence.",
    instruction: "Click the highlighted Inspect arrow for a laboratory report.",
    target: "inspect-lab",
    screen: "Records",
    event: "inspect:lab",
    unavailable: "No laboratory report is available. Run sample data first.",
  },
  {
    id: "observation-filter",
    chapter: "Inspect a report",
    title: "Narrow down the observations",
    description:
      "Each row shows the canonical name, original label, result, unit, range, classification, and issues.",
    instruction:
      "Choose an observation filter, or use Fill example to show Invalid results.",
    target: "observation-filter",
    screen: "Records",
    record: "lab",
    detailTab: "Observations",
    event: "observations-filtered",
    fill: "observations",
  },
  {
    id: "provenance",
    chapter: "Inspect a report",
    title: "Read the evidence and flags",
    description:
      "Derived components retain their parent field. Missing units, contradictory ranges, and ambiguous results remain visible rather than being guessed.",
    instruction:
      "Read the highlighted table. Scroll horizontally if needed to see range sources and issues.",
    target: "observations",
    screen: "Records",
    record: "lab",
    detailTab: "Observations",
  },
  {
    id: "raw",
    chapter: "Inspect a report",
    title: "Compare raw and standardised data",
    description:
      "The original JSON is retained alongside the transformed output so you can check each decision.",
    instruction: "Click Raw & standardised.",
    target: "detail-Raw & standardised",
    screen: "Records",
    record: "lab",
    detailTab: "Observations",
    event: "detail:Raw & standardised",
  },
  {
    id: "mask",
    chapter: "Inspect a report",
    title: "Try identifier masking",
    description:
      "Masking hides patient identifiers, raw source text, and source location in this inspector response. It does not change stored data or protect other routes.",
    instruction:
      "Toggle Mask patient identifiers and raw source and inspect the result.",
    target: "mask",
    screen: "Records",
    record: "lab",
    detailTab: "Raw & standardised",
    event: "mask-changed",
  },
  {
    id: "versions",
    chapter: "Inspect a report",
    title: "Inspect previous output versions",
    description:
      "Refreshing outdated mappings archives the previous output and review state. An unchanged rerun creates no new version.",
    instruction:
      "Expand Previous output versions. A fresh database may have no history yet; skip if unavailable.",
    target: "versions",
    screen: "Records",
    record: "lab",
    event: "versions-opened",
    optional: true,
    unavailable:
      "No previous output versions exist for this record. History appears after a mapping refresh.",
  },
  {
    id: "inspect-discharge",
    chapter: "Medicines",
    title: "Open a discharge summary",
    description:
      "Discharge summaries contain medications and clinical details. They may have no laboratory observations.",
    instruction: "Click the highlighted Inspect arrow for a discharge summary.",
    target: "inspect-discharge",
    screen: "Records",
    event: "inspect:discharge",
    unavailable: "No discharge summary is available. Run sample data first.",
  },
  {
    id: "medications",
    chapter: "Medicines",
    title: "Look at medicine mappings",
    description:
      "Verified products are mapped to generic ingredients. Formulation suffixes and strengths matter; unresolved names remain for review.",
    instruction:
      "Click Medications and read the mapping status and reference links.",
    target: "detail-Medications",
    screen: "Records",
    record: "discharge",
    detailTab: "Observations",
    event: "detail:Medications",
  },
  {
    id: "review-queue",
    chapter: "Review and export",
    title: "Open the review queue",
    description:
      "This queue contains flagged records that have not been acknowledged as reviewed.",
    instruction: "Click Review queue in the navigation.",
    target: "nav-Review queue",
    screen: "Records",
    event: "nav:Review queue",
  },
  {
    id: "inspect-review",
    chapter: "Review and export",
    title: "Inspect an open review",
    description:
      "Check the observations or source before acknowledging a flagged record.",
    instruction:
      "Click the highlighted Inspect arrow. If the queue is empty, skip this step.",
    target: "inspect-review",
    screen: "Review queue",
    event: "inspect:review",
    optional: true,
    unavailable:
      "There are no open reviews. Reviewed records remain accessible in Records.",
  },
  {
    id: "mark-reviewed",
    chapter: "Review and export",
    title: "Acknowledge a reviewed record",
    description:
      "Review acknowledgement removes an item from the open queue. Its medical values and source flags remain unchanged.",
    instruction:
      "When you have inspected it, click Mark reviewed. Skip if you do not want to change the review status.",
    target: "mark-reviewed",
    screen: "Review queue",
    record: "review",
    event: "record-reviewed",
    optional: true,
    effect: "Updates this record's review status in the database.",
    unavailable:
      "No unreviewed flagged record is available. You can skip this step.",
  },
  {
    id: "export",
    chapter: "Review and export",
    title: "Export the canonical output",
    description:
      "The CSV has five columns for each configured test. Absent tests are blank; repeated observations use additional rows. The export includes all stored records, not just the filtered list.",
    instruction: "Click Export to request the CSV download.",
    target: "export",
    screen: "Records",
    event: "export-requested",
    optional: true,
  },
  {
    id: "refresh",
    chapter: "Review and export",
    title: "Refresh records after mapping changes",
    description:
      "When stored records use an older processor or configuration, a refresh button appears here. It archives earlier outputs and resets review for recalculated records.",
    instruction:
      "Read the coverage panel. Only run a mapping refresh when you intend to recalculate records; it is not needed to complete this guide.",
    target: "coverage",
    screen: "Overview",
  },
  {
    id: "upload",
    chapter: "File ingestion",
    title: "Upload your own JSON",
    description:
      "You can upload a supported clinic format. The downloadable example is synthetic and uses the second configured schema.",
    instruction:
      "Download the example, click Upload JSON, and select it. Upload starts after file selection. You can also skip this demonstration.",
    target: "upload",
    screen: "Overview",
    event: "upload-succeeded",
    download: "valid",
    optional: true,
    effect:
      "Stores the uploaded file and processes it. Re-uploading the same example is idempotent.",
  },
  {
    id: "clinics",
    chapter: "Source quality",
    title: "Compare clinics",
    description:
      "Clinic summaries show duplicate, file-error, and missing-required-field rates with their denominators. Reruns are included.",
    instruction: "Click Clinics and compare the source rows.",
    target: "nav-Clinics",
    screen: "Overview",
    event: "nav:Clinics",
  },
  {
    id: "activity",
    chapter: "Source quality",
    title: "Read processing history",
    description:
      "Activity shows runs and file outcomes, including suppressed duplicates and reasons for file failures.",
    instruction: "Click Activity, then inspect the run and file tables.",
    target: "nav-Activity",
    screen: "Clinics",
    event: "nav:Activity",
  },
  {
    id: "operations",
    chapter: "Operations",
    title: "Open the operational controls",
    description:
      "Operations combines folder intake, local health metrics, alerts, failed-file repair, and the intake queue.",
    instruction: "Click Operations.",
    target: "nav-Operations",
    screen: "Activity",
    event: "nav:Operations",
  },
  {
    id: "watcher",
    chapter: "Operations",
    title: "Try the folder watcher controls",
    description:
      "JSON files saved to the displayed inbox are discovered after a settling period. Pause stops new discovery and processing; it persists across restarts.",
    instruction:
      "Optionally pause and then resume ingestion. Continue unlocks after you click Resume. Leave ingestion running when finished.",
    target: "watcher",
    screen: "Operations",
    event: "watcher-running",
    optional: true,
    effect:
      "Pause/resume changes the real watcher setting. Exiting the guide does not undo a pause.",
  },
  {
    id: "health",
    chapter: "Operations",
    title: "Understand pipeline health",
    description:
      "Throughput is observed traffic, not capacity. p95 starts at local discovery. Oldest pending age includes settling, queued, and processing files.",
    instruction: "Read the four metric cards and the folder queue below them.",
    target: "health",
    screen: "Operations",
  },
  {
    id: "failed-upload",
    chapter: "Recovery",
    title: "See how a malformed file is handled",
    description:
      "The optional example is deliberately incomplete JSON. A failure is retained for investigation while other files can continue.",
    instruction:
      "Download the invalid example, click Upload JSON, and select it. Continue unlocks when the file is recorded as failed.",
    target: "upload",
    screen: "Operations",
    event: "upload-failed",
    download: "invalid",
    optional: true,
    effect:
      "Creates a failed file attempt and dead-letter entry. It may activate the processing error-rate alert.",
  },
  {
    id: "failure-inspect",
    chapter: "Recovery",
    title: "Inspect a failed file",
    description:
      "Failed-file review retains the source payload, error, status, and retry count. Select the walkthrough-invalid.json entry if you uploaded it.",
    instruction:
      "Click the highlighted Inspect / retry button. If there are no failed inputs, skip.",
    target: "failure-inspect",
    screen: "Operations",
    event: "failure-inspected",
    optional: true,
    unavailable:
      "No failed inputs are available. Upload the optional invalid example to demonstrate recovery.",
  },
  {
    id: "repair",
    chapter: "Recovery",
    title: "Repair and retry the JSON",
    description:
      "The original failed payload is preserved. Each retry records the submitted content and outcome.",
    instruction:
      "Use Fill example to put valid synthetic JSON in the editor, then click Retry edited JSON. You must submit the retry yourself.",
    target: "repair",
    screen: "Operations",
    event: "retry-succeeded",
    fill: "repair",
    optional: true,
    effect:
      "Processes the edited JSON and updates the failure status. It may add a synthetic record or suppress a duplicate.",
    unavailable:
      "Open a failed file with Inspect / retry first, or skip if no failure is available.",
  },
  {
    id: "alerts",
    chapter: "Operations",
    title: "Review and acknowledge alerts",
    description:
      "Local alerts track error-rate, lag, and latency breaches. Acknowledgement records that someone has seen the alert; recovery depends on the underlying metrics.",
    instruction:
      "Read Monitoring alerts. Optionally click Acknowledge on an active alert. No action is needed if there are no breaches.",
    target: "alerts",
    screen: "Operations",
  },
  {
    id: "finish",
    chapter: "Complete",
    title: "You have explored the workspace",
    description:
      "You have seen ingestion, coverage, inspection, medicine mapping, review, export, clinic quality, history, and operational recovery.",
    instruction:
      "Finish to close the guide. You can start again from Walkthrough in the header. Any actions you chose to submit remain in the workspace.",
    target: "navigation",
    screen: "Overview",
  },
];
