// Scripted drone approach after L, for the drone-HUD shot. The policy is not run for this shot.
// The track is a model of a multirotor flown by a learned controller:
//  - the controller sends a new speed command every 40 ms, with a little jitter;
//  - the airframe responds as a second-order system (slight overshoot, no instant changes);
//  - the nose turns toward the boat with its own second-order response, capped in rate;
//  - the body tilts into its acceleration and into turns (attitudeOf), which the HUD reads too;
//  - the gimbal lags behind the aim point and hunts a little (camHunt, render.mjs).
// Plain maths only: this module is shared by render.mjs and hud-overlay.mjs.
export const SCRIPT = {
	slowTo: 1.0, cruise: 2.0, slowTime: 2.6, accelTime: 2.6,   // speed plan (m/s, s)
	speedFreq: 2.5, speedDamp: 0.55,                           // airframe speed response
	turnFreq: 1.0, turnDamp: 0.9, turnMax: 8 * Math.PI / 180,  // nose response, rate cap
	command: 0.04, commandJitter: 0.04,                        // policy command period, jitter (m/s)
	camLag: 0.35,                                              // gimbal lag (s)
	dt: 1 / 60, span: 7.5, g: 9.81,
};

// small wobble in the position and nose: sums of slow sines with fixed phases
export const WOBBLE = { lateral: 0.5, altitude: 0.10, psi: 2.0 * Math.PI / 180, attitude: 0.007 };

export function rowIndex( rows, t ) {

	let lo = 0, hi = rows.length - 1;
	while ( lo < hi ) { const mid = ( lo + hi + 1 ) >> 1; if ( rows[ mid ].t <= t ) lo = mid; else hi = mid - 1; }
	return lo;

}

export const smooth = ( x ) => { const c = Math.min( 1, Math.max( 0, x ) ); return c * c * ( 3 - 2 * c ); };
const wrap = ( a ) => Math.atan2( Math.sin( a ), Math.cos( a ) );

function wobble( u, seed, amp ) {

	const f = [ 0.31, 0.53, 0.87, 1.27 ];
	let sum = 0;
	for ( let i = 0; i < f.length; i ++ ) sum += Math.sin( 2 * Math.PI * f[ i ] * 0.5 * u + seed * ( i + 1.3 ) + i );
	return amp * sum / f.length;

}

// reproducible pseudo-random value in [0, 1) for command number k
const noise = ( k ) => { const x = Math.sin( k * 12.9898 + 78.233 ) * 43758.5453; return x - Math.floor( x ); };

// speed plan (m/s) u seconds after L, starting from v0
export function speedCommand( u, v0 ) {

	const a = SCRIPT.slowTime, b = a + SCRIPT.accelTime;
	if ( u < a ) return v0 + ( SCRIPT.slowTo - v0 ) * smooth( u / a );
	if ( u < b ) return SCRIPT.slowTo + ( SCRIPT.cruise - SCRIPT.slowTo ) * smooth( ( u - a ) / SCRIPT.accelTime );
	return SCRIPT.cruise;

}

// The track from the handover H, every SCRIPT.dt:
// t (s), pos [x, y, z] (m), speed (m/s), psi (rad, nose bearing in the HUD convention),
// ax (forward acceleration, m/s^2), rate (nose turn rate, rad/s).
export function buildScripted( rows, H ) {

	const h = rows[ rowIndex( rows, H ) ];
	const boat = ( t ) => rows[ rowIndex( rows, t ) ].boat.position;
	const N = Math.round( SCRIPT.span / SCRIPT.dt ) + 1, dt = SCRIPT.dt;
	const tr = { H, dt, t: [], pos: [], speed: [], psi: [], ax: [], rate: [] };
	const y0 = h.drone.position[ 1 ];
	let p = h.drone.position.slice(), v = h.drone.speed, vr = 0, psi = h.drone.heading, r = 0;
	let cmd = v, cmdStep = - 1;
	for ( let k = 0; k < N; k ++ ) {

		const u = k * dt, t = H + u, b = boat( t );
		const step = Math.floor( u / SCRIPT.command + 1e-9 );
		if ( step !== cmdStep ) { cmdStep = step; cmd = speedCommand( step * SCRIPT.command, h.drone.speed ) + SCRIPT.commandJitter * ( 2 * noise( step ) - 1 ); }
		const dx = b[ 0 ] - p[ 0 ], dz = b[ 2 ] - p[ 2 ], L = Math.hypot( dx, dz ) || 1, ex = dx / L, ez = dz / L;
		const lat = wobble( u, 2, WOBBLE.lateral ), perp = [ - ez, ex ];
		tr.t.push( t );
		tr.pos.push( [ p[ 0 ] + perp[ 0 ] * lat, y0 + wobble( u, 3, WOBBLE.altitude ), p[ 2 ] + perp[ 1 ] * lat ] );
		tr.speed.push( v ); tr.psi.push( psi + wobble( u, 4, WOBBLE.psi ) ); tr.ax.push( vr ); tr.rate.push( r );
		// airframe and nose responses, one step
		const vrDot = SCRIPT.speedFreq * SCRIPT.speedFreq * ( cmd - v ) - 2 * SCRIPT.speedDamp * SCRIPT.speedFreq * vr;
		vr += vrDot * dt; v += vr * dt;
		const rDot = SCRIPT.turnFreq * SCRIPT.turnFreq * wrap( Math.atan2( dx, - dz ) - psi ) - 2 * SCRIPT.turnDamp * SCRIPT.turnFreq * r;
		r = Math.max( - SCRIPT.turnMax, Math.min( SCRIPT.turnMax, r + rDot * dt ) );
		psi += r * dt;
		p = [ p[ 0 ] + ex * v * dt, p[ 1 ], p[ 2 ] + ez * v * dt ];

	}

	return tr;

}

export function sampleScripted( tr, t ) {

	const k = Math.min( tr.pos.length - 1, Math.max( 0, ( t - tr.H ) / tr.dt ) );
	const i = Math.floor( k ), f = k - i, j = Math.min( i + 1, tr.pos.length - 1 );
	const lerp = ( a, b ) => a + ( b - a ) * f;
	return {
		t,
		pos: [ 0, 1, 2 ].map( ( c ) => lerp( tr.pos[ i ][ c ], tr.pos[ j ][ c ] ) ),
		speed: lerp( tr.speed[ i ], tr.speed[ j ] ),
		psi: lerp( tr.psi[ i ], tr.psi[ j ] ),
		ax: lerp( tr.ax[ i ], tr.ax[ j ] ),
		rate: lerp( tr.rate[ i ], tr.rate[ j ] ),
	};

}

// Attitude from the flight state: the thrust tilts toward the acceleration (forward) and toward the
// centripetal acceleration (speed x turn rate), plus a small wobble. up: the body's up vector.
// pitch < 0: nose down (forward acceleration or braking); roll > 0: right wing down.
export function attitudeOf( s ) {

	const g = SCRIPT.g;
	const F = [ Math.sin( s.psi ), 0, - Math.cos( s.psi ) ], R = [ Math.cos( s.psi ), 0, Math.sin( s.psi ) ];
	const aF = s.ax, aL = s.speed * s.rate;
	const ex = WOBBLE.attitude * Math.sin( 2 * Math.PI * 1.3 * s.t + 0.4 ), ez = WOBBLE.attitude * Math.sin( 2 * Math.PI * 1.9 * s.t + 1.1 );
	let up = [ aF / g * F[ 0 ] + aL / g * R[ 0 ] + ex, 1, aF / g * F[ 2 ] + aL / g * R[ 2 ] + ez ];
	const n = Math.hypot( ...up );
	up = up.map( ( c ) => c / n );
	const fwd = up[ 0 ] * F[ 0 ] + up[ 2 ] * F[ 2 ];
	const right = up[ 0 ] * R[ 0 ] + up[ 2 ] * R[ 2 ];
	return { up, pitch: Math.asin( Math.max( - 1, Math.min( 1, - fwd ) ) ), roll: Math.asin( Math.max( - 1, Math.min( 1, right ) ) ) };

}

// Gimbal hunting around the aim point (radians, camera-local yaw and pitch)
export function camHunt( t ) {

	return {
		yaw: 0.006 * Math.sin( 2 * Math.PI * 0.7 * t ) + 0.003 * Math.sin( 2 * Math.PI * 1.6 * t + 2 ),
		pitch: 0.005 * Math.sin( 2 * Math.PI * 0.9 * t + 1 ),
	};

}
