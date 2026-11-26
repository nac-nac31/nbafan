// ---------- Pazar: takas analizcisi + waiver radarı (render_page bu dosyayı /*__MARKET__*/ yerine koyar) ----------
const MEN=document.documentElement.lang==='en';
const MX=MEN?{
  tab1:'Trade analyzer',tab2:'Waiver radar',
  tTitle:'Trade analyzer',tIntro:'Pick two teams and the players they swap. The rest of the season and the playoffs are re-simulated with the new rosters, using the same model as the playoff odds.',
  teamA:'Team A',teamB:'Team B',gives:n=>`${n} gives`,none:'Pick at least one player on each side.',
  same:'Pick two different teams.',value:'Value',valIn:'Value in',valOut:'Value out',net:'Net value',
  odds:'Season odds',before:'Before',after:'After',po:'Playoff',champ:'Title',rec:'Proj. categories',
  cats:'Weekly categories',catHint:'Projected weekly total and league rank (1 = best). Green: improves.',
  fair:(a,b,d)=>d>=1.5?`<b>${a}</b> wins this trade on value (+${d.toFixed(1)}).`:d<=-1.5?`<b>${b}</b> wins this trade on value (+${(-d).toFixed(1)}).`:'Roughly even on value. Category fit decides.',
  dropped:(t,n)=>`${t} has to drop ${n} to make room (lowest value bench players).`,added:(t,n)=>`${t} has open spots and picks up ${n} (best available free agents).`,
  sims:n=>`${n.toLocaleString('en-US')} simulations per scenario with the same random numbers, so the difference comes from the trade, not from noise.`,
  rHint:'Free agents whose value is rising fastest, from ESPN\'s last 7, 15 and 30 day averages. The radar score mixes recent value, the jump versus the season average and how fast ownership is growing across ESPN. Small samples (2-3 games) are flagged.',
  rTitle:'Waiver radar',forWho:'For',all:'Whole league',sortBy:'Sort',sScore:'Radar score',sL7:'Last 7 days',sTrend:'Biggest jump',sOwn:'Ownership growth',sFit:'Fit for team',
  pos:'All positions',l7:'7d',l15:'15d',l30:'30d',sea:'Season',min:'min',own:'owned',fitFor:'Best fit',instead:n=>`instead of ${n}`,
  small:'small sample',gain:'Gain vs. drop candidate',noTeam:'Choose your team on My team to see personal fit.',empty:'No players with this filter.',
  inj:{Sakat:'Out',Belirsiz:'DTD',IR:'IR',Ceza:'Susp.'},jump:'Jump',hot:'Hot',
}:{
  tab1:'Takas analizcisi',tab2:'Waiver radarı',
  tTitle:'Takas analizcisi',tIntro:'İki takımı ve takas edilecek oyuncuları seç. Sezonun kalanı ve playofflar yeni kadrolarla, playoff ihtimallerindeki modelin aynısıyla yeniden simüle edilir.',
  teamA:'A takımı',teamB:'B takımı',gives:n=>`${n} veriyor`,none:'Her iki taraftan da en az bir oyuncu seç.',
  same:'İki farklı takım seç.',value:'Değer',valIn:'Gelen değer',valOut:'Giden değer',net:'Net değer',
  odds:'Sezon ihtimalleri',before:'Önce',after:'Sonra',po:'Playoff',champ:'Şampiyonluk',rec:'Tahmini kategori',
  cats:'Haftalık kategoriler',catHint:'Tahmini haftalık toplam ve lig sırası (1 en iyi). Yeşil iyileşme.',
  fair:(a,b,d)=>d>=1.5?`Değer olarak takası <b>${a}</b> kazanıyor (+${d.toFixed(1)}).`:d<=-1.5?`Değer olarak takası <b>${b}</b> kazanıyor (+${(-d).toFixed(1)}).`:'Değer olarak dengeli. Kategori uyumu belirleyici.',
  dropped:(t,n)=>`${t} yer açmak için ${n} bırakır (en düşük değerli oyuncular).`,added:(t,n)=>`${t} boşalan yere ${n} alır (en iyi serbest oyuncular).`,
  sims:n=>`Her senaryo ${n.toLocaleString('tr-TR')} kez, aynı rastgele sayılarla oynandı; fark şanstan değil takastan geliyor.`,
  rHint:'Değeri en hızlı yükselen serbest oyuncular, ESPN\'in son 7, 15 ve 30 gün ortalamalarından. Radar puanı son haftaların değerini, sezon ortalamasına göre sıçramayı ve ESPN genelinde sahipliğin ne hızla arttığını birleştirir. 2-3 maçlık küçük örnekler işaretlenir.',
  rTitle:'Waiver radarı',forWho:'Kime göre',all:'Tüm lig',sortBy:'Sırala',sScore:'Radar puanı',sL7:'Son 7 gün',sTrend:'En büyük sıçrama',sOwn:'Sahiplik artışı',sFit:'Takıma uyum',
  pos:'Tüm pozisyonlar',l7:'7g',l15:'15g',l30:'30g',sea:'Sezon',min:'dk',own:'sahiplik',fitFor:'En çok uyduğu',instead:n=>`${n} yerine`,
  small:'küçük örnek',gain:'Bırakma adayına göre kazanç',noTeam:'Kişisel uyum için Takımım sekmesinden takımını seç.',empty:'Bu filtreyle oyuncu yok.',
  inj:{},jump:'Sıçrama',hot:'Yükselişte',
};
document.head.insertAdjacentHTML('beforeend',`<style>
.seg a{flex:none;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:7px 14px;font-weight:600;font-size:13px;text-decoration:none}
.seg a[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.rvs{display:flex;flex-wrap:wrap;gap:6px;margin:5px 0 3px}
.rv{font-family:var(--f-data);font-size:12px;padding:2px 7px;border-radius:8px;background:var(--surface-2);white-space:nowrap}
.rv small{display:inline;color:var(--muted);margin-right:4px;font-size:10.5px}
.rv i{font-style:normal;color:var(--muted)}
.rad .pv{gap:2px}.rad .pv>span{font-size:16px;font-weight:600}.rs{font-size:11px;color:var(--muted)}
@media (max-width:420px){nav.tabs a{white-space:nowrap;letter-spacing:0}}
.rad small a{color:var(--accent);text-decoration:none;font-weight:600}
.tcols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
@media (max-width:640px){.tcols{grid-template-columns:minmax(0,1fr)}}
.tcol{display:flex;flex-direction:column;gap:10px;min-width:0}
.tcol .lab{font-family:var(--f-data);font-size:10.5px;color:var(--accent)}
.tcol .phead .nm{font-size:24px}
.tpick{max-height:420px;overflow-y:auto}
.tp{display:grid;grid-template-columns:20px minmax(0,1fr) auto 44px;gap:8px;align-items:center;padding:9px 12px;cursor:pointer;font-size:14px}
.tp+.tp{border-top:1px solid var(--line)}
.tp input{accent-color:var(--accent);width:16px;height:16px;margin:0}
.tp .nm{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tp small{color:var(--muted);font-size:11.5px}.tp b{font-family:var(--f-data);font-size:13px;text-align:right}
.tp:has(input:checked){background:color-mix(in srgb,var(--accent) 10%,transparent)}
.ttab{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}
.ttab th,.ttab td{padding:7px 12px;text-align:right}.ttab th:first-child,.ttab td:first-child{text-align:left}
.ttab th{font-family:var(--f-data);font-size:10.5px;color:var(--muted);font-weight:500}
.ttab tr+tr td{border-top:1px solid var(--line)}.ttab small{color:var(--muted)}
#tres{display:flex;flex-direction:column;gap:14px}
</style>`);
const mPc=x=>MEN?x+'%':'%'+x;
const RAD=DATA.radar||[], TS=DATA.tradeSim||null, MCATS=DATA.cats, MNT=T.length;
const mFmt=(c,v)=>c.includes('%')?v.toFixed(3).replace(/^0/,''):(Math.abs(v)<100?v.toFixed(1):String(Math.round(v)));
function mWeights(t){const w={};MCATS.forEach(c=>{const r=t.rank[c];let x=1;if(r>=MNT-4)x+=.5;if(r<=3)x-=.3;if(r===MNT)x=.4;w[c]=x});return w}
function mWorst(tid){const L=P.filter(p=>p.team===tid&&!(TS&&TS.half.includes(p.id)));return L.length?L.reduce((a,b)=>b.val<a.val?b:a):null}

// ---- waiver radarı ----
const RF={team:null,sort:'score',pos:''};
function radarFit(r,t){const w=mWeights(t),wr=mWorst(t.id);
  return MCATS.reduce((a,c)=>a+w[c]*(r.z[c]-(wr?wr.z[c]:0)),0)}
function radarRows(){const t=RF.team!=null?byId[RF.team]:null;
  let L=RAD.filter(r=>!RF.pos||r.pos===RF.pos).map(r=>({r,g:t?radarFit(r,t):null}));
  const k={score:x=>x.r.score,l7:x=>x.r.v.l7??-99,trend:x=>x.r.trend,own:x=>x.r.chg,fit:x=>x.g??x.r.score}[RF.sort];
  L.sort((a,b)=>k(b)-k(a));
  const pn=id=>{const p=P.find(x=>x.id===id);return p?esc(p.name):''};
  const chip=(r,s)=>{const v=r.v[s];if(v==null)return '';const sm=r.gp[s]<=3;
    return `<span class="rv ${v>=0?'pos':'neg'}" title="${r.gp[s]} ${MEN?'games':'maç'}${r.min[s]!=null?' · '+r.min[s]+' '+MX.min:''}"><small>${MX[s]}</small>${zfmt(v)}${sm&&s!=='sea'?'<i>*</i>':''}</span>`};
  return L.slice(0,40).map(({r,g})=>{const inj=r.inj?(MX.inj[r.inj]||r.inj):'';
    const mt=r.min.l7!=null&&r.min.sea!=null?r.min.l7-r.min.sea:null;
    const fit=t?`<small>${MX.gain}: <b class="${g>=0?'pos':'neg'}">${zfmt(g)}</b>${mWorst(t.id)?' · '+MX.instead(esc(mWorst(t.id).name)):''}</small>`
      :r.fit.length?`<small>${MX.fitFor}: ${r.fit.slice(0,2).map(f=>`<a href="${link(byId[f.t])}">${esc(byId[f.t].abbrev||byId[f.t].name)}</a>${f.drop?` (${MX.instead(pn(f.drop))})`:''}`).join(', ')}</small>`:'';
    return `<div class="pl rad"><div class="pn"><div class="nm">${esc(r.name)}${inj?` <span class="pill down">${inj}</span>`:''}${r.trend>=3?` <span class="pill up">${MX.hot}</span>`:''}${r.fa==='WAIVERS'?' <span class="pill flat">W</span>':''}</div>
     <small>${r.pos} · ${mPc(r.owned)} ${MX.own}${Math.abs(r.chg)>=.05?` <b class="${r.chg>0?'pos':'neg'}">${r.chg>0?'▲':'▼'}${Math.abs(r.chg).toFixed(1)}</b>`:''}${r.min.l7!=null?` · ${r.min.l7} ${MX.min}${mt!=null&&Math.abs(mt)>=3?` (<b class="${mt>0?'pos':'neg'}">${mt>0?'+':''}${mt.toFixed(0)}</b>)`:''}`:''}</small>
     <div class="rvs">${['l7','l15','l30','sea'].map(s=>chip(r,s)).join('')}</div>${fit}</div>
     <div class="pv"><span title="${MX.sScore}">${r.score.toFixed(1)}</span><small class="rs">${MX.jump} <b class="${r.trend>=0?'pos':'neg'}">${r.trend>=0?'↑':'↓'}${Math.abs(r.trend).toFixed(1)}</b></small></div></div>`}).join('')||`<p class="hint" style="padding:14px">${MX.empty}</p>`}
V.radar=()=>{if(RF.team==null){const my=getMy()??memMy;if(my!=null)RF.team=my}
  return `${mTabs('radar')}<section class="sec"><h2>${MX.rTitle}</h2><p class="hint">${MX.rHint}</p>
  <div class="filters">
   <select id="rteam" aria-label="${MX.forWho}"><option value="">${MX.forWho}: ${MX.all}</option>${[...T].sort((a,b)=>a.name.localeCompare(b.name,'tr')).map(t=>`<option value="${t.id}">${esc(t.name)}</option>`).join('')}</select>
   <select id="rpos" aria-label="${MX.pos}"><option value="">${MX.pos}</option>${['PG','SG','SF','PF','C'].map(x=>`<option>${x}</option>`).join('')}</select>
   <select id="rsort" aria-label="${MX.sortBy}"><option value="score">${MX.sScore}</option><option value="l7">${MX.sL7}</option><option value="trend">${MX.sTrend}</option><option value="own">${MX.sOwn}</option><option value="fit">${MX.sFit}</option></select>
  </div>
  <div class="panel" id="rlist">${radarRows()}</div>
  <p class="hint">* ${MX.small}. ${RF.team==null?MX.noTeam:''}</p></section>`};

// ---- takas analizcisi ----
const TR={a:null,b:null,ga:new Set(),gb:new Set()};
function mRng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function mGauss(r){let u=0;while(!u)u=r();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*r())}
function mPhi(x){const z=Math.abs(x)/Math.SQRT2,t=1/(1+.3275911*z),y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t*Math.exp(-z*z);return .5*(1+(x>=0?y:-y))}
function mRost(players){const acc={};const half=new Set(TS.half);
  for(const p of players){if(!p.g)continue;const w=half.has(p.id)?.5:1;for(const k in p.g)acc[k]=(acc[k]||0)+p.g[k]*TS.perWeek*w}
  const r={};for(const c of MCATS){const ks=TS.keys[c];r[c]=ks.length===2?(acc[ks[1]]?acc[ks[0]]/acc[ks[1]]:0):(acc[ks[0]]||0)}return r}
function mMu(rosters){const ids=Object.keys(TS.hist),rost={},mu={};ids.forEach(t=>rost[t]=mRost(rosters[t]||[]));
  for(const c of MCATS){const hm=ids.reduce((a,t)=>a+TS.hist[t][c],0)/ids.length,rm=ids.reduce((a,t)=>a+rost[t][c],0)/ids.length||1;
    ids.forEach(t=>{const rv=rost[t][c]?rost[t][c]*hm/rm:TS.hist[t][c];(mu[t]=mu[t]||{})[c]=.5*TS.hist[t][c]+.5*rv})}return mu}
let mShifts=null;
function mSim(mu,N){const ids=Object.keys(TS.hist).map(Number),low=new Set(TS.lower),nC=MCATS.length;
  if(!mShifts){const r=mRng(7);mShifts=[];for(let w=0;w<200;w++){const s={};ids.forEach(t=>{const g=mGauss(r);s[t]=MCATS.map(()=>.6*g+.8*mGauss(r))});mShifts.push(s)}}
  const worlds=mShifts.map(sh=>{const m={};ids.forEach(t=>m[t]=MCATS.map((c,i)=>{const d=TS.pooled[c]*.35*sh[t][i];return mu[t][c]+(low.has(c)?-d:d)}));
    const P={};for(const a of ids)for(const b of ids)if(a!==b)P[a*1000+b]=MCATS.map((c,i)=>{let d=m[a][i]-m[b][i];if(low.has(c))d=-d;return mPhi(d/(TS.pooled[c]*Math.SQRT2))});return P});
  const rr=mRng(42),n=TS.playoffTeams,res={};ids.forEach(t=>res[t]={po:0,champ:0,w:0,l:0});
  const br=n===8?[1,8,4,5,2,7,3,6]:(n&(n-1))===0?(()=>{let s=[1];while(s.length<n){const m=s.length*2+1;s=s.flatMap(x=>[x,m-x])}return s})():null;
  const play=pr=>{let w=0;for(let i=0;i<nC;i++)if(rr()<pr[i])w++;return w};
  for(let si=0;si<N;si++){const P=worlds[si%worlds.length],rec={};ids.forEach(t=>rec[t]=TS.base[t].slice());
    const g=(h,a,pr)=>{const wh=play(pr),wa=nC-wh;rec[h][0]+=wh;rec[h][1]+=wa;rec[a][0]+=wa;rec[a][1]+=wh};
    TS.curP.forEach(([h,a,pr])=>g(h,a,pr));TS.future.forEach(([h,a])=>g(h,a,P[h*1000+a]));
    const key={};ids.forEach(t=>{const r=rec[t];key[t]=-(r[0]+.5*(r[2]||0))/Math.max(1,r[0]+r[1]+(r[2]||0))});
    const tb={};ids.forEach(t=>tb[t]=rr());const order=[...ids].sort((a,b)=>key[a]-key[b]||tb[a]-tb[b]);
    order.forEach((t,i)=>{res[t].w+=rec[t][0];res[t].l+=rec[t][1];if(i<n)res[t].po++});
    if(br){let field=br.map(s=>order[s-1]);const rk={};order.forEach((t,i)=>rk[t]=i);
      while(field.length>1){const nx=[];for(let i=0;i<field.length;i+=2){const a=field[i],b=field[i+1],wa=play(P[a*1000+b]);nx.push(wa>nC-wa||(wa*2===nC&&rk[a]<rk[b])?a:b)}field=nx}
      res[field[0]].champ++}}
  ids.forEach(t=>{const r=res[t];r.po/=N;r.champ/=N;r.w/=N;r.l/=N});return res}
function mRosters(){const R={};P.forEach(p=>{if(p.team)(R[p.team]=R[p.team]||[]).push(p)});return R}
function tradeResult(){const {a,b}=TR;if(a==null||b==null)return '';if(a===b)return `<p class="hint">${MX.same}</p>`;
  if(!TR.ga.size||!TR.gb.size)return `<p class="hint">${MX.none}</p>`;
  const R0=mRosters(),R1={};for(const k in R0)R1[k]=R0[k].slice();
  const outA=R0[a].filter(p=>TR.ga.has(p.id)),outB=R0[b].filter(p=>TR.gb.has(p.id));
  R1[a]=R0[a].filter(p=>!TR.ga.has(p.id)).concat(outB);R1[b]=R0[b].filter(p=>!TR.gb.has(p.id)).concat(outA);
  const notes=[],used=new Set();
  const fix=(t,size)=>{const d=R1[t].length-size;if(d>0){const drop=R1[t].filter(p=>!outA.includes(p)&&!outB.includes(p)).sort((x,y)=>x.val-y.val).slice(0,d);
      R1[t]=R1[t].filter(p=>!drop.includes(p));notes.push(MX.dropped(esc(byId[t].name),drop.map(p=>esc(p.name)).join(', ')))}
    else if(d<0){const fa=(TS.fa||[]).filter(f=>!used.has(f.id)).slice(0,-d);fa.forEach(f=>used.add(f.id));
      R1[t]=R1[t].concat(fa);if(fa.length)notes.push(MX.added(esc(byId[t].name),fa.map(f=>esc(f.name)).join(', ')))}};
  fix(a,R0[a].length);fix(b,R0[b].length);
  const mu0=mMu(R0),mu1=mMu(R1),N=3000,s0=mSim(mu0,N),s1=mSim(mu1,N);
  const sum=L=>L.reduce((x,p)=>x+p.val,0),dA=sum(outB)-sum(outA);
  const rank=(mu,t,c)=>{const low=TS.lower.includes(c);return 1+Object.keys(mu).filter(u=>low?mu[u][c]<mu[t][c]:mu[u][c]>mu[t][c]).length};
  const side=t=>{const T0=s0[t],T1=s1[t],tm=byId[t];
    const cell=(k,f)=>{const d=T1[k]-T0[k];return `<div class="tile"><span class="k">${f}</span><span class="v">${mPc(op(T1[k]))}</span><span class="s ${Math.abs(d)<.005?'':d>0?'pos':'neg'}">${MX.before} ${mPc(op(T0[k]))} · ${d>=0?'+':'−'}${Math.abs(d*100).toFixed(1)}</span></div>`};
    const rows=MCATS.map(c=>{const r0=rank(mu0,t,c),r1=rank(mu1,t,c),dv=mu1[t][c]-mu0[t][c],low=TS.lower.includes(c),good=low?dv<0:dv>0;
      return `<tr><td><b>${c}</b></td><td>${mFmt(c,mu0[t][c])} <small>(${r0}.)</small></td><td class="${Math.abs(dv)<=Math.abs(mu0[t][c])*.004?'':good?'pos':'neg'}">${mFmt(c,mu1[t][c])} <small>(${r1}.)</small></td></tr>`}).join('');
    return `<div class="tcol"><div class="phead">${logo(tm,40)}<div><div class="nm">${esc(tm.name)}</div><div class="sub">${MX.net} <b class="${(t===a?dA:-dA)>=0?'pos':'neg'}">${zfmt(t===a?dA:-dA)}</b></div></div></div>
     <div class="tiles">${cell('po',MX.po)}${cell('champ',MX.champ)}</div>
     <div class="panel"><table class="ttab"><thead><tr><th></th><th>${MX.before}</th><th>${MX.after}</th></tr></thead><tbody>${rows}</tbody></table></div></div>`};
  return `<div class="panel"><div class="tips" style="padding:14px"><p>${MX.fair(esc(byId[a].name),esc(byId[b].name),dA)}</p>${notes.map(n=>`<p>${n}</p>`).join('')}</div></div>
   <section class="sec"><h2>${MX.odds} · ${MX.cats}</h2><p class="hint">${MX.catHint}</p><div class="tcols">${side(a)}${side(b)}</div>
   <p class="hint">${MX.sims(N)}</p></section>`}
function tradePick(side){const t=side==='a'?TR.a:TR.b,set=side==='a'?TR.ga:TR.gb;if(t==null)return '';
  const L=P.filter(p=>p.team===t).sort((x,y)=>y.val-x.val);
  return `<div class="panel tpick">${L.map(p=>`<label class="tp"><input type="checkbox" data-tp="${side}" value="${p.id}"${set.has(p.id)?' checked':''}><span class="nm">${esc(p.name)}${p.inj?` <span class="pill down">${p.inj}</span>`:''}</span><small>${p.pos}</small><b class="${p.val>=0?'pos':'neg'}">${zfmt(p.val)}</b></label>`).join('')}</div>`}
V.takas=()=>{if(!TS)return mTabs('takas')+`<p class="hint">–</p>`;
  if(TR.a==null){const my=getMy()??memMy;TR.a=my!=null?my:T[0].id}
  const opts=sel=>[...T].sort((x,y)=>x.name.localeCompare(y.name,'tr')).map(t=>`<option value="${t.id}"${t.id===sel?' selected':''}>${esc(t.name)}</option>`).join('');
  return `${mTabs('takas')}<section class="sec"><h2>${MX.tTitle}</h2><p class="hint">${MX.tIntro}</p>
  <div class="tcols"><div class="tcol"><div class="filters"><select id="ta" aria-label="${MX.teamA}">${opts(TR.a)}</select></div><div class="lab">${MX.gives(esc(byId[TR.a].name))}</div>${tradePick('a')}</div>
   <div class="tcol"><div class="filters"><select id="tb" aria-label="${MX.teamB}"><option value="">${MX.teamB}</option>${opts(TR.b)}</select></div>${TR.b!=null?`<div class="lab">${MX.gives(esc(byId[TR.b].name))}</div>`:''}${tradePick('b')}</div></div></section>
  <div id="tres">${tradeResult()}</div>`};
function mTabs(cur){return `<div class="chips seg" role="group"><a href="#takas" aria-pressed="${cur==='takas'}">${MX.tab1}</a><a href="#radar" aria-pressed="${cur==='radar'}">${MX.tab2}</a></div>`}
function marketBind(h){
  if(h==='radar'){const nav=document.querySelector('nav.tabs a[data-v="takas"]');if(nav)nav.setAttribute('aria-current','page');
    const sel={rteam:'team',rpos:'pos',rsort:'sort'};
    for(const [id,k] of Object.entries(sel)){const el=document.getElementById(id);if(!el)continue;el.value=RF[k]??'';
      el.onchange=()=>{RF[k]=k==='team'?(el.value?+el.value:null):el.value;document.getElementById('rlist').innerHTML=radarRows()}}}
  if(h==='takas'){const ta=document.getElementById('ta'),tb=document.getElementById('tb');if(!ta)return;
    ta.onchange=()=>{TR.a=+ta.value;TR.ga.clear();render()};tb.onchange=()=>{TR.b=tb.value?+tb.value:null;TR.gb.clear();render()};
    app.querySelectorAll('[data-tp]').forEach(cb=>cb.onchange=()=>{const s=cb.dataset.tp==='a'?TR.ga:TR.gb;cb.checked?s.add(+cb.value):s.delete(+cb.value);
      const r=document.getElementById('tres');r.innerHTML='<p class="hint">…</p>';setTimeout(()=>{r.innerHTML=tradeResult()},10)})}
}
