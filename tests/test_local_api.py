"""Local uploads and review work without a sign-in token."""
import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from pipeline import api
from pipeline.engine import ROOT, process_files
from pipeline.store import connect


class LocalApiTests(unittest.TestCase):
    def test_upload_and_review_without_authorization(self):
        sample = (ROOT/'examples/clinic-v2.json').read_text()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            db = root/'api.sqlite'
            with patch.object(api, 'ROOT', root), patch.object(api, 'DB', db), patch.object(api, 'process_files', side_effect=lambda files, **kw: process_files(files, db=db, **kw)):
                server = ThreadingHTTPServer(('127.0.0.1', 0), api.Handler)
                thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
                thread.start()
                try:
                    def post(path, body):
                        request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/{path}', json.dumps(body).encode(), {'Content-Type':'application/json'})
                        with urllib.request.urlopen(request, timeout=10) as response:
                            return json.load(response)
                    result = post('process', {'files':[{'name':'synthetic.json','content':sample}]})
                    self.assertEqual(result['records'], 1)
                    with connect(db) as c:
                        identifier = c.execute('SELECT id FROM records').fetchone()[0]
                    self.assertTrue(post('review', {'id':identifier,'status':'Reviewed'})['ok'])
                    with connect(db) as c:
                        self.assertEqual(c.execute('SELECT status FROM reviews').fetchone()[0], 'Reviewed')
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=2)
