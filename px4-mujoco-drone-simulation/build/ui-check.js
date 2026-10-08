
let ws,keys=new Set(),keyboard=false;
const $=id=>document.getElementById(id);
const valid=new Set(['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','KeyR','KeyF','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Space','Escape']);
function send(action,cameraStep,extra={}){if(ws?.readyState===1)ws.send(JSON.stringify({keys:[...keys],action:action||null,camera_step:cameraStep||null,...extra}));}
function focusKeyboard(enabled){keyboard=enabled;keys.clear();$('focus').textContent=enabled?'Keyboard active':'Keyboard inactive';$('keyboard').textContent=enabled?'Release keyboard':'Enable keyboard';send();}
$('keyboard').onclick=()=>focusKeyboard(!keyboard);
$('takeoff').onclick=()=>{send('takeoff');focusKeyboard(true);};
$('reset').onclick=()=>{focusKeyboard(false);$('reset').disabled=true;send('reset');};
document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{if(b.dataset.action==='hover')keys.clear();send(b.dataset.action);});
function changeWind(){const seed=Number($('seed').value);if(!Number.isInteger(seed)||seed<0||seed>=4294967296){$('seed').reportValidity();return;}send(null,null,{environment:{profile:$('wind').value,seed,direction_deg:Number($('direction').value)}});}
for(const id of ['wind','direction','seed'])$(id).addEventListener('change',changeWind);
$('world').addEventListener('wheel',event=>{event.preventDefault();const delta=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?450:1);send(null,null,{zoom:Math.max(-500,Math.min(500,delta))});},{passive:false});
window.addEventListener('keydown',e=>{if(!keyboard||!valid.has(e.code))return;e.preventDefault();if(e.code==='Escape'){focusKeyboard(false);return;}if(e.code==='Space'){keys.clear();send('hover');return;}keys.add(e.code);const step=e.repeat?null:({ArrowLeft:[1,0],ArrowRight:[-1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.code]||null);send(null,step);});
window.addEventListener('keyup',e=>{if(valid.has(e.code)){keys.delete(e.code);if(keyboard)e.preventDefault();send();}});
window.addEventListener('blur',()=>{keys.clear();send();});
function connect(){
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
  ws.onclose=()=>{keys.clear();$('status').textContent='Disconnected — reconnecting';setTimeout(connect,1500);};
  ws.onmessage=event=>{
    const p=JSON.parse(event.data),t=p.telemetry;
    $('status').textContent=t.status;$('takeoff').disabled=!t.ready||t.armed;$('reset').disabled=t.status.startsWith('Resetting');
    for(const [id,img] of Object.entries(p.images||{}))$(id).src='data:image/jpeg;base64,'+img;
    if(t.mass_kg){
      $('height').innerHTML=t.height_m.toFixed(2)+'<small>m</small>';$('speed').innerHTML=Math.hypot(...t.velocity_m_s.slice(0,2)).toFixed(2)+'<small>m/s</small>';
      $('angles').textContent=t.pan_deg.toFixed(0)+'° / '+t.tilt_deg.toFixed(0)+'°';$('power').innerHTML=t.battery_V.toFixed(1)+'<small>V · '+t.current_A.toFixed(1)+' A'+(t.power_limited?' · limited':'')+'</small>';
      $('mass').innerHTML=t.mass_kg.toFixed(3)+'<small>kg</small>';
    }
    if(t.environment){
      $('windSpeed').textContent=Math.hypot(...t.environment.velocity_m_s).toFixed(1)+' m/s';
      if(document.activeElement!==$('wind'))$('wind').value=t.environment.profile;
      if(document.activeElement!==$('seed'))$('seed').value=t.environment.seed;
      const direction=String(t.environment.direction_deg);
      if(![...$('direction').options].some(o=>o.value===direction))$('direction').add(new Option(direction+'°',direction));
      if(document.activeElement!==$('direction'))$('direction').value=direction;
    }
    const strikes=(t.failed_rotors||[]).flatMap((failed,i)=>failed?[i+1]:[]);$('strike').hidden=!strikes.length;$('strike').textContent='Propeller strike · rotor '+strikes.join(', ')+' disabled. Reset scene to restore flight.';
    $('messages').textContent=(t.messages||[]).join('\n');
  };
}
setInterval(()=>send(),100);connect();
