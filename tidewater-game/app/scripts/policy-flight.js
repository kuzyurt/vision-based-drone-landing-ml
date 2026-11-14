// Developer tool (console only, never imported by the game): fly the drone to
// a start point with the normal keyboard controls, then start an ML test run.
//
//   const F = await import('/scripts/policy-flight.js');
//   F.goTo([-22.7, -53.9], 5.8);   // background; progress in window.__flightLog
//   await F.startRun({radio: false, record: true});
const ops = () => window.__flightOps;
const sleep = ms => new Promise( r => setTimeout( r, ms ) );
const wrap = a => ( ( a + 540 ) % 360 ) - 180;
const log = text => { ( window.__flightLog ??= [] ).push( `${ new Date().toISOString().slice( 11, 19 ) } ${ text }` ); };

export function key( code, key = code.replace( /^Key/, '' ).toLowerCase(), ms = 100 ) {

	window.dispatchEvent( new KeyboardEvent( 'keydown', { code, key, bubbles: true } ) );
	return new Promise( r => setTimeout( () => { window.dispatchEvent( new KeyboardEvent( 'keyup', { code, key, bubbles: true } ) ); r(); }, ms ) );

}

export function drone() {

	const d = ops().bridge.state.drone;
	return { enu: [ d.position[ 0 ], - d.position[ 2 ], d.position[ 1 ] ], heading: d.heading * 180 / Math.PI, armed: d.armed, landed: d.landed, tilt: d.tilt * 180 / Math.PI };

}

export async function yawTo( deg ) {

	for ( let i = 0; i < 60; i ++ ) {

		const e = wrap( deg - drone().heading );
		if ( Math.abs( e ) < 3 ) return drone().heading;
		await key( e > 0 ? 'KeyE' : 'KeyQ', e > 0 ? 'e' : 'q', Math.min( 500, Math.max( 40, Math.abs( e ) * 15 ) ) );
		await sleep( 150 );

	}
	return drone().heading;

}

export async function climbTo( height ) {

	for ( let i = 0; i < 60; i ++ ) {

		const e = height - drone().enu[ 2 ];
		if ( Math.abs( e ) < 0.25 ) return drone().enu[ 2 ];
		await key( e > 0 ? 'KeyR' : 'KeyF', e > 0 ? 'r' : 'f', Math.min( 1500, Math.max( 60, Math.abs( e ) * 500 ) ) );
		await sleep( 300 );

	}
	return drone().enu[ 2 ];

}

// Take off if needed, climb, then fly to an [east, north] point at full stick.
export function goTo( target, height = 5.8 ) {

	window.__flightLog = [];
	( async () => {

		const o = ops();
		if ( o.freeCamera ) o.toggleFreeCamera();
		if ( ! drone().armed || drone().landed ) { log( 'takeoff' ); await key( 'KeyT', 't' ); for ( let i = 0; i < 40 && ( drone().landed || drone().enu[ 2 ] < 1 ); i ++ ) await sleep( 500 ); }
		log( 'climb ' + ( await climbTo( height ) ).toFixed( 1 ) );
		for ( let leg = 0; leg < 400; leg ++ ) {

			const p = drone().enu, dx = target[ 0 ] - p[ 0 ], dy = target[ 1 ] - p[ 1 ], dist = Math.hypot( dx, dy );
			if ( dist < 3 ) break;
			const bearing = ( Math.atan2( dx, dy ) * 180 / Math.PI + 360 ) % 360;
			if ( Math.abs( wrap( bearing - drone().heading ) ) > 6 ) await yawTo( bearing );
			await key( 'KeyW', 'w', Math.min( 2500, dist * 400 ) );
			if ( leg % 5 === 0 ) { log( `dist ${ dist.toFixed( 1 ) } h ${ p[ 2 ].toFixed( 1 ) }` ); await climbTo( height ); }

		}
		await sleep( 1500 );
		log( 'arrived ' + drone().enu.map( v => v.toFixed( 1 ) ).join( ',' ) );
		window.__flightLog.push( 'DONE' );

	} )();
	return 'flying';

}

// Save exact policy frames during a run (every few seconds and whenever the
// glare logic decides something) for scripts/glare-overlay.py.
export async function tapFrames( { file = 'run-frames', every_s = 3 } = {} ) {

	const { decodeStudentSearch } = await import( '/src/landing/StudentSearch.js' );
	const manifest = await ( await fetch( '/policy/manifest.json' ) ).json();
	let last = - Infinity, lastGlare = 0, lastReal = 0;
	const b64 = u8 => { let s = ''; for ( let i = 0; i < u8.length; i += 0x8000 ) s += String.fromCharCode.apply( null, u8.subarray( i, i + 0x8000 ) ); return btoa( s ); };
	globalThis.__policyTap = ( { rgb, observation, search, state, diagnostics } ) => {

		const g = diagnostics?.guidance || {}, t = observation.mission?.elapsed_s ?? 0;
		const event = ( g.zone_glare ?? 0 ) > lastGlare ? 'glare' : ( g.zone_real ?? 0 ) > lastReal ? 'real' : null;
		lastGlare = g.zone_glare ?? 0; lastReal = g.zone_real ?? 0;
		if ( ! event && t - last < every_s ) return;
		last = t;
		const view = state.views.drone, proposals = decodeStudentSearch( search, manifest.search_thresholds );
		const frame = { name: `t${ t.toFixed( 1 ) }-${ diagnostics?.control_phase }${ event ? '-' + event : '' }`,
			label: `t=${ t.toFixed( 1 ) } ${ diagnostics?.control_phase } sel=${ diagnostics?.search_selected } zone=${ JSON.stringify( g.zone_now || {} ) }`,
			matrix: Array.from( view.matrix ), fovy: view.fovy, sun_enu: observation.ephemeris?.sun_direction_enu, proposals, weak: [], rgb_b64: b64( rgb ) };
		fetch( '/__session-recording?id=' + file, { method: 'POST', body: JSON.stringify( frame ) + '\n' } );

	};
	return 'tapping';

}

// Radio off (X) if wanted, ML on (L), session recording (Z).
export async function startRun( { radio = false, record = true } = {} ) {

	const o = ops();
	if ( o.freeCamera ) o.toggleFreeCamera();
	const linked = o.state?.radio?.enabled !== false;
	if ( ! radio && linked ) { await key( 'KeyX', 'x' ); await sleep( 500 ); }
	if ( record && ! o.recorder?.active ) { await key( 'KeyZ', 'z' ); await sleep( 300 ); }
	await key( 'KeyL', 'l' );
	return { radio: o.state?.radio?.enabled, recording: !! o.recorder?.active };

}
