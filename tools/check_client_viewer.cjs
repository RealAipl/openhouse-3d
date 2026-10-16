/* Exercise the standalone, offline 3D deliverable with its actual embedded model. */
const fs=require('node:fs');const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('../tmp/repair/web/node_modules/playwright');
const root=path.resolve(__dirname,'..');
const out=path.join(root,'houses/blizniak_dwulokalowy/output/refined');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try {
  const page=await browser.newPage({viewport:{width:960,height:540}});const errors=[],externalRequests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('request',r=>{if(/^https?:/.test(r.url()))externalRequests.push(r.url())});
  await page.goto(pathToFileURL(path.join(out,'Spacer_3D.html')).href);
  await page.waitForFunction(()=>window.ready===true,{timeout:120000});
  const units=[];
  for(const unit of ['A_upper','A_ground','B_upper','B_ground']){
   await page.selectOption('#unit',unit);
   const pose=await page.evaluate(()=>window.getPose());
   if(Math.abs(pose.position[0]-(unit[0]==='A'?-4.365:4.365))>.001)throw Error('Mirror selection mismatch '+unit);
   if(Math.abs(pose.position[1]-(unit.endsWith('upper')?4.48:1.55))>.001)throw Error('Floor selection mismatch '+unit);
   units.push({unit,pose});console.log('UNIT_OK',unit);
  }
  await page.selectOption('#unit','A_upper');
  const before=await page.evaluate(()=>window.getPose());
  await page.mouse.move(650,300);await page.mouse.down();await page.mouse.move(690,320);await page.mouse.up();
  const after=await page.evaluate(()=>window.getPose());
  if(JSON.stringify(before.quaternion)===JSON.stringify(after.quaternion))throw Error('Dragging did not rotate camera');
  await page.click('#play');await page.waitForTimeout(700);
  const played=await page.evaluate(()=>window.getPose());
  if(JSON.stringify(played.position)===JSON.stringify(before.position))throw Error('Tour button did not move camera');
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>document.querySelector('header').getBoundingClientRect().right>innerWidth);
  if(overflow)throw Error('Mobile toolbar overflow');
  await page.screenshot({path:path.join(root,'tmp/repair/viewer-mobile.png')});
  if(errors.length||externalRequests.length)throw Error(JSON.stringify({errors,externalRequests}));
  fs.writeFileSync(path.join(out,'KONTROLA_SPACERU_HTML.json'),JSON.stringify({offline:true,units,drag_look:true,tour_button:true,mobile_toolbar:true,errors,externalRequests},null,2));
  console.log('OFFLINE_VIEWER_OK');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
