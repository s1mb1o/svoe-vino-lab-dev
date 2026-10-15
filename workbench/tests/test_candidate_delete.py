"""Immediate candidate removal, with isolated data and the page's real JavaScript."""
import json
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_testset_routes as RT  # noqa: E402
import testsets as TS  # noqa: E402


class CandidateDeleteRoutesTest(unittest.TestCase):
    setUp = RT.TestsetRoutesTest.setUp
    tearDown = RT.TestsetRoutesTest.tearDown
    request = RT.TestsetRoutesTest.request
    post = RT.TestsetRoutesTest.post
    get_view = RT.TestsetRoutesTest.get_view

    def test_remove_updates_cached_view_and_preserves_shared_image(self):
        RT.IT.import_testset(self.db, "other", RT.FX.write_set(
            self.root, {"wine-a/01.jpg": RT.PHOTOS["wine-a/01.jpg"]},
            {"wine-a": {"01.jpg": {"comment": "other comment"}}}, name="other"),
            lambda m: None, self.schema)
        self.assertEqual(self.post("/api/testset-photo-tag", place="wine-a",
                                   file="01.jpg", tag="front")[0], 200)
        before = self.get_view()  # Warm the GET payload cache before the write.
        photo = next(r for r in before["rows"] if r["slug"] == "wine-a")["photos"][0]
        status, answer = self.post("/api/testset-photo-remove", place="wine-a", file="01.jpg")
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["counts"]["photos"], before["counts"]["photos"] - 1)
        after = self.get_view()
        wine = next(r for r in after["rows"] if r["slug"] == "wine-a")
        self.assertEqual(wine["photos"], [])
        self.assertTrue(wine["catalog_only"])
        self.assertIsNotNone(after["edited_at"])
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM test_photo_comment "
                                          "WHERE set_name = 'my' AND place = 'wine-a'")
                             .fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM wine_catalog").fetchone()[0], 3)
            self.assertEqual(conn.execute("SELECT text FROM test_photo_comment "
                                          "WHERE set_name = 'other'").fetchall(),
                             [("other comment",)])
        status, text = self.request("/api/testset?set=other")
        other = next(r for r in json.loads(text)["rows"] if r["slug"] == "wine-a")
        self.assertEqual((status, len(other["photos"])), (200, 1))
        self.assertEqual(other["photos"][0]["tags"], ["front"])
        with RT.urllib.request.urlopen(self.base + photo["url"]) as response:
            self.assertEqual(response.read(), RT.PHOTOS["wine-a/01.jpg"])

    def test_already_marked_photo_is_removed_and_old_mark_api_is_preserved(self):
        self.assertEqual(self.post("/api/testset-delete", place="wine-b", file="01.jpg",
                                   delete=True)[0], 200)
        before = self.get_view()
        self.assertEqual(before["counts"]["deleting"], 1)
        status, answer = self.post("/api/testset-photo-remove", place="wine-b", file="01.jpg")
        self.assertEqual((status, answer["counts"]["deleting"]), (200, 0))
        self.assertEqual(self.post("/api/testset-photo-remove", place="wine-b", file="01.jpg")
                         [0], 404)

    def test_invalid_requests_and_drawer_guard_leave_photos_in_place(self):
        before = self.get_view()["counts"]
        for place, file, expected in (("../wine-a", "01.jpg", 404),
                                      ("wine-a", "../01.jpg", 404),
                                      (None, "01.jpg", 400),
                                      ("wine-a", None, 400),
                                      ("wine-a", "missing.jpg", 404)):
            self.assertEqual(self.post("/api/testset-photo-remove", place=place, file=file)
                             [0], expected)
        self.assertEqual(self.request("/api/testset-photo-remove", "POST",
                                      {"set": "unknown", "place": "wine-a", "file": "01.jpg"})
                         [0], 404)
        self.assertEqual(self.post("/api/testset-drawer-remove", place="wine-a", file="01.jpg")
                         [0], 400)
        self.assertEqual(self.get_view()["counts"], before)

    def test_failure_rolls_back_photo_and_comments(self):
        before = self.get_view()
        with mock.patch.object(TS, "_edited", side_effect=sqlite3.OperationalError("test fault")):
            status, _ = self.post("/api/testset-photo-remove", place="wine-a", file="01.jpg")
        self.assertEqual(status, 503)
        self.assertEqual(self.get_view(), before)


PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/testset.html"
SOURCE = PAGE.read_text(encoding="utf-8")
REMOVE = SOURCE[SOURCE.index("const PHOTO_REMOVE_BUSY ="):
                SOURCE.index("async function removeDrawerPhoto(")]
MENU = SOURCE[SOURCE.index("function showCtxMenu("):SOURCE.index("function photoAtEvent(")]
SETUP = r"""
const assert=require('assert');
let SET='my', CMT_AT=null, LB=null, TOTAL=3, DRAWER_VIEW=null;
let ROWS=[{slug:'wine-a',photos:[{file:'a.jpg',conf:.8},{file:'b.jpg',conf:.9}]},
          {slug:'__drawer__',photos:[{file:'c.jpg',conf:null}]}], VIEW=ROWS;
let V={'wine-a':{'a.jpg':{delete:true},'b.jpg':{}},'__drawer__':{'c.jpg':{}}};
let requests=[],alerts=[],refreshed=[],opened=[],closed=0,statsCalls=0,drawerCalls=0;
const post=async(route,body)=>{requests.push([route,body]);return {ok:true}};
const flushComment=async()=>{};
const photoTotal=()=>ROWS.reduce((n,r)=>n+r.photos.length,0);
const isDrawerRow=r=>r.slug==='__drawer__';
const isSpecialRow=r=>['__drawer__','__null__'].includes(r.slug);
const refreshRow=r=>refreshed.push(r.slug);
const stats=()=>statsCalls++;
const renderDrawerResults=()=>drawerCalls++;
const lbPhoto=()=>{const r=VIEW[LB.wine],p=r.photos[LB.photo];
 return p?{slug:r.slug,file:p.file}:null};
const closeLightbox=()=>{closed++;LB=null};
const showLightbox=(wine,photo)=>{opened.push([wine,photo]);LB={wine,photo}};
const alert=text=>alerts.push(text);
const load=async()=>assert.fail('unexpected reload');
const controls=new Map();
const $=id=>{if(!controls.has(id))controls.set(id,{value:'',dataset:{},style:{},
 getBoundingClientRect:()=>({width:100,height:100})});return controls.get(id)};
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required")
class CandidateDeletePageTest(unittest.TestCase):
    def run_js(self, check, setup=SETUP, source=REMOVE):
        result = subprocess.run(["node", "-e", setup + source +
                                 "\n(async()=>{\n" + check +
                                 "\n})().catch(e=>{console.error(e);process.exitCode=1});"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_delete_removes_only_selected_photo_and_updates_counts(self):
        self.run_js("""
await removePhoto('wine-a','a.jpg');
assert.deepEqual(requests,[['/api/testset-photo-remove',{set:'my',place:'wine-a',file:'a.jpg'}]]);
assert.deepEqual(ROWS[0].photos.map(p=>p.file),['b.jpg']);assert.equal(TOTAL,2);
assert(!V['wine-a']['a.jpg']);assert(V['wine-a']['b.jpg']);
assert.equal(ROWS[0].min_conf,.9);assert.equal(statsCalls,1);assert.equal(alerts.length,0);
await removePhoto('wine-a','b.jpg');assert.equal(TOTAL,1);
assert(ROWS[0].catalog_only);assert.equal(ROWS[0].min_conf,null);
""")

    def test_lightbox_closes_deleted_photo_and_keeps_other_photo(self):
        self.run_js("""
LB={wine:0,photo:0};CMT_AT={slug:'wine-a',file:'a.jpg'};
await removePhoto('wine-a','a.jpg');assert.equal(closed,1);assert.equal(CMT_AT,null);
assert.equal(opened.length,0);
""")
        self.run_js("""
LB={wine:0,photo:1};await removePhoto('wine-a','a.jpg');
assert.equal(closed,0);assert.deepEqual(opened,[[0,0]]);assert.equal(lbPhoto().file,'b.jpg');
""")

    def test_failure_preserves_photo_and_duplicate_click_sends_one_request(self):
        setup = SETUP.replace("const post=async(route,body)=>{requests.push([route,body]);return {ok:true}};",
                             "let finish;const post=(route,body)=>{requests.push([route,body]);"
                             "return new Promise((resolve,reject)=>{finish=reject})};")
        self.run_js("""
const before=JSON.stringify(ROWS),pending=removePhoto('wine-a','a.jpg');
await removePhoto('wine-a','a.jpg');assert.equal(requests.length,1);
finish(new Error('write failed'));await pending;
assert.equal(JSON.stringify(ROWS),before);assert.equal(TOTAL,3);assert(V['wine-a']['a.jpg']);
assert.equal(alerts.length,1);assert.equal(PHOTO_REMOVE_BUSY.size,0);
""", setup)

    def test_set_switch_does_not_remove_from_new_set(self):
        setup = SETUP.replace("const post=async(route,body)=>{requests.push([route,body]);return {ok:true}};",
                             "let finish;const post=(route,body)=>{requests.push([route,body]);"
                             "return new Promise(resolve=>{finish=resolve})};")
        self.run_js("""
const pending=removePhoto('wine-a','a.jpg');SET='other';finish({ok:true});await pending;
assert.equal(ROWS[0].photos.length,2);assert.equal(TOTAL,3);assert.equal(statsCalls,0);
assert.equal(requests[0][1].set,'my');
""", setup)

    def test_drawer_results_refresh_and_marked_photo_has_delete_action(self):
        self.run_js("""
DRAWER_VIEW={};await removePhoto('__drawer__','c.jpg');
assert.equal(ROWS[1].photos.length,0);assert(!ROWS[1].catalog_only);assert.equal(drawerCalls,1);
""")
        self.run_js("""
showCtxMenu(10,10,'wine-a','a.jpg');assert($('#ctxmenu').innerHTML.includes('data-act="delete"'));
assert($('#ctxmenu').innerHTML.includes('Clear deletion mark'));
""", SETUP + "const esc=v=>v,deleteMarked=()=>true,DRAWER_SLUG='__drawer__',"
                    "NULL_SLUG='__null__',window={innerWidth:800,innerHeight:600};", MENU)
        self.assertIn('else if (act === "delete") removePhoto(slug, file);', SOURCE)


if __name__ == "__main__":
    unittest.main()
