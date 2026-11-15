// Pass 1 of the hero film: fly the scripted mission headlessly with the real PX4/MuJoCo physics
// and the trained policy in the loop, and record every physics packet (body poses, telemetry).
//   HERO_W=320 HERO_H=180 node tools/hero/record.mjs <out.jsonl>
// Nothing here uses simulator truth to steer the landing: after "L" the policy flies alone.
import { state } from './dom-shim.mjs';
import { createWriteStream } from 'node:fs';
const out = createWriteStream( process.argv[ 2 ] || '/tmp/hero-flight.jsonl' );
const { App } = await import( '../../src/App.js' );
const { SimulationBridge } = await import( '../../src/landing/SimulationBridge.js' );
const app = new App();
const t0 = performance.now(), wall = () => ( ( performance.now() - t0 ) / 1000 ).toFixed( 0 );
await app.init( () => {} );
app.settings.timeOfDay = 15;
const ops = app.flightOps = { active: true, freeCamera: false, mode: 'drone', boatCamera: 'boat_dock', beforePhysics() {}, update( dt ) { this.bridge?.update( dt ); }, _refreshUI() {} };
const bridge = ops.bridge = new SimulationBridge( app, () => {} );

let phase = 'boot', phaseStart = 0, wroteLayout = false, last = null, done = false, tiltSign = 0, tiltProbe = null;
const log = ( text ) => console.log( `[wall ${ wall() } s | sim ${ last ? last.time_s.toFixed( 1 ) : '-' } s] ${ text }` );
const go = ( name ) => { phase = name; phaseStart = last.time_s; log( 'phase ' + name ); out.write( JSON.stringify( { mark: name, t: last.time_s } ) + '\n' ); };
const send = ( p ) => bridge.send( p );

function record( s ) {

	const row = { t: s.time_s, bodies: s.bodies, hull_pose: s.hull_pose, views: s.views, waves: s.waves, drone: s.drone, boat: s.boat, ml: s.ml, radio: s.radio };
	if ( s.geoms && ! wroteLayout ) { row.geoms = s.geoms; wroteLayout = true; }
	out.write( JSON.stringify( row ) + '\n' );

}

function step( s ) {

	last = s;
	const d = s.drone, b = s.boat, since = s.time_s - phaseStart;
	const above = d.position[ 1 ] - b.position[ 1 ];
	const range = Math.hypot( d.position[ 0 ] - b.position[ 0 ], d.position[ 2 ] - b.position[ 2 ] );
	if ( phase === 'boot' ) {

		if ( ! ( s.ready && d.px4_ready ) ) return;
		send( { mode: 'drone', keys: [] } );
		send( { action: 'autopilot', enabled: true } );
		bridge.policy.preload()?.then( () => log( 'policy loaded' ), ( e ) => log( 'policy preload failed: ' + e.message ) );
		go( 'stow' );

	} else if ( phase === 'stow' ) {

		// the simulation starts with the bay open and the platform up: stow it for the opening shots
		if ( b.platform > .02 ) { if ( ! b.mechanism_busy && b.platform_target > .02 ) send( { action: 'platform', raised: false } ); }
		else if ( Math.max( b.aft_lid, b.fore_lid ) > .02 ) { if ( ! b.mechanism_busy && b.aft_lid_target > .02 ) send( { action: 'lid', open: false } ); }
		else if ( ! b.mechanism_busy ) go( 'cruise' );

	} else if ( phase === 'cruise' ) {

		if ( since > 14 && b.speed > 1.2 ) { send( { action: 'lid', open: true } ); go( 'lids' ); }

	} else if ( phase === 'lids' ) {

		if ( Math.min( b.aft_lid, b.fore_lid ) >= .98 && ! b.mechanism_busy ) { send( { action: 'platform', raised: true } ); go( 'platform' ); }

	} else if ( phase === 'platform' ) {

		if ( b.platform >= .995 && ! b.mechanism_busy && since > 1 ) go( 'ready' );

	} else if ( phase === 'ready' ) {

		if ( since > 1.5 ) { send( { action: 'takeoff' } ); go( 'takeoff' ); }

	} else if ( phase === 'takeoff' ) {

		if ( d.armed && ! d.landed && above > 1.6 ) go( 'climb' );
		else if ( since > 40 ) { log( 'take-off failed' ); done = true; }

	} else if ( phase === 'climb' ) {

		// climb while the boat drives on; then tilt the camera down toward it
		send( { keys: above < 7 ? [ 'KeyR' ] : [] } );
		if ( above >= 7 && range > 22 ) { tiltProbe = { tilt: d.tilt, t: s.time_s }; go( 'aim' ); }

	} else if ( phase === 'aim' ) {

		// find which way look_y moves the camera, then tilt until the boat sits in the frame
		const wanted = Math.atan2( above, range ) * .8; // radians below the horizon
		if ( ! tiltSign ) {

			send( { keys: [], look_y: 6 } );
			if ( since > .6 ) tiltSign = Math.sign( d.tilt - tiltProbe.tilt ) || 1;

		} else {

			const error = ( tiltProbe.tilt + tiltSign * 0 ) - d.tilt; // unused; kept simple below
			const down = d.tilt - tiltProbe.tilt; // camera travel since the probe
			const target = wanted; // travel wanted (magnitude)
			if ( Math.abs( down ) < target && since < 8 ) send( { keys: [], look_y: 6 } );
			else go( 'approach' );

		}

	} else if ( phase === 'approach' ) {

		send( { keys: since < 6 ? [ 'KeyW' ] : [] } );
		if ( since >= 6 ) {

			send( { keys: [] } );
			go( 'handover' );
			bridge.policy.enable().then( () => log( 'policy enabled' ), ( e ) => { log( 'policy enable failed: ' + e.message ); done = true; } );

		}

	} else if ( phase === 'handover' ) {

		if ( s.ml?.enabled ) go( 'policy' );
		else if ( since > 60 ) { log( 'policy never engaged' ); done = true; }

	} else if ( phase === 'policy' ) {

		if ( Math.floor( since ) % 10 === 0 && Math.floor( since ) !== step.lastLog ) { step.lastLog = Math.floor( since ); log( `policy ${ s.ml?.phase } above ${ above.toFixed( 1 ) } range ${ range.toFixed( 1 ) } ${ s.ml?.error || '' }` ); }
		if ( d.landed && ! d.armed && above < 1.2 && range < 1 ) go( 'landed' );
		else if ( ! s.ml?.enabled && since > 2 ) { log( 'policy stopped: ' + ( s.ml?.error || s.ml?.message || 'disabled' ) ); go( 'after' ); }
		else if ( since > 240 ) { log( 'policy timeout' ); done = true; }

	} else if ( phase === 'landed' || phase === 'after' ) {

		if ( since > 4 ) done = true;

	}

}

// tap the worker's packets
const tap = setInterval( () => {

	const worker = bridge.worker;
	if ( ! worker || worker.tapped ) return;
	const forward = worker.onmessage;
	worker.onmessage = ( event ) => {

		forward( event );
		const s = event.data;
		if ( s?.bodies && s.drone && s.boat ) { try { record( s ); step( s ); } catch ( e ) { console.log( 'script error', e.stack ); done = true; } }
		else if ( s?.error ) { console.log( 'worker error', s.error ); done = true; }

	};
	worker.tapped = true;

}, 50 );

// keep the scene alive (ocean, terrain streaming, clouds) for the onboard camera
while ( ! done && performance.now() - t0 < Number( process.env.HERO_LIMIT_S || 3600 ) * 1000 ) {

	app._frame( 1 / 30 );
	await state.device.queue.onSubmittedWorkDone();
	await new Promise( ( r ) => setTimeout( r, 15 ) );
	if ( bridge.state?.error && bridge.state.error !== step.err ) { step.err = bridge.state.error; log( 'bridge error: ' + bridge.state.error ); }

}

clearInterval( tap );
log( 'finished in phase ' + phase );
await new Promise( ( r ) => out.end( r ) );
process.exit( 0 );
