// Developer tool (console only, never imported by the game): render the exact
// policy camera image from any position/direction without flying there, run
// the search head on it and save it for scripts/glare-overlay.py.
//
//   const S = await import('/scripts/policy-shots.js');
//   await S.shot({name, pos:[east,north,up], az: compassDeg, el: elevationDeg}, {file:'replay-shots', n:3});
//
// The main view (free camera) is moved to the same pose first, so the water
// and level of detail are built around the shot as in flight. The first frame
// after a jump can be empty (temporal history); render n >= 3.
import { decodeStudentSearch, weakSearchPeaks } from '/src/landing/StudentSearch.js';
import { policyEphemeris } from '/src/landing/PolicyEphemeris.js';

const ops = () => window.__flightOps;
const b64 = u8 => { let s = ''; for ( let i = 0; i < u8.length; i += 0x8000 ) s += String.fromCharCode.apply( null, u8.subarray( i, i + 0x8000 ) ); return btoa( s ); };
let manifest = null;

export function viewMatrix( pos, azDeg, elDeg ) {

	const a = azDeg * Math.PI / 180, e = elDeg * Math.PI / 180;
	const f = [ Math.sin( a ) * Math.cos( e ), Math.sin( e ), - Math.cos( a ) * Math.cos( e ) ]; // view coords
	const cross = ( u, v ) => [ u[ 1 ] * v[ 2 ] - u[ 2 ] * v[ 1 ], u[ 2 ] * v[ 0 ] - u[ 0 ] * v[ 2 ], u[ 0 ] * v[ 1 ] - u[ 1 ] * v[ 0 ] ];
	const norm = v => { const n = Math.hypot( ...v ); return v.map( x => x / n ); };
	const right = norm( cross( f, [ 0, 1, 0 ] ) ), up = cross( right, f ), back = f.map( x => - x ), p = [ pos[ 0 ], pos[ 2 ], - pos[ 1 ] ];
	return [ right[ 0 ], up[ 0 ], back[ 0 ], p[ 0 ], right[ 1 ], up[ 1 ], back[ 1 ], p[ 1 ], right[ 2 ], up[ 2 ], back[ 2 ], p[ 2 ], 0, 0, 0, 1 ];

}

export async function ready() {

	const o = ops(), P = o.bridge.policy;
	if ( ! P.neural ) await P._load();
	P.camera ??= P.createCamera();
	manifest ??= await ( await fetch( '/policy/manifest.json' ) ).json();
	return true;

}

export async function shot( s, { file = 'replay-shots', n = 3, settle_ms = 1500 } = {} ) {

	const o = ops(), P = o.bridge.policy;
	await ready();
	if ( ! o.freeCamera ) o.toggleFreeCamera();
	const a = s.az * Math.PI / 180, e = s.el * Math.PI / 180, f = [ Math.sin( a ) * Math.cos( e ), Math.sin( e ), - Math.cos( a ) * Math.cos( e ) ];
	const V = o.app.camera.position.constructor;
	o.app.fly.setPose( new V( s.pos[ 0 ], s.pos[ 2 ], - s.pos[ 1 ] ), Math.atan2( - f[ 0 ], - f[ 2 ] ), Math.asin( f[ 1 ] ) );
	o.app.fly.velocity.set( 0, 0, 0 );
	await new Promise( r => setTimeout( r, settle_ms ) );
	const st0 = o.bridge.state, matrix = viewMatrix( s.pos, s.az, s.el );
	const st = { ...st0, views: { ...st0.views, drone: { ...st0.views.drone, matrix } } };
	const eph = policyEphemeris( o.app.settings );
	const obs = { px4: { valid: true, position_enu_m: s.pos, velocity_enu_m_s: [ 0, 0, 0 ], attitude_ned_rad: [ 0, 0, 0 ], angular_rate_frd_rad_s: [ 0, 0, 0 ], position_age_s: 0, attitude_age_s: 0, armed: true, landed: false, gimbal_commanded_rad: [ 0, 0 ] },
		beacon: { valid: false, age_s: 0, position_sigma_m: 0, dock_ready: false, relative_heading_m: [ 0, 0, 0 ], velocity_heading_m_s: [ 0, 0, 0 ] }, gimbal_rad: [ 0, 0 ],
		image_capture_time_s: 1, image_delivery_time_s: 1, image_age_s: 0, image_valid: true, previous_executed_action: [ 0, 0, 0, 0, 0, 0 ], decision_dt_s: .04,
		mission: { elapsed_s: 1, budget_s: 180, water_datum_enu_m: 0, nominal_deck_height_above_water_m: .45, recovery_clearance: { valid: false } }, ephemeris: eph };
	const numeric = await P.request( { type: 'numeric', observation: obs } );
	const results = [];
	for ( let k = 0; k < n; k ++ ) {

		for ( let i = 0; i < 300 && P.camera.busy; i ++ ) await new Promise( r => setTimeout( r, 10 ) );
		let run;
		const rgb = await P.camera.capture( st, { onSubmitted: tex => { run = P.neural.runFromTexture( tex, numeric.numeric ); } } );
		const out = await run;
		const proposals = decodeStudentSearch( out.search, manifest.search_thresholds );
		const weak = weakSearchPeaks( out.search, proposals, { minimum: 0.04 } ).map( w => ( { pixel: w.pixel, p: w.confidence } ) );
		const frame = { name: s.name + ( n > 1 ? '#' + k : '' ), label: `${ s.name } pos=${ s.pos.map( x => x.toFixed( 1 ) ) } az=${ s.az } el=${ s.el }`,
			matrix, fovy: st0.views.drone.fovy, sun_enu: eph?.sun_direction_enu, proposals, weak, rgb_b64: b64( new Uint8Array( rgb ) ) };
		await fetch( '/__session-recording?id=' + file, { method: 'POST', body: JSON.stringify( frame ) + '\n' } );
		results.push( proposals.map( p => p.evidence.slice( 0, 7 ) + ' ' + p.confidence.toFixed( 2 ) ) );

	}
	return results;

}

// Run a list of shots in the background; progress in window.__shotLog.
export function runAll( shots, options ) {

	window.__shotLog = [];
	( async () => {

		for ( const s of shots ) {

			try { window.__shotLog.push( [ s.name, await shot( s, options ) ] ); } catch ( error ) { window.__shotLog.push( [ s.name, 'ERR ' + error.message ] ); }

		}
		window.__shotLog.push( 'DONE' );

	} )();
	return 'started';

}
