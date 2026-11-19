// Hosted web build only. The start page can only guess how fast this device
// is; here the game measures it. If the simulation keeps running well below real
// time, offer the video once, without stopping the game.
const WARMUP_S = 15;       // shader compilation and first loads distort the start
const WINDOW_S = 20;       // judge the median over this long
const SLOW_BELOW = 0.5;    // below half real time the drone feels sluggish
const VIDEO_URL = '../#watch';

export function watchSimulationSpeed() {

	let samples = [], startedAt = null, shown = false;
	try { shown = sessionStorage.getItem( 'slow-hint-shown' ) === '1'; } catch { /* storage may be blocked */ }
	if ( shown ) return;

	const timer = setInterval( () => {

		const ops = window.__flightOps, state = ops?.bridge?.state;
		const factor = state?.realtime_factor;
		if ( ! ops?._started || ! state?.ready || ! Number.isFinite( factor ) || document.visibilityState !== 'visible' ) return;
		const now = performance.now() / 1000;
		startedAt ??= now;
		if ( now - startedAt < WARMUP_S ) return;
		samples.push( [ now, factor ] );
		samples = samples.filter( ( [ t ] ) => now - t <= WINDOW_S );
		if ( samples[ 0 ][ 0 ] > now - WINDOW_S + 2 ) return; // not a full window yet
		const sorted = samples.map( ( [ , f ] ) => f ).sort( ( a, b ) => a - b );
		const median = sorted[ sorted.length >> 1 ];
		if ( median >= SLOW_BELOW ) return;
		clearInterval( timer );
		show( median );

	}, 1000 );

}

function show( factor ) {

	try { sessionStorage.setItem( 'slow-hint-shown', '1' ); } catch { /* ignore */ }
	const box = document.createElement( 'div' );
	box.setAttribute( 'role', 'dialog' );
	box.setAttribute( 'aria-label', 'This device runs the simulation slowly' );
	box.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:10001;max-width:min(520px,calc(100vw - 32px));' +
		'background:#10232df2;color:#e8f3f3;border:1px solid #2c4a57;border-radius:10px;padding:14px 16px;font:14px/1.45 system-ui,sans-serif;box-shadow:0 8px 28px #0008';
	const percent = Math.max( 1, Math.round( factor * 100 ) );
	box.innerHTML = `<div style="font-weight:600;margin-bottom:4px">This device runs the simulation at about ${ percent } % of real time</div>` +
		'<div style="opacity:.85;margin-bottom:10px">Flying will feel slow. You can keep playing, or watch a recorded flight instead.</div>' +
		'<div style="display:flex;gap:8px;flex-wrap:wrap"></div>';
	const row = box.lastElementChild;
	const watch = document.createElement( 'a' );
	watch.href = VIDEO_URL; watch.textContent = 'Watch the video';
	watch.style.cssText = 'background:#2bb3a6;color:#062027;font-weight:600;padding:7px 12px;border-radius:7px;text-decoration:none';
	const keep = document.createElement( 'button' );
	keep.type = 'button'; keep.textContent = 'Keep playing';
	keep.style.cssText = 'background:transparent;color:#e8f3f3;border:1px solid #4b6b78;padding:7px 12px;border-radius:7px;font:inherit;cursor:pointer';
	keep.addEventListener( 'click', () => box.remove() );
	row.append( watch, keep );
	document.body.append( box );

}
