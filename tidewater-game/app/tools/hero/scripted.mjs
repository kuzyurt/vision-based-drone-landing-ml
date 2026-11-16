// Scripted drone motion after L, for the drone-HUD shot. The policy is not run for this shot.
// From the handover the drone slows from its speed to SCRIPT.slowTo, accelerates to SCRIPT.cruise,
// flies straight at the boat at constant altitude and turns its nose toward the boat at a limited
// rate. The body, its gimbal and the onboard camera move with it (render.mjs); the HUD reads the
// same track (hud-overlay.mjs). Plain maths only: this module is shared by both.
export const SCRIPT = {
	slowTo: 1.0, cruise: 2.0, slowTime: 2.6, accelTime: 2.6,
	turnRate: 12 * Math.PI / 180, turn: 1.5, dt: 1 / 60, span: 7.5,
};

// Small, reproducible imperfections, so the approach reads as a learned controller and not as a
// keyframed path: slow speed and heading wobble, a few tenths of a metre of lateral drift and a
// few centimetres of altitude change. Sums of slow sines with fixed phases (same in every run,
// and the same for the HUD and the picture). Kept well inside what a real airframe would show.
export const WOBBLE = { speed: 0.07, psi: 0.8 * Math.PI / 180, lateral: 0.3, altitude: 0.05 };
function wobble( u, seed, amp ) {

	const f = [ 0.31, 0.53, 0.87, 1.27 ];
	let sum = 0;
	for ( let i = 0; i < f.length; i ++ ) sum += Math.sin( 2 * Math.PI * f[ i ] * 0.5 * u + seed * ( i + 1.3 ) + i );
	return amp * sum / f.length;

}

export function rowIndex( rows, t ) {

	let lo = 0, hi = rows.length - 1;
	while ( lo < hi ) { const mid = ( lo + hi + 1 ) >> 1; if ( rows[ mid ].t <= t ) lo = mid; else hi = mid - 1; }
	return lo;

}

export const smooth = ( x ) => { const c = Math.min( 1, Math.max( 0, x ) ); return c * c * ( 3 - 2 * c ); };
const wrap = ( a ) => Math.atan2( Math.sin( a ), Math.cos( a ) );

// speed (m/s) u seconds after L, starting from v0
export function speedAt( u, v0 ) {

	const a = SCRIPT.slowTime, b = a + SCRIPT.accelTime;
	if ( u < a ) return v0 + ( SCRIPT.slowTo - v0 ) * smooth( u / a );
	if ( u < b ) return SCRIPT.slowTo + ( SCRIPT.cruise - SCRIPT.slowTo ) * smooth( ( u - a ) / SCRIPT.accelTime );
	return SCRIPT.cruise;

}

// The track from the handover H, integrated every SCRIPT.dt:
// pos [x, y, z] (m), speed (m/s), psi (rad, bearing of the nose in the HUD's convention).
export function buildScripted( rows, H ) {

	const h = rows[ rowIndex( rows, H ) ];
	const boat = ( t ) => rows[ rowIndex( rows, t ) ].boat.position;
	const N = Math.round( SCRIPT.span / SCRIPT.dt ) + 1;
	const tr = { H, dt: SCRIPT.dt, pos: [], speed: [], psi: [] };
	const y0 = h.drone.position[ 1 ];
	// p, psi: the controller's own track; the outputs add the wobble on top of it
	let p = h.drone.position.slice(), psi = h.drone.heading;
	for ( let k = 0; k < N; k ++ ) {

		const u = k * SCRIPT.dt, b = boat( H + u );
		const v = speedAt( u, h.drone.speed ) + wobble( u, 1, WOBBLE.speed );
		const dx = b[ 0 ] - p[ 0 ], dz = b[ 2 ] - p[ 2 ], L = Math.hypot( dx, dz ) || 1;
		const ex = dx / L, ez = dz / L;
		const lat = wobble( u, 2, WOBBLE.lateral ), perp = [ - ez, ex ];
		tr.pos.push( [ p[ 0 ] + perp[ 0 ] * lat, y0 + wobble( u, 3, WOBBLE.altitude ), p[ 2 ] + perp[ 1 ] * lat ] );
		tr.speed.push( v ); tr.psi.push( psi + wobble( u, 4, WOBBLE.psi ) );
		const target = Math.atan2( dx, - dz );
		psi += Math.max( - SCRIPT.turnRate * SCRIPT.dt, Math.min( SCRIPT.turnRate * SCRIPT.dt, wrap( target - psi ) ) );
		p = [ p[ 0 ] + ex * v * SCRIPT.dt, p[ 1 ], p[ 2 ] + ez * v * SCRIPT.dt ];

	}

	return tr;

}

export function sampleScripted( tr, t ) {

	const k = Math.min( tr.pos.length - 1, Math.max( 0, ( t - tr.H ) / tr.dt ) );
	const i = Math.floor( k ), f = k - i, j = Math.min( i + 1, tr.pos.length - 1 );
	const lerp = ( a, b ) => a + ( b - a ) * f;
	return {
		pos: [ 0, 1, 2 ].map( ( c ) => lerp( tr.pos[ i ][ c ], tr.pos[ j ][ c ] ) ),
		speed: lerp( tr.speed[ i ], tr.speed[ j ] ),
		psi: lerp( tr.psi[ i ], tr.psi[ j ] ),
	};

}
