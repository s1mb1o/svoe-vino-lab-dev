"""Check independent-photo scoring of the competitor follow-up."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import benchmark_competitor_followup as followup


class ScoringTest(unittest.TestCase):
    def row(self, sha, truth, candidates, label='positive', error=None):
        return dict(image_sha256=sha,truth=truth,label=label,
                    candidates=[dict(slug=s,score=.8) for s in candidates],
                    latency_ms=10,error=error)

    def test_unusable_acceptance_does_not_inflate_recall(self):
        rows=[self.row('1',['a'],['a']),self.row('2',[],['a'],'unusable')]
        result=followup.metrics(rows)
        self.assertEqual(result['known'],1)
        self.assertEqual(result['recall']['1'],1)
        self.assertEqual(result['accepted_unusable'],1)
        self.assertEqual(result['accepted_correct'],1)

    def test_query_errors_stay_in_the_known_denominator(self):
        result=followup.metrics([self.row('1',['a'],[],error='gateway failed')])
        self.assertEqual(result['known'],1)
        self.assertEqual(result['recall']['1'],0)
        self.assertEqual(result['errors'],1)

    def test_paired_counts_track_fixes_and_regressions(self):
        baseline={'1':self.row('1',['a'],['b']),'2':self.row('2',['b'],['b'])}
        result=followup.metrics([self.row('1',['a'],['a']),self.row('2',['b'],['a'])],baseline)
        self.assertEqual((result['wins'],result['losses']),(1,1))


if __name__=='__main__':unittest.main()
