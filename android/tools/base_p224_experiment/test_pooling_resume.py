"""Check prefix preservation and fail-closed continuation without a phone."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pooling_resume import restore_prefix,inventory
import test_runner
from audit_results import audit


class ResumeTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.source=self.root/'source';self.source.mkdir()
        self.out=self.root/'out';self.out.mkdir()
        self.condition=dict(number=8,name='DIS crop',budget=512,pooling='fractional-bg010',
                            segmenter='GPU',segmenter_model='DIS')
        self.queries=[dict(query_id='q'+str(i),image_sha256='sha'+str(i),image_path=str(i),truth=['a']) for i in range(3)]
        self.meta=dict(mode='full',condition=self.condition,package='isolated',serial='pixel',query_file_sha256='q',
            pack_manifest_sha256='p',pack_version='v',installed_apk_sha256='apk',assignments=3,reranking=False,barcode=False)
        original=dict(self.meta,complete=False,elapsed_s=10,requests=2,errors=0,initial_pid=42,cleanup_errors=['USB lost'])
        self.write('run.json',original);self.write('queries.json',self.queries)
        responses=[];predictions=[]
        for number,q in enumerate(self.queries[:2],1):
            candidates=[dict(slug='a',score=.8)]
            result=dict(variant=8,budget=512,pooling='fractional-bg010',timing_mode='independent',candidates=candidates,slug='a')
            answer=dict(image_sha256=q['image_sha256'],encoder_accelerator='GPU',segmenter_accelerator='GPU',
                dimension=768,pack_version='v',reranking=False,barcode=False,offline=True,encoder_passes=1,
                variants=[result],segmentation=dict(model='DIS'),latency_ms=9)
            responses.append(dict(request_number=number,query_id=q['query_id'],image_sha256=q['image_sha256'],
                status=200,accelerator='GPU',client_ms=10,response=answer))
            predictions.append(dict(query_id=q['query_id'],image_sha256=q['image_sha256'],image_path=q['image_path'],
                client_request_ms=10,pipeline_ms=9,timing_mode='independent',predicted_slug='a',candidates=candidates,error=None))
        for name,rows in [('responses',responses),('predictions',predictions),
                          ('received-responses',[dict(warmup=False,**r) for r in responses]),
                          ('telemetry',[dict(thermal_status=1,pss_kib=100)])]:self.write_lines(name+'.jsonl',rows)
    def write(self,name,row):(self.source/name).write_text(json.dumps(row))
    def write_lines(self,name,rows):(self.source/name).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    def restore(self):return restore_prefix(self.source,self.out,self.queries,self.meta,dict(slugs=['a']),2)
    def test_preserves_raw_prefix_and_original_metadata(self):
        before=inventory(self.source);record,rows,samples=self.restore()
        self.assertEqual(record['next_assignment'],3);self.assertEqual(len(rows),2)
        self.assertEqual(record['original_run']['cleanup_errors'],['USB lost'])
        self.assertEqual(before,inventory(self.source))
        for name in ('responses.jsonl','predictions.jsonl'):
            self.assertEqual((self.source/name).read_bytes(),(self.out/name).read_bytes())
            self.assertEqual((self.source/name).read_bytes(),(self.out/'inherited-attempt'/name).read_bytes())
    def test_rejects_changed_identity_fields(self):
        for field in self.meta:
            with self.subTest(field=field):
                changed=copy.deepcopy(self.meta);changed[field]='changed'
                with self.assertRaises(ValueError):restore_prefix(self.source,self.out,self.queries,changed,dict(slugs=['a']),2)
    def test_rejects_changed_truth(self):
        self.queries[0]['truth']=['changed']
        with self.assertRaises(ValueError):self.restore()
    def test_rejects_changed_order(self):
        path=self.source/'responses.jsonl';rows=list(map(json.loads,path.read_text().splitlines()))
        self.write_lines(path.name,list(reversed(rows)))
        with self.assertRaises(ValueError):self.restore()
    def test_rejects_changed_candidates(self):
        path=self.source/'predictions.jsonl';rows=list(map(json.loads,path.read_text().splitlines()))
        rows[0]['candidates'][0]['score']=.4;self.write_lines(path.name,rows)
        with self.assertRaises(ValueError):self.restore()
    def test_rejects_partial_line(self):
        path=self.source/'responses.jsonl';path.write_bytes(path.read_bytes().rstrip(b'\n'))
        with self.assertRaises(ValueError):self.restore()
    def test_rejects_wrong_prefix_length(self):
        with self.assertRaises(ValueError):restore_prefix(self.source,self.out,self.queries,self.meta,dict(slugs=['a']),1)
    def test_rejects_received_but_unsaved_response(self):
        path=self.source/'received-responses.jsonl';rows=list(map(json.loads,path.read_text().splitlines()))
        self.write_lines(path.name,rows+[rows[-1]])
        with self.assertRaises(ValueError):self.restore()
    def test_rejects_missing_thermal_safety(self):
        self.write_lines('telemetry.jsonl',[dict(thermal_status=4)])
        with self.assertRaises(ValueError):self.restore()
    def test_resumed_quality_is_not_an_uninterrupted_stability_pass(self):
        fixture=test_runner.GateTest();fixture.setUp();self.addCleanup(fixture.doCleanups)
        run=fixture.fixture();meta=json.loads((run/'run.json').read_text());meta['resume']=dict(records=1)
        fixture.save(run/'run.json',meta);result=audit(run,fixture.pack)
        self.assertTrue(result['latency_targets_passed']);self.assertTrue(result['resumed'])
        self.assertFalse(result['smoothness_passed']);self.assertEqual(result['top_k_percent']['1'],50)


if __name__=='__main__':unittest.main()
