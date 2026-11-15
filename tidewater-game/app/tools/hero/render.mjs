// Pass 2 of the hero film: replay the recorded flight (record.mjs) and render the cinematic shots.
//   HERO_REPLAY=1 node tools/hero/render.mjs <flight.jsonl> <outDir> [shot ...] [--preview]
// Each shot becomes <outDir>/<shot>.mp4 (30 fps). --preview writes every 20th frame as PNG instead.
// The vehicles are placed from the recorded physics packets; no physics or policy runs here.
import { state, readCanvas, writePNG } from './dom-shim.mjs';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { spawn } from 'node:child_process';

const [ flightPath, outDir, ...rest ] = process.argv.slice( 2 );
const preview = rest.includes( '--preview' );
const wanted = rest.filter( ( a ) => ! a.startsWith( '--' ) );
const FPS = 30;
mkdirSync( outDir, { recursive: true } );

// ---- recorded flight
const rows = [], marks = {};
let layout = null;
for ( const line of readFileSync( flightPath, 'utf8' ).split( '\n' ) ) {

	if ( ! line ) continue;
	let r;
	try { r = JSON.parse( line ); } catch { continue; }
	if ( r.mark ) marks[ r.mark ] = r.t;
	else if ( r.bodies ) { if ( r.geoms ) layout = r.geoms; rows.push( r ); }

}

const tEnd = rows[ rows.length - 1 ].t;
function indexAt( t ) {

	let lo = 0, hi = rows.length - 1;
	while ( lo < hi ) { const mid = ( lo + hi + 1 ) >> 1; if ( rows[ mid ].t <= t ) lo = mid; else hi = mid - 1; }
	return lo;

}

const rowAt = ( t ) => rows[ indexAt( Math.min( Math.max( t, rows[ 0 ].t ), tEnd ) ) ];
// first time a condition holds at or after t
function when( from, test ) { for ( let i = indexAt( from ); i < rows.length; i ++ ) if ( test( rows[ i ] ) ) return rows[ i ].t; return tEnd; }

// ---- scene
const { App } = await import( '../../src/App.js' );
const { SimulationBridge } = await import( '../../src/landing/SimulationBridge.js' );
const E = await import( '../../src/engine/index.js' );
const { landingWaveParams } = await import( '../../src/landing/PhysicsWaves.js' );
const app = new App();
await app.init( () => {} );
app.settings.timeOfDay = 15;
const ops = app.flightOps = { active: true, freeCamera: false, mode: 'drone', boatCamera: 'boat_dock', beforePhysics() {}, update() {}, _refreshUI() {} };
const bridge = ops.bridge = new SimulationBridge( app, () => {} );
await bridge.vehicleInstallation;
bridge.cameraPaused = true;
bridge.worker.onmessage( { data: { ...rows[ 0 ], geoms: layout, ready: true } } );
console.log( 'scene ready; flight', rows[ 0 ].t.toFixed( 1 ), '-', tEnd.toFixed( 1 ), 's', JSON.stringify( marks ) );

const mA = new E.Matrix4(), mB = new E.Matrix4();
const pA = new E.Vector3(), pB = new E.Vector3(), sA = new E.Vector3(), sB = new E.Vector3(), qA = new E.Quaternion(), qB = new E.Quaternion();
function blend( valuesA, valuesB, k, position, quaternion ) {

	mA.set( ...valuesA ).decompose( pA, qA, sA );
	mB.set( ...valuesB ).decompose( pB, qB, sB );
	position.copy( pA ).lerp( pB, k );
	quaternion.copy( qA ).slerp( qB, k );

}

// place every body at simulation time t (interpolated between the two surrounding packets)
function pose( t ) {

	const i = indexAt( t ), a = rows[ i ], b = rows[ Math.min( i + 1, rows.length - 1 ) ];
	const k = b.t > a.t ? Math.min( 1, Math.max( 0, ( t - a.t ) / ( b.t - a.t ) ) ) : 0;
	const next = new Map( b.bodies );
	for ( const [ name, values ] of a.bodies ) {

		const group = bridge._bodyGroup( name );
		blend( values, next.get( name ) || values, k, group.position, group.quaternion );
		group.target.position.copy( group.position ); group.target.quaternion.copy( group.quaternion );
		group.initialized = true;

	}

	if ( bridge.hull && a.hull_pose ) blend( a.hull_pose, b.hull_pose || a.hull_pose, k, bridge.hull.position, bridge.hull.quaternion );
	bridge.state = a;
	bridge.lastPacketTime = performance.now();
	if ( a.waves ) {

		if ( ! bridge.landingWater ) bridge._takeLandingWater();
		for ( const [ n, c ] of a.waves.entries() ) {

			const omega = Math.sqrt( 9.80665 * Math.hypot( c[ 0 ], c[ 1 ] ) );
			landingWaveParams.fields[ `c${ n }` ].value.set( c[ 0 ], c[ 1 ], c[ 2 ], c[ 3 ] - omega * ( t - a.t ) );

		}

	}

	return { a, b, k };

}

const v3 = ( a ) => new E.Vector3( a[ 0 ], a[ 1 ], a[ 2 ] );
function vehicle( t ) {

	const { a, b, k } = pose( t );
	const boat = v3( a.boat.position ).lerp( v3( b.boat.position ), k );
	const drone = v3( a.drone.position ).lerp( v3( b.drone.position ), k );
	// course from the track over two seconds (the deck's own heading wobbles with the waves)
	const p0 = v3( rowAt( t - 1 ).boat.position ), p1 = v3( rowAt( t + 1 ).boat.position );
	const forward = p1.sub( p0 ); forward.y = 0;
	if ( forward.length() < 0.2 ) forward.set( 1, 0, 0 );
	forward.normalize();
	const right = new E.Vector3().crossVectors( forward, new E.Vector3( 0, 1, 0 ) ).normalize();
	return { a, b, k, boat, drone, forward, right };

}

const { GPU } = await import( '../../src/engine/gpu/GPU.js' );
const wake = app.aerodockWake;
const wakeUpdate = wake ? wake.update.bind( wake ) : null;
// Lay the wake the boat left before the shot starts: step the wake simulation alone along the
// recorded track (the held pre-roll frames below must not deposit foam at one spot).
async function wakePreroll( t0, seconds = 16 ) {

	if ( ! wake ) return;
	const step = 1 / 30;
	for ( let t = Math.max( rows[ 0 ].t, t0 - seconds ); t < t0; t += step ) {

		pose( t );
		GPU.beginFrame();
		wakeUpdate( step, bridge.boatObject, true, bridge.state );
		GPU.submit();

	}

	await state.device.queue.onSubmittedWorkDone();

}

const baseExposure = app.settings.exposure;
const camera = app.camera;
function look( position, target, fov, up = new E.Vector3( 0, 1, 0 ) ) {

	camera.matrixAutoUpdate = true;
	camera.up.copy( up );
	camera.position.copy( position );
	camera.lookAt( target.x, target.y, target.z );
	camera.fov = fov;
	camera.updateProjectionMatrix();
	camera.updateMatrix();
	camera.updateMatrixWorld();

}

function view( v, name ) {

	const a = v.a.views[ name ], b = v.b.views[ name ] || a;
	blend( a.matrix, b.matrix, v.k, camera.position, camera.quaternion );
	camera.matrixAutoUpdate = true;
	camera.fov = a.fovy;
	camera.updateProjectionMatrix();
	camera.updateMatrix();
	camera.updateMatrixWorld();

}

const at = ( v, fwd, rgt, up ) => v.boat.clone().addScaledVector( v.forward, fwd ).addScaledVector( v.right, rgt ).add( new E.Vector3( 0, up, 0 ) );
const ease = ( x ) => { const c = Math.min( 1, Math.max( 0, x ) ); return c * c * ( 3 - 2 * c ); };

// ---- shots: start (simulation seconds), duration, and the camera for local time u = 0..1
const M = marks;
const lidsHalf = when( M.lids, ( r ) => Math.min( r.boat.aft_lid, r.boat.fore_lid ) >= 0.5 );
const platform60 = when( M.platform, ( r ) => r.boat.platform >= 0.6 );
const liftOff = when( M.takeoff, ( r ) => r.drone.armed && r.drone.position[ 1 ] - r.boat.position[ 1 ] > 1.0 );
const landed = M.landed ?? tEnd - 4;
const SHOTS = {
	// wake checks (not in the film): render with `wakeTop wakeLow --preview`
	wakeTop: { debug: true, exposure: 0.62, start: M.lids - 6, length: 1.4, camera( v ) { look( at( v, - 6, 0, 22 ), at( v, - 6, 0, 0 ), 40, v.forward.clone() ); } },
	wakeLow: { debug: true, start: M.lids - 6, length: 1.4, camera( v ) { look( at( v, - 9.5, 2.4, 2.6 ), at( v, - 1, 0, 0.2 ), 42 ); } },
	// the boat under way from off its port bow (needs only a flight recorded with HERO_BOAT_ONLY):
	// the camera travels with the boat over the water, low, and slowly swings round toward the beam
	boatFront: { start: Number( process.env.BOAT_START || 44 ), length: 10, camera( v, u ) {

		const k = ease( u ), r = 7.8 - 1.2 * k, az = ( 22 + 13 * k ) * Math.PI / 180, h = 0.85 + 0.4 * k;
		// the track, not the deck, carries the camera: it does not heave with the boat
		const position = v.boat.clone().addScaledVector( v.forward, Math.cos( az ) * r ).addScaledVector( v.right, - Math.sin( az ) * r );
		position.y = h;
		// aim a little aft of the deck's middle: the bow fills the left, the wake trails across the right
		const target = v.boat.clone().addScaledVector( v.forward, - 1.5 ); target.y = v.boat.y + 1.3;
		look( position, target, 34 );

	} },
	// straight down: the boat drives in from the left edge to the middle of the frame
	top: { exposure: 0.62, start: M.lids - 7.5, length: 5.2, setup( t0, length ) {

		const end = vehicle( t0 + length );
		this.centre = end.boat.clone(); this.forward = end.forward.clone();

	}, camera( v ) {

		look( this.centre.clone().add( new E.Vector3( 0, 14, 0 ) ), this.centre, 30, new E.Vector3().crossVectors( new E.Vector3( 0, 1, 0 ), this.forward ) );

	} },
	// low off the port bow, travelling with the boat while the lids start to open
	bow: { start: M.lids - 1.6, length: lidsHalf - M.lids + 1.6, camera( v, u ) {

		look( at( v, 3.9 - 0.5 * u, - 2.9, 1.0 + 0.25 * u ), at( v, 0.1, 0, 0.45 ), 40 );

	} },
	// off the starboard quarter: the platform lifts the drone out of the bay
	quarter: { start: platform60, length: M.ready - platform60 + 1.2, camera( v, u ) {

		look( at( v, - 3.5 + 0.4 * u, 2.7, 1.7 - 0.15 * u ), at( v, 0, 0, 0.75 ), 40 );

	} },
	// from the side: spool-up and lift-off
	side: { start: liftOff - 3.4, length: 6.4, camera( v, u ) {

		const rise = Math.max( 0, v.drone.y - v.boat.y - 0.9 );
		look( at( v, 0.5, 4.9 - 0.4 * u, 1.0 ), at( v, 0.1, 0, 0.8 + rise * 0.5 ), 44 );

	} },
	// the drone's own camera: manual approach, then L hands over to the policy
	onboard: { start: M.handover - 4.2, length: 9.4, camera( v ) { view( v, 'drone' ); } },
	// the policy flying, seen from behind and above the drone
	chase: { start: Math.max( M.policy + 6, landed - 26 ), length: 5.5, camera( v, u ) {

		const toBoat = v.boat.clone().sub( v.drone ); toBoat.y = 0;
		const d = toBoat.length() > 0.5 ? toBoat.normalize() : v.forward.clone();
		const side = new E.Vector3().crossVectors( d, new E.Vector3( 0, 1, 0 ) );
		look( v.drone.clone().addScaledVector( d, - 5.5 ).addScaledVector( side, 2.2 - 1.2 * u ).add( new E.Vector3( 0, 2.0, 0 ) ), v.drone.clone().lerp( v.boat, 0.3 ), 42 );

	} },
	// the boat's own dock camera: touchdown
	dock: { start: landed - 7.5, length: 9.5, camera( v ) { view( v, 'boat_dock' ); } },
};

// ---- render
const frameOnce = async ( dt ) => { app._frame( dt ); await state.device.queue.onSubmittedWorkDone(); };
for ( const [ name, shot ] of Object.entries( SHOTS ) ) {

	if ( wanted.length ? ! wanted.includes( name ) : shot.debug ) continue;
	if ( ! Number.isFinite( shot.start ) || shot.start + shot.length > tEnd + 0.01 ) { console.log( 'skip', name, '(not recorded yet)' ); continue; }
	shot.setup?.( shot.start, shot.length );
	const frames = Math.round( shot.length * FPS );
	const telemetry = [];
	let encoder = null;
	if ( ! preview ) {

		encoder = spawn( 'ffmpeg', [ '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${ state.width }x${ state.height }`, '-r', String( FPS ), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', `${ outDir }/${ name }.mp4` ], { stdio: [ 'pipe', 'inherit', 'inherit' ] } );

	}

	// settle the temporal filters on the first frame of the shot (a camera cut)
	shot.camera( vehicle( shot.start ), 0 );
	app.clouds?.resetHistory?.();
	// (auto exposure and the cloud history follow the clock: let them run on the held first pose)
	app.settings.exposure = baseExposure * ( shot.exposure ?? 1 );
	if ( wake ) wake.update = () => {};
	for ( let i = 0; i < 14; i ++ ) await frameOnce( 0.12 );
	await wakePreroll( shot.start );
	shot.camera( vehicle( shot.start ), 0 );
	for ( let i = 0; i < 4; i ++ ) await frameOnce( 0 );
	if ( wake ) wake.update = wakeUpdate;
	const began = performance.now();
	for ( let f = 0; f < frames; f += preview ? 20 : 1 ) {

		const t = shot.start + f / FPS;
		// preview: the frames in between still advance the wake along the track
		if ( preview && f > 0 && wake ) for ( let g = f - 19; g < f - 2; g ++ ) { pose( shot.start + g / FPS ); GPU.beginFrame(); wakeUpdate( 1 / FPS, bridge.boatObject, true, bridge.state ); GPU.submit(); }
		// preview: two real frames lead in, so the saved one has ordinary frame-to-frame motion
		if ( preview && f > 0 ) for ( const back of [ 2, 1 ] ) { const u = vehicle( t - back / FPS ); shot.camera( u, f / Math.max( 1, frames - 1 ) ); await frameOnce( 1 / FPS ); }
		const v = vehicle( t );
		shot.camera( v, f / Math.max( 1, frames - 1 ) );
		await frameOnce( 1 / FPS );
		const image = await readCanvas();
		if ( preview ) writePNG( `${ outDir }/${ name }-${ String( f ).padStart( 4, '0' ) }.png`, image.width, image.height, image.data );
		else if ( ! encoder.stdin.write( Buffer.from( image.data.buffer ) ) ) await new Promise( ( r ) => encoder.stdin.once( 'drain', r ) );
		telemetry.push( { f, t, drone: v.a.drone, boat: v.a.boat, ml: v.a.ml, radio: v.a.radio } );
		if ( f % 30 === 0 ) console.log( name, f, '/', frames, ( ( performance.now() - began ) / 1000 ).toFixed( 0 ), 's' );

	}

	if ( encoder ) { encoder.stdin.end(); await new Promise( ( r ) => encoder.on( 'close', r ) ); }
	writeFileSync( `${ outDir }/${ name }.json`, JSON.stringify( { name, start: shot.start, length: shot.length, fps: FPS, marks, telemetry } ) );
	console.log( 'done', name );

}

process.exit( 0 );
