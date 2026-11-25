// Service worker: sayfa önce ağdan (güncel veri), ağ yoksa ya da 2,5 sn'de gelmezse son kopyadan açılır.
// Logolar, ikonlar ve fontlar önbellekten gelir.
const V='__VERSION__', PAGES='pages-v1', ASSETS='assets-v1';
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(PAGES).then(c=>c.addAll(['./','./en.html']).catch(()=>{})))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==PAGES&&k!==ASSETS).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
function fresh(req){
  return new Promise(res=>{let done=false;
    const t=setTimeout(()=>caches.match(req,{ignoreSearch:true}).then(r=>{if(r&&!done){done=true;res(r)}}),2500);
    fetch(req).then(r=>{if(r.ok){const c=r.clone();caches.open(PAGES).then(x=>x.put(req,c))}clearTimeout(t);if(!done){done=true;res(r)}})
      .catch(()=>caches.match(req,{ignoreSearch:true}).then(r=>{clearTimeout(t);if(!done){done=true;res(r||Response.error())}}));
  });
}
self.addEventListener('fetch',e=>{const r=e.request,u=new URL(r.url);
  if(r.method!=='GET')return;
  if(r.mode==='navigate'||(u.origin===location.origin&&/\.html$|\/$/.test(u.pathname))){e.respondWith(fresh(r));return}
  if(u.origin===location.origin&&/\/logos\/|icon|\.png$|\.webmanifest$/.test(u.pathname)||/fonts\.(gstatic|googleapis)\.com$/.test(u.hostname)){
    e.respondWith(caches.open(ASSETS).then(c=>c.match(r).then(hit=>hit||fetch(r).then(resp=>{if(resp.ok||resp.type==='opaque')c.put(r,resp.clone());return resp}))));
  }
});
