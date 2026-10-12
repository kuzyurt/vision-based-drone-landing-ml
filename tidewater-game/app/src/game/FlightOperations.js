import { SimulationBridge } from '../landing/SimulationBridge.js';

const MAP = { xMin: - 250, xMax: 330, zMin: - 125, zMax: 285 };
const clamp = ( value, low, high ) => Math.max( low, Math.min( high, value ) );
const degrees = value => ( ( value * 180 / Math.PI % 360 ) + 360 ) % 360;
const DRONE_KEYS = [ 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyQ', 'KeyE', 'KeyR', 'KeyF', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown' ];

export class FlightOperations {

	constructor( app ) {

		this.app = app;
		this.active = false;
		this.mode = 'drone';
		this.boatCamera = 'boat_dock';
		this.autopilot = true;
		this.state = null;
		this.radio = null;
		this.bridge = null;
		this._uiTime = 0;
		this._mapTime = 0;
		this._inputTime = 0;
		this._ui = null;
		this.manualMotors = [ 0, 0 ];
		this.suppressedKeys = new Set();
		this._buildUI();

	}

	_buildUI() {

		const root = document.createElement( 'div' );
		root.id = 'flight-console';
		root.hidden = true;
		root.innerHTML = `
			<section class="fc-startup fc-panel" data-bind="startup" role="status">
				<strong data-bind="startup-title">Preparing simulator camera</strong>
				<p data-bind="startup-detail">Loading the original vehicles and checking the safe boat course.</p>
				<button data-action="retry" hidden>Retry simulation</button>
			</section>
			<header class="fc-top">
				<div class="fc-wordmark"><span class="fc-mark">T</span><span><b>Tidewater</b><small>Coastal flight operations · native MuJoCo</small></span></div>
				<div class="fc-link" data-bind="link" data-state="waiting"><i></i><span data-bind="link-label">Connecting simulator</span><small data-bind="controller-source">Native MuJoCo</small></div>
				<div class="fc-top-actions"><span class="fc-mode" data-bind="mode-label">Drone feed</span><button data-action="switch">Switch to boat <kbd>B</kbd></button><button class="fc-icon-btn" data-action="reset" title="Reset both vehicles">Reset <kbd>Home</kbd></button></div>
			</header>
			<aside class="fc-map-panel fc-panel">
				<div class="fc-panel-head"><span>Live telemetry map</span><small>Shared MuJoCo frame</small></div>
				<canvas class="fc-map" width="520" height="360" aria-label="Map showing the actual Tidewater coastline, route, drone and boat"></canvas>
				<div class="fc-map-legend"><span><i class="fc-dot fc-dot-drone"></i>Drone</span><span><i class="fc-dot fc-dot-boat"></i>Boat</span><span class="fc-map-course">Verified closed water route</span></div>
				<div class="fc-range"><strong data-bind="range">—</strong><span>m separation</span><span class="fc-bearing">Bearing <b data-bind="bearing">—</b></span></div>
			</aside>
			<aside class="fc-right-rail">
				<section class="fc-panel fc-attitude-panel">
					<div class="fc-panel-head"><span data-bind="attitude-title">Drone attitude</span><small>MuJoCo body pose</small></div>
					<div class="fc-attitude">
						<div class="fc-horizon"><div class="fc-horizon-sky"></div><div class="fc-horizon-ground"></div><div class="fc-horizon-graticule" data-bind="horizon"></div><div class="fc-horizon-mark"><i></i><b></b><i></i></div><span class="fc-horizon-tick fc-tick-top"></span><span class="fc-horizon-tick fc-tick-bottom"></span><span class="fc-horizon-tick fc-tick-left"></span><span class="fc-horizon-tick fc-tick-right"></span></div>
						<div class="fc-attitude-readings"><div><small>Pitch</small><b data-bind="pitch">—</b></div><div><small>Roll</small><b data-bind="roll">—</b></div><div><small>Heading</small><b data-bind="heading">—</b></div><div><small>Gimbal tilt</small><b data-bind="tilt">—</b></div><div><small>Gimbal pan</small><b data-bind="pan">—</b></div></div>
					</div>
					<div class="fc-flight-stats"><div><small>Altitude</small><b data-bind="altitude">—<em> m</em></b></div><div><small>Drone speed</small><b data-bind="drone-speed">—<em> m/s</em></b></div><div><small>Boat speed</small><b data-bind="boat-speed">—<em> m/s</em></b></div><div><small>Boat course</small><b data-bind="boat-course">—</b></div></div>
				</section>
				<section class="fc-panel fc-radio-panel">
					<div class="fc-panel-head"><span>Vehicle telemetry link</span><small>Estimated SX1262 pair · simulated</small></div>
					<div class="fc-quality-row"><strong data-bind="quality">—</strong><span>%<small>link quality</small></span><div class="fc-bars" data-bind="bars"><i></i><i></i><i></i><i></i><i></i></div></div>
					<div class="fc-radio-grid"><div><small>RSSI</small><b data-bind="rssi">— <em>dBm</em></b></div><div><small>SNR</small><b data-bind="snr">— <em>dB</em></b></div><div><small>Latency</small><b data-bind="latency">— <em>ms</em></b></div><div><small>Packet loss</small><b data-bind="loss">— <em>%</em></b></div></div>
					<div class="fc-packet-line"><span>TX <b data-bind="tx">0</b></span><span>RX <b data-bind="rx">0</b></span><span>Dropped <b data-bind="dropped">0</b></span><span>868 MHz · SF7</span></div>
					<div class="fc-radio-note" data-bind="radio-note">RSSI, SNR and packet delivery are simulated; no radio hardware is connected.</div>
					<button class="fc-reconnect" data-action="reconnect">Retry connection <kbd>C</kbd></button>
				</section>
			</aside>
			<div class="fc-center-mark" aria-hidden="true"><i></i><b></b><i></i><span></span></div>
			<section class="fc-bottom fc-panel">
				<div class="fc-bottom-main">
					<div class="fc-vehicle-summary"><span class="fc-summary-symbol" data-bind="vehicle-symbol">⌖</span><span><small data-bind="vehicle-type">X500 aircraft</small><b data-bind="vehicle-name">Holybro X500 V2</b></span></div>
					<div class="fc-controls-copy"><small>Controls</small><b data-bind="controls">WASD flight · R/F altitude · Q/E yaw · arrows/mouse camera · B boat</b></div>
					<div class="fc-bottom-actions"><button class="fc-flight-button" data-action="flight">Take off</button><button class="fc-autopilot is-on" data-action="autopilot"><span class="fc-switch-dot"></span><span data-bind="autopilot-label">Route following</span><kbd>P</kbd></button><button data-action="camera">Dock camera <kbd>U</kbd></button><button data-action="lid"><span data-bind="lid-label">Close lids</span></button><button data-action="platform"><span data-bind="platform-label">Lower platform</span></button></div>
				</div>
			<div class="fc-manual-controls" data-bind="manual-controls" hidden>
				<div class="fc-motor-mode"><span data-bind="motor-mode">Route following</span><button data-action="manual">Manual motors</button><button data-action="automatic">Auto route</button><button data-action="stop">Stop motors</button></div>
				<div class="fc-motor-sliders"><label><span>Port throttle</span><input aria-label="Port motor throttle" data-control="port" type="range" min="0" max="100" value="0"><b data-bind="port">0%</b><small data-bind="port-actual">Output 0%</small></label>
				<label><span>Starboard throttle</span><input aria-label="Starboard motor throttle" data-control="starboard" type="range" min="0" max="100" value="0"><b data-bind="starboard">0%</b><small data-bind="starboard-actual">Output 0%</small></label></div>
				<div class="fc-deck-state"><span data-bind="deck-state">Deck mechanisms ready</span><small>W/S throttle · A/D differential steering · P auto/manual</small></div>
			</div>
			<div class="fc-bottom-foot"><span data-bind="route-status">Waiting for terrain collision import</span><span data-bind="performance">WebGPU · native MuJoCo</span></div>
			</section>
			<div class="fc-toast" data-bind="toast" role="status"></div>
		`;
		document.body.append( root );
		this._ui = {
			root,
			canvas: root.querySelector( '.fc-map' ),
			bindings: new Map( Array.from( root.querySelectorAll( '[data-bind]' ), element => [ element.dataset.bind, element ] ) ),
		};
		root.addEventListener( 'click', event => {
			const action = event.target.closest( '[data-action]' )?.dataset.action;
			if ( action === 'switch' ) this.switchVehicle();
			else if ( action === 'retry' ) this.bridge?.retry();
			else if ( action === 'reset' ) this.resetVehicles();
			else if ( action === 'reconnect' ) this.reconnect();
			else if ( action === 'flight' ) this.toggleFlight();
			else if ( action === 'autopilot' ) this.setAutopilot( ! this.autopilot );
			else if ( action === 'manual' ) this.setAutopilot( false );
			else if ( action === 'automatic' ) this.setAutopilot( true );
			else if ( action === 'stop' ) { this.setAutopilot( false ); this.manualMotors = [ 0, 0 ]; this.bridge?.send( { motors: [ 0, 0 ] } ); }
			else if ( action === 'camera' ) this.toggleBoatCamera();
			else if ( action === 'lid' ) this.toggleLid();
			else if ( action === 'platform' ) this.togglePlatform();
		} );
		root.addEventListener( 'input', event => {
			const side = event.target.dataset.control;
			if ( side !== 'port' && side !== 'starboard' ) return;
			const index = side === 'port' ? 0 : 1;
			this.manualMotors[ index ] = Number( event.target.value );
			this._text( side, `${ event.target.value }%` );
			this.bridge?.send( { motors: this.manualMotors, mode: this.mode } );
		} );

	}

	activate() {

		if ( this.active ) return;
		this.active = true;
		this.mode = 'drone';
		this.boatCamera = 'boat_dock';
		this._ui.root.hidden = false;
		document.body.classList.add( 'flight-mode-active' );
		// Tidewater supplies the scenery. The existing combined CAD simulation owns both vehicles.
		this.app.boat.group.visible = false;
		this.app.boatCtl.update = () => {};
		this.app.boatCtl.queueQueries = () => {};
		this.app.boatSpray.update = () => {};
		this.app.wake.update = () => {};
		this.app.boat.update = () => {};
		this.app.game.update = () => {};
		this.bridge = new SimulationBridge( this.app, state => this._receive( state ) );
		// Input installs its listeners first; transport changes after its key set
		// is updated, independently of slow GPU frames. PX4 keeps its 25 Hz pilot.
		const sendKeys = event => {
			if ( event.repeat || ( event.code && ! DRONE_KEYS.includes( event.code ) ) ) return;
			queueMicrotask( () => this._sendDroneKeys() );
		};
		window.addEventListener( 'keydown', sendKeys );
		window.addEventListener( 'keyup', sendKeys );
		window.addEventListener( 'blur', sendKeys );
		this._refreshUI();
		this._toast( 'Loading original X500 and AERODOCK CAD into MuJoCo' );

	}

	_receive( state ) {

		this.state = state;
		this.radio = state.radio || this.radio;
		// Operator choices are local; delayed feedback must not undo a click.

	}

	_sendDroneKeys() {

		if ( ! this.active || this.mode !== 'drone' || ! this.state?.ready || ! this.bridge?.installed || this.state?.error ) return;
		for ( const code of this.suppressedKeys ) if ( ! this.app.input.down( code ) ) this.suppressedKeys.delete( code );
		const keys = DRONE_KEYS.filter( code => this.app.input.down( code ) && ! this.suppressedKeys.has( code ) );
		this.bridge.send( { keys } );

	}

	switchVehicle() {

		this.mode = this.mode === 'drone' ? 'boat' : 'drone';
		for ( const code of this.app.input.keys ) if ( code !== 'KeyB' ) this.suppressedKeys.add( code );
		this.bridge?.send( { mode: this.mode, keys: [], look_x: 0, look_y: 0 } );
		this.bridge?.selectCamera();
		this._toast( this.mode === 'boat' ? 'AERODOCK helm · U switches the two CAD cameras' : 'X500 pilot view' );
		this._refreshUI();

	}

	toggleBoatCamera() {

		if ( this.mode !== 'boat' ) return;
		this.boatCamera = this.boatCamera === 'boat_dock' ? 'boat_nav' : 'boat_dock';
		this.bridge?.send( { action: 'camera', name: this.boatCamera } );
		this.bridge?.selectCamera();
		this._refreshUI();

	}

	setAutopilot( enabled ) {

		this.autopilot = !! enabled;
		this.bridge?.send( { action: 'autopilot', enabled: this.autopilot, motors: [ 0, 0 ] } );
		if ( this.autopilot ) {
			this.manualMotors = [ 0, 0 ];
			this._toast( 'Verified water loop engaged' );
		} else this._toast( 'Manual port and starboard motor control' );
		this._refreshUI();

	}

	toggleLid() {

		const positions = this.state?.boat;
		if ( positions?.mechanism_busy ) return;
		const isOpen = positions && positions.aft_lid > .92 && positions.fore_lid > .92;
		this.bridge?.send( { action: 'lid', open: ! isOpen } );

	}

	togglePlatform() {

		if ( this.state?.boat?.mechanism_busy ) return;
		const raised = ( this.state?.boat?.platform ?? 0 ) > .92;
		this.bridge?.send( { action: 'platform', raised: ! raised } );

	}

	toggleFlight() {

		if ( ! this.state?.ready || ! this.state?.drone?.px4_ready || ! this.bridge?.cameraView || ! this.bridge?.installed ) return;
		const flying = !! this.state?.drone?.flight_requested;
		this.bridge?.send( { action: flying ? 'land' : 'takeoff' } );
		this._toast( flying ? 'Landing target set' : 'Takeoff requested' );

	}

	reconnect() {

		this.bridge?.send( { action: 'reconnect' } );
		this._toast( 'Retrying SX1262 telemetry handshake' );

	}

	resetVehicles() {

		if ( this.state?.error ) {
			this.bridge?.retry();
			return;
		}
		this.mode = 'drone';
		this.boatCamera = 'boat_dock';
		this.autopilot = true;
		this.manualMotors = [ 0, 0 ];
		this.bridge?.send( { action: 'reset', keys: [], mode: 'drone' } );
		this._toast( 'Resetting both MuJoCo vehicles' );
		this._refreshUI();

	}

	beforePhysics( dt ) {

		if ( ! this.active ) return;
		const input = this.app.input;
		if ( input.hit( 'Home' ) ) this.resetVehicles();
		if ( ! this.state?.ready || ! this.bridge?.installed || ! this.bridge?.cameraView || this.state?.error ) return;
		if ( input.hit( 'KeyB' ) ) this.switchVehicle();
		if ( input.hit( 'KeyC' ) && this.radio?.connected === false ) this.reconnect();
		if ( input.hit( 'KeyP' ) && this.mode === 'boat' ) this.setAutopilot( ! this.autopilot );
		if ( input.hit( 'KeyU' ) && this.mode === 'boat' ) this.toggleBoatCamera();

		this._inputTime += dt;
		if ( this._inputTime < .033 ) return;
		this._inputTime %= .033;
		const codes = this.mode === 'drone'
			? DRONE_KEYS
			: [ 'KeyW', 'KeyA', 'KeyS', 'KeyD' ];
		for ( const code of this.suppressedKeys ) if ( ! input.down( code ) ) this.suppressedKeys.delete( code );
		const held = code => input.down( code ) && ! this.suppressedKeys.has( code );
		const keys = codes.filter( held );
		let look = { x: 0, y: 0 };
		if ( this.mode === 'drone' ) look = input.consumeLook();
		let motors = this.manualMotors;
		if ( this.mode === 'boat' && ! this.autopilot ) {
			if ( held( 'KeyW' ) ) this.manualMotors = this.manualMotors.map( v => clamp( v + 45 * .033, 0, 100 ) );
			if ( held( 'KeyS' ) ) this.manualMotors = this.manualMotors.map( v => clamp( v - 65 * .033, 0, 100 ) );
			motors = this.manualMotors.slice();
			if ( held( 'KeyA' ) ) motors = [ Math.min( 100, motors[ 0 ] + 30 ), Math.max( 0, motors[ 1 ] - 30 ) ];
			if ( held( 'KeyD' ) ) motors = [ Math.max( 0, motors[ 0 ] - 30 ), Math.min( 100, motors[ 1 ] + 30 ) ];
		}
		this.bridge?.send( { keys, look_x: look.x, look_y: look.y,
			motors: this.mode === 'boat' && ! this.autopilot ? motors : this.manualMotors } );

	}

	update( dt ) {

		if ( ! this.active ) return;
		this.bridge?.update( dt );
		this._uiTime += dt;
		this._mapTime += dt;
		if ( this._uiTime >= .1 ) {
			this._uiTime %= .1;
			this._refreshUI();
		}
		if ( this._mapTime >= .14 ) {
			this._mapTime %= .14;
			this._paintMap();
		}

	}

	_refreshUI() {

		if ( ! this._ui ) return;
		const state = this.state || {};
		const cameraReady = !! this.bridge?.cameraView && !! this.bridge?.installed;
		this._bind( 'startup' ).hidden = !! state.ready && cameraReady && ! state.error;
		this._text( 'startup-title', state.error ? 'Simulation needs a restart' : state.status || 'Preparing simulator camera' );
		this._text( 'startup-detail', state.error || ( ! cameraReady ? 'Loading the original vehicle camera feed. Flight controls become available when the simulator is ready.' : 'Vehicle camera connected. Waiting for the flight controller.' ) );
		this._ui.root.querySelector( '[data-action="retry"]' ).hidden = ! state.error;
		const boat = state.boat;
		const drone = state.drone;
		const link = state.radio || this.radio || {};
		const isBoat = this.mode === 'boat';
		const current = isBoat ? boat : drone;
		const localDrone = drone?.position;
		const localBoat = boat?.position;
		const distance = localDrone && localBoat ? Math.hypot( localDrone[ 0 ] - localBoat[ 0 ], localDrone[ 2 ] - localBoat[ 2 ] ) : null;
		const heading = current?.heading;
		const pitch = current?.pitch;
		const roll = current?.roll;
		const altitude = drone?.position ? drone.position[ 1 ] - Math.max( 0, this.app.terrainData.heightAt( drone.position[ 0 ], drone.position[ 2 ] ) ) : null;

		this._text( 'mode-label', isBoat ? 'Boat helm' : 'Drone feed' );
		this._text( 'attitude-title', isBoat ? 'Boat attitude' : 'Drone attitude' );
		this._text( 'range', distance === null ? '—' : distance.toFixed( 1 ) );
		this._text( 'bearing', localDrone && localBoat ? `${ this._bearing( localBoat, localDrone ).toFixed( 0 ) }°` : '—' );
		this._text( 'pitch', pitch === undefined ? '—' : `${ ( pitch * 180 / Math.PI ).toFixed( 1 ) }°` );
		this._text( 'roll', roll === undefined ? '—' : `${ ( roll * 180 / Math.PI ).toFixed( 1 ) }°` );
		this._text( 'heading', heading === undefined ? '—' : `${ degrees( heading ).toFixed( 0 ) }°` );
		this._text( 'tilt', drone ? `${ ( drone.tilt * 180 / Math.PI ).toFixed( 1 ) }°` : '—' );
		this._text( 'pan', drone ? `${ degrees( drone.pan ).toFixed( 1 ) }°` : '—' );
		this._text( 'altitude', altitude === null ? '—<em> m</em>' : `${ altitude.toFixed( 1 )}<em> m</em>` );
		this._text( 'drone-speed', drone ? `${ drone.speed.toFixed( 2 )}<em> m/s</em>` : '—<em> m/s</em>' );
		this._text( 'boat-speed', boat ? `${ boat.speed.toFixed( 2 )}<em> m/s</em>` : '—<em> m/s</em>' );
		this._text( 'boat-course', boat ? `${ degrees( boat.heading ).toFixed( 0 ) }°` : '—' );
		this._text( 'quality', link.quality ?? '—' );
		this._text( 'rssi', link.rssi === undefined ? '— <em>dBm</em>' : `${ link.rssi }<em> dBm</em>` );
		this._text( 'snr', link.snr === undefined ? '— <em>dB</em>' : `${ link.snr }<em> dB</em>` );
		this._text( 'latency', link.latency === undefined ? '— <em>ms</em>' : `${ link.latency }<em> ms</em>` );
		this._text( 'loss', link.packet_loss === undefined ? '— <em>%</em>' : `${ link.packet_loss.toFixed( 1 )}<em> %</em>` );
		this._text( 'tx', link.tx ?? 0 );
		this._text( 'rx', link.rx ?? 0 );
		this._text( 'dropped', link.dropped ?? 0 );
		this._text( 'link-label', ! state.ready ? ( state.status || 'Connecting simulator' ) :
			link.status === 'handshake' ? 'Pairing…' : link.connected ? `${ link.status } link` : 'Telemetry link lost' );
		this._text( 'radio-note', link.connected
			? `Estimated line of sight · last packet ${ link.telemetry_age_s ?? '—' } s ago · video stays local`
			: 'Telemetry is stale. Move closer or clear the obstruction, then press C to retry.' );
		this._bind( 'link' ).dataset.state = ! state.ready ? 'waiting' : ( link.status || 'waiting' );
		this._bind( 'bars' ).style.setProperty( '--fc-quality', `${ link.quality ?? 0 }%` );
		this._bind( 'horizon' ).style.transform = `translateY(${ clamp( ( pitch || 0 ) * 180 / Math.PI * .45, - 26, 26 ) }px) rotate(${ -( roll || 0 ) * 180 / Math.PI }deg)`;
		this._text( 'vehicle-type', isBoat ? 'Surface craft · original CAD' : 'X500 aircraft · original CAD' );
		this._text( 'vehicle-name', isBoat ? 'AERODOCK launch' : 'Holybro X500 V2' );
		this._text( 'vehicle-symbol', isBoat ? '◢' : '⌖' );
		this._text( 'controls', isBoat ? 'W/S motors · A/D steer · U boat cameras · B drone' : 'WASD flight · R/F altitude · Q/E yaw · arrows/mouse gimbal · B boat' );
		this._bind( 'manual-controls' ).hidden = ! isBoat;
		this._text( 'motor-mode', this.autopilot ? 'Route following · motors controlled automatically' : 'Manual motors · set both throttles or use WASD' );
		this._text( 'port-actual', `Output ${ Math.round( boat?.port_power || 0 ) }%` );
		this._text( 'starboard-actual', `Output ${ Math.round( boat?.starboard_power || 0 ) }%` );
		this._text( 'deck-state', boat ? `Platform ${ Math.round( boat.platform * 100 ) }% · aft lid ${ Math.round( boat.aft_lid * 100 ) }% · fore lid ${ Math.round( boat.fore_lid * 100 ) }%` : 'Deck mechanisms ready' );
		this._ui.root.querySelector( '[data-action="autopilot"]' ).classList.toggle( 'is-on', this.autopilot );
		this._ui.root.querySelector( '[data-action="autopilot"]' ).hidden = ! isBoat;
		this._text( 'autopilot-label', this.autopilot ? 'Route following' : 'Manual motors' );
		this._text( 'lid-label', boat && boat.aft_lid > .92 && boat.fore_lid > .92 ? 'Close lids' : 'Open lids' );
		this._text( 'platform-label', boat && boat.platform > .92 ? 'Lower platform' : 'Raise platform' );
		for ( const [ index, side ] of [ 'port', 'starboard' ].entries() ) {

			const control = this._ui.root.querySelector( `[data-control="${ side }"]` );
			if ( control && document.activeElement !== control ) control.value = String( this.manualMotors[ index ] );
			if ( control ) control.disabled = this.autopilot || ! state.ready;
			this._text( side, `${ Math.round( this.manualMotors[ index ] )}%` );

		}
		const cameraButton = this._ui.root.querySelector( '[data-action="camera"]' );
		cameraButton.innerHTML = `${ this.boatCamera === 'boat_dock' ? 'Dock camera' : 'Navigation camera' } <kbd>U</kbd>`;
		cameraButton.hidden = ! isBoat;
		this._ui.root.querySelector( '[data-action="flight"]' ).textContent = drone?.takeoff_pending ? 'Stopping boat…' : drone?.flight_requested ? 'Land' : 'Take off';
		this._ui.root.querySelector( '[data-action="flight"]' ).hidden = isBoat;
		this._ui.root.querySelector( '[data-action="flight"]' ).disabled = ! state.ready || ! drone?.px4_ready || ! cameraReady || !! state.error || !! drone?.takeoff_pending;
		for ( const action of [ 'switch', 'autopilot', 'camera', 'lid', 'platform' ] ) this._ui.root.querySelector( `[data-action="${ action }"]` ).disabled = ! state.ready || ! cameraReady || !! state.error;
		if ( boat?.mechanism_busy ) {
			for ( const action of [ 'lid', 'platform' ] ) this._ui.root.querySelector( `[data-action="${ action }"]` ).disabled = true;
			this._text( 'deck-state', `Mechanism moving · platform ${ Math.round( boat.platform * 100 ) }% · lids ${ Math.round( boat.aft_lid * 100 ) }% / ${ Math.round( boat.fore_lid * 100 ) }%` );
		}
		this._bind( 'route-status' ).textContent = state.error || state.message ||
			( state.route?.valid === false ? 'No safe water route found · manual mode only' :
				state.route ? `Closed water loop · ${ state.route.length_m.toFixed( 0 )} m · ${ state.route.error_m.toFixed( 1 )} m cross-track` :
				state.status || 'Importing Tidewater terrain' );
		this._text( 'performance', `Physics ${ ( state.realtime_factor ?? 1 ).toFixed( 2 ) }× real time · ${ ( this.app.fps || 0 ).toFixed( 0 )} FPS · waves ≤5 cm` );
		this._text( 'controller-source', state.source || 'Native MuJoCo' );
		this._ui.root.querySelector( '[data-action="switch"]' ).innerHTML = `${ isBoat ? 'Switch to drone' : 'Switch to boat' } <kbd>B</kbd>`;
		this._ui.root.classList.toggle( 'is-boat', isBoat );
		this._ui.root.classList.toggle( 'is-link-lost', link.connected === false );

	}

	_bearing( from, to ) {

		const dx = to[ 0 ] - from[ 0 ], dz = to[ 2 ] - from[ 2 ];
		return degrees( Math.atan2( dx, - dz ) );

	}

	_paintMap() {

		const state = this.state;
		if ( ! state?.route || ! state.boat || ! state.drone ) return;
		const canvas = this._ui.canvas;
		const ctx = canvas.getContext( '2d' );
		const w = canvas.width, h = canvas.height;
		const X = x => ( x - MAP.xMin ) / ( MAP.xMax - MAP.xMin ) * w;
		const Y = z => ( z - MAP.zMin ) / ( MAP.zMax - MAP.zMin ) * h;
		ctx.clearRect( 0, 0, w, h );
		ctx.fillStyle = '#071922';
		ctx.fillRect( 0, 0, w, h );
		ctx.strokeStyle = 'rgba(156,204,207,.12)';
		ctx.lineWidth = 1;
		for ( let x = Math.ceil( MAP.xMin / 50 ) * 50; x <= MAP.xMax; x += 50 ) {
			ctx.beginPath(); ctx.moveTo( X( x ), 0 ); ctx.lineTo( X( x ), h ); ctx.stroke();
		}
		for ( let z = Math.ceil( MAP.zMin / 50 ) * 50; z <= MAP.zMax; z += 50 ) {
			ctx.beginPath(); ctx.moveTo( 0, Y( z ) ); ctx.lineTo( w, Y( z ) ); ctx.stroke();
		}
		const coast = state.coastline || [];
		if ( coast.length > 2 ) {
			ctx.beginPath();
			coast.forEach( ( point, index ) => index ? ctx.lineTo( X( point[ 0 ] ), Y( point[ 1 ] ) ) : ctx.moveTo( X( point[ 0 ] ), Y( point[ 1 ] ) ) );
			ctx.closePath();
			ctx.fillStyle = 'rgba(79,91,75,.78)'; ctx.fill();
			ctx.strokeStyle = 'rgba(225,207,158,.82)'; ctx.lineWidth = 1.5; ctx.stroke();
		}
		const route = state.route.points;
		ctx.beginPath();
		route.forEach( ( point, index ) => index ? ctx.lineTo( X( point[ 0 ] ), Y( point[ 1 ] ) ) : ctx.moveTo( X( point[ 0 ] ), Y( point[ 1 ] ) ) );
		ctx.closePath(); ctx.strokeStyle = 'rgba(255,184,107,.85)'; ctx.lineWidth = 2;
		ctx.setLineDash( [ 7, 6 ] ); ctx.stroke(); ctx.setLineDash( [] );
		const boat = state.boat.position, drone = state.drone.position;
		const radio = state.radio || {};
		ctx.strokeStyle = radio.connected === false ? 'rgba(255,122,133,.7)' : 'rgba(95,227,212,.58)';
		ctx.setLineDash( [ 3, 7 ] ); ctx.beginPath(); ctx.moveTo( X( boat[ 0 ] ), Y( boat[ 2 ] ) ); ctx.lineTo( X( drone[ 0 ] ), Y( drone[ 2 ] ) ); ctx.stroke(); ctx.setLineDash( [] );
		this._mapCraft( ctx, X( boat[ 0 ] ), Y( boat[ 2 ] ), boat[ 1 ], state.boat.heading, '#ffbf73', 'B', state.boat.velocity );
		this._mapCraft( ctx, X( drone[ 0 ] ), Y( drone[ 2 ] ), drone[ 1 ], state.drone.heading, '#62e4db', 'D', state.drone.velocity );
		const separation = Math.hypot( drone[ 0 ] - boat[ 0 ], drone[ 2 ] - boat[ 2 ] );
		ctx.fillStyle = 'rgba(225,239,239,.9)'; ctx.font = '11px JetBrains Mono, monospace';
		ctx.fillText( `${ separation.toFixed( 0 )} m`, ( X( boat[ 0 ] ) + X( drone[ 0 ] ) ) * .5 + 5, ( Y( boat[ 2 ] ) + Y( drone[ 2 ] ) ) * .5 - 4 );
		if ( radio.connected === false ) {
			ctx.globalAlpha = .45;
			ctx.fillStyle = '#ff7180'; ctx.beginPath(); ctx.arc( X( boat[ 0 ] ), Y( boat[ 2 ] ), 11, 0, Math.PI * 2 ); ctx.stroke();
			ctx.globalAlpha = 1;
		}

	}

	_mapCraft( ctx, x, y, height, heading, color, label, velocity ) {

		const speed = Math.hypot( velocity[ 0 ], velocity[ 2 ] );
		if ( speed > .35 ) {
			const scale = Math.min( 9, speed * 2.8 );
			ctx.strokeStyle = color; ctx.globalAlpha = .62; ctx.lineWidth = 2;
			ctx.beginPath(); ctx.moveTo( x, y ); ctx.lineTo( x + velocity[ 0 ] * scale, y + velocity[ 2 ] * scale ); ctx.stroke();
			ctx.globalAlpha = 1;
		}
		ctx.save(); ctx.translate( x, y ); ctx.rotate( -heading );
		ctx.fillStyle = color; ctx.shadowColor = color; ctx.shadowBlur = 14;
		ctx.beginPath(); ctx.moveTo( 0, 11 ); ctx.lineTo( - 8, - 8 ); ctx.lineTo( 0, - 4 ); ctx.lineTo( 8, - 8 ); ctx.closePath(); ctx.fill();
		ctx.restore(); ctx.fillStyle = color; ctx.font = 'bold 11px JetBrains Mono, monospace'; ctx.fillText( label, x + 9, y - 8 );

	}

	_text( key, value ) {

		const element = this._bind( key );
		if ( ! element ) return;
		if ( String( value ).includes( '<em>' ) ) element.innerHTML = String( value );
		else element.textContent = String( value );

	}

	_bind( key ) {

		return this._ui?.bindings.get( key );

	}

	_toast( text ) {

		const element = this._bind( 'toast' );
		if ( ! element ) return;
		element.textContent = text;
		element.classList.add( 'is-on' );
		clearTimeout( this._toastTimer );
		this._toastTimer = setTimeout( () => element.classList.remove( 'is-on' ), 2600 );

	}

}
