// Developer session recorder (key Z). Records the whole flight session from the
// moment Z is pressed until Z is pressed again: vehicle states, policy phase,
// actions, diagnostics, search output, timings, key presses and messages.
// Rows are sent every two seconds to the local server, which appends them to
// tidewater-game/recordings/session-<time>.jsonl. Without that server (another
// host), the rows are kept in memory and downloaded as a file on stop.

const SAMPLE_MS = 50;
const FLUSH_MS = 2000;
const MEMORY_ROW_LIMIT = 200000;

const finite = value => typeof value === 'number' && Number.isFinite( value ) ? value : null;
const stamp = () => {

	const d = new Date(), p = v => String( v ).padStart( 2, '0' );
	return `${ d.getFullYear() }-${ p( d.getMonth() + 1 ) }-${ p( d.getDate() ) }_${ p( d.getHours() ) }-${ p( d.getMinutes() ) }-${ p( d.getSeconds() ) }`;

};

function searchSummary( search ) {

	const heat = search?.search_heat;
	if ( ! heat?.length ) return null;
	let max = - Infinity, top = 0, above = 0;
	const gate = Math.log( .36 / .64 );
	for ( let i = 0; i < heat.length; i ++ ) {

		if ( heat[ i ] > max ) { max = heat[ i ]; top = i; }
		if ( heat[ i ] >= gate ) above ++;

	}
	const at = ( array, k ) => array?.length ? finite( array[ top + k * heat.length ] ) : null;
	return {
		presence: finite( search.search_presence?.[ 0 ] ), heat_max: finite( max ),
		heat_top_row: Math.floor( top / 80 ), heat_top_col: top % 80, heat_above_036: above,
		evidence_raw: [ 0, 1, 2, 3 ].map( k => at( search.search_evidence, k ) ),
		identity_raw: [ 0, 1 ].map( k => at( search.search_identity, k ) ),
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
		this.pending = [];
		this.memory = [];
		this.serverOk = true;
		this.rows = 0;
		this.lastKey = '';
		this.part = 0;
		this.flushing = null;
		const app = this.ops.app;
		this._push( {
			type: 'header', schema: 'tidewater.session_recording.v1', id: this.id, started_at: this.startedAt,
			user_agent: navigator.userAgent, page: location.href,
			gpu: app.gpu?.adapterInfo ? { vendor: app.gpu.adapterInfo.vendor, architecture: app.gpu.adapterInfo.architecture, description: app.gpu.adapterInfo.description } : null,
			settings: this._plain( app.settings ),
			policy_checkpoint: this.ops.bridge?.policy?.status?.checkpoint ?? null,
		} );
		this.mark( 'recording_started' );
		this._onKey = event => {

			if ( event.repeat ) return;
			const typing = event.target && /^(INPUT|SELECT|TEXTAREA)$/.test( event.target.tagName );
			if ( ! typing ) this.mark( event.type, { code: event.code } );

		};
		window.addEventListener( 'keydown', this._onKey, true );
		window.addEventListener( 'keyup', this._onKey, true );
		this.sampleTimer = setInterval( () => this._sample(), SAMPLE_MS );
		this.flushTimer = setInterval( () => this._flush(), FLUSH_MS );
		this._onHide = event => { if ( event.type === 'pagehide' ) this._flush( true ); else if ( document.visibilityState === 'hidden' ) this._flush(); };
		document.addEventListener( 'visibilitychange', this._onHide );
		window.addEventListener( 'pagehide', this._onHide );
		this._sample();
		this._showBadge( true );
		this.ops._toast( 'Session recording started · Z stops it' );

	}

	async stop() {

		if ( ! this.active ) return;
		this._sample();
		this.mark( 'recording_stopped', { rows: this.rows, duration_s: ( performance.now() - this.started ) / 1000 } );
		this.active = false;
		clearInterval( this.sampleTimer );
		clearInterval( this.flushTimer );
		window.removeEventListener( 'keydown', this._onKey, true );
		window.removeEventListener( 'keyup', this._onKey, true );
		document.removeEventListener( 'visibilitychange', this._onHide );
		window.removeEventListener( 'pagehide', this._onHide );
		this._showBadge( false );
		await this._flush();
		if ( this.serverOk ) {

			this.ops._toast( `Recording saved · tidewater-game/recordings/${ this.id }.jsonl` );

		} else {

			const blob = new Blob( [ this.memory.join( '\n' ) + '\n' ], { type: 'application/x-ndjson' } );
			const url = URL.createObjectURL( blob ), a = document.createElement( 'a' );
			a.href = url; a.download = this.id + '.jsonl'; a.click();
			setTimeout( () => URL.revokeObjectURL( url ), 2000 );
			this.ops._toast( 'Local server unavailable · recording downloaded as ' + this.id + '.jsonl' );

		}
		this.memory = [];

	}

	mark( name, extra = null ) {

		if ( ! this.active ) return;
		this._push( { type: 'mark', wall_s: this._wall(), sim_s: finite( this.ops.state?.time_s ), name, extra } );

	}

	_wall() {

		return ( performance.now() - this.started ) / 1000;

	}

	_plain( value ) {

		try { return JSON.parse( JSON.stringify( value ?? null ) ); } catch { return null; }

	}

	_push( record ) {

		let line;
		try { line = JSON.stringify( record, ( key, value ) => typeof value === 'number' && ! Number.isFinite( value ) ? null : ( ArrayBuffer.isView( value ) ? Array.from( value ) : value ) ); } catch { return; }
		this.pending.push( line );
		if ( ! this.serverOk ) {

			this.memory.push( line );
			if ( this.memory.length > MEMORY_ROW_LIMIT ) this.memory.splice( 1, this.memory.length - MEMORY_ROW_LIMIT );

		}

	}

	_sample() {

		if ( ! this.active ) return;
		const ops = this.ops, state = ops.state;
		if ( ! state ) return;
		const policy = ops.bridge?.policy, d = policy?.latestDiagnostics ?? null;
		const key = `${ finite( state.time_s ) }:${ d?.policy_elapsed_s ?? '' }:${ state.ml?.phase ?? '' }`;
		if ( key === this.lastKey ) return;
		this.lastKey = key;
		this.rows ++;
		const drone = state.drone, boat = state.boat;
		this._push( {
			type: 'row', wall_s: this._wall(), sim_s: finite( state.time_s ),
			realtime_factor: finite( state.realtime_factor ),
			control_mode: ops.mode, free_camera: !! ops.freeCamera, boat_autopilot: !! state.boat_autopilot,
			keys_held: [ ...( ops.app.input?.keys || [] ) ],
			phase: state.ml?.phase ?? null, ml_enabled: !! state.ml?.enabled, ml_error: state.ml?.error ?? null,
			intervention: state.ml?.intervention ?? null, outcome: state.ml?.outcome ?? null,
			action: state.ml?.action ?? null, message: state.message || null,
			drone: drone ? {
				position: drone.position, velocity: drone.velocity, yaw: finite( drone.yaw ), heading: finite( drone.heading ),
				roll: finite( drone.roll ), pitch: finite( drone.pitch ), speed: finite( drone.speed ), altitude: finite( drone.altitude ),
				pan: finite( drone.pan ), tilt: finite( drone.tilt ), armed: drone.armed, landed: drone.landed,
				px4_mode: drone.px4_mode ?? null, battery_pct: finite( drone.battery_pct ), failed_rotors: drone.failed_rotors ?? null,
				flight_requested: drone.flight_requested, landing_requested: drone.landing_requested,
			} : null,
			boat: boat ? {
				position: boat.position, velocity: boat.velocity, heading: finite( boat.heading ?? boat.yaw ), speed: finite( boat.speed ),
				roll: finite( boat.roll ), pitch: finite( boat.pitch ), port_power: finite( boat.port_power ), starboard_power: finite( boat.starboard_power ),
				platform: finite( boat.platform ), aft_lid: finite( boat.aft_lid ), fore_lid: finite( boat.fore_lid ),
			} : null,
			route: state.route ? { progress_m: finite( state.route.progress_m ), error_m: finite( state.route.error_m ), target_speed_m_s: finite( state.route.target_speed_m_s ) } : null,
			radio: state.radio ?? null,
			policy_status: policy ? { enabled: policy.status?.enabled, loading: policy.status?.loading, preloaded: !! policy.preloaded, error: policy.status?.error ?? null } : null,
			camera_exposure: policy?.camera?.exposureState ?? null,
			diagnostics: d,
			search: searchSummary( policy?.latestSearch ),
			timings: policy?.latestTiming ?? null,
		} );

	}

	_flush( unloading = false ) {

		if ( ! this.pending.length || ! this.serverOk ) { if ( ! this.serverOk ) this.pending = []; return this.flushing || Promise.resolve(); }
		const lines = this.pending;
		this.pending = [];
		const body = lines.join( '\n' ) + '\n';
		const url = new URL( '__session-recording?id=' + encodeURIComponent( this.id ), location.href );
		if ( unloading && navigator.sendBeacon ) {

			navigator.sendBeacon( url, new Blob( [ body ], { type: 'text/plain' } ) );
			return Promise.resolve();

		}
		const previous = this.flushing || Promise.resolve();
		// Batches are appended strictly in order.
		this.flushing = previous.then( () => fetch( url, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body } ) ).then( response => {

			if ( ! response.ok ) throw new Error( 'HTTP ' + response.status );

		} ).catch( () => {

			// Keep everything already recorded: switch to in-memory mode for a download on stop.
			if ( this.serverOk ) { this.serverOk = false; this.memory.push( ...lines ); }

		} );
		return this.flushing;

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
