"""Local intake queue, dead-letter repair, measured health, and durable threshold alerts."""
import hashlib
import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from .engine import ROOT, DB, configuration, digest, now, process_files
from .store import connect

PROCESS_LOCK=threading.Lock()


def settings(db=DB,config_dir=ROOT/'config'):
    return configuration(config_dir)['clinics'].get('operations',{})


def import_legacy_errors(db):
    """First-version JSON error files remain accessible in the retry queue."""
    with connect(db) as connection:
        for file in (Path(db).parent/'dead-letter').glob('*.json'):
            try:
                payload=json.loads(file.read_text())
                connection.execute('INSERT OR IGNORE INTO dead_letters(id,source,content,reason,created_at,updated_at,status,last_run_id) VALUES(?,?,?,?,?,?,?,?)',(file.stem,payload['source'],payload['content'],payload['reason'],datetime.fromtimestamp(file.stat().st_mtime,timezone.utc).isoformat(),now(),'Open',payload.get('run_id')))
            except (ValueError,KeyError,OSError):
                continue


def retry_dead_letter(identifier,content=None,db=DB,config_dir=ROOT/'config'):
    with connect(db) as connection:
        old=connection.execute('SELECT * FROM dead_letters WHERE id=?',(identifier,)).fetchone()
        if not old:
            raise ValueError('Dead-letter entry not found')
        if old['status']=='Retrying':
            raise ValueError('This entry is already being retried')
        if content is None:content=old['content']
        if not isinstance(content,str) or len(content.encode())>9_000_000:
            raise ValueError('Corrected JSON must be text below 9 MB')
        stamp=now()
        connection.execute("UPDATE dead_letters SET status='Retrying',retry_count=retry_count+1,updated_at=? WHERE id=?",(stamp,identifier))
        attempt=connection.execute('INSERT INTO retry_attempts(dead_letter_id,content,started_at,outcome) VALUES(?,?,?,?)',(identifier,content,stamp,'Running')).lastrowid
    retained=Path(db).parent/'retries'/identifier/(digest(content)+'.json')
    retained.parent.mkdir(parents=True,exist_ok=True)
    try:
        retained.write_text(content)
        result=process_files([(str(retained),content)],db,config_dir,reprocess=True,arrivals={str(retained):stamp},arrival_basis='manual retry')
        outcome='Resolved' if not result['failed'] else 'Open'
        with connect(db) as connection:
            connection.execute('UPDATE dead_letters SET status=?,updated_at=?,last_run_id=? WHERE id=?',(outcome,now(),result['id'],identifier))
            connection.execute('UPDATE retry_attempts SET run_id=?,outcome=? WHERE id=?',(result['id'],outcome,attempt))
            # A failed retry's raw copy belongs to this same queue entry, not a second open item.
            connection.execute("UPDATE dead_letters SET status='Superseded' WHERE source=? AND id!=?",(str(retained),identifier))
        return result
    except Exception:
        with connect(db) as connection:
            connection.execute("UPDATE dead_letters SET status='Open',updated_at=? WHERE id=?",(now(),identifier))
            connection.execute("UPDATE retry_attempts SET outcome='Interrupted' WHERE id=?",(attempt,))
        raise


class FolderWatcher:
    def __init__(self,db=DB,config_dir=ROOT/'config',folder=None):
        self.db=db;self.config_dir=config_dir
        self.config=settings(db,config_dir).get('watcher',{})
        self.folder=Path(folder or ROOT/self.config.get('folder','data/inbox')).resolve()
        self.stop_event=threading.Event();self.thread=None;self.last_scan=None;self.last_error=None
        with connect(db) as connection:
            connection.execute("UPDATE inbox_files SET status='Pending' WHERE status='Processing' AND julianday(updated_at)<julianday('now','-5 minutes')")
            connection.execute("UPDATE dead_letters SET status='Open' WHERE status='Retrying' AND julianday(updated_at)<julianday('now','-5 minutes')")
            connection.execute("UPDATE retry_attempts SET outcome='Interrupted' WHERE outcome='Running' AND julianday(started_at)<julianday('now','-5 minutes')")
            row=connection.execute("SELECT value FROM settings WHERE name='watcher_enabled'").fetchone()
        self.enabled=(row[0]=='true') if row else self.config.get('enabled',True)

    def set_enabled(self,value):
        if not isinstance(value,bool):raise ValueError('enabled must be boolean')
        self.enabled=value
        with connect(self.db) as connection:
            connection.execute("INSERT OR REPLACE INTO settings VALUES('watcher_enabled',?)",(json.dumps(value),))

    def scan(self):
        if not self.enabled:return
        self.folder.mkdir(parents=True,exist_ok=True)
        stamp=now()
        for source in sorted(self.folder.rglob('*.json')):
            if not source.is_file():continue
            if any(source.resolve().is_relative_to((Path(self.db).parent/name).resolve()) for name in ['intake','retries','dead-letter','uploads']):continue
            # Read-only discovery. A changing file gets a fresh settling entry.
            try:content=source.read_text(errors='replace')
            except OSError:continue
            fingerprint=hashlib.sha256(content.encode()).hexdigest()
            identifier=digest({'source':str(source),'fingerprint':fingerprint})
            with connect(self.db) as connection:
                row=connection.execute('SELECT * FROM inbox_files WHERE id=?',(identifier,)).fetchone()
                if not row:
                    connection.execute("UPDATE inbox_files SET status='Superseded',updated_at=? WHERE source=? AND status='Settling'",(stamp,str(source)))
                    connection.execute('INSERT INTO inbox_files(id,source,fingerprint,seen_at,stable_since,status,updated_at) VALUES(?,?,?,?,?,?,?)',(identifier,str(source),fingerprint,stamp,stamp,'Settling',stamp))
                    row=connection.execute('SELECT * FROM inbox_files WHERE id=?',(identifier,)).fetchone()
                elif row['status']=='Superseded':
                    # A writer can revert to a previously seen partial payload.
                    # Settle it again rather than silently ignoring its final contents.
                    connection.execute("UPDATE inbox_files SET status='Superseded',updated_at=? WHERE source=? AND status='Settling'",(stamp,str(source)))
                    connection.execute("UPDATE inbox_files SET status='Settling',stable_since=?,updated_at=? WHERE id=?",(stamp,stamp,identifier))
                    continue
                if row['status']!='Settling':continue
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['stable_since'])).total_seconds()
                if age<float(self.config.get('settle_seconds',2)):continue
                retained=Path(self.db).parent/'intake'/identifier/source.name
                retained.parent.mkdir(parents=True,exist_ok=True)
                retained.write_text(content)
                connection.execute("UPDATE inbox_files SET status='Pending',retained_path=?,updated_at=? WHERE id=?",(str(retained),stamp,identifier))
        self.last_scan=stamp

    def process_pending(self):
        if not self.enabled or not PROCESS_LOCK.acquire(blocking=False):return
        try:
            with connect(self.db) as connection:
                connection.execute('BEGIN IMMEDIATE')
                connection.execute("UPDATE inbox_files SET status='Pending' WHERE status='Processing' AND julianday(updated_at)<julianday('now','-5 minutes')")
                row=connection.execute("SELECT * FROM inbox_files WHERE status='Pending' ORDER BY seen_at LIMIT 1").fetchone()
                if not row:return
                connection.execute("UPDATE inbox_files SET status='Processing',updated_at=? WHERE id=?",(now(),row['id']))
            try:
                retained=Path(row['retained_path'])
                content=retained.read_text(errors='replace')
                result=process_files([(str(retained),content)],self.db,self.config_dir,arrivals={str(retained):row['seen_at']},arrival_basis='folder discovery')
                status='Failed' if result['failed'] else 'Processed'
                with connect(self.db) as connection:
                    connection.execute('UPDATE inbox_files SET status=?,run_id=?,reason=?,updated_at=? WHERE id=?',(status,result['id'],'See dead-letter queue' if result['failed'] else None,now(),row['id']))
            except Exception as exc:
                with connect(self.db) as connection:
                    connection.execute("UPDATE inbox_files SET status='Pending',reason=?,updated_at=? WHERE id=?",(type(exc).__name__,now(),row['id']))
                raise
        finally:PROCESS_LOCK.release()

    def tick(self):
        self.scan();self.process_pending()
        evaluate_health(self.db,self.config_dir)

    def run(self):
        while not self.stop_event.is_set():
            try:self.tick();self.last_error=None
            except Exception as exc:
                self.last_error=type(exc).__name__+': '+str(exc)
            self.stop_event.wait(max(.1,float(self.config.get('poll_seconds',2))))

    def start(self):
        self.thread=threading.Thread(target=self.run,name='veritas-intake',daemon=True);self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)

    def state(self):
        return {'enabled':self.enabled,'folder':str(self.folder),'poll_seconds':self.config.get('poll_seconds',2),'settle_seconds':self.config.get('settle_seconds',2),'last_scan':self.last_scan,'last_error':self.last_error}


def health(db=DB,config_dir=ROOT/'config'):
    monitoring=settings(db,config_dir).get('monitoring',{})
    window=float(monitoring.get('window_seconds',3600));current=datetime.now(timezone.utc)
    with connect(db) as connection:
        files=[dict(row) for row in connection.execute('SELECT * FROM files') if (current-datetime.fromisoformat(row['ingested_at'])).total_seconds()<=window]
        waiting=[dict(row) for row in connection.execute("SELECT * FROM inbox_files WHERE status IN ('Settling','Pending','Processing')")]
    latencies=sorted(row['latency_seconds'] for row in files if row['latency_seconds'] is not None and row['status']=='Processed')
    completed=sum(row['status']=='Processed' for row in files)
    failed=sum(row['status']=='Failed' for row in files)
    return {'window_seconds':window,'file_attempts':len(files),'processed_files':completed,'failed_files':failed,'error_rate':failed/len(files) if files else 0,'throughput_files_per_second':completed/window,'p95_file_latency_seconds':latencies[max(0,math.ceil(.95*len(latencies))-1)] if latencies else None,'oldest_pending_seconds':max([max(0,(current-datetime.fromisoformat(row['seen_at'])).total_seconds()) for row in waiting] or [0]),'pending_files':len(waiting),'latency_basis':'Local discovery to transaction completion; not a cloud SLA measurement'}


def evaluate_health(db=DB,config_dir=ROOT/'config'):
    metrics=health(db,config_dir);limits=settings(db,config_dir).get('monitoring',{})
    conditions={
        'processing_error_rate':(metrics['file_attempts']>=limits.get('minimum_files',1) and metrics['error_rate']>limits.get('error_rate_threshold',.01),f"Processing error rate {metrics['error_rate']*100:.2f}% over {metrics['file_attempts']} file attempts"),
        'processing_lag':(metrics['oldest_pending_seconds']>limits.get('lag_seconds',900),f"Oldest waiting file: {metrics['oldest_pending_seconds']:.1f} seconds"),
        'processing_latency':((metrics['p95_file_latency_seconds'] or 0)>limits.get('lag_seconds',900),f"Observed local p95 file latency: {metrics['p95_file_latency_seconds']} seconds")}
    events=[]
    with connect(db) as connection:
        connection.execute('BEGIN IMMEDIATE')
        for code,(active,message) in conditions.items():
            row=connection.execute('SELECT * FROM alerts WHERE code=?',(code,)).fetchone()
            status='Active' if active else 'Resolved'
            stamp=now()
            if not row and not active:continue
            if not row or row['status']!=status:
                opened=stamp if active else row['opened_at']
                connection.execute('INSERT OR REPLACE INTO alerts VALUES(?,?,?,?,?,?)',(code,status,message,opened,stamp,None))
                connection.execute('INSERT INTO alert_events(code,status,message,created_at) VALUES(?,?,?,?)',(code,status,message,stamp))
                events.append({'code':code,'status':status,'message':message,'created_at':stamp})
            else:
                connection.execute('UPDATE alerts SET message=?,updated_at=? WHERE code=?',(message,stamp,code))
        alerts=[dict(row) for row in connection.execute('SELECT * FROM alerts ORDER BY updated_at DESC')]
    if events:
        destination=Path(db).parent/'alerts.jsonl'
        with destination.open('a') as output:
            for event in events:output.write(json.dumps(event)+'\n')
    return metrics,alerts


def acknowledge_alert(code,db=DB):
    with connect(db) as connection:
        if not connection.execute('SELECT 1 FROM alerts WHERE code=?',(code,)).fetchone():raise ValueError('Alert not found')
        connection.execute('UPDATE alerts SET acknowledged_at=? WHERE code=?',(now(),code))


def operations_snapshot(db=DB,config_dir=ROOT/'config',watcher=None):
    import_legacy_errors(db)
    metrics,alerts=evaluate_health(db,config_dir)
    with connect(db) as connection:
        errors=[dict(row) for row in connection.execute("SELECT id,source,reason,status,retry_count,created_at,updated_at,last_run_id FROM dead_letters WHERE status!='Superseded' ORDER BY updated_at DESC")]
        queue=[dict(row) for row in connection.execute('SELECT id,source,status,reason,seen_at,updated_at FROM inbox_files ORDER BY seen_at DESC LIMIT 100')]
        events=[dict(row) for row in connection.execute('SELECT code,status,message,created_at FROM alert_events ORDER BY id DESC LIMIT 30')]
    return {'health':metrics,'alerts':alerts,'alert_events':events,'dead_letters':errors,'intake':queue,'watcher':watcher.state() if watcher else {'enabled':False,'folder':str(ROOT/'data/inbox'),'poll_seconds':None,'last_error':None,'last_scan':None}}
