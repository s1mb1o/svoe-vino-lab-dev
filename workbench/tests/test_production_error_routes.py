import base64
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
import testset_fixture as FX
import production_error_routes as R
import lab_server

class QueueRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db,_=FX.make_database(Path(self.tmp.name));self.server=SimpleNamespace(db_path=self.db)
        buf=io.BytesIO();Image.new('RGB',(12,24),'red').save(buf,'PNG');self.data=buf.getvalue()
        self.record=dict(source='test',request_id='request',image_sha256=hashlib.sha256(self.data).hexdigest(),candidates=[dict(slug='wine-b',rank=1,score=.9)],feedback=dict(match=False),image_base64=base64.b64encode(self.data).decode())
    def tearDown(self):self.tmp.cleanup()
    def request(self,path='',body=None,method='POST'):
        return R.respond(self.server,method,'/api/production-errors'+path,lambda limit: json.dumps(body).encode() if body is not None else b'',lab_server.open_database)
    def test_page_and_list(self):
        self.assertEqual(self.request(method='GET')[0],200)
        self.assertEqual(R.respond(self.server,'GET','/production-errors',None,lab_server.open_database)[0],200)
    def test_head_answers_as_get(self):
        # The lab OpenAPI document promises GET status and headers for HEAD.
        self.request('/import',self.record)
        for path in ('','/image?source=test&request_id=request'):
            self.assertEqual(self.request(path,method='HEAD')[:3:2],self.request(path,method='GET')[:3:2])
        self.assertEqual(R.respond(self.server,'HEAD','/production-errors',None,lab_server.open_database)[0],200)
        self.assertEqual(self.request('/import',{},method='HEAD')[0],405)
    def test_import_review_publish_and_image(self):
        self.assertEqual(self.request('/import',self.record)[0],200)
        self.assertEqual(self.request('/image?source=test&request_id=request',method='GET')[1],self.data)
        self.assertEqual(self.request('/review',dict(source='test',request_id='request',identity='wine-a',purpose='benchmark',reviewer='owner',note='Read label'))[0],200)
        self.assertEqual(self.request('/publish',dict(source='test',request_id='request'))[0],200)
        with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('SELECT state FROM production_error').fetchone()[0],'published')
    def test_review_missing_identity_does_not_mean_absence(self):
        self.request('/import',self.record)
        self.assertEqual(self.request('/review',dict(source='test',request_id='request',purpose='benchmark',reviewer='owner',note='Read label'))[0],400)
    def test_bad_import_and_wrong_methods(self):
        self.assertEqual(self.request('/import',dict(self.record,image_base64='!bad!'))[0],400)
        self.assertEqual(self.request('/import',dict(self.record,image_sha256='0'*64))[0],400)
        self.assertEqual(self.request('/import',{},method='GET')[0],405)
    def test_failed_publish_rolls_back_new_test_set(self):
        self.request('/import',self.record)
        self.assertEqual(self.request('/publish',dict(source='test',request_id='request',set='new-set'))[0],400)
        with sqlite3.connect(self.db) as c:self.assertEqual(c.execute('SELECT count(*) FROM test_set').fetchone()[0],0)

if __name__=='__main__':unittest.main()
