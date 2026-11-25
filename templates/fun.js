// ---------- Eğlence sayfası (render_page bu dosyayı body içindeki /*__FUN__*/ yerine koyar) ----------
const EN=document.documentElement.lang==='en';
const FX=EN?{
  kicker:'League gossip',title:'Fun stats',
  intro:n=>`Built from ${n} days of daily lineups, every add, drop and trade, and the draft. Everything is measured in 9-cat value (z-score per game), counting only what was above a bench-level player.`,
  jump:{trade:'Trades',bench:'Bench',rival:'Rivalries',rec:'Records',waiver:'Waivers',regret:'Regrets',draft:'Draft',pers:'Personalities',inj:'Injuries'},
  mon:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
  sl:{PTS:'pts',REB:'reb',AST:'ast',STL:'stl',BLK:'blk','3PM':'3pm'},
  w:w=>`W${w}`,val:'value',games:n=>`${n} games`,
  f:{game:'Game of the season',waiver:'Waiver hero',steal:'Draft steal',regret:'Biggest regret',bench:'Bench disaster',inj:'Sick bay'},
  fsub:{waiver:(t,d)=>`${t} · added ${d}`,steal:(p,r)=>`Pick ${p}, now the ${r}${ord(r)} most valuable draftee`,regret:(t,d,n)=>`${t} dropped him ${d}${n?` · now with ${n}`:' · still a free agent'}`,bench:(t,d)=>`${t} left this on the bench · ${d}`,inj:'games missed by useful players'},
  unit:{pts:'pts',bench:'pts on the bench',games:'games'},
  trade:{h:'Trade report card',hint:'Each side is graded on what its new players produced in its active lineup since the trade (60%) and what they are worth for the rest of the season (40%).',none:'No trades yet this season. When the first one goes through it gets graded here: winner, loser and the heist of the season.',got:'Got',since:'since the trade',now:'rest-of-season value',heist:'Heist of the season'},
  bench:{h:'Bench points',hint:'For every day we rebuilt the best legal lineup (PG, SG, SF, PF, C, G, F, 3 UTIL) from the players who actually played and compared it to the real one. Bar: value left on the bench.',sub:(p,n)=>`${p} pts on the bench · ${n} benched games that should have started`,lost:(w,s,o)=>`Lost ${w} ${s}, best lineup wins ${o}`,worst:'Costliest lineup decisions',none:'No lost matchups because of the bench.'},
  rival:{h:'Rivalries',hint:'Head-to-head across every season we have, matched by manager, so renamed teams keep their history.',games:n=>`${n} meeting${n>1?'s':''}`,cats:'cats',blow:'Biggest blowouts',close:(a,b)=>`${a} of ${b} matchups were decided by one category or less.`,owned:'One-way streets'},
  rec:{h:'Record wall',hint:'Best and worst single week in every category. Older-season records carry the season tag.',low:'Worst',games:'Single-game records (active lineup)',day:'Most points in one day',dayS:(t,d)=>`${t} · ${d}`},
  waiver:{h:'Waiver wire',hint:'Value a pickup produced while in that team\'s active lineup, above a bench-level player.',kept:'still rostered',gone:'dropped later',king:'Waiver kings',kingS:(n,g)=>`${n} adds · ${g} active games from pickups`},
  regret:{h:'Dropped and regretted',hint:'What a player has produced since being dropped (any team, or as a free agent).',now:n=>n?`now with ${n}`:'free agent'},
  draft:{h:'Draft report card',hint:'Each pick vs. what that draft slot should have returned (the value of the n-th best draftee this season). Grade: total over the whole draft.',best:'Best pick',worst:'Worst early pick',steals:'Steals',busts:'Busts',pick:(p,r)=>`Pick ${p} → value rank ${r}`},
  pers:{h:'Team personalities',hint:'Labels from each team\'s category ranks and how active the manager is.',best:'Best',worst:'Worst'},
  inj:{h:'Unlucky manager index',hint:'Rostered games missed while the player\'s NBA team played (injury or rest), weighted by how good the player is.',sub:(n,w)=>`${n} games missed${w?` · ${w}`:''}`},
  P:{paint:['Paint beasts','Owns the boards, the blocks and FG%.'],rain:['Make it rain','Threes and points by the bucket.'],dime:['Dime factory','Assists and steals run the offense.'],thief:['Pickpockets','Nobody steals more.'],line:['Free-throw snipers','Lives at the line and makes them.'],puntft:['Punting FT%','Gave up free throws to win the big-man cats.'],puntto:['Turnovers? Whatever','Playing fast and loose for points and assists.'],careful:['Ball security','Fewest turnovers, even if the passing suffers.'],scorer:['Bucket getters','Top of the league in points.'],balanced:['Jack of all trades','No glaring hole in any category.'],grinder:['Waiver addict','Always on the wire.'],loyal:['Set and forget','Barely touches the roster.'],rebuild:['Building for next year','Struggling across the board.']}
}:{
  kicker:'Ligin dedikodusu',title:'Eğlenceli istatistikler',
  intro:n=>`${n} günlük kadro, her ekleme, bırakma ve takas ile draft verisinden çıkarıldı. Hepsi 9 kategori değeriyle (maç başı z-skoru) ölçülür ve yedek seviyesindeki bir oyuncunun üstünde kalan kısım sayılır.`,
  jump:{trade:'Takaslar',bench:'Yedek',rival:'Rekabet',rec:'Rekorlar',waiver:'Waiver',regret:'Pişmanlık',draft:'Draft',pers:'Kişilik',inj:'Sakatlık'},
  mon:['Oca','Şub','Mar','Nis','May','Haz','Tem','Ağu','Eyl','Eki','Kas','Ara'],
  sl:{PTS:'sayı',REB:'rib',AST:'asist',STL:'top çalma',BLK:'blok','3PM':'üçlük'},
  w:w=>`H${w}`,val:'değer',games:n=>`${n} maç`,
  f:{game:'Sezonun maçı',waiver:'Waiver kahramanı',steal:'Draftın çalıntısı',regret:'En büyük pişmanlık',bench:'Yedek faciası',inj:'Revir'},
  fsub:{waiver:(t,d)=>`${t} · ${d} günü aldı`,steal:(p,r)=>`${p}. seçim, şu an draftın ${r}. en değerli oyuncusu`,regret:(t,d,n)=>`${t} ${d} günü bıraktı${n?` · şimdi ${n} kadrosunda`:' · hâlâ serbest'}`,bench:(t,d)=>`${t} bunu yedekte bıraktı · ${d}`,inj:'işe yarar oyuncuların kaçırdığı maç'},
  unit:{pts:'sayı',bench:'sayı yedekte',games:'maç'},
  trade:{h:'Takas karnesi',hint:'Her taraf, aldığı oyuncuların takastan sonra aktif kadroda ürettiği değer (%60) ve kalan sezon için şu anki değerleri (%40) ile notlanır.',none:'Bu sezon henüz takas yok. İlk takas gerçekleştiğinde burada notlanacak: kazanan, kaybeden ve sezonun soygunu.',got:'Aldı',since:'takastan beri',now:'kalan sezon değeri',heist:'Sezonun soygunu'},
  bench:{h:'Yedekte kalan puanlar',hint:'Her gün için, gerçekten oynayan oyunculardan kurulabilecek en iyi kurala uygun kadroyu (PG, SG, SF, PF, C, G, F, 3 UTIL) hesaplayıp gerçek kadroyla karşılaştırdık. Çubuk: yedekte kalan değer.',sub:(p,n)=>`${p} sayı yedekte · başlaması gereken ${n} maç`,lost:(w,s,o)=>`${w} maçını ${s} kaybetti, en iyi kadroyla ${o} kazanırdı`,worst:'En pahalı kadro kararları',none:'Yedek yüzünden kaybedilen maç yok.'},
  rival:{h:'Rekabetler',hint:'Elimizdeki tüm sezonlardaki ikili maçlar, menajere göre birleştirildi; ismi değişen takımın geçmişi kaybolmaz.',games:n=>`${n} maç`,cats:'kategori',blow:'En farklı skorlar',close:(a,b)=>`${b} maçın ${a} tanesi bir kategori farkla ya da beraberlikle bitti.`,owned:'Tek taraflı seriler'},
  rec:{h:'Rekorlar duvarı',hint:'Her kategoride en iyi ve en kötü tek hafta. Eski sezonlardan gelen rekorda sezon etiketi var.',low:'En kötü',games:'Tek maç rekorları (aktif kadroda)',day:'Bir günde en çok sayı',dayS:(t,d)=>`${t} · ${d}`},
  waiver:{h:'Waiver kahramanları',hint:'Alınan oyuncunun o takımın aktif kadrosunda ürettiği, yedek seviyesinin üstündeki değer.',kept:'hâlâ kadroda',gone:'sonra bırakıldı',king:'Waiver kralları',kingS:(n,g)=>`${n} ekleme · alınanlardan ${g} aktif maç`},
  regret:{h:'Bırakıp pişman olanlar',hint:'Oyuncunun bırakıldıktan sonra ürettiği değer (yeni takımında ya da serbestken).',now:n=>n?`şimdi ${n}`:'serbest'},
  draft:{h:'Draft karnesi',hint:'Her seçim, o sıradan beklenen değerle karşılaştırılır (bu sezon draft edilenler arasında n. en iyi oyuncunun değeri). Not: tüm draftın toplamı.',best:'En iyi seçim',worst:'En kötü erken seçim',steals:'Çalıntılar',busts:'Hayal kırıklıkları',pick:(p,r)=>`${p}. seçim → değerde ${r}.`},
  pers:{h:'Takım kişilikleri',hint:'Takımın kategori sıralamaları ve menajerin ne kadar hareketli olduğuna göre etiketler.',best:'En iyi',worst:'En kötü'},
  inj:{h:'Şanssız menajer endeksi',hint:'Kadrodaki oyuncunun NBA takımı oynarken kaçırdığı maçlar (sakatlık ya da dinlenme), oyuncunun değeriyle ağırlıklı.',sub:(n,w)=>`${n} kaçan maç${w?` · ${w}`:''}`},
  P:{paint:['Boya altı canavarı','Ribaund, blok ve FG% onun.'],rain:['Üçlük yağmuru','Sayı ve üçlük kovayla.'],dime:['Pas fabrikası','Asist ve top çalma ile oyunu kuruyor.'],thief:['Yankesici','Ligde en çok top çalan.'],line:['Çizgi ustası','Serbest atış çizgisinde yaşıyor ve sokuyor.'],puntft:['FT% punt','Uzun kategorileri için serbest atışı gözden çıkardı.'],puntto:['Top kaybı umurunda değil','Sayı ve asist için riski göze alıyor.'],careful:['Topu saklayanlar','En az top kaybı, pas biraz eksik olsa da.'],scorer:['Skor makinesi','Sayıda ligin zirvesinde.'],balanced:['Her işin adamı','Hiçbir kategoride büyük açık yok.'],grinder:['Waiver bağımlısı','Serbest oyuncu listesinden çıkmıyor.'],loyal:['Kur ve unut','Kadroya neredeyse hiç dokunmuyor.'],rebuild:['Seneye bakıyoruz','Her kategoride zorlanıyor.']}
};
function ord(n){const s=['th','st','nd','rd'],v=n%100;return s[(v-20)%10]||s[v]||s[0]}
const FN=DATA.fun;
const byOwner=Object.fromEntries(T.map(t=>[t.owner,t]));
const ownName=k=>{const t=byOwner[k];if(t)return t.name;const o=((DATA.history||{}).owners||[]).find(o=>o.key===k);return o?o.name:'?'};
const dstr=iso=>{if(!iso)return '';const [y,m,d]=iso.split('-').map(Number);return EN?`${FX.mon[m-1]} ${d}`:`${d} ${FX.mon[m-1]}`};
const sv=v=>(v>=0?'+':'')+Math.round(v);
function sl(l,max){if(!l)return '';const o=[`${Math.round(l.PTS)} ${FX.sl.PTS}`];
  [['REB',5],['AST',5],['3PM',3],['STL',2],['BLK',2]].forEach(([c,m])=>{if(l[c]>=m)o.push(`${Math.round(l[c])} ${FX.sl[c]}`)});return o.slice(0,max||4).join(' · ')}
function pg(g){if(!g)return '';return ['PTS','REB','AST','STL','BLK','3PM'].filter(c=>c==='PTS'||g[c]>=(c==='STL'||c==='BLK'?1.2:c==='3PM'?2:4)).slice(0,3).map(c=>`${g[c]} ${FX.sl[c]}`).join(' · ')}
const tnm=id=>esc((byId[id]||{}).name||'');
const tl=(id,s)=>byId[id]?`<a class="ft" href="${link(byId[id])}">${logo(byId[id],s||22)}<span>${tnm(id)}</span></a>`:'';
const gcls=g=>g[0]==='A'?'ga':g[0]==='B'?'gb':g[0]==='C'?'gc':'gd';
function fcard(cls,lab,big,unit,title,sub,team){return `<div class="fcard ${cls}"><div class="fl">${lab}</div><div class="fb">${big}${unit?`<small>${unit}</small>`:''}</div><div class="fn">${title}</div><div class="fs">${sub}</div>${team&&byId[team]?`<span class="flogo">${logo(byId[team],34)}</span>`:''}</div>`}
function fsec(id,h,hint,inner){return `<section class="sec" id="fx-${id}"><div class="sec-h"><h2>${h}</h2></div>${hint?`<p class="hint">${hint}</p>`:''}${inner}</section>`}
function hbar(v,max,col){return `<span class="hb"><i style="width:${Math.max(2,Math.min(100,v/max*100)).toFixed(0)}%;background:var(--${col||'accent'})"></i></span>`}

V.eglence=()=>{if(!FN)return `<div class="hero"><h2>${FX.title}</h2></div>`;
  const R=FN.records||{},bg=R.bestGame,wv=(FN.waiver||{}).top||[],dr=FN.draft||{},rg=FN.regrets||[],bw=FN.benchWorst||[],inj=FN.injury||[];
  // öne çıkanlar
  const cards=[];
  if(bg)cards.push(fcard('dark',FX.f.game,Math.round(bg.line.PTS),FX.unit.pts,esc(bg.name),`${sl(bg.line,5).split(' · ').slice(1).join(' · ')}<br>${tnm(bg.team)} · ${dstr(bg.date)}`,bg.team));
  if(wv[0])cards.push(fcard('acc',FX.f.waiver,sv(wv[0].val),FX.val,esc(wv[0].name),`${FX.fsub.waiver(tnm(wv[0].team),dstr(wv[0].date))}<br>${pg(wv[0].pg)}`,wv[0].team));
  if(dr.steals&&dr.steals[0]){const s=dr.steals[0];cards.push(fcard('cool',FX.f.steal,`${s.pick}<span class="arr">→</span>${s.rank}`,'',esc(s.name),`${tnm(s.team)}<br>${FX.fsub.steal(s.pick,s.rank)}`,s.team))}
  if(rg[0])cards.push(fcard('dark',FX.f.regret,sv(rg[0].val),FX.val,esc(rg[0].name),`${FX.fsub.regret(tnm(rg[0].team),dstr(rg[0].date),rg[0].now?tnm(rg[0].now):'')}<br>${FX.games(rg[0].n)} · ${pg(rg[0].pg)}`,rg[0].team));
  if(bw[0])cards.push(fcard('acc',FX.f.bench,Math.round(bw[0].line.PTS),FX.unit.bench,esc(bw[0].name),`${FX.fsub.bench(tnm(bw[0].team),dstr(bw[0].date))}<br>${sl(bw[0].line,5).split(' · ').slice(1).join(' · ')}`,bw[0].team));
  if(inj[0])cards.push(fcard('cool',FX.f.inj,inj[0].games,FX.unit.games,tnm(inj[0].team),`${FX.fsub.inj}<br>${inj[0].who.map(w=>`${esc(w.name)} ${w.n}`).join(', ')}`,inj[0].team));
  const jump=Object.entries(FX.jump).map(([k,v])=>`<button type="button" data-jump="fx-${k}">${v}</button>`).join('');
  return `<div class="hero"><span class="live" style="--x:0">${FX.kicker}</span><h2>${FX.title}</h2><p class="hint">${FX.intro(FN.days)}</p></div>
  <div class="chips fjump">${jump}</div>
  <div class="feat">${cards.join('')}</div>
  ${fxTrades()}${fxBench()}${fxRivals()}${fxRecords()}${fxWaiver()}${fxRegrets()}${fxDraft()}${fxPers()}${fxInj()}`};

function fxTrades(){const tr=FN.trades||[];
  if(!tr.length)return fsec('trade',FX.trade.h,'',`<div class="panel empty"><svg viewBox="0 0 24 24"><path d="M7 7h11l-3-3M17 17H6l3 3"/></svg><p>${FX.trade.none}</p></div>`);
  return fsec('trade',FX.trade.h,FX.trade.hint,tr.map((c,i)=>`<div class="panel trade">${i===0&&c.gap>0?`<div class="tbadge">${FX.trade.heist}</div>`:''}<div class="tdate">${dstr(c.date)}</div>
   <div class="tsides">${c.sides.map(s=>`<div class="tside"><div class="th">${tl(s.team,30)}<span class="grade ${gcls(s.grade)}">${s.grade}</span></div>
    <div class="tgot">${FX.trade.got}: ${s.got.map(p=>`<b>${esc(p.name)}</b>`).join(', ')}</div>
    <div class="tnum"><span><b class="${s.val>=0?'pos':'neg'}">${sv(s.val)}</b> ${FX.trade.since}</span><span><b>${sv(s.now)}</b> ${FX.trade.now}</span></div></div>`).join('')}</div></div>`).join(''))}

function fxBench(){const B=FN.bench||[];if(!B.length)return '';const mx=Math.max(1,...B.map(b=>b.gain));
  const rows=B.map(b=>`<div class="frow">${logo(byId[b.team],34)}<div class="fm"><a class="nm" href="${link(byId[b.team])}">${tnm(b.team)}</a><small>${FX.bench.sub(b.pts,b.games)}</small>
   ${b.lost.map(l=>`<span class="pill down">${FX.bench.lost(FX.w(l.w),l.score,l.opt)}</span>`).join(' ')}</div><div class="fv"><b>${Math.round(b.gain)}</b>${hbar(b.gain,mx,'cool')}</div></div>`).join('');
  const worst=(FN.benchWorst||[]).map((w,i)=>`<div class="frow"><span class="rk">${i+1}</span><div class="fm"><b>${esc(w.name)}</b><small>${tnm(w.team)} · ${dstr(w.date)}</small><small class="line">${sl(w.line,5)}</small></div><div class="fv"><b>${sv(w.val)}</b></div></div>`).join('');
  return fsec('bench',FX.bench.h,FX.bench.hint,`<div class="panel">${rows}</div><h3 class="fh3">${FX.bench.worst}</h3><div class="panel">${worst}</div>`)}

function fxRivals(){const rv=FN.rivals||[],bl=FN.blowouts||[];
  const side=(k)=>{const t=byOwner[k];return t?`<a class="vs-t" href="${link(t)}">${logo(t,32)}<span>${esc(t.name)}</span></a>`:`<span class="vs-t"><span class="logo" style="width:32px;height:32px"></span><span>${esc(ownName(k))}</span></span>`};
  const rows=rv.map(p=>{const tot=p.cats[0]+p.cats[1]||1;return `<div class="vs">${side(p.a)}<div class="vs-m"><div class="vs-r"><span class="${p.w[0]>p.w[1]?'lead':''}">${p.w[0]}</span>–<span class="${p.w[1]>p.w[0]?'lead r':''}">${p.w[1]}</span>${p.w[2]?`<small>–${p.w[2]}</small>`:''}</div>
   <div class="vs-b"><i style="width:${(p.cats[0]/tot*100).toFixed(0)}%"></i></div><small>${p.cats[0]}–${p.cats[1]} ${FX.rival.cats} · ${FX.rival.games(p.n)}</small></div>${side(p.b)}</div>`}).join('');
  const nm=(g,s)=>g[s==='a'?'ta':'tb']&&byId[g[s==='a'?'ta':'tb']]?esc(byId[g[s==='a'?'ta':'tb']].name):esc(g[s==='a'?'an':'bn']);
  const blow=bl.map(g=>{const aw=g.s[0]>g.s[1];return `<div class="blow"><span class="bs">${Math.max(...g.s)}–${Math.min(...g.s)}</span><div class="fm"><b>${aw?nm(g,'a'):nm(g,'b')}</b><small>${EN?'over ':''}${aw?nm(g,'b'):nm(g,'a')}${EN?'':' karşısında'} · ${FX.w(g.w)}${g.y&&g.y!==DATA.history.seasons.slice(-1)[0]?` · ${g.y-1}-${String(g.y).slice(2)}`:''}</small></div></div>`}).join('');
  const own=(FN.owned||[]).map(p=>{const a=p.w[0]>p.w[1];return `<div class="frow"><div class="fm"><b>${esc(ownName(a?p.a:p.b))}</b><small>${esc(ownName(a?p.b:p.a))} · ${Math.max(p.w[0],p.w[1])}–${Math.min(p.w[0],p.w[1])}</small></div></div>`}).join('');
  return fsec('rival',FX.rival.h,FX.rival.hint,`<div class="panel">${rows}</div><h3 class="fh3">${FX.rival.blow}</h3><div class="blows">${blow}</div><p class="hint">${FX.rival.close(FN.closeCount,FN.nGames)}</p>${own?`<h3 class="fh3">${FX.rival.owned}</h3><div class="panel">${own}</div>`:''}`)}

function fxRecords(){const R=FN.records||{},W=R.week||{};
  const fv=(c,v)=>c.includes('%')?v.toFixed(3).replace(/^0/,''):Math.round(v);
  const who=r=>`${r.team&&byId[r.team]?esc(byId[r.team].name):esc(r.name)} · ${FX.w(r.w)}${r.cur?'':` · ${r.y-1}-${String(r.y).slice(2)}`}`;
  const tiles=DATA.cats.filter(c=>W[c]).map(c=>`<div class="rtile"><span class="k">${c}</span><span class="v">${fv(c,W[c].best.v)}</span><span class="s">${who(W[c].best)}</span><span class="lo">${FX.rec.low}: ${fv(c,W[c].worst.v)} · ${who(W[c].worst)}</span></div>`).join('');
  const G=R.game||{};
  const gt=['PTS','REB','AST','3PM','STL','BLK'].filter(c=>G[c]).map(c=>`<div class="rtile g"><span class="k">${FX.sl[c]}</span><span class="v">${Math.round(G[c].v)}</span><span class="s"><b>${esc(G[c].name)}</b></span><span class="lo">${tnm(G[c].team)} · ${dstr(G[c].date)}</span></div>`).join('');
  const d=R.day;
  return fsec('rec',FX.rec.h,FX.rec.hint,`<div class="rgrid">${tiles}</div><h3 class="fh3">${FX.rec.games}</h3><div class="rgrid">${gt}${d?`<div class="rtile g"><span class="k">${FX.rec.day}</span><span class="v">${d.v}</span><span class="s"><b>${tnm(d.team)}</b></span><span class="lo">${dstr(d.date)}</span></div>`:''}</div>`)}

function prow2(i,name,sub,line,val,team){return `<div class="frow"><span class="rk">${i}</span><div class="fm"><b>${name}</b><small>${sub}</small>${line?`<small class="line">${line}</small>`:''}</div><div class="fv"><b class="${val>=0?'pos':'neg'}">${sv(val)}</b>${team&&byId[team]?logo(byId[team],22):''}</div></div>`}
function fxWaiver(){const W=FN.waiver||{};if(!W.top)return '';
  const top=W.top.map((a,i)=>prow2(i+1,esc(a.name),`${tnm(a.team)} · ${dstr(a.date)} · ${FX.games(a.n)} · ${a.kept?FX.waiver.kept:FX.waiver.gone}`,pg(a.pg),a.val,a.team)).join('');
  const mx=Math.max(1,...W.teams.map(t=>t.val));
  const kings=W.teams.map(t=>`<div class="frow">${logo(byId[t.team],30)}<div class="fm"><a class="nm" href="${link(byId[t.team])}">${tnm(t.team)}</a><small>${FX.waiver.kingS(t.adds,t.n)}</small></div><div class="fv"><b>${sv(t.val)}</b>${hbar(t.val,mx)}</div></div>`).join('');
  return fsec('waiver',FX.waiver.h,FX.waiver.hint,`<div class="panel">${top}</div><h3 class="fh3">${FX.waiver.king}</h3><div class="panel">${kings}</div>`)}

function fxRegrets(){const R=FN.regrets||[];if(!R.length)return '';
  return fsec('regret',FX.regret.h,FX.regret.hint,`<div class="panel">${R.map((r,i)=>prow2(i+1,esc(r.name),`${tnm(r.team)} · ${dstr(r.date)} · ${FX.regret.now(r.now?tnm(r.now):'')}`,`${FX.games(r.n)} · ${pg(r.pg)}`,r.val,r.team)).join('')}</div>`)}

function fxDraft(){const D=FN.draft;if(!D)return '';
  const cards=D.teams.map(g=>`<a class="dcard" href="${link(byId[g.team])}"><span class="grade big ${gcls(g.grade)}">${g.grade}</span><div class="fm"><div class="nm">${tnm(g.team)}</div>
   <small>${FX.draft.best}: <b>${esc(g.best.name)}</b> (${FX.draft.pick(g.best.pick,g.best.rank)})</small>${g.worst?`<small>${FX.draft.worst}: <b>${esc(g.worst.name)}</b> (${FX.draft.pick(g.worst.pick,g.worst.rank)})</small>`:''}</div></a>`).join('');
  const li=(arr)=>arr.map((d,i)=>prow2(i+1,esc(d.name)+(d.inj?` <span class="pill down">${d.inj}</span>`:''),`${tnm(d.team)} · ${FX.draft.pick(d.pick,d.rank)}`,`${FX.games(d.n)} · ${pg(d.pg)}`,d.val,d.team)).join('');
  return fsec('draft',FX.draft.h,FX.draft.hint,`<div class="dgrid">${cards}</div><div class="two"><div><h3 class="fh3">${FX.draft.steals}</h3><div class="panel">${li(D.steals)}</div></div><div><h3 class="fh3">${FX.draft.busts}</h3><div class="panel">${li(D.busts)}</div></div></div>`)}

function fxPers(){const P=FN.personality||{};
  const cards=T.filter(t=>P[t.id]).map(t=>{const p=P[t.id],L=FX.P[p.labels[0]]||['',''];return `<a class="pcard" href="${link(t)}"><div class="ph">${logo(t,40)}<div><div class="pl1">${L[0]}</div><div class="nm">${esc(t.name)}</div></div></div>
   <p>${L[1]}${p.labels[1]&&FX.P[p.labels[1]]?` <span class="pill flat">${FX.P[p.labels[1]][0]}</span>`:''}</p>
   <div class="pc"><span>${FX.pers.best}</span>${p.best.map(c=>`<span class="pill up">${c}</span>`).join('')}<span>${FX.pers.worst}</span>${p.worst.map(c=>`<span class="pill down">${c}</span>`).join('')}</div></a>`}).join('');
  return fsec('pers',FX.pers.h,FX.pers.hint,`<div class="pgrid">${cards}</div>`)}

function fxInj(){const I=FN.injury||[];if(!I.length)return '';const mx=Math.max(1,...I.map(x=>x.val));
  return fsec('inj',FX.inj.h,FX.inj.hint,`<div class="panel">${I.map((x,i)=>`<div class="frow"><span class="rk">${i+1}</span>${logo(byId[x.team],30)}<div class="fm"><a class="nm" href="${link(byId[x.team])}">${tnm(x.team)}</a><small>${FX.inj.sub(x.games,x.who.map(w=>`${esc(w.name)} ${w.n}`).join(', '))}</small></div><div class="fv"><b>${Math.round(x.val)}</b>${hbar(x.val,mx,'bad')}</div></div>`).join('')}</div>`)}
