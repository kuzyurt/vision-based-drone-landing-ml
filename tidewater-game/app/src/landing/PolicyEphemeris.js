// Sun direction for the policy, as a real drone gets it: from its clock and
// GNSS position through a solar ephemeris. Tidewater's mission clock is the
// time-of-day setting; its site (latitude, date, the map's turn about north)
// is fixed per map. This is the same astronomy the sky uses, evaluated from
// those mission inputs; nothing is read back from the renderer.
const RAD = Math.PI / 180;

export function sunDirectionENU( hours, { latitudeDeg = 24, declinationDeg = 6, siteRotationDeg = 0 } = {} ) {

	const phi = latitudeDeg * RAD, dec = declinationDeg * RAD, H = ( hours - 12 ) * 15 * RAD;
	const east = - Math.cos( dec ) * Math.sin( H );
	const north = Math.cos( phi ) * Math.sin( dec ) - Math.sin( phi ) * Math.cos( dec ) * Math.cos( H );
	const up = Math.sin( phi ) * Math.sin( dec ) + Math.cos( phi ) * Math.cos( dec ) * Math.cos( H );
	// The map turns the sun's daily path about the vertical (view x = east, z = -north).
	const a = siteRotationDeg * RAD, x = east, z = - north;
	const xr = Math.cos( a ) * x + Math.sin( a ) * z, zr = - Math.sin( a ) * x + Math.cos( a ) * z;
	const v = [ xr, - zr, up ], n = Math.hypot( ...v );
	return v.map( value => value / n );

}

export function policyEphemeris( settings ) {

	if ( ! settings || ! Number.isFinite( settings.timeOfDay ) ) return null;
	return {
		sun_direction_enu: sunDirectionENU( settings.timeOfDay, { siteRotationDeg: settings.sunAzimuth || 0 } ),
		source: 'solar ephemeris from mission clock and GNSS site',
	};

}
