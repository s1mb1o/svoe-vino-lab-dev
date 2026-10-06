"""Check when the shared step renderer requests candidate previews."""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "pipeline/pages/steps.js"


class Images(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.images = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


@unittest.skipUnless(shutil.which("node"), "Node.js is needed for the shared renderer")
class StepsRenderingTest(unittest.TestCase):
    def run_js(self, code):
        return subprocess.check_output(["node", "-e", SOURCE.read_text() + "\n" + code], text=True)

    def fixture(self, state="done"):
        part = {"id": "search", "view": "full", "n": 1, "name": "Search, space full",
                "state": state, "lists": [{"title": "Top candidates", "items": [
                    {"slug": "a", "rank": 1, "score": 0.5,
                     "image": "/api/run-preview?token=abc&rank=1",
                     "image_fallback": "/images/main/fallback.png"},
                    {"slug": "b", "rank": 2, "score": 0.4, "image": "/embeddings/gw/images/b.png"}]}]}
        return {"rounds": [{"title": "Round 2", "steps": [part]}]}

    def render(self, data, opened=()):
        return self.run_js("process.stdout.write(Steps.html(" + json.dumps(data) +
                           ", new Set(" + json.dumps(opened) + "))); ")

    def test_a_closed_search_step_has_no_candidate_src_attributes(self):
        html = self.render(self.fixture())
        images = Images(html).images
        self.assertEqual(len(images), 2)
        self.assertTrue(all("src" not in image for image in images))
        self.assertEqual(images[0]["data-step-src"], images[0]["data-full"])
        self.assertEqual(images[0]["data-step-fallback"], "/images/main/fallback.png")
        self.assertIn('class="body" hidden', html)

    def test_open_and_failed_search_steps_request_their_previews(self):
        for data, opened in ((self.fixture(), ["search:full"]), (self.fixture("failed"), [])):
            html = self.render(data, opened)
            images = Images(html).images
            self.assertTrue(all("src" in image and "data-step-src" not in image for image in images))
            self.assertNotIn('class="body" hidden', html)

    def test_other_step_images_keep_their_existing_sources(self):
        data = self.fixture()
        data["rounds"][0]["steps"][0]["id"] = "score"
        self.assertTrue(all("src" in image for image in Images(self.render(data)).images))

    def test_open_close_and_reopen_activate_each_preview_once(self):
        result = json.loads(self.run_js('''
const requested = [];
const attrs = new Map([['data-step-src', '/api/run-preview?rank=1']]);
const image = {getAttribute: key => attrs.get(key), removeAttribute: key => attrs.delete(key),
  set src(value) { requested.push(value); }};
const body = {hidden: true, querySelectorAll: () => attrs.has('data-step-src') ? [image] : []};
const card = {dataset: {key: 'search:full'}, querySelector: selector => selector === '.body' ? body : null};
const aria = [];
const head = {closest: () => card, setAttribute: (key, value) => aria.push(value)};
const opened = new Set();
Steps.toggle(head, opened);
const firstOpen = opened.has('search:full');
Steps.toggle(head, opened);
const closed = !opened.has('search:full');
Steps.toggle(head, opened);
process.stdout.write(JSON.stringify({requested, firstOpen, closed, lastOpen: opened.has('search:full'), aria}));
'''))
        self.assertEqual(result["requested"], ["/api/run-preview?rank=1"])
        self.assertTrue(result["firstOpen"] and result["closed"] and result["lastOpen"])
        self.assertEqual(result["aria"], ["true", "false", "true"])

    def test_a_failed_preview_uses_the_fallback_once_and_updates_full_image_viewing(self):
        result = json.loads(self.run_js('''
const requested = [];
const attrs = new Map([['data-step-fallback', '/images/main/fallback.png'],
                       ['data-full', '/api/run-preview?rank=1'], ['onerror', 'Steps.imageError(this)']]);
const image = {getAttribute: key => attrs.get(key), removeAttribute: key => attrs.delete(key),
  setAttribute: (key, value) => attrs.set(key, value), set src(value) { requested.push(value); }};
Steps.imageError(image);
Steps.imageError(image);
process.stdout.write(JSON.stringify({requested, full: attrs.get('data-full'),
  fallback: attrs.has('data-step-fallback'), handler: attrs.has('onerror')}));
'''))
        self.assertEqual(result["requested"], ["/images/main/fallback.png"])
        self.assertEqual(result["full"], "/images/main/fallback.png")
        self.assertFalse(result["fallback"] or result["handler"])

    def test_deferred_urls_are_escaped_as_attributes(self):
        data = self.fixture()
        item = data["rounds"][0]["steps"][0]["lists"][0]["items"][0]
        item["image"] = '/api/run-preview?token="<unsafe>&'
        item["image_fallback"] = '/images/main/"<unsafe>&.png'
        html = self.render(data)
        self.assertNotIn("<unsafe>", html)
        self.assertEqual(Images(html).images[0]["data-step-src"], item["image"])
        self.assertEqual(Images(html).images[0]["data-step-fallback"], item["image_fallback"])

class ArtifactRenderingTest(unittest.TestCase):
    run_js = StepsRenderingTest.run_js
    fixture = StepsRenderingTest.fixture
    render = StepsRenderingTest.render
    def test_checked_artifacts_fetch_only_when_open_or_failed(self):
        data=self.fixture()
        part=data['rounds'][0]['steps'][0]
        part.update(id='model-input',artifacts=[{'src':'/api/run-artifact?token=x&step=2',
                                                'caption':'input.png','deferred':True}])
        part['lists']=[]
        image=Images(self.render(data)).images[0]
        self.assertNotIn('src',image)
        self.assertEqual(image['data-step-src'],image['data-full'])
        self.assertIn('src',Images(self.render(data,['model-input:full'])).images[0])
        part['state']='failed'
        self.assertIn('src',Images(self.render(data)).images[0])
