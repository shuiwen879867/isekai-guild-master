'use strict';
const $=id=>document.getElementById(id);
const DOWNLOAD_MESSAGE='加群2155021664下载';
// Register before fetching configuration: downloads remain group-only even
// when the API is unavailable or returns a stale package list.
document.querySelectorAll('a[href="#download"]').forEach(link=>{
 link.removeAttribute('download');
 link.addEventListener('click',event=>{event.preventDefault();window.alert(DOWNLOAD_MESSAGE);});
});
function copyText(value){
 if(navigator.clipboard&&window.isSecureContext)return navigator.clipboard.writeText(value);
 return new Promise((resolve,reject)=>{
  const area=document.createElement('textarea');
  area.value=value;area.setAttribute('readonly','');
  area.style.position='fixed';area.style.top='-1000px';area.style.opacity='0';
  document.body.appendChild(area);area.select();area.setSelectionRange(0,value.length);
  let succeeded=false;
  try{succeeded=document.execCommand('copy');}catch(ignored){succeeded=false;}
  document.body.removeChild(area);
  if(succeeded)resolve();else reject(new Error('copy failed'));
 });
}
function selectNode(node){
 const range=document.createRange();range.selectNodeContents(node);
 const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
}
const QQ_NODES=['hero-qq','qq-group','notice-qq','notice-qq-2','footer-qq'];
function renderContact(group){
 const number=(group||'').trim()||'未设置';
 QQ_NODES.forEach(id=>{const node=$(id);if(node){node.textContent=number;node.title='点击全选群号';}});
 const button=$('copy-qq');
 if(!button)return;
 if(number==='未设置'){button.disabled=true;button.textContent='未设置群号';return;}
 const restore=()=>setTimeout(()=>{button.textContent='复制群号';},1800);
 button.onclick=()=>{copyText(number).then(()=>{button.textContent='已复制群号';},()=>{button.textContent='请手动框选群号';}).then(restore);};
}
function render(config){
 const version=config.version||'';
 document.title=`${config.name||'异世界公会长'} · 对战器网站`;
 $('version').textContent=version?('版本 '+version):'';
 $('footer-version').textContent=version||'—';
 if(config.tagline)$('tagline').textContent=config.tagline;
 if(config.requirements)$('requirements').textContent=config.requirements;
 if(config.notice)$('footer-notice').textContent=config.notice;
 renderContact(config.qq_group);
 const host=location.hostname||config.server_host||'localhost';
 $('game-addr').textContent=`${config.server_host||host}:${config.game_port||6677}`;
 $('game-port').textContent=String(config.game_port||6677);
 $('replay-port').textContent=String(config.replay_port||6767);
 const replay=$('replay-link'),replayAddress=$('replay-address');
 const replayUrl=`${location.protocol}//${host}:${config.replay_port||6767}/`;
 if(config.replay_enabled===false){
  [replay,replayAddress].forEach(node=>{node.removeAttribute('href');node.classList.add('disabled');node.textContent='回放网站已关闭';});
 }else{
  replay.href=replayUrl;replayAddress.href=replayUrl;replayAddress.textContent=replayUrl;
  $('replay-today-link').href=replayUrl+'#archive';$('replay-stats-link').href=replayUrl+'#statistics';
 }
 if(config.replay_enabled===false){for(const id of ['replay-today-link','replay-stats-link']){$(id).removeAttribute('href');$(id).textContent='回放网站已关闭';}}

}
fetch('/api/site').then(response=>{
 if(!response.ok)throw new Error('HTTP '+response.status);
 return response.json();
}).then(render).catch(()=>{renderContact('2155021664');});

async function refreshLive(){try{const response=await fetch('/api/status');if(!response.ok)throw Error();const data=await response.json();$('live-status').textContent=`在线连接 ${data.connected_people||0} 人 · 进行中 ${data.active_room_count||0} 间 · 在线玩家 ${data.active_online_player_count||0} 人`;$('live-rooms').replaceChildren();for(const room of data.rooms||[]){const card=document.createElement('p');card.textContent=`${room.name||'公会房间'} · 第${room.round||1}季 · ${(room.players||[]).map(p=>p.name).join('、')}`;$('live-rooms').append(card);}if(!(data.rooms||[]).length)$('live-rooms').textContent='当前没有正在游玩的房间。';}catch(ignored){$('live-status').textContent='暂时无法读取实时状态，请稍后刷新。';}}
refreshLive();setInterval(()=>{if(!document.hidden)refreshLive();},30000);
document.querySelectorAll('img').forEach(image=>{image.decoding='async';});
