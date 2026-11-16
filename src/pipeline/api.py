"""Loopback-only local API; Next.js proxies requests without exposing filesystem access."""
import csv
import io
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from .engine import DB, ROOT, now, process_files, read_folder, configuration
from .store import connect
from .auth import identity, Unauthorized
from . import ai, cloud

from .operations import PROCESS_LOCK as LOCK, FolderWatcher, operations_snapshot, retry_dead_letter, acknowledge_alert
WATCHER = None


def dashboard(day=None):
    from .reporting import dashboard as report
    return report(DB, day)


def interval_text(interval):
    low, high = interval['low'], interval['high']
    if low is None:
        return ('<=' if interval['high_inclusive'] else '<')+str(high)
    if high is None:
        return ('>=' if interval['low_inclusive'] else '>')+str(low)
    return f"{'[' if interval['low_inclusive'] else '('}{low}, {high}{']' if interval['high_inclusive'] else ')'}"


def export_csv():
    names = list(configuration()['tests']['tests'])
    fields = ['record_id','document_id','clinic','record_type']+[n+s for n in names for s in ['', '_Result','_Range','_Unit','_Analytics']]
    text = io.StringIO()
    writer = csv.DictWriter(text,fieldnames=fields)
    writer.writeheader()
    with connect(DB) as c:
        for row in c.execute('SELECT output_json FROM records'):
            r = json.loads(row[0])
            grouped = {}
            for o in r['observations']:
                if o['test_name_canonical']:
                    grouped.setdefault(o['test_name_canonical'],[]).append(o)
            # One row per occurrence index; never silently overwrite repeated tests.
            for i in range(max([len(g) for g in grouped.values()] or [1])):
                values = {'record_id':r['id'],'document_id':r['document_id'],'clinic':r['clinic'],'record_type':r['record_type']}
                for n,g in grouped.items():
                    if i<len(g):
                        o = g[i]
                        values.update({n:n,n+'_Result':o['result_value'] if o['result_value'] is not None and o['unit_canonical'] is not None else interval_text(o['result_interval']) if o.get('result_interval') else o['result_text'],n+'_Range':interval_text({'low':o['range_low'],'high':o['range_high'],'low_inclusive':o.get('range_low_inclusive',True),'high_inclusive':o.get('range_high_inclusive',True)}) if o['range_low'] is not None or o['range_high'] is not None else o['range_text'],n+'_Unit':o['unit_canonical'] or o['unit_original'],n+'_Analytics':o['analytics']})
                # Prevent spreadsheet formula execution from source-controlled text.
                writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in values.items()})
    return text.getvalue()


class Handler(BaseHTTPRequestHandler):
    def send(self,value,status=200,content_type='application/json'):
        body = (json.dumps(value) if content_type=='application/json' else value).encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path=='/api/session':
            import os
            return self.send({'required':os.getenv('VERITAS_REQUIRE_AUTH','false').lower()=='true',
                              'firebase':{'apiKey':os.getenv('FIREBASE_WEB_API_KEY',''), 'projectId':os.getenv('FIREBASE_PROJECT_ID',''),
                                          'authDomain':os.getenv('FIREBASE_AUTH_DOMAIN',''), 'appId':os.getenv('FIREBASE_APP_ID','')}})
        if url.path=='/api/mappings':
            return self.send(ai.snapshot(DB))
        if url.path=='/api/cloud':
            return self.send(cloud.snapshot(DB))
        if url.path=='/api/dashboard':
            try:
                return self.send(dashboard(parse_qs(url.query).get('day',[None])[0]))
            except ValueError as exc:
                return self.send({'error':str(exc)},400)
        if url.path=='/api/operations':
            return self.send(operations_snapshot(DB,watcher=WATCHER))
        if url.path=='/api/dead-letter':
            identifier=parse_qs(url.query).get('id',[''])[0]
            with connect(DB) as c:
                row=c.execute('SELECT * FROM dead_letters WHERE id=?',(identifier,)).fetchone()
            return self.send(dict(row) if row else {'error':'Dead-letter entry not found'},200 if row else 404)
        if url.path=='/api/record':
            rid = parse_qs(url.query).get('id',[''])[0]
            with connect(DB) as c:
                r = c.execute('SELECT * FROM records WHERE id=?',(rid,)).fetchone()
                versions = [dict(v) for v in c.execute('SELECT config_version,archived_at,output_json,review_json FROM record_versions WHERE record_id=? ORDER BY id DESC',(rid,))]
                for version in versions:
                    version['output'] = json.loads(version.pop('output_json'))
                    version['review'] = json.loads(version.pop('review_json') or 'null')
            if not r:return self.send({'error':'Record not found'},404)
            detail={'raw':json.loads(r['raw_json']),'output':json.loads(r['output_json']),'source':r['source_file'],'ingested_at':r['ingested_at'],'versions':versions}
            if parse_qs(url.query).get('mask')==['1']:
                from .privacy import masked_record
                detail=masked_record(detail)
            return self.send(detail)
        if url.path=='/api/export':
            return self.send(export_csv(),content_type='text/csv')
        if url.path=='/metrics':
            from .operations import health
            metrics=health(DB)
            d=dashboard()
            lines=[f'veritas_observations{{classification="{key}"}} {value}' for key,value in d['analytics'].items()]
            lines += [f'veritas_{key} {value}' for key,value in metrics.items() if isinstance(value,(int,float))]
            lines += [f'veritas_records {len(d["records"])}', f'veritas_name_resolution_ratio {d["resolved_tests"]/max(d["total_tests"],1)}']
            return self.send('\n'.join(lines)+'\n',content_type='text/plain')
        self.send({'error':'Not found'},404)

    def do_POST(self):
        try:
            actor = identity(self.headers.get('Authorization'))
        except Unauthorized as exc:
            return self.send({'error':str(exc)},401)
        if self.headers.get('Origin') not in [None, 'http://127.0.0.1:3000', 'http://localhost:3000']:
            return self.send({'error':'Origin rejected'},403)
        length = int(self.headers.get('Content-Length','0'))
        if length>10_000_000:
            return self.send({'error':'Upload limit is 10 MB per request'},413)
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(body,dict):raise ValueError('Request body must be an object')
            if self.path=='/api/mappings':
                if body.get('action')=='suggest':
                    if body.get('labels_only') is not True:
                        raise ValueError('Confirm that the input contains a test label only, without patient data.')
                    return self.send(ai.suggest(body.get('label'),DB,configuration()['tests'],actor))
                return self.send(ai.decide(body.get('id'),body.get('decision'),DB,configuration()['tests'],actor))
            if self.path=='/api/cloud':
                if not LOCK.acquire(blocking=False):
                    return self.send({'error':'Processing already in progress'},409)
                try:
                    return self.send(cloud.sync(retry_failed=body.get('retry_failed') is True))
                finally:
                    LOCK.release()
            if self.path=='/api/operations':
                if body.get('action')=='watcher':
                    if WATCHER is None:raise ValueError('Folder watcher is unavailable')
                    WATCHER.set_enabled(body.get('enabled'))
                    return self.send(WATCHER.state())
                if body.get('action')=='acknowledge':
                    acknowledge_alert(body.get('code'),DB)
                    return self.send({'ok':True})
                raise ValueError('Unknown operation')
            if self.path=='/api/review':
                if body.get('status') not in ['Open','Reviewed']:
                    raise ValueError('Invalid review status')
                with connect(DB) as c:
                    if not c.execute('SELECT 1 FROM records WHERE id=?',(body.get('id'),)).fetchone():
                        return self.send({'error':'Record not found'},404)
                    c.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?)',(body['id'],body['status'],now()))
                return self.send({'ok':True})
            if self.path!='/api/process':
                return self.send({'error':'Not found'},404)
            if not LOCK.acquire(blocking=False):
                return self.send({'error':'Processing already in progress'},409)
            try:
                if body.get('mode')=='retry':
                    return self.send(retry_dead_letter(body.get('id'),body.get('content'),DB))
                if body.get('mode')=='samples':
                    files = read_folder(ROOT/'sample-data')
                elif body.get('mode')=='stored':
                    if body.get('reprocess') is not True:
                        raise ValueError('Stored replay requires explicit reprocess=true')
                    with connect(DB) as c:
                        sources = [row[0] for row in c.execute('SELECT DISTINCT source_file FROM records')]
                    from pathlib import Path
                    if any(not Path(source).is_file() for source in sources):
                        raise ValueError('A retained source file is unavailable; restore it before replay')
                    files = [(source,Path(source).read_text(errors='replace')) for source in sources]
                else:
                    uploads = body.get('files',[])
                    if not isinstance(uploads,list) or not uploads or len(uploads)>50:
                        raise ValueError('Upload 1–50 JSON files')
                    files = []
                    for f in uploads:
                        if not isinstance(f.get('name'),str) or not isinstance(f.get('content'),str):
                            raise ValueError('Invalid upload')
                        name = __import__('pathlib').Path(f['name']).name
                        if not name.lower().endswith('.json'):
                            raise ValueError('Only JSON files are accepted')
                        # Persist uploads for audit and later CLI replay.
                        from .engine import digest
                        target = ROOT/'data/uploads'/digest(f['content'])/name
                        target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_text(f['content'])
                        files.append((str(target),f['content']))
                if not isinstance(body.get('reprocess',False),bool):
                    raise ValueError('reprocess must be a boolean')
                result = process_files(files,reprocess=body.get('reprocess',False))
                return self.send(result)
            finally:
                LOCK.release()
        except (ValueError,KeyError,TypeError) as exc:
            self.send({'error':str(exc)},400)
        except Exception:
            logging.exception('Unhandled API failure')
            self.send({'error':'Processing failed. Inspect backend logs.'},500)


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    connect(DB).close()
    print('Veritas API listening on http://127.0.0.1:8000',flush=True)
    WATCHER=FolderWatcher()
    WATCHER.start()
    cloud_watcher=cloud.CloudWatcher()
    cloud_watcher.start()
    server = ThreadingHTTPServer(('127.0.0.1',8000),Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        WATCHER.close()
        cloud_watcher.close()
