"""Check deferred recorded cut/model-input PNGs, tokens, and freshness without model calls."""
import base64
import os
from unittest import mock
from urllib.parse import parse_qs, urlsplit, urlencode
import test_run_steps as TS
import test_embedding_run as TE
import run_routes
import run_steps
import derive


class ArtifactTest(TS.StepsTest):
    def setUp(self):
        super().setUp()
        run_steps.VISUAL_INPUTS.clear()
        directory, rows = self.run_set()
        self.run_id = os.path.basename(directory)
        self.row = rows['green/01.png']
        self.args = (self.runs, self.lab.db_path, self.run_id, self.row['query_id'], TS.no_cards)

    def full(self):
        with mock.patch.object(run_steps.embedding_run, 'CachedSam3', TE.FakeSam3):
            return run_steps.steps_view(*self.args)

    def get(self, url):
        with mock.patch.object(run_steps.embedding_run, 'CachedSam3', TE.FakeSam3):
            return run_routes.artifact_view(self.runs, self.lab.db_path, parse_qs(urlsplit(url).query))

    def pairs(self):
        full = self.full()
        deferred = run_steps.defer_artifacts(self.full())
        return [(a,b) for s,t in zip(self.all_steps(full),self.all_steps(deferred))
                for a,b in zip(s['artifacts'],t['artifacts']) if a['src'].startswith('data:')]

    def test_every_deferred_artifact_keeps_exact_bytes_and_metadata(self):
        pairs = self.pairs()
        self.assertGreaterEqual(len(pairs), 2)
        for original, deferred in pairs:
            status, data, ctype, policy = self.get(deferred['src'])
            self.assertEqual((status,ctype,policy), (200,'image/png','no-store'))
            self.assertEqual(data,base64.b64decode(original['src'].split(',',1)[1]))
            self.assertEqual({k:v for k,v in deferred.items() if k not in ('src','deferred')},
                             {k:v for k,v in original.items() if k != 'src'})
        self.assertTrue(all(a['src'].startswith('/api/run-artifact?') and a['deferred'] for _,a in pairs))

    def test_tampered_unknown_and_invalid_artifact_parameters(self):
        url = self.pairs()[0][1]['src']
        values = parse_qs(urlsplit(url).query)
        for key,value,code in [('token','bad',404),('step','99999',404),('artifact','-1',400),
                               ('artifact','no',400),('id','../outside',404),('query','missing',404)]:
            changed={**values,key:[value]}
            self.assertEqual(self.get('/api/run-artifact?'+urlencode(changed,doseq=True))[0],code)

    def test_replaced_photo_invalidates_an_opened_url(self):
        url = self.pairs()[0][1]['src']
        photo=run_steps.Photo(self.lab.conn,self.lab.db_path,self.row)
        TE.query_photo('red').save(photo.path)
        self.assertEqual(self.get(url)[0],404)

    def test_photo_change_during_read_is_rejected(self):
        url = self.pairs()[0][1]['src']
        photo=run_steps.Photo(self.lab.conn,self.lab.db_path,self.row)
        original=derive.open_image
        def replace(path):
            image=original(path)
            if str(path)==photo.path:
                TE.query_photo('red').save(path)
            return image
        with mock.patch.object(derive,'open_image',side_effect=replace):
            self.assertEqual(self.get(url)[0],404)

    def test_the_http_handler_serves_artifact_get_and_head(self):
        import threading
        import urllib.request
        import lab_server
        url=self.pairs()[0][1]['src']
        expected=self.get(url)[1]
        server=lab_server.make_server(self.lab.db_path,port=0)
        server.runs_dir=self.runs
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with mock.patch.object(run_steps.embedding_run,'CachedSam3',TE.FakeSam3):
                for method in ('GET','HEAD'):
                    request=urllib.request.Request('http://127.0.0.1:%d%s'%(server.server_port,url),method=method)
                    with urllib.request.urlopen(request) as response:
                        self.assertEqual(response.status,200)
                        self.assertEqual(response.headers['Content-Type'],'image/png')
                        self.assertEqual(response.headers['Cache-Control'],'no-store')
                        self.assertEqual(int(response.headers['Content-Length']),len(expected))
                        self.assertEqual(response.read(),expected if method=='GET' else b'')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_changed_trace_comparison_rejects_the_old_artifact_url(self):
        original,deferred=next((a,b) for a,b in self.pairs() if a.get('check')=='same')
        expected=self.get(deferred['src'])[1]
        directory=os.path.join(self.runs,self.run_id)
        rows=TS.read_rows(directory)
        row=next(row for row in rows if row['query_id']==self.row['query_id'])
        for part in row['trace']['steps']:
            if part['id']=='view':part['out']['sha256']='different recorded input'
        TS.write_rows(directory,rows)
        self.assertEqual(self.get(deferred['src'])[0],404)
        current=run_steps.defer_artifacts(self.full())
        artifact=next(a for s in self.all_steps(current) for a in s['artifacts']
                      if a.get('caption')==original['caption'])
        self.assertEqual(artifact['check'],'changed')
        self.assertEqual(self.get(artifact['src'])[1],expected)

    def test_deleted_photo_rejects_the_opened_url(self):
        url=self.pairs()[0][1]['src']
        photo=run_steps.Photo(self.lab.conn,self.lab.db_path,self.row)
        os.unlink(photo.path)
        self.assertEqual(self.get(url)[0],404)
