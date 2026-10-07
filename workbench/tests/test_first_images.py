"""Check small-card preview selection without changing the full-image source."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'pipeline'))
import lab_pages
import lab_server as LAB
import labdb
from PIL import Image


@unittest.skipUnless(shutil.which('node'), 'Node.js required')
class CardPreviewTest(unittest.TestCase):
    def test_original_links_priority_source_changes_and_external_images(self):
        code = r'''
const assert = require('assert'); let changed;
const region = {id:'list',closest:()=>null};
const document = {body:{classList:{contains:()=>false}}};
const MutationObserver = class {constructor(callback){changed=callback;}observe(){}};
class Img {
 constructor(src, srcset){this.nodeType=1;this.tagName='IMG';this.attrs={src};if(srcset)this.attrs.srcset=srcset;this.events={};}
 getAttribute(n){return this.attrs[n]??null;}hasAttribute(n){return n in this.attrs;}
 set srcset(value){this.attrs.srcset=value;}removeAttribute(n){delete this.attrs[n];}
 addEventListener(n,fn){this.events[n]=fn;}matches(){return true;}querySelectorAll(){return [];}
 closest(){return region;}
}
'''
        script = (ROOT/'pipeline/pages/first_images.js').read_text()
        code += script + r'''
const url='/images/main/'+'a'.repeat(64)+'.webp';
const images=Array.from({length:6},()=>new Img(url));
changed([{type:'childList',addedNodes:images}]);
for(const image of images){assert.equal(image.attrs.src,url);assert.equal(image.attrs.srcset,url+'?thumbnail=1');}
assert.equal(images[0].fetchPriority,'high');assert.equal(images[0].loading,'eager');assert(!images[1].loading);
const first=images[0];first.attrs.src=url.replace('.webp','.png');changed([{type:'attributes',target:first}]);
assert.equal(first.attrs.srcset,first.attrs.src+'?thumbnail=1');
first.attrs.src='blob:local';changed([{type:'attributes',target:first}]);assert(!first.attrs.srcset);
const external=new Img('https://example.org/img.jpg');changed([{type:'childList',addedNodes:[external]}]);assert(!external.attrs.srcset);
const responsive=new Img(url,'existing 2x');changed([{type:'childList',addedNodes:[responsive]}]);assert.equal(responsive.attrs.srcset,'existing 2x');
images[1].events.error();assert(!images[1].attrs.srcset);
'''
        subprocess.run(['node','-e',code],check=True,capture_output=True,text=True)

    def test_shared_script_is_before_card_creation_and_only_on_supported_pages(self):
        script = (ROOT/'pipeline/pages/first_images.js').read_text()
        for page in ('dataset','testset','runs'):
            text = lab_pages.page(page+'.html')
            self.assertEqual(text.count(script),1)
            self.assertLess(text.index(script),text.index('<body'))
        for page in ('embedding','clusters','recognize','health'):
            self.assertNotIn(script,lab_pages.page(page+'.html'))


class PreviewRouteTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.handler = LAB.Handler.__new__(LAB.Handler)
        self.handler.server = SimpleNamespace(db_path=str(self.root/'catalog.sqlite3'))
        self.handler._send = mock.Mock()
        self.route = '/images/main/'+'a'*64+'.png'
        self.source = Path(labdb.image_dir(self.handler.server.db_path,'main')) / ('a'*64+'.png')
        self.source.parent.mkdir(parents=True)
        Image.new('RGB',(100,200),'red').save(self.source)

    def test_full_image_remains_exact_and_thumbnail_uses_webp(self):
        self.handler.path = self.route; self.handler._image(self.route)
        args = self.handler._send.call_args.args
        self.assertEqual(args,(200,self.source.read_bytes(),'image/png',LAB.IMAGE_CACHE))
        self.handler.path += '?thumbnail=1'; self.handler._image(self.route)
        args = self.handler._send.call_args.args
        self.assertEqual((args[0],args[2],args[3]),(200,'image/webp',LAB.IMAGE_CACHE))
        self.assertTrue(args[1].startswith(b'RIFF'))

    def test_cache_failure_falls_back_and_missing_invalid_paths_stay_404(self):
        self.handler.path = self.route+'?thumbnail=1'
        with mock.patch.object(LAB.image_thumbnails,'get',side_effect=OSError('cache unavailable')):
            self.handler._image(self.route)
        self.assertEqual(self.handler._send.call_args.args[1],self.source.read_bytes())
        for route in ('/images/main/../private.png','/images/invalid/'+'a'*64+'.png','/images/main/'+'b'*64+'.png'):
            self.handler.path=route+'?thumbnail=1'; self.handler._image(route)
            self.assertEqual(self.handler._send.call_args.args[0],404)

    def test_unknown_sizes_do_not_generate_previews(self):
        for query in ('thumbnail=999','thumbnail=1&thumbnail=999'):
            self.handler.path=self.route+'?'+query
            with mock.patch.object(LAB.image_thumbnails,'get',side_effect=AssertionError('unexpected preview')):
                self.handler._image(self.route)
            self.assertEqual(self.handler._send.call_args.args[1],self.source.read_bytes())
