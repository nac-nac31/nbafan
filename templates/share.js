// ---------- Paylaşım, bildirim kanalı ve uygulama (PWA). scripts/extras.py sayfanın sonuna ekler. ----------
(function(){
const EN=document.documentElement.lang==='en';
const S=EN?{
  story:'Story of the week',img:'Share as image',wa:'Send on WhatsApp',making:'Drawing the image…',share:'Share',dl:'Download',close:'Close',
  tip:'On a phone, "Share" sends the image straight to WhatsApp. On a computer, download it and attach it.',
  potw:'Player of the week',king:'All-play champ',blow:'Biggest win',
  notif:'Notifications',notifHint:'Get a push on your phone when a close matchup flips or someone on your roster gets hurt. Uses the free ntfy app, no account needed.',
  step1:'Install ntfy',step2:'Subscribe to your team channel',step3:'Optional: league channel for the weekly story',open:'Open in ntfy',copy:'Copy',copied:'Copied',
  install:'Add to home screen',installHint:'Opens like an app, full screen, and works offline with the last update.',iosHint:'On iPhone: tap Share, then "Add to Home Screen".',installBtn:'Install',
  wk:w=>`Week ${w}`,more:'Full stats'
}:{
  story:'Haftanın hikayesi',img:'Görsel olarak paylaş',wa:"WhatsApp'ta gönder",making:'Görsel hazırlanıyor…',share:'Paylaş',dl:'İndir',close:'Kapat',
  tip:"Telefonda \"Paylaş\" görseli doğrudan WhatsApp'a gönderir. Bilgisayarda indirip ekleyebilirsin.",
  potw:'Haftanın oyuncusu',king:'All-play şampiyonu',blow:'En farklı galibiyet',
  notif:'Bildirimler',notifHint:'Kıl payı bir maç tersine dönünce ya da kadrondan biri sakatlanınca telefonuna bildirim gelsin. Ücretsiz ntfy uygulamasıyla çalışır, hesap gerekmez.',
  step1:'ntfy uygulamasını kur',step2:'Takımının kanalına abone ol',step3:'İstersen haftalık hikaye için lig kanalı',open:"ntfy'da aç",copy:'Kopyala',copied:'Kopyalandı',
  install:'Ana ekrana ekle',installHint:'Uygulama gibi tam ekran açılır, internet yokken son güncellemeyi gösterir.',iosHint:'iPhone\'da: Paylaş düğmesine, sonra "Ana Ekrana Ekle"ye dokun.',installBtn:'Yükle',
  wk:w=>`${w}. hafta`,more:'Tüm istatistikler'
};
const ST=DATA.story, NT=DATA.notify;
const nm=id=>(byId[id]||{}).name||'';

// ---- Bu hafta: hikaye + paylaş
const baseBH=V['bu-hafta'];
V['bu-hafta']=()=>installCard()+baseBH()+storySec();
function storySec(){if(!ST)return '';const ps=ST[EN?'en':'tr']||[];
  return `<section class="sec story"><div class="sec-h"><h2>${S.story}</h2><span class="chip2">${S.wk(ST.week)}</span></div>
  <div class="panel sbody">${ps.map((p,i)=>`<p${i===0?' class="lead"':''}>${esc(p)}</p>`).join('')}
  <div class="sact"><button type="button" class="sbtn" data-share-img>${icon('img')}${S.img}</button><a class="sbtn wa" href="${waLink()}" target="_blank" rel="noopener">${icon('wa')}${S.wa}</a></div></div></section>`}
function waLink(){const ps=(ST[EN?'en':'tr']||[]).slice(0,5);const u=location.origin+location.pathname;
  return 'https://wa.me/?text='+encodeURIComponent(`*${DATA.league} · ${ST.title[EN?'en':'tr']}*\n\n${ps.join('\n\n')}\n\n${u}`)}
function icon(k){return k==='wa'?'<svg viewBox="0 0 24 24"><path d="M4 20l1.3-3.9A8 8 0 1 1 8 19z"/><path d="M9 9.5c.3 2 2.2 4.2 4.6 4.9l1.2-1.1 1.7.8c-.3 1.2-1.3 1.9-2.6 1.7-3-.5-5.8-3.4-6.1-6.3-.1-1.2.6-2.2 1.7-2.4l.9 1.6z"/></svg>'
  :'<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/></svg>'}

// ---- Takımım: bildirim kanalı
const baseMy=V.takimim;
V.takimim=()=>{const h=baseMy();const my=getMy()??memMy;if(my==null||!NT)return h;
  const topic=`${NT.prefix}-${my}`,lg=`${NT.prefix}-lig`,srv=NT.server.replace(/\/$/,'');
  const row=(t)=>`<div class="ntrow"><code>${esc(t)}</code><button type="button" class="linkbtn" data-copy="${esc(t)}">${S.copy}</button><a class="linkbtn" href="${srv}/${encodeURIComponent(t)}" target="_blank" rel="noopener">${S.open}</a></div>`;
  return h+`<section class="sec"><div class="sec-h"><h2>${S.notif}</h2></div><p class="hint">${S.notifHint}</p>
  <div class="panel ntf"><ol>
   <li><b>${S.step1}</b><div class="ntrow"><a class="linkbtn" href="https://apps.apple.com/app/ntfy/id1625396347" target="_blank" rel="noopener">App Store</a><a class="linkbtn" href="https://play.google.com/store/apps/details?id=io.heckel.ntfy" target="_blank" rel="noopener">Google Play</a></div></li>
   <li><b>${S.step2}</b>${row(topic)}</li>
   <li><b>${S.step3}</b>${row(lg)}</li></ol></div></section>`};

// ---- Uygulama olarak yükle
let deferred=null;
const CAP=window.Capacitor&&window.Capacitor.isNativePlatform&&window.Capacitor.isNativePlatform()?window.Capacitor:null;
const standalone=()=>CAP||matchMedia('(display-mode: standalone)').matches||navigator.standalone;
if(CAP){document.documentElement.classList.add('native');const SB=CAP.Plugins.StatusBar;try{SB&&SB.setBackgroundColor({color:'#122A1E'})}catch(e){}}
// uygulama içinde: görseli önbelleğe yazıp telefonun paylaşım ekranını aç (WhatsApp, Instagram…)
async function nativeShare(blob,name,title){const b64=await new Promise(r=>{const f=new FileReader();f.onload=()=>r(String(f.result).split(',')[1]);f.readAsDataURL(blob)});
  const fs=CAP.Plugins.Filesystem,sh=CAP.Plugins.Share;const w=await fs.writeFile({path:name,data:b64,directory:'CACHE'});
  await sh.share({title,text:title+' · '+location.origin+location.pathname,files:[w.uri],dialogTitle:title})}
const isIOS=/iphone|ipad|ipod/i.test(navigator.userAgent);
function installCard(){if(standalone()||(!deferred&&!isIOS))return '';try{if(localStorage.getItem('pwa-hide'))return ''}catch(e){}
  return `<div class="panel inst"><img src="icon-192.png" alt="" width="44" height="44"><div><b>${S.install}</b><small>${isIOS&&!deferred?S.iosHint:S.installHint}</small></div>
  ${deferred?`<button type="button" class="sbtn" data-install>${S.installBtn}</button>`:''}<button type="button" class="x" data-inst-x aria-label="${S.close}">×</button></div>`}
addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferred=e;if(/bu-hafta|^#?$/.test(location.hash||'#bu-hafta'))render()});
if('serviceWorker' in navigator&&location.protocol==='https:')addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));

// ---- tıklamalar
document.addEventListener('click',async e=>{const b=e.target.closest('[data-share-img],[data-install],[data-inst-x],[data-copy],[data-modal-x],[data-dl],[data-sh]');if(!b)return;
  if(b.dataset.copy!=null){try{await navigator.clipboard.writeText(b.dataset.copy);b.textContent=S.copied;setTimeout(()=>b.textContent=S.copy,1500)}catch(x){}return}
  if(b.hasAttribute('data-install')){if(deferred){deferred.prompt();await deferred.userChoice;deferred=null;render()}return}
  if(b.hasAttribute('data-inst-x')){try{localStorage.setItem('pwa-hide','1')}catch(x){}render();return}
  if(b.hasAttribute('data-modal-x')){document.getElementById('shm')?.remove();return}
  if(b.hasAttribute('data-share-img')){openModal();return}
});

// ---- paylaşım görseli (1080×1350, WhatsApp/Instagram oranı)
async function openModal(){document.getElementById('shm')?.remove();
  const m=document.createElement('div');m.id='shm';m.className='shm';m.innerHTML=`<div class="shc"><p class="hint">${S.making}</p></div>`;document.body.appendChild(m);
  m.addEventListener('click',e=>{if(e.target===m)m.remove()});
  try{const blob=await drawImage();const url=URL.createObjectURL(blob);const file=new File([blob],`hafta-${ST.week}.png`,{type:'image/png'});
    const can=CAP||(navigator.canShare&&navigator.canShare({files:[file]}));
    m.querySelector('.shc').innerHTML=`<img src="${url}" alt="${esc(ST.title[EN?'en':'tr'])}"><p class="hint">${S.tip}</p><div class="sact">
     ${can?`<button type="button" class="sbtn" data-sh>${S.share}</button>`:''}${CAP?'':`<a class="sbtn ghost" href="${url}" download="hafta-${ST.week}.png">${S.dl}</a>`}<button type="button" class="sbtn ghost" data-modal-x>${S.close}</button></div>`;
    const sh=m.querySelector('[data-sh]');if(sh&&CAP)sh.onclick=()=>nativeShare(blob,file.name,`${DATA.league} · ${ST.title[EN?'en':'tr']}`).catch(()=>{});else if(sh)sh.onclick=()=>navigator.share({files:[file],title:`${DATA.league} · ${ST.title[EN?'en':'tr']}`,text:location.origin+location.pathname}).catch(()=>{});
  }catch(err){m.querySelector('.shc').innerHTML=`<p class="hint">${esc(String(err))}</p><button type="button" class="sbtn ghost" data-modal-x>${S.close}</button>`}}

function loadImg(src){return new Promise(r=>{if(!src)return r(null);const i=new Image();i.crossOrigin='anonymous';i.onload=()=>r(i);i.onerror=()=>r(null);i.src=src})}
async function drawImage(){
  const W=1080,H=1350,c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');
  const css=getComputedStyle(document.documentElement);
  const sys='-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif',cv=k=>(css.getPropertyValue(k)||'').trim()||sys;
  const F=cv('--f-display'),B=cv('--f-body'),M=B;
  const bg='#0A130E',head='#122A1E',acc='#3DB97C',cool='#E5844F',ink='#EAF3EC',mut='#9DB5A6',line='#21342A';
  x.fillStyle=bg;x.fillRect(0,0,W,H);
  const g=x.createLinearGradient(0,0,W,420);g.addColorStop(0,'#1d4a33');g.addColorStop(1,head);x.fillStyle=g;x.fillRect(0,0,W,330);
  x.strokeStyle='rgba(255,255,255,.06)';x.lineWidth=40;x.beginPath();x.arc(W-60,40,260,0,Math.PI*2);x.stroke();
  x.fillStyle=acc;x.font=`500 26px ${M}`;x.fillText((DATA.league+' · ESPN 9-cat H2H').toUpperCase(),64,92);
  x.fillStyle=ink;x.font=`800 124px ${F}`;x.fillText(ST.title[EN?'en':'tr'].toLocaleUpperCase(EN?'en':'tr'),60,226);
  x.fillStyle=mut;x.font=`500 26px ${M}`;x.fillText(DATA.updated||'',64,286);
  const rows=ST.results.slice(0,6),y0=370,rh=118;
  const logos=await Promise.all(rows.flatMap(r=>[r.a,r.b]).map(id=>loadImg((byId[id]||{}).logo)));
  const clip=(s,w,font)=>{x.font=font;if(x.measureText(s).width<=w)return s;while(s.length>1&&x.measureText(s+'…').width>w)s=s.slice(0,-1);return s+'…'};
  rows.forEach((r,i)=>{const y=y0+i*rh,aw=r.s[0]>r.s[1],bw=r.s[1]>r.s[0];
    x.fillStyle=i%2?bg:'#0E1A13';x.fillRect(0,y,W,rh);
    const circ=(img,id,cx)=>{x.save();x.beginPath();x.arc(cx,y+rh/2,36,0,Math.PI*2);x.closePath();x.fillStyle=line;x.fill();x.clip();
      if(img)x.drawImage(img,cx-36,y+rh/2-36,72,72);else{x.fillStyle=mut;x.font=`700 26px ${F}`;x.textAlign='center';x.fillText(((byId[id]||{}).abbrev||nm(id)).slice(0,3).toUpperCase(),cx,y+rh/2+9);x.textAlign='left'}x.restore()};
    circ(logos[i*2],r.a,100);circ(logos[i*2+1],r.b,W-100);
    x.font=`600 32px ${B}`;x.fillStyle=aw?ink:mut;x.textAlign='left';x.fillText(clip(nm(r.a),300,`600 32px ${B}`),152,y+rh/2+11);
    x.fillStyle=bw?ink:mut;x.textAlign='right';x.fillText(clip(nm(r.b),300,`600 32px ${B}`),W-152,y+rh/2+11);
    x.textAlign='center';x.font=`800 72px ${F}`;
    const fs=v=>Number.isInteger(v)?String(v):v.toFixed(1),sa=fs(r.s[0]),sb=fs(r.s[1]),mid=W/2;if(ST.points)x.font=`800 56px ${F}`;
    x.fillStyle=aw?acc:mut;x.textAlign='right';x.fillText(sa,mid-18,y+rh/2+26);
    x.fillStyle=mut;x.textAlign='center';x.fillText('–',mid,y+rh/2+22);
    x.fillStyle=bw?cool:mut;x.textAlign='left';x.fillText(sb,mid+18,y+rh/2+26);x.textAlign='left';
  });
  let y=y0+rows.length*rh+40;
  const hl=[];
  if(ST.pw)hl.push([S.potw,`${ST.pw.name}`,`${nm(ST.pw.team)} · ${ST.pw.pg.PTS} ${EN?'ppg':'sayı'} · ${ST.pw.n} ${EN?'g':'maç'}`]);
  if(ST.king!=null)hl.push([S.king,nm(ST.king),`${ST.kingBeat}/${ST.nOpp||DATA.nOpp||11}`]);
  hl.slice(0,2).forEach((h,i)=>{const bx=64+i*488,bw2=464;x.fillStyle=head;roundRect(x,bx,y,bw2,150,22);x.fill();
    x.fillStyle=i?cool:acc;x.font=`500 22px ${M}`;x.fillText(h[0].toLocaleUpperCase(EN?'en':'tr'),bx+28,y+44);
    x.fillStyle=ink;x.font=`700 40px ${B}`;x.fillText(clip(h[1],bw2-56,`700 40px ${B}`),bx+28,y+94);
    x.fillStyle=mut;x.font=`400 24px ${B}`;x.fillText(clip(h[2],bw2-56,`400 24px ${B}`),bx+28,y+130)});
  x.fillStyle=mut;x.font=`500 24px ${M}`;x.textAlign='center';x.fillText((location.host+location.pathname).replace(/\/$/,''),W/2,H-44);
  return await new Promise((res,rej)=>c.toBlob(b=>b?res(b):rej(new Error('canvas')),'image/png'));
}
function roundRect(x,a,b,w,h,r){x.beginPath();x.moveTo(a+r,b);x.arcTo(a+w,b,a+w,b+h,r);x.arcTo(a+w,b+h,a,b+h,r);x.arcTo(a,b+h,a,b,r);x.arcTo(a,b,a+w,b,r);x.closePath()}

addEventListener('hashchange',()=>document.getElementById('shm')?.remove());
addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('shm')?.remove()});
render();
})();
