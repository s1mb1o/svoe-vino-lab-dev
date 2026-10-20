"""Test gates and accepted-alternative scoring without a connected phone."""
import json
from pathlib import Path
import tempfile
import unittest

from audit_results import audit
from profiles import digest
from run_comparison import prerequisite,paired
from run_device import pilot_queries


class GateTest(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.pack=self.root/'pack';self.pack.mkdir()
        self.save(self.pack/'manifest.json',dict(slugs=['a','alternative','b']))
    def save(self,path,value):path.write_text(json.dumps(value))
    def fixture(self):
        run=self.root/'run';run.mkdir()
        queries=[dict(query_id='q1',image_sha256='sha1',truth=['a','alternative']),
                 dict(query_id='q2',image_sha256='sha2',truth=['b'])]
        candidates=[dict(slug='alternative',score=.8)]
        predictions=[dict(query_id='q1',image_sha256='sha1',predicted_slug='alternative',candidates=candidates),
                     dict(query_id='q2',image_sha256='sha2',predicted_slug=None,candidates=[])]
        responses=[dict(request_number=1,query_id='q1',image_sha256='sha1',status=200,client_ms=200,
            response=dict(reranking=False,barcode=False,variants=[dict(variant=1,candidates=candidates)])),
            dict(request_number=2,query_id='q2',image_sha256='sha2',status=400,client_ms=100,response={})]
        metadata=dict(mode='pilot',condition=dict(name='base-p224-standard',number=1),reranking=False,barcode=False,
            pack_manifest_sha256=digest(self.pack/'manifest.json'),query_file_sha256='frozen',complete=True,
            initial_pid=1,final_pid=1,maximum_thermal_status=2,peak_sampled_pss_kib=100,cleanup_errors=[])
        self.save(run/'queries.json',queries);self.save(run/'run.json',metadata)
        for name,rows in (('predictions',predictions),('responses',responses)):
            (run/(name+'.jsonl')).write_text('\n'.join(map(json.dumps,rows))+'\n')
        return run
    def test_alternative_is_accepted_and_failure_stays_in_denominator(self):
        result=audit(self.fixture(),self.pack)
        self.assertEqual(result['top_k_percent'],{'1':50.,'5':50.,'10':50.})
        self.assertEqual(result['errors'],1);self.assertTrue(result['smoothness_passed'])
    def test_partial_run_has_no_complete_score(self):
        run=self.fixture();row=json.loads((run/'run.json').read_text());row['complete']=False
        self.save(run/'run.json',row)
        with self.assertRaises(ValueError):audit(run,self.pack)
    def test_missing_failure_is_rejected(self):
        run=self.fixture();path=run/'predictions.jsonl';path.write_text(path.read_text().splitlines()[0]+'\n')
        with self.assertRaises(ValueError):audit(run,self.pack)
    def test_changed_pack_is_rejected(self):
        run=self.fixture();self.save(self.pack/'manifest.json',dict(slugs=['changed']))
        with self.assertRaises(ValueError):audit(run,self.pack)
    def test_reranking_is_rejected(self):
        run=self.fixture();row=json.loads((run/'run.json').read_text());row['reranking']=True
        self.save(run/'run.json',row)
        with self.assertRaises(ValueError):audit(run,self.pack)
    def test_slow_run_does_not_pass_pilot_gate(self):
        run=self.fixture();path=run/'responses.jsonl';rows=list(map(json.loads,path.read_text().splitlines()))
        rows[0]['client_ms']=12000;path.write_text('\n'.join(map(json.dumps,rows))+'\n')
        self.assertFalse(audit(run,self.pack)['smoothness_passed'])
    def test_preceding_run_is_read_only_and_must_finish(self):
        self.assertFalse(prerequisite(self.root))
        self.save(self.root/'run.json',dict(complete=False))
        self.save(self.root/'independent-audit.json',dict(verification_passed=True,complete=False))
        self.save(self.root/'coordinator-cleanup.json',dict(runner_exit_code=0,audit_exit_code=0,switch_exit_code=0,final_pid=None))
        with self.assertRaises(RuntimeError):prerequisite(self.root)
    def test_only_successful_cleanup_releases_phone(self):
        self.save(self.root/'run.json',dict(complete=True))
        self.save(self.root/'independent-audit.json',dict(verification_passed=True,complete=True))
        cleanup=dict(runner_exit_code=0,audit_exit_code=0,switch_exit_code=0,final_pid=None)
        self.save(self.root/'coordinator-cleanup.json',cleanup);self.assertTrue(prerequisite(self.root))
        cleanup['final_pid']='12';self.save(self.root/'coordinator-cleanup.json',cleanup)
        with self.assertRaises(RuntimeError):prerequisite(self.root)
    def test_pilot_selection_does_not_read_truth(self):
        rows=[dict(image_sha256=str(i),truth=['anything']) for i in range(100)]
        first=pilot_queries(rows)
        for row in rows:row['truth']=['different']
        self.assertEqual([r['image_sha256'] for r in first],[r['image_sha256'] for r in pilot_queries(rows)])
        self.assertEqual(len({r['image_sha256'] for r in first}),30)
    def test_comparison_counts_paired_gains_and_regressions(self):
        common=dict(query_file_sha256='q',pack_manifest_sha256='p')
        a=dict(common,outcomes=dict(q1={'1':True},q2={'1':False}),top_k_percent={'1':50})
        b=dict(common,outcomes=dict(q1={'1':False},q2={'1':True}),top_k_percent={'1':50})
        result=paired({1:a,2:b})['1-to-2']
        self.assertEqual(result['gains'],['q2']);self.assertEqual(result['regressions'],['q1'])

    def test_p512_standard_custom_and_custom_budget_pairs_are_reported(self):
        common=dict(query_file_sha256='q',pack_manifest_sha256='p')
        baseline=dict(common,outcomes=dict(q1={'1':False}),top_k_percent={'1':0})
        custom=dict(common,outcomes=dict(q1={'1':True}),top_k_percent={'1':100})
        result=paired({1:baseline,2:custom,3:baseline,4:custom})
        self.assertEqual(len(result),6)
        self.assertEqual(result['3-to-4']['gains'],['q1'])
        self.assertEqual(result['2-to-4']['top1_gain_pp'],0)


if __name__=='__main__':unittest.main()
