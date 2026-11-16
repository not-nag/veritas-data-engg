# Gemini mapping suggestions

The local pipeline works without an API key. To enable **More → AI mappings**, add the following to the ignored root `.env`, then restart `npm run dev`:

```dotenv
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

The Python server loads the file without evaluating shell commands. The key is never sent to the browser. No additional Python packages are required.

Only an explicitly confirmed test label is sent to Gemini, together with the allowed canonical names. Reports, patient results, reference ranges and medicines are not sent or generated. Use synthetic labels for the demo; free-tier content may be used by Google to improve its products.

Gemini selects an existing canonical name or returns unresolved. The server validates the response and stores a pending suggestion. Accepting adds a persistent alias to SQLite; rejecting leaves the dictionary unchanged. The model, reason, timestamps and local operator label are retained. The label `local-user` identifies a local action, not a verified person.

Accepted aliases apply to future ingestion and explicit reprocessing. Existing reports remain unchanged until reprocessed; previous outputs are archived. Values, units, reference checks and outlier flags still use deterministic Python rules.

The app allows 10 Gemini requests per UTC day, including failed calls. There is no automatic retry or paid-model fallback. This cap does not change the API key's billing plan; use a free-tier key if charges must be avoided.

Unresolved names can be selected directly from stored reports. Result-only labels, numeric fragments and known headings are rejected before calling Gemini. Inputs such as ABSENT, ET and 9-11 cannot establish a missing analyte; correcting them requires the source report. The sample name-resolution metric remains 92.6% raw / 96.0% eligible, and no 98% achievement is claimed.
