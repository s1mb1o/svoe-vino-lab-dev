import copy
import sys
from pathlib import Path
import unittest
import importlib.util
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import benchmark_competitor_experiments as bench


def row(truth=('a',),evidence='untriggered',score=.75,margin=.01):
    return dict(image_sha256='sha',label='positive' if truth else 'absent',truth=list(truth),
                cascade=dict(candidates=[dict(slug='a',score=score),dict(slug='b',score=score-margin)],evidence=evidence),
                base=dict(candidates=[]),arcface=dict(candidates=[]),split='test')


class ExperimentTests(unittest.TestCase):
    def test_archive_passes_executor_not_outer_matcher(self):
        path=bench.OUT/'run_archive.py'
        spec=importlib.util.spec_from_file_location('archive_adapter',path)
        adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
        executor=object();wrapper=SimpleNamespace(cascade=executor)
        self.assertIs(adapter.cascade_context(wrapper),executor)

    def test_trigger_uses_only_prediction_and_preserves_supported_evidence(self):
        positive=row();negative=row(())
        self.assertEqual(bench.trigger(positive),bench.trigger(negative))
        self.assertTrue(bench.trigger(positive))
        self.assertFalse(bench.trigger(row(evidence='supported')))
        self.assertFalse(bench.trigger(row(evidence='unique-code')))
        self.assertTrue(bench.trigger(row(evidence='unsure',margin=.1)))
        self.assertFalse(bench.trigger(row(score=.9,margin=.1)))

    def test_membership_is_not_identity_correctness(self):
        wrong=row(('b',));wrong['image_sha256']='wrong'
        absent=row(());absent['image_sha256']='absent'
        s=bench.gate_stats([wrong,absent],{'wrong':True,'absent':True})
        self.assertEqual(s['wrong_known'],1);self.assertEqual(s['accepted_absent'],1)
        self.assertEqual(s['correct'],0)
        self.assertEqual(len(bench.features(wrong)),6)

    def test_recall_keeps_failed_queries_in_denominator(self):
        good=row();bad=row();bad['cascade']['candidates']=[]
        self.assertEqual(bench.rank_stats([good,bad],'cascade')['recall']['1'],.5)

    def test_rrf_does_not_compare_model_score_scales(self):
        a=[dict(slug='a',score=.01),dict(slug='b',score=.009)]
        b=[dict(slug='b',score=999),dict(slug='c',score=998)]
        self.assertEqual(bench.rrf([a,b],[1,1])[0]['slug'],'b')
        alternate=copy.deepcopy(b);alternate[0]['score']=.1
        self.assertEqual(bench.rrf([a,b],[1,1]),bench.rrf([a,alternate],[1,1]))

    def test_logistic_standardization_is_training_only(self):
        x=[[0,0],[0,1],[1,0],[1,1]];y=[0,0,1,1]
        model=bench.fit_logistic(x,y)
        self.assertEqual(model['mean'],[.5,.5])
        before=copy.deepcopy(model)
        p=bench.probability(model,[[0,0],[1,0],[999,999]])
        self.assertGreater(p[1],p[0]);self.assertEqual(model,before)


if __name__=='__main__':unittest.main()
