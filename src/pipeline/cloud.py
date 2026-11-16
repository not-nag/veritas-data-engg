"""Generation-aware GCS ingestion; source objects remain untouched."""
import hashlib
import os
import threading
from pathlib import Path
from .engine import DB, ROOT, now, process_files
from .store import connect

MAX_BYTES = 10_000_000


def snapshot(db=DB):
    with connect(db) as c:
        rows = [dict(r) for r in c.execute('SELECT bucket,name,generation,status,run_id,error,updated_at FROM cloud_objects ORDER BY updated_at DESC LIMIT 50')]
    return {'configured': bool(os.getenv('GCS_BUCKET')), 'bucket': os.getenv('GCS_BUCKET', ''),
            'prefix': os.getenv('GCS_PREFIX', ''), 'automatic': os.getenv('GCS_AUTO_SYNC', 'false').lower() == 'true',
            'poll_seconds': 60, 'objects': rows}


def client():
    try:
        from google.cloud import storage
        return storage.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))
    except ImportError:
        raise ValueError('Install the optional Python requirements for GCS ingestion.') from None
    except Exception:
        raise ValueError('Google Cloud credentials are unavailable. Authenticate with Application Default Credentials.') from None


def sync(db=DB, config_dir=ROOT/'config', storage_client=None, retry_failed=False):
    bucket = os.getenv('GCS_BUCKET', '')
    prefix = os.getenv('GCS_PREFIX', '')
    if not bucket:
        raise ValueError('GCS is not configured. Set GCS_BUCKET after a bucket is available.')
    storage_client = storage_client or client()
    results, skipped = [], 0
    try:
        # Bound a scan to keep the interactive demo predictable; later scans skip completed objects.
        candidates = storage_client.list_blobs(bucket, prefix=prefix)
        attempted = 0
        for blob in candidates:
            if not blob.name.lower().endswith('.json'):
                continue
            if attempted >= 50:
                break
            generation = str(blob.generation)
            identifier = hashlib.sha256(f'{bucket}\n{blob.name}\n{generation}'.encode()).hexdigest()
            with connect(db) as c:
                prior = c.execute('SELECT status FROM cloud_objects WHERE id=?', (identifier,)).fetchone()
            if prior and (prior['status'] == 'Processed' or (prior['status'] == 'Failed' and not retry_failed)):
                skipped += 1
                continue
            attempted += 1
            target = ROOT/'data/cloud'/identifier/'source.json'
            with connect(db) as c:
                c.execute('INSERT OR REPLACE INTO cloud_objects VALUES (?,?,?,?,?,?,?,?,?)',
                          (identifier, bucket, blob.name, generation, 'Processing', str(target), None, None, now()))
            try:
                if blob.size is None or int(blob.size) > MAX_BYTES:
                    raise ValueError('Object exceeds the 10 MB limit or has no known size.')
                # Immutable generation prevents an overwrite between listing and download from changing the input.
                content = blob.download_as_bytes(if_generation_match=int(generation), timeout=30)
                if len(content) > MAX_BYTES:
                    raise ValueError('Object exceeds the 10 MB limit.')
                text = content.decode('utf-8')
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix('.part')
                temporary.write_text(text)
                temporary.replace(target)
                arrival = getattr(blob, 'time_created', None)
                result = process_files([(str(target), text)], db, config_dir,
                                       arrivals={str(target): arrival.isoformat()} if arrival else None,
                                       arrival_basis='GCS object creation')
                status = 'Failed' if result['failed'] else 'Processed'
                with connect(db) as c:
                    c.execute('UPDATE cloud_objects SET status=?,run_id=?,error=?,updated_at=? WHERE id=?',
                              (status, result['id'], 'Source validation failed; inspect failed files.' if status == 'Failed' else None, now(), identifier))
                results.append(result)
            except Exception:
                # Keep errors concise; provider exceptions can contain internal request details.
                with connect(db) as c:
                    c.execute('UPDATE cloud_objects SET status=?,error=?,updated_at=? WHERE id=?',
                              ('Failed', 'Download or processing failed. Check bucket permissions, generation, UTF-8 encoding and size.', now(), identifier))
        return {'runs': results, 'skipped': skipped, **snapshot(db)}
    except Exception:
        raise ValueError('Cannot list the GCS bucket. Check billing, credentials, bucket name and objectViewer permissions.') from None


class CloudWatcher:
    def __init__(self):
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        if os.getenv('GCS_BUCKET') and os.getenv('GCS_AUTO_SYNC', 'false').lower() == 'true':
            self.thread.start()

    def run(self):
        from .operations import PROCESS_LOCK
        import logging
        while not self.stop.is_set():
            if PROCESS_LOCK.acquire(blocking=False):
                try:
                    sync()
                except Exception as exc:
                    logging.warning('GCS sync: %s', exc)
                finally:
                    PROCESS_LOCK.release()
            self.stop.wait(60)

    def close(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)
