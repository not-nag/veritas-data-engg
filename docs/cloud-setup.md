# Cloud integration

The application runs locally without cloud services. Gemini and GCS are independent optional integrations. The backend remains Python with a persistent SQLite database; a static frontend host cannot run the full application.

## Local configuration

Run `npm run setup` to install the web packages and Python cloud libraries in `.venv`. Add settings to the ignored root `.env`, then restart `npm run dev`. The Python service loads this file without evaluating shell commands. Never prefix the Gemini key with `NEXT_PUBLIC_`.

```dotenv
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.5-flash-lite
GOOGLE_CLOUD_PROJECT=your-project-id
GCS_BUCKET=your-private-bucket
GCS_PREFIX=clinic/
GCS_AUTO_SYNC=false
```

Only configure services you intend to use. The Gemini key stays on the Python server. **More → AI mappings** sends one explicitly confirmed test label, without a report, patient result, reference range, or medicine. Use synthetic labels with the free-tier API. Google may use free-tier content to improve its products; this demo is not configured for processing identifiable health information through Gemini.

Gemini selects from the existing canonical dictionary or returns unresolved. The server validates the response, stores a pending suggestion, and requires acceptance before adding a SQLite-backed alias. Reviewer identity, model, timestamps, and the decision are retained. Accepted aliases apply to future ingestion and explicit reprocessing; existing reports are unchanged until reprocessed. The deterministic processor still handles values, units, ranges, and validation. The entire demo has a limit of 10 AI requests per UTC day, including failed requests. There is no automatic retry, model fallback, or upgrade to a paid tier. An application limit does not change the API key's billing plan; use a free-tier project for a zero-charge requirement.

## Google Cloud Storage

Authenticate using Application Default Credentials (`gcloud auth application-default login`), or a workload's attached service account. The identity needs `roles/storage.objectViewer` on the configured bucket; do not make the bucket public. Bucket creation and billing are separate administrative steps.

Use **More → System tools → Google Cloud Storage → Sync now**, or:

```bash
PYTHONPATH=src .venv/bin/python -m pipeline --gcs
PYTHONPATH=src .venv/bin/python -m pipeline --gcs --watch
```

Setting `GCS_AUTO_SYNC=true` starts 60-second polling with the API. Each scan processes at most 50 new/retryable JSON object generations. Object identity includes bucket, name, and generation. Downloads are pinned to the listed generation, bounded to 10 MB, and retained locally before processing. Source objects are never deleted or modified. Successful generations are skipped; overwritten objects are new generations. Record-level content deduplication still applies across files and generations.

A crash after committing records but before marking a generation processed causes the next scan to replay it; duplicate suppression prevents additional records. Failed downloads are retained as failed cloud outcomes, and need **Retry failed objects**. Invalid JSON/schema files also appear in the existing failed-file workflow. Polling and SQLite are a single-instance implementation, not a horizontally scaled service. Retained files and database checkpoints must share persistent storage.

## Public viewing and signed-in writes

Firebase Google sign-in is used for interactive users. The API verifies Firebase token signatures, issuer, audience, expiry, and a non-anonymous user identity before every POST when authentication is enabled. All existing mutation endpoints, GCS sync, and AI actions use the same guard. The Next.js proxy forwards the token; a caller cannot bypass checks by contacting Python directly. GET requests remain public.

```dotenv
VERITAS_REQUIRE_AUTH=true
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_WEB_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
FIREBASE_APP_ID=your-web-app-id
```

Firebase web configuration is public project metadata; it is separate from the secret Gemini key. Enable Google sign-in in Firebase Authentication and add `localhost`, `127.0.0.1`, and the eventual hosted domain to authorised domains. Missing configuration or invalid tokens fail closed when `VERITAS_REQUIRE_AUTH=true`. Local-only use defaults to no sign-in requirement. Any signed-in non-anonymous user may mutate this shared demo, as opposed to a tenant-isolated patient portal. Use synthetic records only for a public deployment: public reads include reports, original inputs, exports and operational history. Do not publish the existing assignment database without reviewing its contents.

## Hosting status and cost

The selected project is `testing-514806`. At the integration check, billing was disabled and there were no GCS buckets. GCS and Cloud Run require an enabled Cloud Billing account even for free-tier allowances. This repository does not enable billing, create paid infrastructure, or guarantee zero charges from free-tier quotas. Firebase's Spark authentication can be configured separately; static Firebase Hosting alone cannot execute this Python/SQLite application.

Full deployment still needs an approved runtime and durable storage. Keep SQLite and retained uploads on a persistent volume with backups for a single-instance deployment, or migrate storage and coordination before using ephemeral/scaled instances. Do not mount a SQLite file on an object-storage bucket or store it on Cloud Run's ephemeral filesystem. BigQuery is appropriate for analytical exports, not as a direct replacement for the application's transactional review/checkpoint store.
