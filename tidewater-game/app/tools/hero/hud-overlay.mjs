// The game's drone HUD (markup from FlightOperations.js, styles from drone-hud.css) drawn over a
// transparent page with the recorded telemetry, one PNG per film frame, for the onboard shot.
//   node tools/hero/hud-overlay.mjs <flight.jsonl> <start s> <length s> <outDir> [width height]
// The handover animation starts on the frame the recorded flight enabled the policy.
import { createRequire } from 'node:module';
import { readFileSync, mkdirSync } from 'node:fs';
const { chromium } = createRequire( import.meta.url )( 'playwright' );
const [ flightPath, startArg, lengthArg, outDir, W = '1280', H = '720' ] = process.argv.slice( 2 );
const start = Number( startArg ), length = Number( lengthArg ), FPS = 30;
mkdirSync( outDir, { recursive: true } );
const rows = [], marks = {};
for ( const line of readFileSync( flightPath, 'utf8' ).split( '\n' ) ) {

	if ( ! line ) continue;
	let r; try { r = JSON.parse( line ); } catch { continue; }
	if ( r.mark ) marks[ r.mark ] = r.t; else if ( r.drone && r.t >= start - 1 && r.t <= start + length + 1 ) rows.push( { t: r.t, drone: r.drone, boat: r.boat, phase: r.ml?.phase, ml: !! r.ml?.enabled } );

}

const source = readFileSync( new URL( '../../src/game/FlightOperations.js', import.meta.url ), 'utf8' );
const from = source.indexOf( 'root.innerHTML = `', source.indexOf( "root.id = 'drone-hud'" ) ) + 18;
const markup = source.slice( from, source.indexOf( '`;', from ) );
const css = readFileSync( new URL( '../../src/game/drone-hud.css', import.meta.url ), 'utf8' );
const html = `<!doctype html><meta charset="utf8"><style>html,body{margin:0;height:100%;background:transparent;overflow:hidden}${ css }
#drone-hud .scrim{display:none}</style><body><div id="drone-hud" data-link="live">${ markup }</div><script>
const root=document.getElementById('drone-hud'),bind=k=>root.querySelector('[data-bind="'+k+'"]'),text=(k,v)=>{const e=bind(k);if(e)e.textContent=v;};
const c=bind('compass');let ring='';for(let i=0;i<72;i++){const a=i*5*Math.PI/180,major=i%6===0,mid=i%3===0,r2=major?213:mid?224:230;ring+='<line x1="'+(Math.sin(a)*238).toFixed(1)+'" y1="'+(-Math.cos(a)*238).toFixed(1)+'" x2="'+(Math.sin(a)*r2).toFixed(1)+'" y2="'+(-Math.cos(a)*r2).toFixed(1)+'" stroke="currentColor" stroke-opacity="'+(major?.36:mid?.19:.1)+'"/>';}c.innerHTML=ring;
for(const s of root.querySelectorAll('.segbar i'))s.classList.add('on');
text('link-text','SX1262 · LIVE');text('link-state','LIVE');text('quality','96');text('rssi','−68');text('snr','10.2');text('loss','0.0%');text('age','0.1 s');text('stamp','');
const deg=r=>r*180/Math.PI,pad=(v,n)=>String(v).padStart(n,'0');
window.setFrame=(row,ms)=>{
 const d=row.drone,b=row.boat,dx=b.position[0]-d.position[0],dz=b.position[2]-d.position[2],range=Math.hypot(dx,dz),above=d.position[1]-b.position[1];
 const heading=(deg(d.heading)%360+360)%360,bearing=(deg(Math.atan2(dx,-dz))%360+360)%360;
 text('alt',d.position[1].toFixed(1));text('spd',(d.speed*3.6).toFixed(1));text('hdg',pad(Math.round(heading),3));text('sep',range.toFixed(0));text('batt',Math.round(d.battery_pct));
 text('agl',d.position[1].toFixed(1));text('gx',(d.position[0]>=0?'+':'−')+Math.abs(d.position[0]).toFixed(1));text('gz',(d.position[2]>=0?'+':'−')+Math.abs(d.position[2]).toFixed(1));
 text('bspd',b.speed.toFixed(1));text('bcrs',pad(Math.round((deg(b.heading)%360+360)%360),3));text('range',range.toFixed(0));text('bearing',pad(Math.round(bearing),3));
 text('pitch',(deg(d.pitch)>=0?'+':'−')+Math.abs(deg(d.pitch)).toFixed(1)+'°');text('roll',(deg(d.roll)>=0?'+':'−')+Math.abs(deg(d.roll)).toFixed(1)+'°');
 const armed=bind('armed');armed.textContent=d.armed?'ARMED':'DISARMED';armed.classList.toggle('is-off',!d.armed);
 bind('horizon')?.setAttribute('transform','rotate('+(-deg(d.roll)).toFixed(2)+') translate(0 '+(deg(d.pitch)*3).toFixed(1)+')');
 bind('compass')?.setAttribute('transform','rotate('+(-heading).toFixed(2)+')');
 const other=bind('other'),k=Math.min(1,150/Math.max(range,1)),rel=(bearing)*Math.PI/180,r=Math.min(range,150);
 if(other){other.style.display='';other.setAttribute('transform','translate('+(Math.sin(rel)*r).toFixed(1)+' '+(-Math.cos(rel)*r).toFixed(1)+')');}
 const line=bind('other-line');if(line){line.setAttribute('x2',(Math.sin(rel)*r).toFixed(1));line.setAttribute('y2',(-Math.cos(rel)*r).toFixed(1));}
 bind('own-rot')?.setAttribute('transform','rotate('+heading.toFixed(1)+')');bind('own-vec')?.setAttribute('transform','rotate('+heading.toFixed(1)+')');
 const on=ms>=0;root.classList.toggle('is-ml',on);root.classList.toggle('ml-engage',on&&ms<2600);
 const banner=bind('ml-banner');banner.hidden=!on;text('ml-banner-note',String(row.phase||'search').replaceAll('_',' '));
 const ml=bind('ml-btn');if(ml)ml.textContent=on?'Manual · L':'Policy · L';const fl=bind('flight-btn');if(fl)fl.textContent='Land · T';
 text('keys',on?'L manual control · T land':'WASD fly · R/F altitude · Q/E yaw · Mouse look · X radio');
 for(const a of document.getAnimations()){a.pause();const delay=a.effect.getComputedTiming().delay||0;a.currentTime=Math.max(0,ms);}
};
</script>`;
const browser = await chromium.launch();
const page = await browser.newPage( { viewport: { width: Number( W ), height: Number( H ) } } );
await page.setContent( html );
await page.waitForTimeout( 300 );
const frames = Math.round( length * FPS );
const engage = marks.policy ?? marks.handover;
let i = 0;
for ( let f = 0; f < frames; f ++ ) {

	const t = start + f / FPS;
	while ( i + 1 < rows.length && rows[ i + 1 ].t <= t ) i ++;
	await page.evaluate( ( [ row, ms ] ) => window.setFrame( row, ms ), [ rows[ i ], ( t - engage ) * 1000 ] );
	await page.screenshot( { path: `${ outDir }/hud-${ String( f ).padStart( 4, '0' ) }.png`, omitBackground: true } );

}

await browser.close();
console.log( 'wrote', frames, 'HUD frames; policy engaged at film frame', Math.round( ( engage - start ) * FPS ) );
