import { Euler, Vector3 } from '../engine/index.js';
import { SimulationBridge } from '../landing/SimulationBridge.js';
import { recordPerformance } from '../landing/PerformanceRecording.js';

const MAP = { xMin: - 250, xMax: 330, zMin: - 125, zMax: 285 };
const clamp = ( value, low, high ) => Math.max( low, Math.min( high, value ) );
const degrees = value => ( ( value * 180 / Math.PI % 360 ) + 360 ) % 360;
const DRONE_KEYS = [ 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyQ', 'KeyE', 'KeyR', 'KeyF', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown' ];
// The opening AERODOCK shot: the keyart studio's "Front right" framing (5 m out, 31.5 deg to
// starboard of the bow, a hand's height above the deck, 38 deg lens) in world units.
const SHOT = { distance: 4.96, bearing: 0.55, eye: 1.13, aim: 0.48, fov: 38 };
const _shotPos = new Vector3(), _shotAim = new Vector3(), _shotFwd = new Vector3(), _shotStbd = new Vector3();

export class FlightOperations {

	constructor( app ) {

		this.app = app;
		this.active = false;
		this.freeCamera = false;
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
		this._helmFix = null;
		this._droneFix = null;
		// Boot flow: the simulator starts behind the loader, the camera holds the AERODOCK shot and the
		// start card waits on it; the click releases both the card and the camera to the drone.
		this._booted = false;
		this._holding = true;
		this._started = false;
		this._revealed = false;
		this._startGone = false;
		this._loader = null;
		this._loaderStatus = '';
		this._buildUI();
		this._buildHelmUI();
		this._buildDroneUI();
		this._buildIntro();
		this._buildStart();

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
				<div class="fc-wordmark"><span class="fc-mark">T</span><span><b>Tidewater</b><small>Coastal flight operations · browser PX4 / MuJoCo</small></span></div>
				<div class="fc-link" data-bind="link" data-state="waiting"><i></i><span data-bind="link-label">Connecting simulator</span><small data-bind="controller-source">Native MuJoCo</small></div>
				<div class="fc-top-actions"><span class="fc-mode" data-bind="mode-label">Drone feed</span><button data-action="timing">Record timing (10 s)</button><button class="fc-icon-btn" data-action="freecam" aria-pressed="false" title="Toggle free camera (V)">Free cam <kbd>V</kbd></button><button data-action="switch">Switch to boat <kbd>B</kbd></button><button class="fc-icon-btn" data-action="reset" title="Reset both vehicles">Reset <kbd>Home</kbd></button></div>
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
					<button class="fc-reconnect" data-action="radio" aria-pressed="true">Disable SX1262</button>
					<button class="fc-reconnect" data-action="reconnect">Retry connection <kbd>C</kbd></button>
				</section>
			</aside>
			<div class="fc-center-mark" aria-hidden="true"><i></i><b></b><i></i><span></span></div>
			<section class="fc-bottom fc-panel">
				<div class="fc-bottom-main">
					<div class="fc-vehicle-summary"><span class="fc-summary-symbol" data-bind="vehicle-symbol">⌖</span><span><small data-bind="vehicle-type">X500 aircraft</small><b data-bind="vehicle-name">Holybro X500 V2</b></span></div>
					<div class="fc-controls-copy"><small>Controls</small><b data-bind="controls">WASD flight · R/F altitude · Q/E yaw · arrows/mouse camera · B boat</b></div>
					<div class="fc-bottom-actions"><button class="fc-flight-button" data-action="flight">Take off</button><button data-action="ml" aria-pressed="false">ML landing</button><button class="fc-autopilot is-on" data-action="autopilot"><span class="fc-switch-dot"></span><span data-bind="autopilot-label">Route following</span><kbd>P</kbd></button><button data-action="camera">Dock camera <kbd>U</kbd></button><button data-action="lid"><span data-bind="lid-label">Close lids</span></button><button data-action="platform"><span data-bind="platform-label">Lower platform</span></button></div>
				</div>
			<div class="fc-manual-controls" data-bind="manual-controls" hidden>
				<div class="fc-motor-mode"><span data-bind="motor-mode">Route following</span><button data-action="manual">Manual motors</button><button data-action="automatic">Auto route</button><button data-action="stop">Stop motors</button></div>
				<div class="fc-motor-sliders"><label><span>Port throttle</span><input aria-label="Port motor throttle" data-control="port" type="range" min="0" max="100" value="0"><b data-bind="port">0%</b><small data-bind="port-actual">Output 0%</small></label>
				<label><span>Starboard throttle</span><input aria-label="Starboard motor throttle" data-control="starboard" type="range" min="0" max="100" value="0"><b data-bind="starboard">0%</b><small data-bind="starboard-actual">Output 0%</small></label></div>
				<div class="fc-deck-state"><span data-bind="deck-state">Deck mechanisms ready</span><small>W/S throttle · A/D differential steering · P auto/manual</small></div>
			</div>
			<div class="fc-bottom-foot"><span data-bind="route-status">Waiting for terrain collision import</span><span data-bind="performance">WebGPU · browser PX4 / MuJoCo</span></div>
			</section>
			<div class="fc-toast" data-bind="toast" role="status"></div>
		`;
		document.body.append( root );
		this._ui = {
			root,
			canvas: root.querySelector( '.fc-map' ),
			bindings: new Map( Array.from( root.querySelectorAll( '[data-bind]' ), element => [ element.dataset.bind, element ] ) ),
		};
		root.addEventListener( 'click', event => this._handleAction( event.target.closest( '[data-action]' )?.dataset.action ) );
		root.addEventListener( 'input', event => this._handleMotorInput( event.target ) );

	}

	_buildHelmUI() {

		const root = document.createElement( 'div' );
		root.id = 'helm-hud';
		root.hidden = true;
		root.dataset.link = 'live';
		root.innerHTML = `
			<div class="scrim" aria-hidden="true"></div>
			<header class="top">
				<div class="brand"><b>AERODOCK</b></div>
				<div class="stats" aria-label="Boat data">
					<div class="stat"><label>SOG</label><b><span data-bind="sog">—</span><i>kn</i></b></div>
					<div class="stat"><label>COG</label><b><span data-bind="cog">—</span><i>°</i></b></div>
					<div class="stat"><label>HDG</label><b><span data-bind="hdg">—</span><i>°</i></b></div>
					<div class="stat"><label>XTE</label><b><span data-bind="xte">—</span><i>m</i></b></div>
				</div>
				<div class="top-right">
					<span class="freecam">Free camera</span>
					<span class="link"><i></i><span data-bind="link-text">LINK · WAIT</span></span>
					<button class="chip" type="button" data-action="switch">Drone<kbd>B</kbd></button>
					<button class="chip" type="button" data-action="camera"><span data-bind="cam">CAM · DOCK</span><kbd>U</kbd></button>
				</div>
			</header>

			<div class="datum">
				<div class="agl-block">
					<small>SPD</small>
					<div class="agl"><span class="agl-bar"></span><b><span data-bind="spd">—</span><em>kn</em></b></div>
				</div>
				<div class="coords">
					<div class="coord"><small>Drn</small><b><span data-bind="drn-range">—</span><i>m</i></b></div>
					<div class="coord"><small>Brg</small><b><span data-bind="drn-bearing">—</span><i>°</i></b></div>
				</div>
			</div>

			<figure class="scope" aria-label="Range rings around the boat and the radio-reported drone position">
				<svg viewBox="-180 -180 360 360" role="img">
					<circle r="50" fill="none" stroke="currentColor" stroke-opacity=".13" stroke-width="1.2"></circle>
					<circle r="100" fill="none" stroke="currentColor" stroke-opacity=".16" stroke-width="1.2"></circle>
					<circle r="150" fill="none" stroke="currentColor" stroke-opacity=".22" stroke-width="1.2"></circle>
					<path d="M-170 0H170M0 -170V170" stroke="currentColor" stroke-opacity=".08"></path>
					<g class="ring-label" text-anchor="end"><text x="-4" y="-46">50</text><text x="-4" y="-96">100</text><text x="-4" y="-146">150 m</text></g>
					<g class="cardinal" text-anchor="middle"><text x="0" y="-166">N</text></g>
					<path d="M0 -176l-4 6h8z" fill="currentColor" fill-opacity=".5"></path>
					<line data-bind="drn-line" x1="0" y1="0" x2="0" y2="0" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="2 5"></line>
					<g data-bind="drn" transform="translate(0 0)">
						<circle data-bind="drn-sigma" r="6" fill="none" stroke="currentColor" stroke-opacity=".35" stroke-width="1.2" stroke-dasharray="2 4"></circle>
						<g data-bind="drn-rot" transform="rotate(0)"><path data-bind="drn-glyph" d="M0 -8L6 8L0 4L-6 8Z" fill="currentColor" fill-opacity=".95"></path></g>
						<g data-bind="drn-vec"><line x1="0" y1="-11" x2="0" y2="-32" stroke="currentColor" stroke-opacity=".6" stroke-width="1.3"></line><path d="M0 -34l-3.5 6h7z" fill="currentColor" fill-opacity=".8"></path></g>
						<text data-bind="drn-label" x="-12" y="-8" text-anchor="end" class="blip-label">DRN</text>
					</g>
					<circle r="2.4" fill="currentColor"></circle>
					<path d="M-11 0H-5M5 0H11M0 -11V-5M0 5V11" stroke="currentColor" stroke-opacity=".55" stroke-width="1.1"></path>
				</svg>
				<div class="scope-foot"><span class="scope-note" data-bind="scope-note"></span></div>
			</figure>

			<div class="rail">
				<section class="attitude" aria-label="Boat attitude">
					<figure class="sketch side">
						<header class="sketch-head"><b>Pitch <em data-bind="pitch">—</em></b></header>
						<div class="stage"><div class="horizon"></div><img class="craft" data-bind="side-craft" src="/ui/aerodock-side.png" alt="AERODOCK side profile" style="--tilt: 0deg"></div>
					</figure>
					<figure class="sketch stern">
						<header class="sketch-head"><b>Roll <em data-bind="roll">—</em></b></header>
						<div class="stage"><div class="horizon"></div><img class="craft" data-bind="stern-craft" src="/ui/aerodock-stern.png" alt="AERODOCK stern view" style="--tilt: 0deg"></div>
					</figure>
				</section>

				<section class="panel link-panel" aria-label="Vehicle link">
					<div class="panel-head"><b>Vehicle link</b><small data-bind="link-state">WAIT</small></div>
					<div class="radio-quality"><b data-bind="quality">—</b><span>% QLT</span></div>
					<div class="segbar" data-bind="segbar"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
					<div class="radio-grid">
						<div><small>RSSI</small><b data-bind="rssi">—</b></div>
						<div><small>SNR</small><b data-bind="snr">—</b></div>
						<div><small>Loss</small><b data-bind="loss">—</b></div>
						<div class="age"><small>Age</small><b data-bind="age">—</b></div>
					</div>
					<div class="panel-actions">
						<button class="act is-on" type="button" data-action="radio" data-bind="radio-btn">Disable SX1262</button>
						<button class="act" type="button" data-action="reconnect" data-bind="retry-btn">Retry · C</button>
					</div>
				</section>

				<section class="panel propulsion" aria-label="Propulsion">
					<div class="panel-head"><b>Propulsion</b><small data-bind="drive">—</small></div>
					<div class="motor">
						<div class="bar-row"><span>Port</span><div class="bar"><i data-bind="port-bar"></i></div><b data-bind="port">0%</b></div>
						<input class="thr" data-control="port" type="range" min="0" max="100" value="0" aria-label="Port motor throttle">
					</div>
					<div class="motor">
						<div class="bar-row"><span>Stbd</span><div class="bar"><i data-bind="stbd-bar"></i></div><b data-bind="stbd">0%</b></div>
						<input class="thr" data-control="starboard" type="range" min="0" max="100" value="0" aria-label="Starboard motor throttle">
					</div>
				</section>
			</div>

			<section class="panel deck-panel" aria-label="Deck mechanisms">
				<div class="panel-head"><b>Deck</b><small data-bind="deck-state">READY</small></div>
				<div class="bar-row"><span>Platform</span><div class="bar"><i data-bind="plat-bar"></i></div><b data-bind="plat">0%</b></div>
				<div class="bar-row"><span>Lids</span><div class="bar"><i data-bind="lids-bar"></i></div><b data-bind="lids">0%</b></div>
				<div class="panel-actions">
					<button class="act" type="button" data-action="lid" data-bind="lid-btn">Open lids</button>
					<button class="act" type="button" data-action="platform" data-bind="plat-btn">Raise platform</button>
				</div>
				<div class="bilge" data-bind="bilge"><span>Bilge <b data-bind="bilge-l">—</b> L</span><span>Flow <b data-bind="flow">—</b> L/min</span></div>
			</section>

			<nav class="actions" aria-label="Helm actions">
				<svg class="actions-frame" viewBox="0 0 640 56" preserveAspectRatio="none" aria-hidden="true"><path d="M32 55 L82 1 H558 L608 55"></path></svg>
				<button class="act is-on" type="button" data-action="automatic" data-bind="auto-btn">Auto route · P</button>
				<button class="act" type="button" data-action="manual" data-bind="manual-btn">Manual</button>
				<button class="act" type="button" data-action="stop">Stop</button>
				<button class="act" type="button" data-action="reset">Reset · Home</button>
			</nav>

			<footer class="foot">
				<span class="keys" data-bind="keys">W/S THROTTLE · A/D STEER · U CAMERA · P AUTO · B DRONE · C RETRY · V FREE · G SHOT · HOME RESET</span>
				<span class="right"><button type="button" data-action="freecam">Free cam · V</button><button type="button" data-action="shot">Frame · G</button></span>
			</footer>

			<div class="toast" data-bind="toast" role="status"></div>
		`;
		document.body.append( root );
		this._helm = { root, bindings: new Map( Array.from( root.querySelectorAll( '[data-bind]' ), element => [ element.dataset.bind, element ] ) ) };
		root.addEventListener( 'click', event => this._handleAction( event.target.closest( '[data-action]' )?.dataset.action ) );
		root.addEventListener( 'input', event => this._handleMotorInput( event.target ) );

	}

	_buildDroneUI() {

		const root = document.createElement( 'div' );
		root.id = 'drone-hud';
		root.hidden = true;
		root.innerHTML = `
			<div class="scrim" aria-hidden="true"></div>
			<header class="top">
				<div class="brand"><b>TIDEWATER</b><small>X500 · PX4 · MuJoCo</small></div>
				<div class="stats" aria-label="Flight data">
					<div class="stat"><label>ALT</label><b><span data-bind="alt">—</span><i>m</i></b></div>
					<div class="stat"><label>SPD</label><b><span data-bind="spd">—</span><i>m/s</i></b></div>
					<div class="stat"><label>HDG</label><b><span data-bind="hdg">—</span><i>°</i></b></div>
					<div class="stat"><label>SEP</label><b><span data-bind="sep">—</span><i>m</i></b></div>
					<div class="stat"><label>BAT</label><b><span data-bind="batt">—</span><i>%</i></b></div>
				</div>
				<div class="top-right">
					<span class="freecam">Free camera</span>
					<span class="link"><i></i><span data-bind="link-text">SX1262 · WAIT</span></span>
					<button class="mode-toggle hit" type="button" data-action="switch">Helm · B</button>
				</div>
			</header>

			<div class="datum">
				<div class="agl-block"><small>AGL</small><div class="agl"><span class="agl-bar"></span><b><span data-bind="agl">—</span><em>m</em></b></div></div>
				<div class="datum-right">
					<div class="coords">
						<div class="coord"><small>GNSS X</small><b data-bind="gx">—</b></div>
						<div class="coord"><small>GNSS Z</small><b data-bind="gz">—</b></div>
					</div>
					<div class="boat-strip">Boat <b data-bind="bspd">—</b> m/s · CRS <b data-bind="bcrs">—</b>°</div>
				</div>
			</div>

			<section class="optic" aria-hidden="true">
				<svg class="optics" viewBox="-260 -260 520 520">
					<defs><clipPath id="drone-optic-clip"><circle r="236"></circle></clipPath></defs>
					<g data-bind="compass"></g>
					<circle r="238" fill="none" stroke="currentColor" stroke-opacity=".1"></circle>
					<g clip-path="url(#drone-optic-clip)">
						<g data-bind="horizon">
							<path d="M-100 -60H100" stroke="currentColor" stroke-opacity=".12" fill="none"></path>
							<path d="M-160 -30H160" stroke="currentColor" stroke-opacity=".22" fill="none"></path>
							<path d="M-238 0H238" stroke="currentColor" stroke-opacity=".52" fill="none"></path>
							<path d="M-160 30H160" stroke="currentColor" stroke-opacity=".22" fill="none"></path>
							<path d="M-100 60H100" stroke="currentColor" stroke-opacity=".12" fill="none"></path>
							<g stroke="currentColor" stroke-opacity=".34"><path d="M-100 -60h8M-160 -30h6M-160 30h6M-100 60h8"></path></g>
							<g fill="currentColor" fill-opacity=".55" font-size="7.5" letter-spacing="1.2" text-anchor="end"><text x="-110" y="-57.5">20</text><text x="-170" y="-27.5">10</text><text x="-170" y="33">10</text><text x="-110" y="62.5">20</text></g>
						</g>
					</g>
					<path d="M-172 -172L-236 -236M172 172L236 236M172 -172L236 -236M-172 172L-236 236" stroke="currentColor" stroke-opacity=".13" fill="none"></path>
					<circle r="150" fill="none" stroke="currentColor" stroke-opacity=".26" stroke-dasharray="200 35.6" transform="rotate(18)"></circle>
					<circle r="96" fill="none" stroke="currentColor" stroke-opacity=".48" stroke-width="1.2" stroke-dasharray="150 151.6" transform="rotate(135)"></circle>
					<circle r="26" fill="none" stroke="currentColor" stroke-opacity=".16"></circle>
					<path d="M-30 0H-8M8 0H30M0 -30V-8M0 8V30" stroke="currentColor" stroke-opacity=".38"></path>
					<circle r="1.8" fill="currentColor"></circle>
					<path d="M0 -247l-3.4 7h6.8z" fill="currentColor" fill-opacity=".7"></path>
				</svg>
				<div class="opt-foot"><span>Pitch <b data-bind="pitch">—</b> · Roll <b data-bind="roll">—</b></span><span class="armed is-off" data-bind="armed">DISARMED</span></div>
			</section>

			<figure class="scope" aria-label="Range rings centred on the drone, with the boat's reported track">
				<svg viewBox="-180 -180 360 360" role="img">
					<circle r="50" fill="none" stroke="currentColor" stroke-opacity=".13" stroke-width="1.2"></circle>
					<circle r="100" fill="none" stroke="currentColor" stroke-opacity=".16" stroke-width="1.2"></circle>
					<circle r="150" fill="none" stroke="currentColor" stroke-opacity=".22" stroke-width="1.2"></circle>
					<path d="M-170 0H170M0 -170V170" stroke="currentColor" stroke-opacity=".08"></path>
					<g class="ring-label" text-anchor="end"><text x="-4" y="-46">050</text><text x="-4" y="-96">100</text><text x="-4" y="-146">150 m</text></g>
					<g class="cardinal" text-anchor="middle"><text x="0" y="-166">N</text></g>
					<path d="M0 -176l-4 6h8z" fill="currentColor" fill-opacity=".5"></path>
					<line data-bind="sc-line" x1="0" y1="0" x2="0" y2="0" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="2 5"></line>
					<g data-bind="boat" transform="translate(0 0)">
						<circle data-bind="boat-sigma" r="6" fill="none" stroke="currentColor" stroke-opacity=".35" stroke-width="1.2" stroke-dasharray="2 4"></circle>
						<g data-bind="boat-rot"><path data-bind="boat-glyph" d="M0 -8L6 8L0 4L-6 8Z" fill="currentColor" fill-opacity=".95"></path></g>
						<g data-bind="boat-vec"><line x1="0" y1="-11" x2="0" y2="-34" stroke="currentColor" stroke-opacity=".6" stroke-width="1.3"></line><path d="M0 -36l-3.5 6h7z" fill="currentColor" fill-opacity=".8"></path></g>
						<text data-bind="boat-label" x="12" y="-8" class="blip-label">BOAT</text>
					</g>
					<g data-bind="drone-vec"><line x1="0" y1="-10" x2="0" y2="-40" stroke="currentColor" stroke-opacity=".8" stroke-width="1.3"></line><path d="M0 -42l-3.5 6h7z" fill="currentColor" fill-opacity=".95"></path></g>
					<circle r="2.4" fill="currentColor"></circle>
					<path d="M-11 0H-5M5 0H11M0 -11V-5M0 5V11" stroke="currentColor" stroke-opacity=".55" stroke-width="1.1"></path>
				</svg>
				<div class="scope-foot"><span>RNG <b data-bind="sc-range">—</b> m · BRG <b data-bind="sc-bearing">—</b>°</span></div>
			</figure>

			<section class="radio" aria-label="Vehicle link">
				<div class="radio-head"><b>Vehicle link</b><small data-bind="link-state">WAIT</small></div>
				<div class="radio-quality"><b data-bind="quality">—</b><span>% QLT</span></div>
				<div class="segbar" data-bind="segbar"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
				<div class="radio-grid">
					<div><small>RSSI</small><b data-bind="rssi">—</b></div>
					<div><small>SNR</small><b data-bind="snr">—</b></div>
					<div><small>Loss</small><b data-bind="loss">—</b></div>
					<div class="age"><small>Age</small><b data-bind="age">—</b></div>
				</div>
				<div class="radio-actions">
					<button class="mini hit" type="button" data-action="radio" data-bind="radio-btn">Disable SX1262</button>
					<button class="mini hit" type="button" data-action="reconnect" data-bind="retry-btn">Retry · C</button>
				</div>
			</section>

			<nav class="actions" aria-label="Flight actions">
				<svg class="actions-frame" viewBox="0 0 720 56" preserveAspectRatio="none" aria-hidden="true"><path d="M36 55 L92 1 H628 L684 55"></path></svg>
				<button class="hit" type="button" data-action="flight" data-bind="flight-btn">Take off</button>
				<button class="hit" type="button" data-action="ml" data-bind="ml-btn">ML landing</button>
				<button class="hit" type="button" data-action="timing" data-bind="timing-btn">Record 10 s</button>
				<button class="hit" type="button" data-action="switch">Helm · B</button>
			</nav>

			<p class="alarm" data-bind="alarm" role="status"></p>

			<footer class="foot">
				<span class="keys" data-bind="keys">WASD FLY · R/F ALT · Q/E YAW · LOOK MOUSE/ARROWS · B HELM · U BOAT CAM · V FREE · G SHOT · C RETRY · HOME RESET</span>
				<span class="right"><button class="mini hit" type="button" data-action="freecam">Free cam · V</button><button class="mini hit" type="button" data-action="shot">Frame · G</button><button class="mini hit" type="button" data-action="reset">Reset · Home</button></span>
			</footer>

			<div class="toast" data-bind="toast" role="status"></div>
		`;
		document.body.append( root );
		this._drone = { root, bindings: new Map( Array.from( root.querySelectorAll( '[data-bind]' ), element => [ element.dataset.bind, element ] ) ) };
		const compass = root.querySelector( '[data-bind="compass"]' );
		let ring = '';
		for ( let i = 0; i < 72; i ++ ) {

			const a = i * 5 * Math.PI / 180;
			const major = i % 6 === 0, mid = i % 3 === 0;
			const r1 = 238, r2 = major ? 213 : mid ? 224 : 230;
			ring += `<line x1="${ ( Math.sin( a ) * r1 ).toFixed( 1 ) }" y1="${ ( - Math.cos( a ) * r1 ).toFixed( 1 ) }" x2="${ ( Math.sin( a ) * r2 ).toFixed( 1 ) }" y2="${ ( - Math.cos( a ) * r2 ).toFixed( 1 ) }" stroke="currentColor" stroke-opacity="${ major ? .36 : mid ? .19 : .1 }" stroke-width="${ major ? 1 : .6 }"/>`;

		}
		for ( const [ deg, label ] of [ [ 0, 'N' ], [ 90, 'E' ], [ 180, 'S' ], [ 270, 'W' ] ] ) {

			const a = deg * Math.PI / 180, r = 201;
			ring += `<text x="${ ( Math.sin( a ) * r ).toFixed( 1 ) }" y="${ ( - Math.cos( a ) * r + 2.4 ).toFixed( 1 ) }" text-anchor="middle" font-size="7" letter-spacing="1.5" fill="currentColor" fill-opacity=".46">${ label }</text>`;

		}
		compass.innerHTML = ring;
		root.addEventListener( 'click', event => this._handleAction( event.target.closest( '[data-action]' )?.dataset.action ) );

	}

	_buildIntro() {

		const el = document.createElement( 'div' );
		el.id = 'flight-intro';
		el.hidden = true;
		el.innerHTML = '<b>AERODOCK</b><small>Surface craft · launch platform</small>';
		document.body.append( el );
		this._introEl = el;

	}

	// The mission start card: the game opens here instead of the fishing HUD, so nothing from the
	// old interface shows before the flight console exists. It doubles as the simulator's loading
	// status and its error / retry card.
	_buildStart() {

		const el = document.createElement( 'div' );
		el.id = 'flight-start';
		el.hidden = true;
		el.innerHTML = `
			<div class="fs-card" role="dialog" aria-labelledby="fs-title">
				<div class="fs-brand"><span class="fs-mark">T</span><span><b id="fs-title">Tidewater</b><small>Coastal flight operations</small></span></div>
				<p class="fs-lead">Land the X500 on the AERODOCK deck. Fly the approach yourself, or hand it to the MuJoCo-trained landing policy.</p>
				<div class="fs-keys">
					<span><kbd>W A S D</kbd>Fly</span>
					<span><kbd>R</kbd><kbd>F</kbd>Climb / descend</span>
					<span><kbd>Q</kbd><kbd>E</kbd>Yaw</span>
					<span><kbd>Mouse</kbd>Camera</span>
					<span><kbd>B</kbd>Helm</span>
					<span><kbd>U</kbd>Boat camera</span>
					<span><kbd>P</kbd>Auto route</span>
					<span><kbd>V</kbd>Free camera</span>
					<span><kbd>G</kbd>Frame</span>
					<span><kbd>Home</kbd>Reset</span>
				</div>
				<button class="fs-go" type="button">Start flight operations</button>
				<div class="fs-status" data-bind="start-status" role="status">Browser PX4 · MuJoCo · WebGPU</div>
			</div>`;
		document.body.append( el );
		this._startEl = el;
		this._startStatusEl = el.querySelector( '[data-bind="start-status"]' );
		this._startGo = el.querySelector( '.fs-go' );
		el.addEventListener( 'click', () => {

			if ( this.state?.error ) this.bridge?.retry();
			else this._begin();

		} );

	}

	// Boots straight into the scene: the simulator starts while the loader is still up, the camera
	// holds the front-right AERODOCK shot, and only when the flight console can take over does the
	// loader lift onto that shot with the start card. Nothing else is ever the first view.
	boot( ui ) {

		if ( this._booted ) return;
		this._booted = true;
		this._loader = ui;
		document.body.classList.add( 'flight-mode-active' );
		this._startEl.hidden = false;
		this._introEl.hidden = false;
		this._setLoader( 'Starting the browser simulator' );
		this.activate();
		window.addEventListener( 'keydown', event => {

			if ( this._startGone || ( event.code !== 'Enter' && event.code !== 'Space' ) ) return;
			event.preventDefault();
			this._begin();

		}, true );

	}

	// One gate: the click (or Enter) on the AERODOCK shot. It releases the camera to the simulator's
	// drone camera and gets out of the way.
	_begin() {

		if ( this._started || ! this.state?.ready ) return;
		this._started = true;
		this._startGone = true;
		this._startEl.classList.add( 'is-off' );
		setTimeout( () => {

			if ( this._startGone ) this._startEl.hidden = true;

		}, 420 );
		this._introEl.hidden = true;
		this._holding = false;
		if ( this.bridge ) {

			this.bridge.cameraPaused = false;
			this.bridge.selectCamera();

		}
		if ( this.app.audio ) this.app.audio.resume();
		this.app.input.requestLock?.();
		this._refreshUI();

	}

	// The loader's own status line, only when it changes (setLoading restarts its creep animation).
	_setLoader( status ) {

		if ( ! this._loader || this._loaderStatus === status ) return;
		this._loaderStatus = status;
		this._loader.setLoading( .97, status, .99 );

	}

	_startStatus( text, alert = false ) {

		if ( ! this._startStatusEl ) return;
		if ( this._startStatusEl.textContent !== String( text ) ) this._startStatusEl.textContent = String( text );
		this._startEl.classList.toggle( 'is-error', !! alert );

	}

	// The card waits on the AERODOCK shot through startup and becomes the only gate once the flight
	// console is ready. It also carries the simulator's error and its retry.
	_syncStart( state, flightReady ) {

		if ( ! this._booted || this._startGone || ! this._startEl ) return;
		if ( state?.error ) {

			this._startGo.textContent = 'Retry simulation';
			this._startGo.disabled = false;
			this._startStatus( state.error, true );
			this._reveal();
			return;

		}
		if ( ! flightReady ) {

			this._startGo.textContent = 'Starting simulator…';
			this._startGo.disabled = true;
			this._startStatus( state?.status || 'Loading the original vehicles…' );
			this._setLoader( state?.status || 'Starting the browser simulator' );
			return;

		}
		this._startGo.textContent = 'Start flight operations';
		this._startGo.disabled = false;
		this._startStatus( 'Simulator ready · X500 on the deck' );
		this._reveal();

	}

	// Lifts the loader, revealing the AERODOCK shot with the card already on it. Once.
	_reveal() {

		if ( this._revealed ) return;
		this._revealed = true;
		this._startEl.hidden = false;
		this._loader?.hideLoader?.();

	}

	// The opening shot: the AERODOCK from ahead and to starboard, close enough to read the boat.
	// The pose comes from the rendered body group (the same interpolated pose the CAD is drawn
	// with) so the framing never disagrees with what is on screen.
	_poseAerodock() {

		const group = this.bridge?.groups?.get( 'Physics body boat' );
		const boat = this.state?.boat;
		if ( group ) {

			_shotPos.copy( group.position );
			// the body's x axis is the bow; in this model +y is the port side, so starboard is -y
			_shotFwd.set( 1, 0, 0 ).applyQuaternion( group.quaternion );
			_shotStbd.set( 0, - 1, 0 ).applyQuaternion( group.quaternion );

		} else if ( boat?.position ) {

			_shotPos.set( boat.position[ 0 ], boat.position[ 1 ], boat.position[ 2 ] );
			const h = boat.heading || 0;
			_shotFwd.set( Math.sin( h ), 0, - Math.cos( h ) );
			_shotStbd.set( Math.cos( h ), 0, Math.sin( h ) );

		} else return;

		// level the heading: the shot keeps its height above the water, whatever the deck is doing
		_shotFwd.y = 0;
		_shotFwd.normalize();
		_shotStbd.y = 0;
		_shotStbd.normalize();
		const camera = this.app.camera;
		camera.position.copy( _shotPos )
			.addScaledVector( _shotFwd, Math.cos( SHOT.bearing ) * SHOT.distance )
			.addScaledVector( _shotStbd, Math.sin( SHOT.bearing ) * SHOT.distance );
		camera.position.y = _shotPos.y + SHOT.eye;
		_shotAim.copy( _shotPos );
		_shotAim.y += SHOT.aim;
		camera.up.set( 0, 1, 0 );
		camera.lookAt( _shotAim );
		if ( camera.fov !== SHOT.fov ) {

			camera.fov = SHOT.fov;
			camera.updateProjectionMatrix();

		}

	}

	_handleAction( action ) {

		if ( ! action ) return;
		if ( action === 'freecam' ) this.toggleFreeCamera();
		else if ( action === 'shot' ) this.captureScreenshot();
		else if ( action === 'switch' ) this.switchVehicle();
		else if ( action === 'retry' ) this.bridge?.retry();
		else if ( action === 'reset' ) this.resetVehicles();
		else if ( action === 'reconnect' ) this.reconnect();
		else if ( action === 'radio' ) this.toggleRadio();
		else if ( action === 'flight' ) this.toggleFlight();
		else if ( action === 'ml' ) this.toggleML();
		else if ( action === 'timing' ) this.recordTiming();
		else if ( action === 'autopilot' ) this.setAutopilot( ! this.autopilot );
		else if ( action === 'manual' ) this.setAutopilot( false );
		else if ( action === 'automatic' ) this.setAutopilot( true );
		else if ( action === 'stop' ) {

			this.setAutopilot( false );
			this.manualMotors = [ 0, 0 ];
			this.bridge?.send( { motors: [ 0, 0 ] } );
			this._toast( 'Motors stopped' );

		} else if ( action === 'camera' ) this.toggleBoatCamera();
		else if ( action === 'lid' ) this.toggleLid();
		else if ( action === 'platform' ) this.togglePlatform();

	}

	_handleMotorInput( target ) {

		if ( this._holding ) return;

		const side = target.dataset.control;
		if ( side !== 'port' && side !== 'starboard' ) return;
		if ( this.autopilot ) this.setAutopilot( false );
		this.manualMotors[ side === 'port' ? 0 : 1 ] = Number( target.value );
		this.bridge?.send( { motors: this.manualMotors, mode: this.mode } );

	}

	activate() {

		if ( this.active ) return;
		this.active = true;
		this.freeCamera = false;
		this.mode = 'drone';
		this.boatCamera = 'boat_dock';
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

	toggleFreeCamera() {

		if ( ! this.active || this._holding ) return;
		if ( ! this.freeCamera ) {

			if ( ! this.state?.ready || ! this.bridge?.installed || ! this.bridge?.cameraView || this.state?.error ) {

				this._toast( 'Free camera becomes available when the flight camera is ready' );
				return;

			}
			const camera = this.app.camera;
			const angle = new Euler().setFromQuaternion( camera.quaternion, 'YXZ' );
			this.freeCamera = true;
			if ( this.bridge ) this.bridge.cameraPaused = true;
			this.app.fly.setPose( camera.position.clone(), angle.y, angle.x );
			this.app.fly.velocity.set( 0, 0, 0 );
			this.bridge?.send( { keys: [], look_x: 0, look_y: 0 } );
			this.app.input.requestLock?.();
			this._toast( 'Free camera · WASD move · Q/E height · drag to look · G screenshot · V return' );

		} else {

			this.freeCamera = false;
			if ( this.bridge ) {

				this.bridge.cameraPaused = false;
				this.bridge.selectCamera();

			}
			if ( document.pointerLockElement ) document.exitPointerLock?.();
			this._toast( 'Flight camera restored' );

		}
		this._refreshUI();

	}

	_receive( state ) {

		this.state = state;
		this.radio = state.radio || this.radio;
		// Operator choices are local; delayed feedback must not undo a click.

	}

	_sendDroneKeys() {

		if ( this._holding || this.freeCamera || ! this.active || this.mode !== 'drone' || ! this.state?.ready || ! this.bridge?.installed || this.state?.error ) return;
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

		const boat = this.state?.boat;
		if ( ! boat || boat.mechanism_busy ) {

			this._toast( 'Wait for the current mechanism movement to finish' );
			return;

		}
		const isOpen = boat.aft_lid > .978 && boat.fore_lid > .978;
		if ( isOpen && boat.platform > .02 ) {

			this._toast( 'Lower the launch platform before closing both lids' );
			return;

		}
		this.bridge?.send( { action: 'lid', open: ! isOpen } );

	}

	togglePlatform() {

		const boat = this.state?.boat;
		if ( ! boat || boat.mechanism_busy ) {

			this._toast( 'Wait for the current mechanism movement to finish' );
			return;

		}
		const raised = boat.platform > .92;
		if ( ! raised && Math.min( boat.aft_lid, boat.fore_lid ) < .978 ) {

			this._toast( 'Open both lids before raising the launch platform' );
			return;

		}
		this.bridge?.send( { action: 'platform', raised: ! raised } );

	}

	toggleFlight() {

		if ( ! this.state?.ready || ! this.state?.drone?.px4_ready || ! this.bridge?.cameraView || ! this.bridge?.installed || this.state?.error ) return;
		const control = this._flightControl();
		if ( control.busy ) return;
		this.bridge?.send( { action: control.action } );
		this._toast( control.action === 'takeoff' ? 'Takeoff requested' : this.state.drone.armed ? 'Landing target set' : 'Takeoff cancelled' );

	}

	async recordTiming() {
		const buttons=[this._ui.root.querySelector('[data-action="timing"]'),this._dBind('timing-btn')].filter(Boolean);
		if(!buttons.length||buttons.some(button=>button.disabled)||!this.bridge)return;
		const label=text=>{for(const button of buttons)button.textContent=text;};
		for(const button of buttons)button.disabled=true;
		try {
			const report=await recordPerformance(this.app,{onProgress:seconds=>label(`Recording ${seconds} s…`)});
			const response=await fetch(new URL('__timing',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report)}).catch(()=>null);
			if(response?.ok){label('Timing saved locally');this._toast('Timing saved to the local Tidewater server');}
			else {const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='tidewater-timing.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);label('Timing report downloaded');}
		}catch(error){label('Record 10 s');this._toast(error.message);}
		finally{for(const button of buttons)button.disabled=false;}
	}

	toggleML() {
		const policy=this.bridge?.policy;if(!policy)return;
		if(policy.status.enabled||policy.status.loading)policy.disable();
		else policy.enable().catch(error=>this._toast(error.message));
	}

	_flightControl() {

		const drone = this.state?.drone;
		if ( drone?.takeoff_pending ) return { label: 'Stopping boat…', action: 'land', busy: true };
		if ( drone?.landing_requested ) return { label: 'Landing…', action: 'land', busy: true };
		if ( drone?.armed ) return { label: 'Land', action: 'land', busy: false };
		if ( drone?.flight_requested ) return { label: 'Cancel takeoff', action: 'land', busy: false };
		return { label: 'Take off', action: 'takeoff', busy: false };

	}

	reconnect() {

		if ( ( this.state?.radio || this.radio )?.enabled === false ) return;
		this.bridge?.send( { action: 'reconnect' } );
		this._toast( 'Retrying SX1262 telemetry handshake' );

	}

	toggleRadio() {

		const enabled = ( this.state?.radio || this.radio )?.enabled === false;
		this.bridge?.send( { action: 'radio', enabled } );
		this._toast( enabled ? 'Enabling SX1262 telemetry link' : 'SX1262 disabled · radio inputs to ML are zero' );

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
		this._helmFix = null;
		this.bridge?.send( { action: 'reset', keys: [], mode: 'drone' } );
		this._toast( 'Resetting both MuJoCo vehicles' );
		this._refreshUI();

	}

	beforePhysics( dt ) {

		if ( ! this.active || this._holding ) return;
		const input = this.app.input;
		if ( input.hit( 'KeyG' ) ) this.captureScreenshot();
		if ( input.hit( 'KeyV' ) ) this.toggleFreeCamera();
		if ( this.freeCamera ) return;
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
		// Hold the opening shot, following the boat, until the player takes the controls. The camera
		// is paused only once the bridge knows its view (it reports `cameraView` from _applyCamera,
		// which returns early while paused) so the console can still become ready behind the loader.
		if ( this._holding ) {

			if ( this.bridge?.cameraView ) this.bridge.cameraPaused = true;
			this._poseAerodock();

		}
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
		const freeCamera = this.freeCamera;
		const current = isBoat ? boat : drone;
		const localDrone = drone?.position;
		const localBoat = boat?.position;
		const distance = localDrone && localBoat ? Math.hypot( localDrone[ 0 ] - localBoat[ 0 ], localDrone[ 2 ] - localBoat[ 2 ] ) : null;
		const heading = current?.heading;
		const pitch = current?.pitch;
		const roll = current?.roll;
		const altitude = drone?.position ? drone.position[ 1 ] - Math.max( 0, this.app.terrainData.heightAt( drone.position[ 0 ], drone.position[ 2 ] ) ) : null;

		this._text( 'mode-label', freeCamera ? 'Free camera' : isBoat ? 'Boat helm' : 'Drone feed' );
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
			link.enabled === false ? 'SX1262 disabled' : link.status === 'handshake' ? 'Pairing…' : link.connected ? `${ link.status } link` : 'Telemetry link lost' );
		this._text( 'radio-note', link.enabled === false ? 'Manually disabled · radio inputs to ML are zero · video stays local' : link.connected
			? `Estimated line of sight · last packet ${ link.telemetry_age_s ?? '—' } s ago · video stays local`
			: 'Telemetry is stale. Move closer or clear the obstruction, then press C to retry.' );
		const radioButton = this._ui.root.querySelector( '[data-action="radio"]' );
		radioButton.textContent = link.enabled === false ? 'Enable SX1262' : 'Disable SX1262';
		radioButton.setAttribute( 'aria-pressed', String( link.enabled !== false ) );
		radioButton.disabled = ! state.ready || !! state.error;
		this._ui.root.querySelector( '[data-action="reconnect"]' ).disabled = link.enabled === false || ! state.ready || !! state.error;
		this._bind( 'link' ).dataset.state = ! state.ready ? 'waiting' : ( link.status || 'waiting' );
		this._bind( 'bars' ).style.setProperty( '--fc-quality', `${ link.quality ?? 0 }%` );
		this._bind( 'horizon' ).style.transform = `translateY(${ clamp( ( pitch || 0 ) * 180 / Math.PI * .45, - 26, 26 ) }px) rotate(${ -( roll || 0 ) * 180 / Math.PI }deg)`;
		this._text( 'vehicle-type', isBoat ? 'Surface craft · original CAD' : 'X500 aircraft · original CAD' );
		this._text( 'vehicle-name', isBoat ? 'AERODOCK launch' : 'Holybro X500 V2' );
		this._text( 'vehicle-symbol', isBoat ? '◢' : '⌖' );
		this._text( 'controls', freeCamera ? 'WASD move · Q/E height · drag/mouse look · G screenshot · V flight camera' : isBoat ? 'W/S motors · A/D steer · U boat cameras · B drone' : 'WASD flight · R/F altitude · Q/E yaw · arrows/mouse gimbal · B boat' );
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
		const freeButton = this._ui.root.querySelector( '[data-action="freecam"]' );
		if ( freeButton ) {

			freeButton.innerHTML = `${ freeCamera ? 'Flight camera' : 'Free camera' } <kbd>V</kbd>`;
			freeButton.setAttribute( 'aria-pressed', String( freeCamera ) );

		}
		const flightControl = this._flightControl();
		const ml=this.bridge?.policy?.status||{},mlButton=this._ui.root.querySelector('[data-action="ml"]');
		mlButton.textContent=ml.loading?'Cancel ML loading':ml.enabled?'Manual control':'ML landing';mlButton.setAttribute('aria-pressed',String(!!ml.enabled));
		mlButton.disabled=!(ml.loading||ml.enabled)&&(!state.ready||!cameraReady||!drone?.armed||drone.landed||drone.landing_requested||!!state.error);
		this._ui.root.querySelector( '[data-action="flight"]' ).textContent = flightControl.label;
		this._ui.root.querySelector( '[data-action="flight"]' ).hidden = isBoat;
		this._ui.root.querySelector( '[data-action="flight"]' ).disabled = ! state.ready || ! drone?.px4_ready || ! cameraReady || !! state.error || flightControl.busy;
		for ( const action of [ 'switch', 'freecam', 'autopilot', 'camera', 'lid', 'platform' ] ) this._ui.root.querySelector( `[data-action="${ action }"]` ).disabled = ! state.ready || ! cameraReady || !! state.error;
		if ( boat?.mechanism_busy ) {
			for ( const action of [ 'lid', 'platform' ] ) this._ui.root.querySelector( `[data-action="${ action }"]` ).disabled = true;
			this._text( 'deck-state', `Mechanism moving · platform ${ Math.round( boat.platform * 100 ) }% · lids ${ Math.round( boat.aft_lid * 100 ) }% / ${ Math.round( boat.fore_lid * 100 ) }%` );
		}
		const mlCommand=state.ml?.action?.slice(0,3).map(v=>v.toFixed(2)).join(', ');
		this._bind( 'route-status' ).textContent = state.error || ml.error || state.ml?.error || (ml.loading?'Loading trained ML policy…':ml.enabled?`ML · ${state.ml?.phase||'acquire'} · ${state.ml?.intervention||'no override'} · ${link.connected?'radio on':'radio 0'}${mlCommand?` · velocity ${mlCommand} m/s`:''} · boat ${this.autopilot?'auto':'manual'}`:null) || state.message ||
			( state.route?.valid === false ? 'No safe water route found · manual mode only' :
				state.route ? `Closed water loop · ${ state.route.length_m.toFixed( 0 )} m · ${ state.route.error_m.toFixed( 1 )} m cross-track` :
				state.status || 'Importing Tidewater terrain' );
		this._text( 'performance', `GPU ${ this.app.gpu?.adapter?.info?.vendor || 'WebGPU' } · Physics ${ ( state.realtime_factor ?? 1 ).toFixed( 2 ) }× real time · ${ ( this.app.fps || 0 ).toFixed( 0 )} FPS · waves ≤5 cm` );
		this._text( 'controller-source', state.source || 'Native MuJoCo' );
		this._ui.root.querySelector( '[data-action="switch"]' ).innerHTML = `${ isBoat ? 'Switch to drone' : 'Switch to boat' } <kbd>B</kbd>`;
		this._ui.root.classList.toggle( 'is-boat', isBoat );
		this._ui.root.classList.toggle( 'is-freecam', freeCamera );
		this._ui.root.classList.toggle( 'is-link-lost', link.connected === false );

		if ( this.active ) {

			const flightReady = !! state.ready && cameraReady && ! state.error;
			// Nothing but the AERODOCK shot until the player starts; the consoles appear on the click.
			const started = ! this._holding;
			// The helm and drone consoles own the screen. The free camera keeps the active one up (with
			// its own key line) instead of falling back to the superseded `fc-*` console.
			const showHelm = isBoat && flightReady && started;
			const showDrone = ! isBoat && flightReady && started;
			this._helm.root.hidden = ! showHelm;
			this._drone.root.hidden = ! showDrone;
			this._helm.root.classList.toggle( 'is-freecam', freeCamera );
			this._drone.root.classList.toggle( 'is-freecam', freeCamera );
			this._ui.root.hidden = true;
			this._syncStart( state, flightReady );
			if ( showHelm ) this._updateHelm( state, link, boat, drone );
			if ( showDrone ) this._updateDrone( state, link, boat, drone );

		}

	}

	_updateHelm( state, link, boat, drone ) {

		if ( ! this._helm ) return;

		const helm = this._helm.root;
		const lost = link.connected === false;
		const status = String( link.status || '' ).toLowerCase();
		const age = Number.isFinite( link.telemetry_age_s ) ? Math.max( 0, link.telemetry_age_s ) : 0;
		const knots = boat ? boat.speed * 1.943844 : null;
		const heading = boat ? ( ( boat.heading * 180 / Math.PI % 360 ) + 360 ) % 360 : null;
		const velocity = boat?.velocity || [ 0, 0, 0 ];
		const course = boat && Math.hypot( velocity[ 0 ], velocity[ 2 ] ) > .3
			? ( ( Math.atan2( velocity[ 0 ], - velocity[ 2 ] ) * 180 / Math.PI % 360 ) + 360 ) % 360
			: heading;

		this._hText( 'sog', knots === null ? '—' : knots.toFixed( 1 ).padStart( 4, '0' ) );
		this._hText( 'spd', knots === null ? '—' : knots.toFixed( 1 ).padStart( 4, '0' ) );
		this._hText( 'cog', course === null ? '—' : String( Math.round( course ) ).padStart( 3, '0' ) );
		this._hText( 'hdg', heading === null ? '—' : String( Math.round( heading ) ).padStart( 3, '0' ) );
		this._hText( 'xte', Number.isFinite( state.route?.error_m ) ? state.route.error_m.toFixed( 1 ) : '—' );

		const word = ! link.enabled ? 'DISABLED' : status === 'handshake' ? 'PAIRING' : lost ? 'LOST' : status === 'critical' ? 'CRITICAL' : status === 'degraded' ? 'DEGRADED' : 'STABLE';
		this._hText( 'link-text', `LINK · ${ word }` );
		this._hText( 'link-state', lost ? 'NO TELEMETRY' : status === 'handshake' ? 'HANDSHAKE' : word );
		this._hBind( 'link-state' )?.classList.toggle( 'is-alert', lost );
		helm.dataset.link = lost ? 'lost' : 'live';
		const quality = lost ? 0 : Math.round( link.quality ?? 0 );
		this._hText( 'quality', String( quality ).padStart( 3, '0' ) );
		const segments = this._hBind( 'segbar' )?.children || [];
		for ( let i = 0; i < segments.length; i ++ ) segments[ i ].classList.toggle( 'on', ! lost && i < Math.round( quality / 10 ) );
		this._hText( 'rssi', lost || ! Number.isFinite( link.rssi ) ? '—' : `${ link.rssi < 0 ? '−' : '+' }${ String( Math.abs( Math.round( link.rssi ) ) ).padStart( 3, '0' ) } dBm` );
		this._hText( 'snr', lost || ! Number.isFinite( link.snr ) ? '—' : `${ link.snr < 0 ? '−' : '+' }${ Math.abs( link.snr ).toFixed( 1 ) } dB` );
		this._hText( 'loss', lost ? '100.0 %' : Number.isFinite( link.packet_loss ) ? `${ link.packet_loss.toFixed( 1 ) } %` : '—' );
		this._hText( 'age', `${ age.toFixed( 1 ) } s` );
		const radioButton = this._hBind( 'radio-btn' );
		if ( radioButton ) {

			radioButton.textContent = link.enabled === false ? 'Enable SX1262' : 'Disable SX1262';
			radioButton.classList.toggle( 'is-on', link.enabled !== false );

		}
		const retryButton = this._hBind( 'retry-btn' );
		if ( retryButton ) retryButton.disabled = link.enabled === false || link.connected !== false || status === 'handshake';

		let fix = null;
		const boatPosition = boat?.position, dronePosition = drone?.position;
		if ( boatPosition && dronePosition ) {

			fix = {
				range: Math.hypot( dronePosition[ 0 ] - boatPosition[ 0 ], dronePosition[ 2 ] - boatPosition[ 2 ] ),
				bearing: this._bearing( boatPosition, dronePosition ),
				heading: ( ( drone.heading * 180 / Math.PI % 360 ) + 360 ) % 360,
				speed: drone.speed,
				velocity: drone.velocity,
			};

		}
		if ( fix && ! lost ) this._helmFix = fix;
		const shown = lost ? this._helmFix : fix;
		this._hText( 'drn-range', shown ? shown.range.toFixed( 1 ) : '—' );
		this._hText( 'drn-bearing', shown ? String( Math.round( shown.bearing ) ).padStart( 3, '0' ) : '—' );

		const blip = this._hBind( 'drn' ), line = this._hBind( 'drn-line' );
		if ( blip ) blip.style.display = shown ? '' : 'none';
		if ( line ) line.style.display = shown ? '' : 'none';
		if ( shown ) {

			const radius = Math.min( shown.range, 150 );
			const angle = shown.bearing * Math.PI / 180;
			const x = radius * Math.sin( angle ), y = - radius * Math.cos( angle );
			blip.setAttribute( 'transform', `translate(${ x.toFixed( 1 ) } ${ y.toFixed( 1 ) })` );
			line.setAttribute( 'x2', x.toFixed( 1 ) );
			line.setAttribute( 'y2', y.toFixed( 1 ) );
			this._hBind( 'drn-rot' )?.setAttribute( 'transform', `rotate(${ shown.heading.toFixed( 0 ) })` );
			const glyph = this._hBind( 'drn-glyph' );
			glyph?.setAttribute( 'fill-opacity', lost ? '.06' : '.95' );
			glyph?.setAttribute( 'stroke', 'currentColor' );
			glyph?.setAttribute( 'stroke-width', lost ? '1.2' : '1.1' );
			this._hBind( 'drn-sigma' )?.setAttribute( 'r', ( lost ? 9 + Math.min( age, 10 ) * 2.4 : 6 ).toFixed( 1 ) );
			const vector = this._hBind( 'drn-vec' );
			const speed = shown.speed || 0;
			if ( vector ) vector.style.display = lost || speed < .4 ? 'none' : '';
			if ( vector && speed >= .4 && shown.velocity ) {

				const vectorCourse = ( ( Math.atan2( shown.velocity[ 0 ], - shown.velocity[ 2 ] ) * 180 / Math.PI % 360 ) + 360 ) % 360;
				vector.setAttribute( 'transform', `rotate(${ vectorCourse.toFixed( 0 ) })` );

			}
			this._hText( 'drn-label', lost ? `DRN · LAST ${ age.toFixed( 1 ) } s` : 'DRN' );

		}
		this._hText( 'scope-note', lost ? ( link.enabled === false ? 'LINK DISABLED' : `LAST FIX ${ age.toFixed( 1 ) } s · PRESS C` ) : '' );

		const pitch = boat ? boat.pitch * 180 / Math.PI : 0;
		const roll = boat ? boat.roll * 180 / Math.PI : 0;
		this._hText( 'pitch', `${ pitch < 0 ? '−' : '+' }${ Math.abs( pitch ).toFixed( 1 ) }°` );
		this._hText( 'roll', `${ roll < 0 ? '−' : '+' }${ Math.abs( roll ).toFixed( 1 ) }°` );
		this._hBind( 'side-craft' )?.style.setProperty( '--tilt', `${ ( - pitch ).toFixed( 1 ) }deg` );
		this._hBind( 'stern-craft' )?.style.setProperty( '--tilt', `${ roll.toFixed( 1 ) }deg` );

		const platform = boat?.platform ?? 0;
		const lids = boat ? Math.min( boat.aft_lid, boat.fore_lid ) : 0;
		if ( this._hBind( 'plat-bar' ) ) this._hBind( 'plat-bar' ).style.width = `${ platform * 100 }%`;
		this._hText( 'plat', `${ Math.round( platform * 100 ) }%` );
		if ( this._hBind( 'lids-bar' ) ) this._hBind( 'lids-bar' ).style.width = `${ lids * 100 }%`;
		this._hText( 'lids', `${ Math.round( lids * 100 ) }%` );
		const open = lids > .978;
		this._hText( 'lid-btn', open ? 'Close lids' : 'Open lids' );
		this._hText( 'plat-btn', platform > .92 ? 'Lower platform' : 'Raise platform' );
		const busy = !! boat?.mechanism_busy;
		if ( this._hBind( 'lid-btn' ) ) this._hBind( 'lid-btn' ).disabled = busy;
		if ( this._hBind( 'plat-btn' ) ) this._hBind( 'plat-btn' ).disabled = busy;
		this._hText( 'deck-state', busy ? 'MOVING' : 'READY' );

		const litres = boat && Number.isFinite( boat.cabin_water_l ) ? boat.cabin_water_l : null;
		const flowRaw = boat?.drain_flow_lpm;
		const flow = Array.isArray( flowRaw ) ? flowRaw.reduce( ( sum, value ) => sum + ( Number( value ) || 0 ), 0 ) : Number.isFinite( flowRaw ) ? flowRaw : null;
		this._hText( 'bilge-l', litres === null ? '—' : litres.toFixed( 1 ) );
		this._hText( 'flow', flow === null ? '—' : flow.toFixed( 1 ) );
		this._hBind( 'bilge' )?.classList.toggle( 'is-alert', !! boat?.drain_high_water );

		const portPower = boat?.port_power ?? 0, starboardPower = boat?.starboard_power ?? 0;
		if ( this._hBind( 'port-bar' ) ) this._hBind( 'port-bar' ).style.width = `${ portPower }%`;
		if ( this._hBind( 'stbd-bar' ) ) this._hBind( 'stbd-bar' ).style.width = `${ starboardPower }%`;
		this._hText( 'port', `${ Math.round( portPower ) }%` );
		this._hText( 'stbd', `${ Math.round( starboardPower ) }%` );
		this._hText( 'drive', this.autopilot ? `AUTO · ${ ( state.route?.target_speed_m_s ?? 2.8 ).toFixed( 1 ) } m/s` : 'MANUAL' );
		for ( const [ side, value, index ] of [ [ 'port', portPower, 0 ], [ 'starboard', starboardPower, 1 ] ] ) {

			const slider = helm.querySelector( `[data-control="${ side }"]` );
			if ( ! slider ) continue;
			if ( document.activeElement !== slider ) slider.value = String( Math.round( this.autopilot ? value : this.manualMotors[ index ] ) );
			slider.disabled = ! state.ready;

		}
		this._hBind( 'auto-btn' )?.classList.toggle( 'is-on', this.autopilot );
		this._hBind( 'manual-btn' )?.classList.toggle( 'is-on', ! this.autopilot );
		this._hText( 'cam', this.boatCamera === 'boat_dock' ? 'CAM · DOCK' : 'CAM · NAV' );
		this._hText( 'keys', this.freeCamera
			? 'FREE CAMERA · WASD MOVE · Q/E HEIGHT · SHIFT FAST · V FLIGHT CAMERA'
			: 'W/S THROTTLE · A/D STEER · U CAMERA · P AUTO · B DRONE · C RETRY · V FREE · G SHOT · HOME RESET' );

	}

	_updateDrone( state, link, boat, drone ) {

		if ( ! this._drone ) return;
		const root = this._drone.root;
		const lost = link.connected === false;
		const status = String( link.status || '' ).toLowerCase();
		const age = Number.isFinite( link.telemetry_age_s ) ? Math.max( 0, link.telemetry_age_s ) : 0;
		const position = drone?.position;
		const boatPosition = boat?.position;
		const heading = drone ? ( ( drone.heading * 180 / Math.PI % 360 ) + 360 ) % 360 : null;
		const separation = position && boatPosition ? Math.hypot( boatPosition[ 0 ] - position[ 0 ], boatPosition[ 2 ] - position[ 2 ] ) : null;
		const ground = position ? Math.max( 0, this.app.terrainData.heightAt( position[ 0 ], position[ 2 ] ) ) : 0;
		const agl = position ? position[ 1 ] - ground : null;
		const signed = value => `${ value < 0 ? '−' : '+' }${ String( Math.abs( Math.round( value ) ) ).padStart( 4, '0' ) }`;

		this._dText( 'alt', position ? position[ 1 ].toFixed( 1 ).padStart( 5, '0' ) : '—' );
		this._dText( 'spd', drone && Number.isFinite( drone.speed ) ? drone.speed.toFixed( 2 ).padStart( 5, '0' ) : '—' );
		this._dText( 'hdg', heading === null ? '—' : String( Math.round( heading ) ).padStart( 3, '0' ) );
		this._dText( 'sep', separation === null ? '—' : separation.toFixed( 0 ).padStart( 3, '0' ) );
		this._dText( 'batt', Number.isFinite( drone?.battery_pct ) ? String( Math.round( drone.battery_pct ) ).padStart( 2, '0' ) : '—' );
		this._dText( 'agl', agl === null ? '—' : agl.toFixed( 1 ) );
		this._dText( 'gx', position ? signed( position[ 0 ] ) : '—' );
		this._dText( 'gz', position ? signed( position[ 2 ] ) : '—' );
		this._dText( 'bspd', boat ? boat.speed.toFixed( 1 ) : '—' );
		this._dText( 'bcrs', boat ? String( Math.round( degrees( boat.heading ) ) ).padStart( 3, '0' ) : '—' );

		const pitch = drone ? drone.pitch * 180 / Math.PI : 0;
		const roll = drone ? drone.roll * 180 / Math.PI : 0;
		this._dText( 'pitch', `${ pitch < 0 ? '−' : '+' }${ Math.abs( pitch ).toFixed( 1 ) }°` );
		this._dText( 'roll', `${ roll < 0 ? '−' : '+' }${ Math.abs( roll ).toFixed( 1 ) }°` );
		this._dBind( 'horizon' )?.setAttribute( 'transform', `rotate(${ ( - roll ).toFixed( 1 ) }) translate(0 ${ ( pitch * 3 ).toFixed( 1 ) })` );
		this._dBind( 'compass' )?.setAttribute( 'transform', `rotate(${ ( - ( heading || 0 ) ).toFixed( 1 ) })` );
		this._dText( 'armed', drone?.armed ? 'ARMED' : 'DISARMED' );
		this._dBind( 'armed' )?.classList.toggle( 'is-off', ! drone?.armed );
		const velocity = drone?.velocity;
		if ( velocity && Math.hypot( velocity[ 0 ], velocity[ 2 ] ) > .4 ) {

			const course = ( ( Math.atan2( velocity[ 0 ], - velocity[ 2 ] ) * 180 / Math.PI % 360 ) + 360 ) % 360;
			this._dBind( 'drone-vec' )?.setAttribute( 'transform', `rotate(${ course.toFixed( 0 ) })` );

		}

		const word = ! link.enabled ? 'DISABLED' : status === 'handshake' ? 'PAIRING' : lost ? 'LOST' : status === 'critical' ? 'CRITICAL' : status === 'degraded' ? 'DEGRADED' : 'STABLE';
		this._dText( 'link-text', `SX1262 · ${ word }` );
		this._dText( 'link-state', lost ? 'NO TELEMETRY' : status === 'handshake' ? 'HANDSHAKE' : word );
		root.classList.toggle( 'is-lost', lost );
		const quality = lost ? 0 : Math.round( link.quality ?? 0 );
		this._dText( 'quality', String( quality ).padStart( 3, '0' ) );
		const segments = this._dBind( 'segbar' )?.children || [];
		for ( let i = 0; i < segments.length; i ++ ) segments[ i ].classList.toggle( 'on', ! lost && i < Math.round( quality / 10 ) );
		this._dText( 'rssi', lost || ! Number.isFinite( link.rssi ) ? '—' : `${ link.rssi < 0 ? '−' : '+' }${ String( Math.abs( Math.round( link.rssi ) ) ).padStart( 3, '0' ) } dBm` );
		this._dText( 'snr', lost || ! Number.isFinite( link.snr ) ? '—' : `${ link.snr < 0 ? '−' : '+' }${ Math.abs( link.snr ).toFixed( 1 ) } dB` );
		this._dText( 'loss', lost ? '100.0 %' : Number.isFinite( link.packet_loss ) ? `${ link.packet_loss.toFixed( 1 ) } %` : '—' );
		this._dText( 'age', `${ age.toFixed( 1 ) } s` );
		const radioButton = this._dBind( 'radio-btn' );
		if ( radioButton ) {

			radioButton.textContent = link.enabled === false ? 'Enable SX1262' : 'Disable SX1262';
			radioButton.classList.toggle( 'is-on', link.enabled !== false );

		}
		const retryButton = this._dBind( 'retry-btn' );
		if ( retryButton ) retryButton.disabled = link.enabled === false || link.connected !== false || status === 'handshake';

		let fix = null;
		if ( position && boatPosition ) {

			fix = {
				range: separation,
				bearing: this._bearing( position, boatPosition ),
				heading: degrees( boat.heading ),
				speed: boat.speed,
				velocity: boat.velocity,
			};

		}
		if ( fix && ! lost ) this._droneFix = fix;
		const shown = lost ? this._droneFix : fix;
		this._dText( 'sc-range', shown ? shown.range.toFixed( 0 ) : '—' );
		this._dText( 'sc-bearing', shown ? String( Math.round( shown.bearing ) ).padStart( 3, '0' ) : '—' );
		const group = this._dBind( 'boat' ), line = this._dBind( 'sc-line' );
		if ( group ) group.style.display = shown ? '' : 'none';
		if ( line ) line.style.display = shown ? '' : 'none';
		if ( shown && group && line ) {

			const radius = Math.min( shown.range, 150 );
			const angle = shown.bearing * Math.PI / 180;
			const x = radius * Math.sin( angle ), y = - radius * Math.cos( angle );
			group.setAttribute( 'transform', `translate(${ x.toFixed( 1 ) } ${ y.toFixed( 1 ) })` );
			line.setAttribute( 'x2', x.toFixed( 1 ) );
			line.setAttribute( 'y2', y.toFixed( 1 ) );
			this._dBind( 'boat-rot' )?.setAttribute( 'transform', `rotate(${ shown.heading.toFixed( 0 ) })` );
			const glyph = this._dBind( 'boat-glyph' );
			glyph?.setAttribute( 'fill-opacity', lost ? '.06' : '.95' );
			glyph?.setAttribute( 'stroke', 'currentColor' );
			glyph?.setAttribute( 'stroke-width', lost ? '1.2' : '1.1' );
			this._dBind( 'boat-sigma' )?.setAttribute( 'r', ( lost ? 9 + Math.min( age, 10 ) * 2.4 : 6 ).toFixed( 1 ) );
			const vector = this._dBind( 'boat-vec' );
			if ( vector ) vector.style.display = lost || shown.speed < .4 ? 'none' : '';
			if ( vector && shown.speed >= .4 && shown.velocity ) {

				const course = ( ( Math.atan2( shown.velocity[ 0 ], - shown.velocity[ 2 ] ) * 180 / Math.PI % 360 ) + 360 ) % 360;
				vector.setAttribute( 'transform', `rotate(${ course.toFixed( 0 ) })` );

			}
			this._dText( 'boat-label', lost ? `BOAT · LAST ${ age.toFixed( 1 ) } s` : 'BOAT' );

		}
		this._dText( 'alarm', lost ? ( link.enabled === false ? 'SX1262 DISABLED · TELEMETRY OFF' : status === 'handshake' ? 'SX1262 PAIRING · TELEMETRY STALE' : `SX1262 LINK LOST · LAST FIX ${ age.toFixed( 1 ) } s · PRESS C` ) : '' );

		this._dText( 'keys', this.freeCamera
			? 'FREE CAMERA · WASD MOVE · Q/E HEIGHT · SHIFT FAST · V FLIGHT CAMERA'
			: 'WASD FLY · R/F ALT · Q/E YAW · LOOK MOUSE/ARROWS · B HELM · U BOAT CAM · V FREE · G SHOT · C RETRY · HOME RESET' );
		const control = this._flightControl();
		const flightButton = this._dBind( 'flight-btn' );
		if ( flightButton ) flightButton.disabled = ! state.ready || ! drone?.px4_ready || ! this.bridge?.cameraView || !! state.error || control.busy;
		const ml = this.bridge?.policy?.status || {};
		const mlButton = this._dBind( 'ml-btn' );
		if ( mlButton ) {

			mlButton.textContent = ml.loading ? 'Cancel ML loading' : ml.enabled ? 'Manual control' : 'ML landing';
			mlButton.disabled = ! ( ml.loading || ml.enabled ) && ( ! state.ready || ! this.bridge?.cameraView || ! drone?.armed || drone.landed || drone.landing_requested || !! state.error );

		}

	}

	captureScreenshot() {

		if ( this._screenshotPending ) return;
		this._screenshotPending = true;
		this._toast( 'Rendering screenshot · 1920 × 1080' );
		requestAnimationFrame( () => {

			this.app.captureScreenshot?.().then( result => this._toast( `Screenshot saved · ${ result.width } × ${ result.height }` ) )
				.catch( error => {

					console.error( 'Screenshot failed', error );
					this._toast( 'Screenshot failed: ' + error.message );

				} ).finally( () => { this._screenshotPending = false; } );

		} );

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

	_hText( key, value ) {

		const element = this._hBind( key );
		if ( element ) element.textContent = String( value );

	}

	_hBind( key ) {

		return this._helm?.bindings.get( key );

	}

	_dText( key, value ) {

		const element = this._dBind( key );
		if ( element ) element.textContent = String( value );

	}

	_dBind( key ) {

		return this._drone?.bindings.get( key );

	}

	_toast( text ) {

		const elements = [ this._bind( 'toast' ), this._hBind( 'toast' ), this._dBind( 'toast' ) ].filter( Boolean );
		if ( ! elements.length ) return;
		for ( const element of elements ) {

			element.textContent = text;
			element.classList.add( 'is-on' );

		}
		clearTimeout( this._toastTimer );
		this._toastTimer = setTimeout( () => {

			for ( const element of elements ) element.classList.remove( 'is-on' );

		}, 2600 );

	}

}
