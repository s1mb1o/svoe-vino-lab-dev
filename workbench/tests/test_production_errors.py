import hashlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX
import labdb
import production_errors as E
import testsets

class ProductionErrorsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db,_=FX.make_database(Path(self.tmp.name))
        self.conn=labdb.connect(self.db)
        buf=io.BytesIO();Image.new('RGB',(22,30),'red').save(buf,'PNG');self.data=buf.getvalue()
        self.record=dict(source='telegram',request_id='req-1',image_sha256=hashlib.sha256(self.data).hexdigest(),candidates=[dict(slug='wine-b',rank=1,score=.9)],feedback=dict(match=False,selected_slug=None,selected_rank=0,user_id='private'))
    def tearDown(self):self.conn.close();self.tmp.cleanup()
    def capture(self,request_id='req-1'):return E.capture(self.conn,dict(self.record,request_id=request_id),self.data)
    def review(self,purpose='benchmark',identity='wine-a'):return E.review(self.conn,'telegram','req-1',identity,purpose,'operator','Label inspected')
    def test_feedback_does_not_label_or_publish(self):
        self.capture();r=E.get(self.conn,'telegram','req-1');self.assertIsNone(r['identity']);self.assertEqual(r['state'],'pending');self.assertNotIn('user_id',r['feedback_json'])
        with self.assertRaises(E.ReviewError):E.publish(self.conn,'telegram','req-1')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM wine_image').fetchone()[0],0)
    def test_import_is_idempotent_and_hash_is_verified(self):
        self.capture();self.assertTrue(self.capture()['duplicate'])
        with self.assertRaises(E.ReviewError):E.capture(self.conn,dict(self.record,image_sha256='0'*64),self.data)
    def test_review_requires_identity_and_operator_evidence(self):
        self.capture()
        for identity,purpose in [('missing','benchmark'),(None,'reference')]:
            with self.assertRaises(E.ReviewError):self.review(purpose,identity)
        with self.assertRaises(E.ReviewError):E.review(self.conn,'telegram','req-1','wine-a','benchmark','','')
    def test_benchmark_publication_uses_reviewed_identity(self):
        self.capture();self.review();r=E.publish(self.conn,'telegram','req-1');self.assertTrue(r['destination'].startswith('testset:'))
        self.assertEqual(self.conn.execute('SELECT place,label FROM test_photo').fetchone(),('wine-a','positive'))
        self.assertTrue(E.publish(self.conn,'telegram','req-1')['duplicate'])
        with self.assertRaises(E.ReviewError):self.review()
    def test_explicit_no_match_uses_existing_null_positive_contract(self):
        self.capture();self.review(identity=None);E.publish(self.conn,'telegram','req-1')
        self.assertEqual(self.conn.execute('SELECT place,label FROM test_photo').fetchone(),('__null__','positive'))
    def test_reference_is_not_a_benchmark(self):
        self.capture();self.review('reference');r=E.publish(self.conn,'telegram','req-1');self.assertTrue(r['index_update_required'])
        self.assertEqual(self.conn.execute('SELECT wine_slug,match_method FROM wine_image').fetchone(),('wine-a','production-reviewed'))
        self.capture('req-2')
        with self.assertRaises(E.ReviewError):E.review(self.conn,'telegram','req-2','wine-a','benchmark','operator','Reviewed')
    def test_benchmark_hash_blocks_reference_even_in_another_set(self):
        self.capture();self.review();E.publish(self.conn,'telegram','req-1');self.capture('req-2')
        with self.assertRaises(E.ReviewError):E.review(self.conn,'telegram','req-2','wine-a','reference','operator','Reviewed')
    def test_reject_is_audited(self):
        self.capture();E.review(self.conn,'telegram','req-1',None,None,'operator','Unreadable',True)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM production_error_review').fetchone()[0],1)
        with self.assertRaises(E.ReviewError):E.publish(self.conn,'telegram','req-1')
    def test_conflicting_identity_on_same_hash_is_refused(self):
        self.capture();self.review();self.capture('req-2')
        with self.assertRaises(E.ReviewError):E.review(self.conn,'telegram','req-2','wine-b','benchmark','operator','Reviewed')

    def test_linked_derivative_cannot_cross_reference_benchmark_purposes(self):
        self.capture();original=self.record['image_sha256'];derived='f'*64
        self.conn.execute("INSERT INTO image(sha256,folder,extension,width,height) VALUES(?,'main','png',12,24)",(original,))
        self.conn.execute("INSERT INTO image(sha256,folder,extension,width,height) VALUES(?,'cropped','png',12,24)",(derived,))
        self.conn.execute("INSERT INTO image_derivative(source_sha256,kind,method,settings,sha256,box_left,box_top,box_right,box_bottom) VALUES(?,'package','crop','test',?,0,0,12,24)",(original,derived))
        self.conn.execute("INSERT INTO wine_image(wine_slug,image_type,sha256,source_name,match_method) VALUES('wine-a','main',?,'test','test')",(derived,))
        with self.assertRaises(E.ReviewError):self.review('benchmark')

if __name__=='__main__':unittest.main()
