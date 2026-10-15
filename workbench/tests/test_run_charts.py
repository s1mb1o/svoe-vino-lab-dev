"""Check chart cohorts, representative runs, time axes, and missing metrics offline."""
from pathlib import Path
import shutil
import subprocess
import unittest

PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/run_charts.html"
SOURCE = PAGE.read_text(encoding="utf-8")
MODEL = SOURCE[SOURCE.index("const RunCharts ="):
               SOURCE.index("/* Page state uses")]
SETUP = r"""
const assert = require('assert');
const run = (id, configuration, started, extra = {}) => ({
  id, configuration, started, set:'my', has_metrics:true, queries:100,
  recall_at_1:.7, recall_at_5:.8, recall_at_10:.9, f1_at_1:.6, f1_at_5:.8,
  within_sla_share:.9, latency_median:200, ...extra
});
const rows = [
  run('old-a','a','2026-10-01T10:00:00+0300',{use_cache:false}),
  run('new-a','a','2026-10-07T10:00:00+0300',{use_cache:true}),
  run('only-b','b','2026-10-02T10:00:00Z',{use_cache:null})
];
const ids = rows => rows.map(r => r.id);
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class RunChartsTest(unittest.TestCase):
    def run_js(self, check):
        result = subprocess.run(["node", "-e", SETUP + MODEL + check],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_testset_scope_and_non_comparable_runs(self):
        self.run_js("""
const extras = [
  {...rows[0],id:'other-set',set:'other'},
  {...rows[0],id:'drawer',query_scope:'drawer'},
  {...rows[0],id:'dry',dry_run:true},
  {...rows[0],id:'unscored',has_metrics:false},
  {...rows[0],id:'subset',subset:'positive'},
  {...rows[0],id:'unnamed',configuration:null}
];
assert.deepStrictEqual(ids(RunCharts.eligible([...rows,...extras],'my')),ids(rows));
assert.equal(RunCharts.eligible(rows,'absent').length,0);
assert.deepStrictEqual(ids(RunCharts.eligible([...rows,...extras],'other')),['other-set']);
""")

    def test_cache_filters_keep_unknown_separate(self):
        self.run_js("""
assert.deepStrictEqual(ids(RunCharts.eligible(rows,'my','on')),['new-a']);
assert.deepStrictEqual(ids(RunCharts.eligible(rows,'my','off')),['old-a']);
assert.deepStrictEqual(ids(RunCharts.eligible(rows,'my','unknown')),['only-b']);
assert.deepStrictEqual(ids(RunCharts.eligible(rows,'my','all')),ids(rows));
""")

    def test_newest_run_choices_and_selection_are_independent_of_file_order(self):
        self.run_js("""
const before=JSON.stringify(rows);
const groups=RunCharts.group([rows[2],rows[0],rows[1]]);
assert.deepStrictEqual([...groups.keys()],['a','b']);
assert.deepStrictEqual(ids(RunCharts.comparison(groups,new Set(['a','b']),new Map())),['new-a','only-b']);
assert.deepStrictEqual(ids(RunCharts.comparison(groups,new Set(['a']),new Map([['a','old-a']]))),['old-a']);
assert.deepStrictEqual(ids(RunCharts.comparison(groups,new Set(['a']),new Map([['a','gone']]))),['new-a']);
assert.equal(RunCharts.comparison(groups,new Set(),new Map()).length,0);
assert.equal(JSON.stringify(rows),before);
""")

    def test_timeline_uses_actual_time_offsets_and_excludes_undated_runs(self):
        self.run_js("""
const input = [
 run('a-utc','a','2026-10-01T08:00:00Z'),
 run('z-moscow','a','2026-10-01T10:00:00+0300'),
 run('no-date','a','not-a-date'),...rows
];
const out=RunCharts.timeline(input,'a');
assert.deepStrictEqual(ids(out),['old-a','z-moscow','a-utc','new-a']);
assert.equal(RunCharts.epoch(input[0])-RunCharts.epoch(input[1]),3600000);
assert.equal(RunCharts.timeline(input,'missing').length,0);
const group=RunCharts.group([run('undated','a',''),rows[0]]);
assert.equal(group.get('a')[0].id,'old-a');
""")

    def test_zero_is_data_and_absent_or_invalid_metrics_are_not_zero(self):
        self.run_js("""
const m=RunCharts.metric('recall_at_10');
assert.equal(RunCharts.value({recall_at_10:0},m),0);
assert.equal(RunCharts.format(0,m),'0.0%');
for(const v of [null,undefined,NaN,Infinity,'0.5',-1,1.1])
 assert.strictEqual(RunCharts.value({recall_at_10:v},m),null);
assert.equal(RunCharts.format(null,m),'—');
assert.equal(RunCharts.format(.7,RunCharts.metric('f1_at_1')),'0.700');
const missing=RunCharts.plots([run('x','a','2026-10-01',{recall_at_10:null})],'pipelines','recall_at_10');
assert(missing.includes('not recorded'));assert(!missing.includes('<svg'));
""")

    def test_time_series_breaks_at_missing_values_and_single_points_are_finite(self):
        self.run_js("""
const sample=[rows[0],run('gap','a','2026-10-03',{recall_at_1:null}),rows[1]];
const html=RunCharts.plots(sample,'history','recall_at_1');
assert.equal((html.match(/<circle /g)||[]).length,2);
const path=html.match(/<path d="([^"]*)"/)[1];
assert.equal((path.match(/M/g)||[]).length,2);assert(!path.includes('L'));
const single=RunCharts.plots([rows[0]],'history','overview');
assert.equal((single.match(/<section /g)||[]).length,4);
assert(!single.includes('NaN'));assert(!single.includes('Infinity'));
const equal=RunCharts.plots([rows[0],{...rows[0],id:'same-time'}],'history','latency_median');
assert(!equal.includes('NaN'));assert.equal((equal.match(/<circle /g)||[]).length,2);
""")

    def test_chart_links_are_escaped_and_axes_keep_units_separate(self):
        self.run_js("""
const malicious=run('id/<bad>','<img src=x onerror=alert(1)>','2026-10-01',{latency_median:0});
const html=RunCharts.plots([malicious],'pipelines','overview');
assert(!html.includes('<img'));assert(html.includes('&lt;img'));
assert(html.includes('/runs#id%2F%3Cbad%3E'));
assert(html.includes('100.0%'));assert(html.includes('1.000'));assert(html.includes('0 ms'));
assert.equal((html.match(/<section /g)||[]).length,4);
const zero=RunCharts.plots([{...rows[0],false_match_at_1:0}],'pipelines','false_match_at_1');
assert(!zero.includes('NaN'));assert(zero.includes('Lower is better'));
""")


if __name__ == "__main__":
    unittest.main()
