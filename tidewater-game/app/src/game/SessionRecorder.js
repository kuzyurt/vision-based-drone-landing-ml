// Developer session log (key Z). One compact row every 0.5 s of simulation time from the
// moment Z is pressed until Z is pressed again, plus a few small event rows when something
// changes (policy phase, boat enters / leaves the camera view, identity confirmed, ...).
//
// A row answers, at that moment: where the boat and the drone are, how they move and which way
// they face; where the gimbal camera points and how fast it turns; how far apart the vehicles
// are; whether the camera sees the boat and where in the 640x360 policy image it is; what the
// policy is doing; and what the pad finder (search head + pose head) reports.
//
// Z starts the recording, Z again stops it and saves everything as one JSON file
// (session-<time>.json: { header, rows: [...] }) in the browser's Downloads folder.

const ROW_S = 0.5; // simulation seconds between rows
const POLL_MS = 50; // how often the state is checked for the next row and for events
const IMAGE_W = 640, IMAGE_H = 360; // the policy camera image
const HEAT_W = 80, HEAT_H = 45; // pad finder heat map grid
const DEG = 180 / Math.PI;
const TOP_PROPOSALS = 3;

const finite = value => typeof value === 'number' && Number.isFinite( value ) ? value : null;
const round = ( value, digits = 2 ) => {

	const v = finite( value );
	if ( v === null ) return null;
	const k = 10 ** digits;
	return Math.round( v * k ) / k;

};
const roundAll = ( values, digits = 2 ) => values && typeof values.length === 'number' ? Array.from( values, v => round( v, digits ) ) : null;
const sigmoid = x => x >= 0 ? 1 / ( 1 + Math.exp( - x ) ) : Math.exp( x ) / ( 1 + Math.exp( x ) );
const dot = ( a, b ) => a[ 0 ] * b[ 0 ] + a[ 1 ] * b[ 1 ] + a[ 2 ] * b[ 2 ];
const sub = ( a, b ) => [ a[ 0 ] - b[ 0 ], a[ 1 ] - b[ 1 ], a[ 2 ] - b[ 2 ] ];
const wrap180 = deg => ( ( ( deg + 180 ) % 360 ) + 360 ) % 360 - 180;
const stamp = () => {

	const d = new Date(), p = v => String( v ).padStart( 2, '0' );
	return `${ d.getFullYear() }-${ p( d.getMonth() + 1 ) }-${ p( d.getDate() ) }_${ p( d.getHours() ) }-${ p( d.getMinutes() ) }-${ p( d.getSeconds() ) }`;

};

// The game state uses view coordinates [x, y(up), z]; the log uses [east, north, up] (metres).
const toENU = p => p ? [ p[ 0 ], - p[ 2 ], p[ 1 ] ] : null;
const compass = ( east, north ) => ( ( Math.atan2( east, north ) * DEG ) + 360 ) % 360; // 0 = north, 90 = east

// The drone's gimbal camera from its view matrix (row-major, view coordinates; columns are the
// camera's right, up and back axes, the last column its position).
function cameraFrame( view ) {

	const M = view?.matrix;
	if ( ! M || M.length < 16 || ! Number.isFinite( view.fovy ) ) return null;
	return {
		pos: [ M[ 3 ], M[ 7 ], M[ 11 ] ], right: [ M[ 0 ], M[ 4 ], M[ 8 ] ], up: [ M[ 1 ], M[ 5 ], M[ 9 ] ],
		back: [ M[ 2 ], M[ 6 ], M[ 10 ] ], fovy: view.fovy * Math.PI / 180,
	};

}

// Geometric projection of a world point into the policy image. It says where the point would be
// in the image, not whether it is visible (terrain or other objects in front of it are ignored).
function project( cam, point ) {

	const rel = sub( point, cam.pos ), range = Math.hypot( rel[ 0 ], rel[ 1 ], rel[ 2 ] );
	const x = dot( rel, cam.right ), y = dot( rel, cam.up ), z = - dot( rel, cam.back ); // z: depth in front of the lens
	if ( z <= 0.05 ) return { in_view: false, reason: 'behind_camera', px: null, off_axis_deg: round( Math.acos( Math.max( - 1, Math.min( 1, z / range ) ) ) * DEG, 1 ) };
	const focal = ( IMAGE_H / 2 ) / Math.tan( cam.fovy / 2 );
	const px = [ IMAGE_W / 2 + focal * x / z, IMAGE_H / 2 - focal * y / z ];
	const inside = px[ 0 ] >= 0 && px[ 0 ] < IMAGE_W && px[ 1 ] >= 0 && px[ 1 ] < IMAGE_H;
	return {
		in_view: inside, reason: inside ? null : 'outside_frame', px: [ round( px[ 0 ], 0 ), round( px[ 1 ], 0 ) ],
		off_axis_deg: round( Math.acos( Math.max( - 1, Math.min( 1, z / range ) ) ) * DEG, 1 ),
	};

}

// Peak of the pad finder's heat map (logits) as an image position.
function heatPeak( search ) {

	const heat = search?.search_heat;
	if ( ! heat?.length ) return null;
	let max = - Infinity, top = 0;
	for ( let i = 0; i < heat.length; i ++ ) if ( heat[ i ] > max ) { max = heat[ i ]; top = i; }
	return {
		prob: round( sigmoid( max ), 3 ),
		px: [ Math.round( ( ( top % HEAT_W ) + 0.5 ) * IMAGE_W / HEAT_W ), Math.round( ( Math.floor( top / HEAT_W ) + 0.5 ) * IMAGE_H / HEAT_H ) ],
		presence_raw: round( search.search_presence?.[ 0 ], 3 ),
	};

}

export class SessionRecorder {

	constructor( ops ) {

		this.ops = ops;
		this.active = false;
		this.badge = null;

	}

	toggle() {

		return this.active ? this.stop() : this.start();

	}

	start() {

		if ( this.active ) return;
		this.active = true;
		this.id = 'session-' + stamp();
		this.started = performance.now();
		this.startedAt = new Date().toISOString();
		this.lines = []; // every row, already serialised
		this.rows = 0;
		this.events = 0;
		this.nextT = null;
		this.lastT = null;
		this.prev = null; // previous row's values, for rates
		this.watch = null; // previous values of the things whose changes are logged
		this.header = {
			schema: 'tidewater.session_log.v3', id: this.id, started_at: this.startedAt,
			policy_checkpoint: this.ops.bridge?.policy?.status?.checkpoint ?? null,
			row_interval_sim_s: ROW_S,
			units: {
				positions: '[east, north, up] metres (up = height above sea level)', velocities: 'm/s, same axes',
				angles: 'degrees; heading and *_az/bearing are compass (0 north, 90 east); pan/tilt are the gimbal joint angles',
				rates: 'deg/s', image: `${ IMAGE_W }x${ IMAGE_H } policy camera, px = [column, row] from the top left`,
				boat_in_cam: 'geometric projection of the boat origin, ignores occlusion',
				action: 'policy output [forward, right, down, yaw rate, pan rate, tilt rate] as sent, raw units',
			},
		};
		this.mark( 'recording_started' );
		this.pollTimer = setInterval( () => this._poll(), POLL_MS );
		this._poll();
		this._showBadge( true );
		this.ops._toast( 'Session recording started · Z stops it and saves the file' );

	}

	stop() {

		if ( ! this.active ) return;
		this._poll( true );
		this.mark( 'recording_stopped', { rows: this.rows, events: this.events, duration_s: round( ( performance.now() - this.started ) / 1000, 1 ) } );
		this.active = false;
		clearInterval( this.pollTimer );
		this._showBadge( false );
		const name = this.id + '.json';
		this._download( name );
		this._saveLocal();
		this.ops._toast( `Recording saved to Downloads · ${ name }` );
		this.lines = [];

	}

	// Also keep a copy on the local dev/static server (tidewater-game/recordings/<id>.jsonl:
	// first line { header }, then one row per line). Only works on a local host; silently
	// skipped anywhere else.
	_saveLocal() {

		if ( ! /^(127\.0\.0\.1|localhost|\[::1\])$/.test( globalThis.location?.hostname ?? '' ) ) return;
		const body = [ JSON.stringify( { header: this.header } ), ...this.lines ].join( '\n' ) + '\n';
		const url = new URL( '__session-recording', location.href );
		url.searchParams.set( 'id', this.id );
		this.lastSaved = fetch( url, { method: 'POST', body, headers: { 'Content-Type': 'application/x-ndjson' } } )
			.then( r => r.ok ? r.text() : null ).catch( () => null );

	}

	// One valid JSON file { header, rows: [...] }, each row on its own line.
	_download( name ) {

		const text = '{\n"header": ' + JSON.stringify( this.header ) + ',\n"rows": [\n' + this.lines.join( ',\n' ) + '\n]\n}\n';
		const url = URL.createObjectURL( new Blob( [ text ], { type: 'application/json' } ) ), a = document.createElement( 'a' );
		a.href = url; a.download = name;
		document.body.appendChild( a );
		a.click();
		a.remove();
		setTimeout( () => URL.revokeObjectURL( url ), 10000 );

	}

	// A small event row (other code calls this for policy toggles and on-screen messages).
	mark( name, extra = null ) {

		if ( ! this.active ) return;
		this.events ++;
		this._push( { type: 'event', t: round( this.ops.state?.time_s, 2 ), event: name, ...extra } );

	}

	_push( record ) {

		let line;
		try { line = JSON.stringify( record, ( key, value ) => typeof value === 'number' && ! Number.isFinite( value ) ? null : value ); } catch { return; }
		this.lines.push( line );

	}

	_poll( final = false ) {

		if ( ! this.active ) return;
		const state = this.ops.state;
		if ( ! state || ! Number.isFinite( state.time_s ) ) return;
		const t = state.time_s;
		if ( this.lastT !== null && t < this.lastT - 1 ) { this.mark( 'sim_time_reset', { from_t: round( this.lastT, 2 ) } ); this.nextT = null; this.prev = null; }
		this.lastT = t;
		let snap;
		try { snap = this._snapshot( state, t ); } catch ( error ) { this.mark( 'log_error', { message: String( error?.message ?? error ) } ); return; }
		this._events( snap, t );
		if ( final && this.prev && t - this.prev.t < 0.05 ) return; // the last row is already this moment
		if ( this.nextT === null || t >= this.nextT || final ) {

			this.nextT = this.nextT === null ? t + ROW_S : this.nextT + ROW_S;
			if ( this.nextT < t ) this.nextT = t + ROW_S;
			this.rows ++;
			this._push( { type: 'tick', t: round( t, 2 ), wall_s: round( ( performance.now() - this.started ) / 1000, 1 ), ...snap.row } );
			this.prev = { t, pan: snap.raw.pan, tilt: snap.raw.tilt };

		}

	}

	_snapshot( state, t ) {

		const ops = this.ops, policy = ops.bridge?.policy;
		const drone = state.drone, boat = state.boat, ml = state.ml || {};
		const diag = policy?.latestDiagnostics ?? ml.diagnostics ?? {};
		const guidance = diag.guidance ?? null;
		const dt = this.prev ? t - this.prev.t : 0;

		// ---- vehicles
		const dPos = toENU( drone?.position ), dVel = toENU( drone?.velocity );
		const bPos = toENU( boat?.position ), bVel = toENU( boat?.velocity );
		const bSpeed = bVel ? Math.hypot( bVel[ 0 ], bVel[ 1 ] ) : null;
		const boatRow = boat ? {
			pos: roundAll( bPos ), vel: roundAll( bVel ), speed: round( boat.speed ?? bSpeed ),
			heading: round( boat.heading * DEG, 1 ), course: bSpeed > 0.15 ? round( compass( bVel[ 0 ], bVel[ 1 ] ), 1 ) : null,
			autopilot: !! state.boat_autopilot,
		} : null;
		const droneRow = drone ? {
			pos: roundAll( dPos ), vel: roundAll( dVel ), speed: round( drone.speed ), climb: round( dVel?.[ 2 ] ),
			heading: round( drone.heading * DEG, 1 ), course: drone.speed > 0.15 ? round( compass( dVel[ 0 ], dVel[ 1 ] ), 1 ) : null,
			roll: round( drone.roll * DEG, 1 ), pitch: round( drone.pitch * DEG, 1 ),
			armed: !! drone.armed, landed: !! drone.landed, px4: drone.px4_mode ?? null, battery_pct: round( drone.battery_pct, 0 ),
		} : null;

		// ---- gimbal camera
		const cam = cameraFrame( state.views?.drone );
		const pan = finite( drone?.pan ), tilt = finite( drone?.tilt );
		const look = cam ? toENU( [ - cam.back[ 0 ], - cam.back[ 1 ], - cam.back[ 2 ] ] ) : null;
		const cameraRow = drone ? {
			pan: round( pan * DEG, 1 ), tilt: round( tilt * DEG, 1 ),
			pan_rate: dt > 0 && this.prev.pan !== null && pan !== null ? round( wrap180( ( pan - this.prev.pan ) * DEG ) / dt, 1 ) : null,
			tilt_rate: dt > 0 && this.prev.tilt !== null && tilt !== null ? round( ( tilt - this.prev.tilt ) * DEG / dt, 1 ) : null,
			look_az: look ? round( compass( look[ 0 ], look[ 1 ] ), 1 ) : null,
			look_el: look ? round( Math.asin( Math.max( - 1, Math.min( 1, look[ 2 ] ) ) ) * DEG, 1 ) : null,
		} : null;

		// ---- drone <-> boat
		let rel = null, boatInCam = null;
		if ( dPos && bPos ) {

			const d = sub( bPos, dPos ), horiz = Math.hypot( d[ 0 ], d[ 1 ] ), range = Math.hypot( d[ 0 ], d[ 1 ], d[ 2 ] );
			const bearing = compass( d[ 0 ], d[ 1 ] );
			const rv = sub( bVel || [ 0, 0, 0 ], dVel || [ 0, 0, 0 ] );
			rel = {
				range: round( range ), horiz: round( horiz ), above_boat: round( - d[ 2 ] ),
				bearing: round( bearing, 1 ), bearing_vs_body: drone ? round( wrap180( bearing - drone.heading * DEG ), 1 ) : null,
				bearing_vs_camera: look ? round( wrap180( bearing - compass( look[ 0 ], look[ 1 ] ) ), 1 ) : null,
				closing_speed: horiz > 0.05 ? round( - ( rv[ 0 ] * d[ 0 ] + rv[ 1 ] * d[ 1 ] ) / horiz ) : null,
			};
			if ( cam ) boatInCam = project( cam, boat.position );

		}

		// ---- policy
		const action = ml.action ?? null;
		const proposals = Array.isArray( diag.search_proposals ) ? diag.search_proposals : [];
		const peak = heatPeak( policy?.latestSearch );
		const policyRow = {
			on: !! ml.enabled, loading: !! policy?.status?.loading, phase: ml.phase ?? null, control_phase: diag.control_phase ?? null,
			intervention: ml.intervention ?? diag.intervention ?? null, error: ml.error ?? null,
			landed: ml.outcome?.landed ?? null, collision: ml.outcome?.collision_failure ?? null,
			action: roundAll( action ),
			search: {
				mode: diag.search_mode ?? null, phase: diag.search_phase ?? null, passes_done: diag.scan_passes_completed ?? null,
				identity_confirmed: diag.search_identity_confirmed ?? null, selected: diag.search_selected ?? diag.selected_visual_track ?? null,
				warning: diag.search_warning ?? null, pre360_done: diag.pre360_done ?? null,
			},
			// radio approach (intercept + braking): metres to the waiting point, closing speed, warnings
			approach: diag.approach_hold_distance_m === undefined ? null : {
				hold_dist: round( diag.approach_hold_distance_m, 1 ), closing: round( diag.approach_closing_m_s ),
				closing_max: round( diag.approach_closing_limit_m_s ), boat_speed: round( diag.approach_boat_speed_m_s ),
				warning: diag.approach_warning ?? null,
			},
			guidance: guidance ? { ...guidance, pause_respected_s: round( guidance.pause_respected_s ) } : null,
		};
		const padFinder = {
			heat_peak: peak,
			proposals: proposals.slice( 0, TOP_PROPOSALS ).map( p => ( {
				px: roundAll( p.pixel, 0 ), conf: round( p.confidence, 2 ), label: p.evidence ?? null, target_p: round( p.identity_target_probability, 2 ),
			} ) ),
			proposal_count: proposals.length,
			pose_valid: diag.pose_valid ?? null, pad_visible_p: round( diag.pad_visibility_probability, 2 ), image_head_visibility: round( diag.image_head_visibility, 2 ),
			metric_confirmed: diag.metric_confirmed ?? null,
			est_rel_pos: roundAll( diag.estimated_relative_position ), est_lateral_err: round( diag.estimated_lateral_error_m ), est_clearance: round( diag.estimated_clearance_m ),
			est_heading_err: round( diag.estimated_heading_error_deg, 1 ),
		};
		const radio = state.radio ? { status: state.radio.status ?? null, quality: round( state.radio.quality, 0 ), age_s: round( state.radio.telemetry_age_s, 1 ) } : null;

		return {
			raw: { pan, tilt },
			watch: {
				phase: policyRow.phase, control_phase: policyRow.control_phase, search_phase: policyRow.search.phase,
				identity_confirmed: policyRow.search.identity_confirmed, warning: policyRow.search.warning, intervention: policyRow.intervention,
				on: policyRow.on, landed_on_boat: policyRow.landed, collision: policyRow.collision, armed: droneRow?.armed, landed: droneRow?.landed,
				radio: radio?.status ?? null, boat_in_view: boatInCam ? boatInCam.in_view : null,
				proposals: proposals.length > 0, pose_valid: padFinder.pose_valid, metric: padFinder.metric_confirmed,
				// guidance decisions (glare / approach / near-deck); each change is one event row
				early_commit: guidance?.early_commit_active ?? null, hop: guidance?.hop_active ?? null,
				commit_gate: guidance?.last_gate ?? null, commit_abort: guidance?.last_abort ?? null,
				glare_flags: guidance?.glare_flags ?? null, radio_blocking: guidance ? guidance.radio_blocked_views > 0 : null,
				approach_warning: policyRow.approach?.warning ?? null,
				// sun-glare zone and horizon evidence
				zone_glare: guidance?.zone_glare ?? null, zone_real: guidance?.zone_real ?? null,
				glare_active: guidance?.glare_active ?? null, glare_protocols: guidance?.glare_protocols ?? null,
				horizon_evidence: guidance ? guidance.horizon_promoted_frames > 0 : null,
			},
			detail: { boat_in_cam: boatInCam, rel },
			row: { boat: boatRow, drone: droneRow, camera: cameraRow, rel, boat_in_cam: boatInCam, policy: policyRow, pad_finder: padFinder, radio },
		};

	}

	// One small event row per change of the watched values (the first poll only stores them).
	_events( snap, t ) {

		const now = snap.watch, before = this.watch;
		this.watch = now;
		if ( ! before ) return;
		for ( const key of Object.keys( now ) ) {

			if ( now[ key ] === before[ key ] ) continue;
			const extra = { from: before[ key ] ?? null, to: now[ key ] ?? null };
			if ( key === 'boat_in_view' ) {

				const b = snap.detail.boat_in_cam;
				extra.px = b?.px ?? null; extra.reason = b?.reason ?? null; extra.range = snap.detail.rel?.range ?? null;

			}
			this.mark( 'changed_' + key, extra );

		}

	}

	_showBadge( on ) {

		if ( on && ! this.badge ) {

			const badge = document.createElement( 'div' );
			badge.textContent = '● REC  ·  Z to stop';
			badge.setAttribute( 'role', 'status' );
			Object.assign( badge.style, { position: 'fixed', top: '10px', left: '50%', transform: 'translateX(-50%)', zIndex: 100000, padding: '4px 10px', borderRadius: '6px', background: 'rgba(160,20,20,.85)', color: '#fff', font: '600 12px/1.4 system-ui, sans-serif', letterSpacing: '.04em', pointerEvents: 'none' } );
			document.body.appendChild( badge );
			this.badge = badge;

		} else if ( ! on && this.badge ) {

			this.badge.remove();
			this.badge = null;

		}

	}

}
