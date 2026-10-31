'use strict';
const $=id=>document.getElementById(id), colors=['#e77e70','#e7c859','#627fdf','#75bd83','#eeeade'];
let current=null, count=0, index=0, request=0, timer=null;
let matchList=[],shownMatches=20,listRequest=0,statsRequest=0,playingBusy=false;
const snapshotCache=new Map();
const chineseDate=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date());
const localTime=value=>new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
let catalog={cards:{},tiles:{},achievements:{},heroes:{},slots:{},treasures:{},tags:{}};
const cardInfo=id=>catalog.cards[String(id)]||{};
const tileInfo=key=>catalog.tiles[key]||{};
const heroInfo=key=>catalog.heroes[key]||{};
const slotName=key=>(catalog.slots[key]||{}).name||key;
const tagName=key=>(catalog.tags[key]||key);
const treasureName=key=>(catalog.treasures[key]||{}).name||key;
const text=(tag,value,cls)=>{const el=document.createElement(tag);el.textContent=value;if(cls)el.className=cls;return el;};
async function api(path){const r=await fetch(path);if(!r.ok)throw Error('无法读取回放，请刷新后重试。');return r.json();}
function stop(){clearInterval(timer);timer=null;$('play').textContent='播放';}
function renderMatches(){const needle=$('match-search').value.trim().toLowerCase(),state=$('match-status').value;const list=matchList.filter(m=>(!state||m.status===state)&&(!needle||[m.room,...(m.preview?.players||[]).flatMap(p=>[p.name,p.hero_name])].join(' ').toLowerCase().includes(needle)));$('matches').replaceChildren();$('match-count').textContent=`${list.length} 场`;$('more-matches').hidden=list.length<=shownMatches;
 if(!list.length)$('matches').append(text('p','没有符合条件的对局。试试全部日期或清除筛选。','hint'));
 for(const m of list.slice(0,shownMatches)){const b=text('button',m.room,'match');b.classList.toggle('active',m.id===current);b.append(text('small',localTime(m.created)),text('small',`${m.status} · ${m.preview?.players.length||0}人 · ${m.count}步`));for(const p of m.preview?.players||[])b.append(text('small',`P${p.seat} ${p.name} · ${p.hero_name}（${p.variant==='black'?'黑':'白'}）`));const names=m.preview?.winner_names||[];b.append(text('strong',names.length?`获胜：${names.join('、')}`:m.status==='已中断'?'对局中断 · 不计胜率':m.preview?.mode==='solo'&&m.preview?.finished?'单人挑战已结束':'尚未决出获胜者','match-winner'));b.onclick=()=>select(m.id);$('matches').append(b);}}
async function refresh(){const token=++listRequest;const day=$('match-date').value||'all';$('archive-status').textContent='正在更新对局…';try{const list=await api('/api/replays?date='+encodeURIComponent(day));if(token!==listRequest)return;matchList=list;renderMatches();const finished=list.filter(m=>m.preview?.finished).length,ongoing=list.filter(m=>m.status==='进行中').length;$('daily-summary').replaceChildren(...[[day==='all'?'全部对局':'当日对局',list.length],['已结束',finished],['进行中',ongoing],['已中断',list.filter(m=>m.status==='已中断').length]].map(([label,n])=>{const card=text('div','','metric');card.append(text('strong',n),text('span',label));return card;}));$('archive-status').textContent=`${day==='all'?'全部日期':day} · 北京时间 · 已更新`;if(current){const m=list.find(x=>x.id===current);if(m){count=m.count;$('slider').max=Math.max(0,count-1);}}await refreshStats();}catch(e){if(token===listRequest)$('archive-status').textContent=e.message;}}
function statTable(rows,hero=false){if(!rows.length)return text('p','暂无可统计的已结束多人对局。','hint');const table=document.createElement('table');const head=document.createElement('thead'),tr=document.createElement('tr');for(const name of [hero?'角色':'位次','场次','获胜','胜率'])tr.append(text('th',name));head.append(tr);table.append(head);const body=document.createElement('tbody');for(const row of rows){const line=document.createElement('tr');for(const value of [hero?`${row.name}（${row.variant==='black'?'黑版':'白版'}）`:row.position===1?'第1位':`第${row.position}位`,row.games,row.wins,`${row.win_rate.toFixed(1)}%`])line.append(text('td',value));body.append(line);}table.append(body);return table;}
async function refreshStats(){const token=++statsRequest;const day=$('stats-period').value==='selected'?$('match-date').value||'all':'all';const players=$('stats-players').value;try{const data=await api(`/api/statistics?date=${encodeURIComponent(day)}${players?'&players='+players:''}`);if(token!==statsRequest)return;$('statistics-note').textContent=data.note;$('statistics-status').textContent=`统计 ${data.matches} 场已结束多人对局 · ${day==='all'?'全部日期':day}`;$('position-stats').replaceChildren(statTable(data.positions));$('hero-stats').replaceChildren(statTable(data.heroes,true));}catch(e){if(token===statsRequest)$('statistics-status').textContent=e.message;}}
async function select(id){stop();current=id;const token=++request;try{const m=await api('/api/replays/'+id);if(token!==request)return;if(m.catalog)catalog=m.catalog;count=m.count;history.replaceState(null,'','#replay='+id);$('title').textContent=m.room;$('status').textContent=`${m.status} · ${localTime(m.created)} · 完整视角：全体公会的看板娘、手牌、板块与发展均已解封`;$('slider').max=Math.max(0,count-1);$('slider').disabled=!count;$('play').disabled=!count;$('last').disabled=!count;await show(0);renderMatches();}catch(e){if(token===request)$('status').textContent=e.message;}}
async function snapshot(id,n){const key=id+':'+n;if(snapshotCache.has(key))return snapshotCache.get(key);const data=await api(`/api/replays/${id}/steps/${n}`);snapshotCache.set(key,data);while(snapshotCache.size>48)snapshotCache.delete(snapshotCache.keys().next().value);return data;}
function svg(tag,attrs,value){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(value!==undefined)el.textContent=value;return el;}
function render(game){
 const map=$('map');map.replaceChildren();
 const defs=svg('defs',{});map.append(defs);
 const xs=game.board.map(c=>c.q+c.r/2),ys=game.board.map(c=>c.r);
 const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
 const step=Math.min(82,780/(maxX-minX+1.25),610/((maxY-minY)*.866+1.25));
 const centerX=420-step*(maxX+minX)/2,centerY=335-step*.866*(maxY+minY)/2;
 for(const c of game.board){
  const x=centerX+step*(c.q+c.r/2),y=centerY+step*.866*c.r;
  const owned=c.owner!==null&&c.owner!==undefined,seat=game.players.findIndex(p=>p.id===c.owner),tokenColor=Number.isInteger(c.owner)?((c.owner%5)+5)%5:Math.max(0,seat)%5,color=owned?colors[tokenColor]:'#806537';
  const g=svg('g',{}),radius=step*.52;
  const points=Array.from({length:6},(_,i)=>{const a=(i*60-30)*Math.PI/180;return `${x+radius*Math.cos(a)},${y+radius*Math.sin(a)}`;}).join(' ');
  g.append(svg('polygon',{points,fill:c.forest?'#343721':owned?'#46361c':c.revealed?'#49391e':'#282014'}));
  const info=c.loot?tileInfo(c.loot):{},clipId=`tile-${String(c.id).replace(/[^A-Za-z0-9_-]/g,'-')}`;
  if(owned){
   g.classList.add('occupied');g.dataset.owner=String(c.owner);
   g.append(svg('image',{href:`/assets/tokens/${c.base?'base':'adventurer'}-${tokenColor}.png`,x:x-radius*.68,y:y-radius*.8,width:radius*1.36,height:radius*1.36,preserveAspectRatio:'xMidYMid meet',class:'owner-token'}));
  }else if(c.revealed&&info.art){
   const clip=svg('clipPath',{id:clipId});clip.append(svg('polygon',{points}));defs.append(clip);
   g.append(svg('image',{href:info.art,x:x-radius,y:y-radius,width:radius*2,height:radius*2,preserveAspectRatio:'xMidYMid slice','clip-path':`url(#${clipId})`}));
   g.classList.add('zoomable');g.onclick=()=>openLightbox(info.art,null,info.name||c.name||'迷宫板块');
  }
  g.append(svg('polygon',{points,fill:'none',stroke:game.pending?.target===c.id?'#e1bc80':color,'stroke-width':game.pending?.target===c.id?5:2}));
  const dragon=game.dragon?.active&&game.dragon.tile===c.id;
  const name=c.blocked?'禁止进入':c.forest?'魔之森':dragon?'潜行之龙':owned?(c.base?'据点':'营地'):(c.revealed?(c.name||'已揭示'):(c.boss?'魔王 · 背面':'未探索'));
  g.append(svg('title',{},`${name} (${c.q}, ${c.r}) · 区域声望 ${c.region||c.point||0}`));
  if(!owned)g.append(svg('text',{x,y:y-5,'font-size':Math.max(9,step*.14)},name.length>7?name.slice(0,7):name));
  g.append(svg('text',{x,y:y+(owned?radius*.83:12),'font-size':Math.max(9,step*.15)},owned?`P${seat+1} · ${c.base?'据点':'冒险者'}`:'★'.repeat(Math.min(c.visible_star||c.star||0,7))));
  if(!owned)g.append(svg('text',{x,y:y+26,class:'coord'},`${c.q},${c.r}`));map.append(g);
 }
$('phase').textContent=`第 ${game.round} 季 · ${['春','夏','秋','冬'][game.season]||''} · ${({draft:'开局轮抽',research:'情报收集',action:'公会行动',final:'最终阶段',finished:'已结束'})[game.phase]||game.phase}`;
renderShared(game);renderSeats(game);$('log').replaceChildren(...game.log.slice().reverse().map(e=>text('li',e.message)));}
function el(tag,value,cls){const node=document.createElement(tag);if(value!==undefined)node.textContent=value;if(cls)node.className=cls;return node;}
function chip(label,cls,title){const node=el('span',label,'chip'+(cls?' '+cls:''));if(title)node.title=title;return node;}
function chipRow(title,items,open){const box=el('details','','pc-block');if(open)box.open=true;const sum=el('summary');sum.append(document.createTextNode(title+' '),el('b',String(items.length)));box.append(sum);const wrap=el('div','','chips');wrap.append(...(items.length?items:[el('span','—','muted')]));box.append(wrap);return box;}
function artChip(label,cls,full,thumb){const node=el('span',undefined,'chip '+cls);const img=el('img');img.className='chip-art';img.alt='';img.loading='lazy';img.src=thumb;img.onerror=()=>img.remove();img.onload=()=>{node.classList.add('zoomable');node.tabIndex=0;node.setAttribute('role','button');node.title=label+' · 点击放大';node.onclick=()=>openLightbox(full,thumb,label);node.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();openLightbox(full,thumb,label);}};};node.append(img,el('span',label));return node;}
function cardChips(ids,showPrice){return ids.map(id=>{const info=cardInfo(id);const label=(info.name||('事件卡 '+id))+(showPrice&&info.price?` (${info.price})`:'');const meta=(info.tags||[]).map(tagName).join('/');if(typeof info.image!=='number')return chip(label,'card',meta);return artChip(meta?`${label} · ${meta}`:label,'card',`/assets/cards/${info.image}.jpg`,`/assets/cardthumbs/${info.image}.jpg`);});}
function achChips(keys){return keys.map(key=>{const info=catalog.achievements[key]||{},label=info.name||key;return typeof info.image==='number'?artChip(label,'ach',`/assets/cards/${info.image}.jpg`,`/assets/cardthumbs/${info.image}.jpg`):chip(label,'ach');});}
function tileChips(keys){return keys.map(key=>{const info=tileInfo(key),label=info.name||key,node=el('span',undefined,'chip tile');if(info.art){const img=el('img');img.className='chip-art';img.alt='';img.loading='lazy';img.src=info.art;img.onerror=()=>img.remove();img.onload=()=>{node.classList.add('zoomable');node.tabIndex=0;node.setAttribute('role','button');node.title=label+' · 点击放大';node.onclick=()=>openLightbox(info.art,null,label);};node.append(img);}node.append(el('span',label));if(info.star)node.append(el('i','★'.repeat(info.star)));return node;});}
function openLightbox(full,thumb,title){const box=$('lightbox'),img=$('lightbox-img');$('lightbox-title').textContent=title||'';img.dataset.fallback='';img.onerror=()=>{if(thumb&&img.dataset.fallback!=='1'){img.dataset.fallback='1';img.src=thumb;}else img.onerror=null;};img.src=full;box.hidden=false;$('lightbox-close').focus();}
function closeLightbox(){$('lightbox').hidden=true;$('lightbox-img').removeAttribute('src');}
function face(player){const hero=heroInfo(player.hero),box=el('div','','pc-face');const fallback=()=>{box.replaceChildren(el('span',(hero.name||player.name||'?').slice(0,1)));};if(hero.portrait){const img=el('img');img.src=hero.portrait;img.alt=hero.name||'看板娘';img.loading='lazy';img.onerror=fallback;box.append(img);}else fallback();return box;}
function statList(entries){const list=el('ul','','pc-res');for(const [key,value] of entries){const li=el('li');li.append(el('span',key,'pc-k'),el('b',String(value)));list.append(li);}return list;}
const SCORE_LABELS={hero:'看板娘',grid:'疆域',loot:'板块',cards:'事件',achievements:'成就',reputation:'额外',treasures:'宝物',retreat:'撤退'};
function seatCard(game,player,seat){const hero=heroInfo(player.hero);const card=el('article','','pc');card.style.setProperty('--pc',colors[seat%5]);
 const top=el('div','','pc-top'),ident=el('div','','pc-ident');
 ident.append(el('h3',`P${player.id+1} ${player.name}`),el('p',`看板娘 · ${hero.name||player.hero}（${hero.variant==='black'?'黑版':'白版'}）· Lv${player.hero_level||1}`,'pc-hero'),el('p',`声望 ${player.score} · 已打出 ${(player.played||[]).length} · 板块 ${(player.tiles||[]).length}`,'pc-score'));
 top.append(face(player),ident,el('span',`#${seat+1}`,'pc-seat'));
 card.append(top);
 card.append(statList([['金币',player.gold],['力量',player.strength],['秘药',player.pot],['金币产能',player.gold_pro],['力量产能',player.str_pro],['秘药产能',player.pot_pro],['好感',`${'♥'.repeat(player.affection||0)||'♡'}`],['冒险者',player.available],['宝石',player.gems||0],['庆典',player.festival_tokens||0],['贡献',player.contribution||0]]));
 const breakdown=player.score_breakdown||{};card.append(el('p',Object.keys(SCORE_LABELS).filter(key=>breakdown[key]).map(key=>`${SCORE_LABELS[key]} ${breakdown[key]}`).join(' · ')||'尚无计分','pc-breakdown'));
 card.append(chipRow('手牌',player.hand?cardChips(player.hand,true):[],true));
 if((player.offered||[]).length)card.append(chipRow('保留情报',cardChips(player.offered),false));
 card.append(chipRow('已打出',cardChips(player.played||[]),false));
 card.append(chipRow('迷宫板块',tileChips(player.tiles||[]),false));
 if((player.private_tiles||[]).length)card.append(chipRow('私人板块',tileChips(player.private_tiles),false));
 card.append(chipRow('私人王权',achChips(player.achievements||[]),false));
 card.append(chipRow('已完成王权',achChips(player.earned_achievements||[]),false));
 card.append(chipRow('宝物',(player.treasures||[]).map(key=>chip(treasureName(key),'treasure')),false));
 const owned=player.developed_slots||player.developed||[];
 const slots=owned.map(key=>chip(slotName(key),'slot'));
 Object.keys(game.rules?.development_slots||{}).filter(key=>!owned.includes(key)).forEach(key=>slots.push(chip('未发展 · '+slotName(key),'slot muted')));
 card.append(chipRow('发展',slots,false));
 const tags=Object.entries(player.tag_counts||{}).map(([key,value])=>chip(`${tagName(key)} ${value}`,'tag'));
 if(tags.length)card.append(chipRow('标记',tags,false));
 if(game.phase==='final')card.append(el('p',`终局剩余行动 ${game.final_remaining[seat]||0} 次`,'pc-note'));
 if(game.options?.solo&&seat===0)card.append(el('p',`单人第 ${game.round} / 6 轮 · ${game.solo_rank||'挑战中'}`,'pc-note'));
 return card;}
function renderSeats(game){const grid=$('players');grid.replaceChildren();grid.style.setProperty('--seats',Math.max(1,Math.min(5,game.players.length)));game.players.forEach((player,seat)=>grid.append(seatCard(game,player,seat)));if(!game.players.length)grid.append(el('p','该步骤没有玩家数据。','muted'));}
function renderShared(game){const legend=$('legend');legend.replaceChildren(el('h3','座位与地图颜色','side-title'));game.players.forEach((player,seat)=>{const row=el('div','','legend-row'),dot=el('span','','legend-dot');dot.style.background=colors[seat%5];row.append(dot,el('span',`P${player.id+1} ${heroInfo(player.hero).name||player.name}`));legend.append(row);});
 const side=$('shared');side.replaceChildren(el('h3','公共状态','side-title'));
 [['回合',`第 ${game.round} 季 · ${['春','夏','秋','冬'][game.season]||''}`],['文明',game.civ],['瘴气',game.miasma],['当前行动',game.players[game.turn]?`P${game.players[game.turn].id+1} ${game.players[game.turn].name}`:'—'],['公共王权',(game.public_achievements||[]).length],['可购宝物',(game.treasures_available||[]).length]].forEach(([key,value])=>{const line=el('p');line.append(el('span',key,'pc-k'),el('b',String(value)));side.append(line);});
 if(game.pending)side.append(el('p',`等待处理：${game.pending.title||'进行中'}`,'pc-note'));
 if(game.dragon?.active)side.append(el('p',`潜行之龙已现身（${game.dragon.tile}）`,'pc-note'));}
async function show(n){if(!current||!count)return;n=Math.max(0,Math.min(count-1,Number(n)));index=n;const token=++request;$('slider').value=n;$('step').textContent=`${n+1} / ${count}`;$('prev').disabled=n===0;$('next').disabled=n===count-1;try{const s=await snapshot(current,n);if(token!==request)return;render(s.game);$('event').textContent=s.label;if(n===count-1)stop();}catch(e){if(token===request){stop();$('status').textContent=e.message;}}}
let sliderFrame=0;$('slider').oninput=e=>{stop();cancelAnimationFrame(sliderFrame);const value=e.target.value;sliderFrame=requestAnimationFrame(()=>show(value));};$('prev').onclick=()=>{stop();show(index-1);};$('next').onclick=()=>{stop();show(index+1);};$('last').onclick=()=>{stop();show(count-1);};$('refresh').onclick=refresh;$('lightbox-close').onclick=closeLightbox;$('lightbox').onclick=event=>{if(event.target===$('lightbox'))closeLightbox();};document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('lightbox').hidden)closeLightbox();});$('play').onclick=async()=>{if(timer){stop();return;}if(index===count-1)await show(0);$('play').textContent='暂停';timer=setInterval(async()=>{if(playingBusy)return;playingBusy=true;try{await show(index+1);}finally{playingBusy=false;}},Number($('speed').value));};$('speed').onchange=()=>{if(timer){stop();$('play').click();}};
$('match-date').value=chineseDate();$('match-date').onchange=()=>{shownMatches=20;refresh();};$('today').onclick=()=>{$('match-date').value=chineseDate();shownMatches=20;refresh();};$('all-days').onclick=()=>{$('match-date').value='';shownMatches=20;refresh();};$('match-status').onchange=renderMatches;$('match-search').oninput=renderMatches;$('more-matches').onclick=()=>{shownMatches+=20;renderMatches();};$('stats-period').onchange=refreshStats;$('stats-players').onchange=refreshStats;
const replayHash=location.hash.match(/^#replay=([a-f0-9]{32})$/);refresh();if(replayHash)select(replayHash[1]);setInterval(()=>{if(!document.hidden)refresh();},30000);
