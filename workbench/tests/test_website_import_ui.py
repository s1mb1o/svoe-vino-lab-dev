"""Execute the production website import UI against bounded DOM and HTTP fixtures."""

import json
from pathlib import Path
import subprocess
import unittest


class WebsiteImportUiTest(unittest.TestCase):
    def test_three_choices_escaping_warning_and_bulk_safety(self):
        source = Path(__file__).resolve().parents[1] / 'pipeline/pages/website_import.js'
        code = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const nodes = {}, calls = [];
const node = () => ({dataset:{}, handlers:{}, setAttribute(){}, classList:{toggle(){}}, querySelector:s=>nodes[s] || node(),
  querySelectorAll:()=>[], addEventListener(name, fn){this.handlers[name]=fn;}, appendChild(){},
  hidden:false, innerHTML:'', textContent:''});
const body = node(); nodes['#website-body']=body;
const document = {getElementById:()=>node(), createElement:()=>node(), head:node(),
  body:node(), addEventListener(){}};
const window = {addEventListener(){}};
let source = fs.readFileSync(process.argv[1], 'utf8');
source = source.slice(0, source.lastIndexOf('})();')) +
  'window.__test={choicesHtml,reviewHtml,apply,modal,setDiff:v=>diff=v};})();';
const pending = () => new Promise(()=>{});
const context = {document, window, location:{pathname:'/dataset'}, history:{},
  fetch:(url, opts)=>{calls.push({url,opts}); return pending();}, clearTimeout(){}, setTimeout(){},
  CSS:{escape:x=>x}, Map, console};
vm.runInNewContext(source, context);
const test = window.__test;
const image={id:'image:muskat-premium',slug:'muskat-premium',kind:'image',name:'Muscat',
 database:{url:'/old.webp',source_name:'Screenshot_25_e7771a3f2d.webp'},
 website:{file:'images/new.webp',name:'MAX_02198_7f3ccea6d6.webp'},
 review:{eligible:false,reasons:['Wrong wine <img src=x onerror=alert(1)>'],
  verdict:{identity:'mismatch',readability:'better',sharpness:'better',reason:'Wrong grape'},
  crops:{old:{package:{size:[100,300],file:'images/old.png'},label:{size:[90,100],file:'images/old-label.png'}},
         new:{package:{size:[200,600],file:'images/new.png'},label:{size:[180,200],file:'images/new-label.png'}}}}};
const text={id:'text:a:producer',slug:'a',kind:'text',field:'producer',database:'Old',website:'New'};
test.setDiff({run:'20261016T080000',conflicts:[image,text],changes:[]});
const html=test.choicesHtml(image);
assert(html.includes('value="skip"')); assert(html.includes('Do nothing'));
assert(html.includes('manual review required')); assert(html.includes('100 × 300'));
assert(html.includes('200 × 600')); assert(html.includes('VLM identity: mismatch'));
assert(!html.includes('<img src=x onerror=')); assert(html.includes('&lt;img'));
assert(test.choicesHtml(text).includes('value="skip"'));
const corruptHtml=test.choicesHtml({...image,review_required:true});
assert(/value="website"[\s\S]*?disabled/.test(corruptHtml));
assert(source.includes('Check and apply safe updates'));
assert(!source.includes('Check prepared updates'));
assert(source.includes('Use Compare again to refresh the report'));
assert(source.includes('button.hidden = true'));
const imageInput={dataset:{conflict:image.id},checked:false}, textInput={dataset:{conflict:text.id},checked:false};
body.querySelectorAll=s=>s.includes('value="website"')?[imageInput,textInput]:[];
body.querySelector=()=>null;
test.modal.handlers.click({target:{closest:s=>s==='[data-website]'?({dataset:{website:'all',side:'website'}}):null}});
assert.strictEqual(imageInput.checked,false); assert.strictEqual(textInput.checked,true);
body.querySelectorAll=s=>s==='input[data-conflict]:checked'?[{dataset:{conflict:image.id},value:'skip'}]:[];
test.apply();
const sent=JSON.parse(calls[calls.length-1].opts.body);
assert.strictEqual(sent.conflicts[image.id],'skip');
console.log(JSON.stringify({three_choices:true,html_escaped:true,wrong_image_warning:true,
 native_crop_dimensions:true,bulk_does_not_approve_images:true,skip_payload:true}));
'''
        run = subprocess.run(['node', '-e', code, str(source)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(all(json.loads(run.stdout).values()))
