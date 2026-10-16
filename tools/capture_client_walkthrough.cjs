/* Render distinct model-based camera frames, never a slideshow or interpolated still. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require('../tmp/repair/web/node_modules/playwright');
const root = path.resolve(__dirname, '..');
const web = path.join(root, 'tmp/repair/web');
const inspect = process.argv.includes('--inspect');
const destination = path.join(root, 'tmp/repair', inspect ? 'walk-inspection' : 'walk-frames');
fs.mkdirSync(destination, {recursive:true});
const server = http.createServer((req,res) => {
  const name = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file = path.resolve(web, '.'+(name==='/'?'/index.html':name));
  if(!file.startsWith(web+path.sep)){res.writeHead(403);return res.end();}
  fs.readFile(file,(error,data)=>{
    if(error){res.writeHead(404);return res.end();}
    res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.glb')?'model/gltf-binary':'text/html');
    res.end(data);
  });
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try {
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('http://127.0.0.1:'+server.address().port,{waitUntil:'load'});
  await page.waitForFunction(()=>window.ready===true,{timeout:120000});
  await page.evaluate(()=>window.captureMode());
  console.log('VIEWER_READY');
  const count=inspect?7:480,poses=[];
  for(let i=0;i<count;i++){
   const seconds=20*i/(count-1);
   const result=await page.evaluate(t=>({image:window.captureFrame(t),pose:window.getPose()}),seconds);
   fs.writeFileSync(path.join(destination,String(i).padStart(4,'0')+'.png'),Buffer.from(result.image.split(',')[1],'base64'));
   poses.push({...result.pose,time_seconds:seconds});
   if(i%24===0)console.log('CAPTURE',i,'/',count);
  }
  fs.writeFileSync(path.join(destination,'camera.json'),JSON.stringify(poses));
  fs.writeFileSync(path.join(destination,'capture.json'),JSON.stringify({width:1920,height:1080,frames:count,duration_seconds:20,fps:24,native_frames:true,errors},null,2));
  if(errors.length)throw new Error(errors.join('\n'));
  console.log('CAPTURE_COMPLETE',count);
 } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);process.exitCode=1;server.close()});
