import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
if (!process.env.SHARP_MODULE) throw Error('Set SHARP_MODULE to the installed sharp module entry.');
const { default: sharp } = await import(process.env.SHARP_MODULE);
sharp.concurrency(1);
const root=process.cwd();
const out=path.join(root,'reports/product-image-frames');fs.mkdirSync(out,{recursive:true});
const items=[];
for(const file of fs.readdirSync(root+'/shared/data/product-line-maps').filter(f=>f.endsWith('.json'))){
 const map=JSON.parse(fs.readFileSync(root+'/shared/data/product-line-maps/'+file,'utf8'));
 for(const product of map.products) if(product.image) items.push({producer:map.producer.id,product_id:product.id,src:product.image.src,group_id:product.group_id,declared_frame:product.image.frame});
}
let cursor=0;const records=[];
async function worker(){
 while(cursor<items.length){
  const item=items[cursor++];const file=path.join(root,'public',item.src);
  const metadata=await sharp(file).metadata();
  assert(metadata.hasAlpha, 'Missing alpha channel: '+item.src);
  const {data,info}=await sharp(file).extractChannel('alpha').raw().toBuffer({resolveWithObject:true});
  const sw=info.width,sh=info.height;let bx=sw,by=sh,rightmost=-1,bottommost=-1;
  if(info.channels!==1)throw Error('Expected one alpha channel');
  for(let row=0;row<sh;row++){const offset=row*sw;let left=0;while(left<sw&&data[offset+left]<128)left++;if(left===sw)continue;let right=sw-1;while(data[offset+right]<128)right--;bx=Math.min(bx,left);by=Math.min(by,row);rightmost=Math.max(rightmost,right);bottommost=row;}
  if(rightmost<0)throw Error('Empty bottle '+item.src);
  const bw=rightmost-bx+1,bh=bottommost-by+1;
  const margin=Math.max(1,Math.round(bh*.005));
  const x=Math.max(0,bx-margin),y=Math.max(0,by-margin),right=Math.min(sw,bx+bw+margin),bottom=Math.min(sh,by+bh+margin);
  const frame={x,y,width:right-x,height:bottom-y,source_width:sw,source_height:sh};
  const visible={x:bx,y:by,width:bw,height:bh};
  const declared=item.declared_frame;
  assert(declared, 'Missing frame: '+item.src);
  assert.equal(declared.source_width, sw, 'Wrong source_width: '+item.src);
  assert.equal(declared.source_height, sh, 'Wrong source_height: '+item.src);
  assert(declared.x<=bx && declared.y<=by && declared.x+declared.width>rightmost && declared.y+declared.height>bottommost, 'Frame clips visible alpha: '+item.src);
  assert(data.some(alpha=>alpha===0), 'No transparent pixels: '+item.src);
  const before=bh*Math.min(176/sh,120/sw),after=bh*Math.min(176/frame.height,120/frame.width);
  records.push({...item,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),frame,visible,desktop_before:Number(before.toFixed(2)),desktop_after:Number(after.toFixed(2))});
  if(records.length%100===0)console.log(records.length+' images measured');
 }
}
await Promise.all([worker(),worker(),worker(),worker()]);
records.sort((a,b)=>a.src.localeCompare(b.src));
fs.writeFileSync(out+'/frames.json',JSON.stringify({scope:'Read-only source-image measurement. No image or producer JSON is modified.',method:'Find the bounding rectangle of alpha >= 128. Add a margin of 0.5% of the visible height, rounded to at least one source pixel. Clamp the frame to the original image. Measure only. Do not modify pixels.',records},null,2)+'\n');
console.log(JSON.stringify({images:records.length,producers:new Set(records.map(r=>r.producer)).size,small_before:records.filter(r=>r.desktop_before<130).length,small_after:records.filter(r=>r.desktop_after<130).map(r=>({src:r.src,height:r.desktop_after}))}));
