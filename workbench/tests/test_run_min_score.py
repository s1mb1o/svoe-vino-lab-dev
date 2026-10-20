"""Check the Testset Run score default, overrides, audit, and repeat isolation."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import benchmark
import run_job
import run_jobs
from score_threshold import ScoreThreshold, checked
from test_run_jobs import Lab, REMOTE


class ScoreThresholdTest(unittest.TestCase):
    def backend(self, score, *extra):
        candidates = [{'slug': 'wine-a', 'score': score}, {'slug': 'wine-b', 'score': 0.5}]
        return SimpleNamespace(id='fixture', top_k=2, spec={'backend': 'fixture'},
                               ask=lambda path: (candidates, 12, 200, None, *extra))

    def test_default_validation_and_explicit_zero(self):
        self.assertEqual(checked(None), 0.7)
        self.assertEqual(checked(0), 0)
        for value in (True, '0.7', -1, 1.1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checked(value)

    def test_rejection_preserves_raw_candidates_trace_group_and_timing(self):
        inner = self.backend(0.69, {'stages': ['original']}, {'bottles': []})
        answer = ScoreThreshold(inner, 0.7).ask('image')
        self.assertEqual(answer[:4], ([], 12, 200, None))
        self.assertEqual(answer[4]['stages'], ['original'])
        self.assertEqual(answer[4]['score_threshold']['raw_candidates'][0]['score'], 0.69)
        self.assertEqual(answer[5], {'bottles': []})
        self.assertNotIn('min_score', inner.spec)

    def test_equality_override_disabled_and_missing_scores(self):
        self.assertEqual(ScoreThreshold(self.backend(0.7), 0.7).ask('image')[0][0]['slug'], 'wine-a')
        self.assertEqual(ScoreThreshold(self.backend(0.69), 0.6).ask('image')[0][0]['slug'], 'wine-a')
        self.assertEqual(ScoreThreshold(self.backend(0.69), 0).ask('image')[0][0]['slug'], 'wine-a')
        answer = ScoreThreshold(self.backend(None), 0.7).ask('image')
        self.assertEqual(answer[0][0]['slug'], 'wine-a')
        self.assertFalse(answer[4]['score_threshold']['applied'])

    def test_repeat_lookup_never_reuses_a_different_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name, backend in [('2026-10-20T100000', {}),
                                  ('2026-10-20T110000', {'min_score': 0.7}),
                                  ('2026-10-20T120000', {'min_score': 0.8})]:
                path = Path(temporary) / name
                path.mkdir()
                (path / 'results.jsonl').write_text('')
                (path / 'run.json').write_text(json.dumps({
                    'configuration': 'p', 'options': {'set': 'my'}, 'backend': backend}))
            self.assertTrue(benchmark.last_run(temporary, 'p', 'my', None, 0.7).endswith('110000'))
            self.assertTrue(benchmark.last_run(temporary, 'p', 'my', None, 0).endswith('100000'))
            self.assertIsNone(benchmark.last_run(temporary, 'p', 'my', None, 0.9))


class RunThresholdIntegrationTest(Lab):
    def test_api_passes_default_and_override_to_runner(self):
        for value, expected in [(None, 0.7), (0.85, 0.85), (0, 0)]:
            body = {'configuration': REMOTE, 'set': 'my'}
            if value is not None:
                body['min_score'] = value
            with mock.patch.object(run_jobs.subprocess, 'Popen') as popen:
                popen.return_value.pid = 99999999
                popen.return_value.poll.return_value = 0
                status, response = run_jobs.start(self.settings(), self.jobs, body, self.runs)
                self.assertEqual(status, 202, response)
                command = popen.call_args.args[0]
                self.assertEqual(float(command[command.index('--min-score') + 1]), expected)
                self.assertEqual(response['min_score'], expected)

    def test_api_refuses_invalid_threshold_before_launch(self):
        for value in (True, '0.7', -0.1, 1.1, float('nan')):
            with mock.patch.object(run_jobs.subprocess, 'Popen') as popen:
                status, _ = run_jobs.start(self.settings(), self.jobs,
                    {'configuration': REMOTE, 'set': 'my', 'min_score': value}, self.runs)
                self.assertEqual(status, 400)
                popen.assert_not_called()

    def test_runner_applies_default_before_scoring_and_records_it(self):
        backend = SimpleNamespace(id='fixture', top_k=1, spec={'id': 'fixture', 'backend': 'fixture'},
             ask=lambda path: ([{'slug': 'wine-a', 'score': 0.69}], 1, 200, None))
        with mock.patch.object(run_job, 'build', return_value=(backend, {}, None)):
            code, events = self.run_main(REMOTE, '--limit', '1', '--workers', '1')
        self.assertEqual(code, 0, events)
        run_id = next(row['run_id'] for row in events if row['event'] == 'run_dir')
        directory = Path(self.runs) / run_id
        self.assertEqual(json.loads((directory / 'run.json').read_text())['backend']['min_score'], 0.7)
        result = json.loads((directory / 'results.jsonl').read_text().splitlines()[0])
        self.assertEqual(result['candidates'], [])
        self.assertIsNone(result['predicted_slug'])
        self.assertEqual(result['outcome'], 'no_answer')
        self.assertEqual(result['trace']['score_threshold']['raw_candidates'][0]['score'], 0.69)


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class RunThresholdUiTest(unittest.TestCase):
    def run_js(self, check):
        source = (Path(__file__).resolve().parents[1] / "pipeline/pages/testset.html").read_text()
        logic = source[source.index("const RUN_ACTIVE ="):source.index("// Plan 88:")]
        setup = r'''
const assert = require('node:assert/strict');
const SET = 'official', nodes = new Map();
const $ = id => {if (!nodes.has(id)) nodes.set(id, {value:'',checked:false,disabled:false,
 textContent:'',setAttribute(){},focus(){}}); return nodes.get(id)};
const localStorage = {getItem(){return null},setItem(){}};
const document = {querySelectorAll:()=>[]};
const config = name => ({name,runnable:true,workers:1});
const pollRunJobs = ()=>{};
'''
        # Selection and transport are fixtures; execute real dialog validation and POST code.
        code = setup + logic + "\nrunChosen=()=>RUN_CONFIGS;runRenderList=()=>{};\n"
        code += "(async()=>{\n" + check + "\n})().catch(error=>{console.error(error);process.exitCode=1});"
        result = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_override_and_invalid_threshold_in_run_request(self):
        self.run_js(r'''
RUN_CONFIGS=[config('alpha')];RUN_QUERY_TOTAL=100;runRenderList(['alpha']);
const posts=[];runJson=async(url,options)=>posts.push(JSON.parse(options.body));
await startRun();assert.equal(posts[0].min_score,0.7);
$('#run-min-score').value='0.8';await startRun();assert.equal(posts[1].min_score,0.8);
$('#run-min-score').value='0';await startRun();assert.equal(posts[2].min_score,0);
$('#run-min-score').value='1.1';runSyncFields();assert.equal($('#run-start').disabled,true);
await startRun();assert.equal(posts.length,3);assert.match($('#run-error').textContent,/Minimum score/);
''')

    def test_opening_the_dialog_restores_the_default(self):
        self.run_js(r'''
runJson=async()=>({configurations:[config('alpha')],queries:100,set:'official'});
$('#run-min-score').value='0.9';await openRunDialog();
assert.equal($('#run-min-score').value,'0.7');
''')
