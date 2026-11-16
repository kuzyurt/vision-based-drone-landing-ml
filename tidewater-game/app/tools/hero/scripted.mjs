// Scripted drone motion after L, for the drone-HUD shot.
// The policy is not run for this shot. From the handover the drone eases from the position it had
// then to a hover 3 m astern of the boat and 4 m above its deck; the camera and the HUD follow.
// The boat is the recorded physics.
export const SCRIPT = { ramp: 18, standoff: 3, height: 4, turn: 1.5 };

export function rowIndex( rows, t ) {

	let lo = 0, hi = rows.length - 1;
	while ( lo < hi ) { const mid = ( lo + hi + 1 ) >> 1; if ( rows[ mid ].t <= t ) lo = mid; else hi = mid - 1; }
	return lo;

}

export const smooth = ( x ) => { const c = Math.min( 1, Math.max( 0, x ) ); return c * c * ( 3 - 2 * c ); };

// { position [x, y, z], speed (m/s), heading (rad, bearing to the boat) } at simulation time t
export function scriptedDrone( rows, handover, t ) {

	const boat = ( tt ) => rows[ rowIndex( rows, tt ) ].boat.position;
	const hover = ( tt ) => {

		const p0 = boat( tt - 1 ), p1 = boat( tt + 1 ), b = boat( tt );
		let fx = p1[ 0 ] - p0[ 0 ], fz = p1[ 2 ] - p0[ 2 ];
		const L = Math.hypot( fx, fz );
		if ( L < 0.2 ) { fx = 1; fz = 0; } else { fx /= L; fz /= L; }
		return [ b[ 0 ] - fx * SCRIPT.standoff, b[ 1 ] + SCRIPT.height, b[ 2 ] - fz * SCRIPT.standoff ];

	};
	const start = rows[ rowIndex( rows, handover ) ].drone.position;
	const position = ( tt ) => {

		const k = smooth( ( tt - handover ) / SCRIPT.ramp ), h = hover( tt );
		return [ 0, 1, 2 ].map( ( i ) => start[ i ] + ( h[ i ] - start[ i ] ) * k );

	};
	const p = position( t ), q = position( t + 0.05 ), r = position( t - 0.05 );
	const speed = Math.hypot( q[ 0 ] - r[ 0 ], q[ 1 ] - r[ 1 ], q[ 2 ] - r[ 2 ] ) / 0.1;
	const b = boat( t );
	return { position: p, speed, heading: Math.atan2( b[ 0 ] - p[ 0 ], - ( b[ 2 ] - p[ 2 ] ) ) };

}
