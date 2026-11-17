# Gemini test-name mapping

The local pipeline works without an API key. Add these values to the ignored root `.env` and restart `npm run dev`:

```dotenv
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_AUTO_MAPPING=true
```

## Automatic ingestion fallback

Dictionary aliases, fuzzy matching and configured context rules run first. With automatic mapping enabled, unresolved test labels are sent to Gemini before the transformed report is stored. Gemini chooses an existing canonical name or returns unresolved. Numeric parsing, units, reference ranges and medicine mapping still use existing deterministic rules. The original JSON is never rewritten.

Only individual test labels and the canonical vocabulary are sent, not the patient object or the complete report. Labels may themselves contain identifying text in poorly structured input; basic checks do not guarantee de-identification. Use synthetic or redacted inputs. Free-tier content may be used by Google to improve its products. The key stays on the Python server.

Automatic decisions are recorded in `ai_mapping_events`, linked to the run and source file. Observations retain model, reason and decision ID, with matching method `gemini`; no numerical confidence is invented. Automatic mappings do not become human-approved dictionary aliases. Duplicate labels share a request within one run. Exact duplicate records skip AI. Mapping calls occur before the file write transaction.

Result-only labels, numeric fragments and known headings are excluded. Unsupported names, timeouts, invalid responses and exhausted quota leave names unresolved without failing the file. Automatic requests use a 10-second timeout. All automatic and manual calls share the 10-request UTC daily cap, including failures. There is no automatic retry or paid fallback. This application cap does not change the API key's billing plan.

Inspect **More → AI mappings → Automatic processing decisions**. Open a report and expand source details to see which observations used Gemini. Set `GEMINI_AUTO_MAPPING=false` to disable this fallback. Tests disable it globally and mock requests in dedicated integration tests.

## Optional human-reviewed aliases

The same page also supports manually requesting a suggestion. These remain pending until accepted or rejected. Accepting adds a reusable alias to SQLite; automatic decisions are not presented as human approvals. Accepted aliases affect future processing. Existing reports require explicit reprocessing, which preserves previous output and resets review status.

AI changes a test name only, not a measured value. A valid name does not make a contradictory result or unit valid. Unknown labels such as ABSENT or damaged extractions require source clarification. The deterministic sample baseline remains 92.6% raw / 96.0% excluding non-test rows; enabling AI does not establish 98% coverage or mapping accuracy.
