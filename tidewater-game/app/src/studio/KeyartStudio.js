import {
	BufferGeometry, Color, Float32BufferAttribute, Group, MathUtils, Matrix4, Mesh, Uint32BufferAttribute, Vector3,
} from '../engine/index.js';
import { Texture } from '../engine/gpu/Texture.js';
import { standard } from '../materials/Materials.js';
import './studio.css';

// A separate, read-only presentation mode. It uses Tidewater's renderer, island,
// water and lighting, but only the original AERODOCK CAD: no PX4 worker, no
// flight physics, and no changes to the normal boat or drone.
const ASSET_BASE = new URL( import.meta.env?.BASE_URL || './', location.href );
const BOAT = { x: 34, y: - 0.02, z: - 24, heading: - Math.PI / 2 };
const DEFAULTS = { time: 16.35, exposure: 0.55, fov: 38 };
const PRESETS = {
	frontRight: { label: 'Front right', yaw: - 0.55, pitch: 0.13, distance: 5.0, targetY: 0.48, fov: 38 },
	profile: { label: 'Starboard', yaw: - 1.25, pitch: 0.11, distance: 5.4, targetY: 0.48, fov: 38 },
	bow: { label: 'Bow', yaw: - 0.08, pitch: 0.12, distance: 4.8, targetY: 0.5, fov: 38 },
	low: { label: 'Waterline', yaw: - 0.38, pitch: 0.04, distance: 4.4, targetY: 0.42, fov: 42 },
	aerial: { label: 'Aerial', yaw: - 0.7, pitch: 0.55, distance: 9.5, targetY: 0.4, fov: 45 },
};

const clockText = ( hours ) => {

	const m = Math.round( ( ( ( hours % 24 ) + 24 ) % 24 ) * 60 ) % 1440;
	return `${ String( Math.floor( m / 60 ) ).padStart( 2, '0' ) }:${ String( m % 60 ).padStart( 2, '0' ) }`;

};

const assetURL = ( path ) => new URL( String( path ).replace( /^\/+/, '' ), ASSET_BASE );

export class KeyartStudio {

	constructor( app, ui ) {

		this.app = app;
		this.ui = ui;
		this.ready = new Promise( ( resolve, reject ) => {

			this._resolve = resolve;
			this._reject = reject;

		} );
		this.boatRoot = new Group();
		this.boatRoot.name = 'AERODOCK keyart';
		this.boatRoot.position.set( BOAT.x, BOAT.y, BOAT.z );
		this.boatRoot.rotation.y = BOAT.heading;
		// The CAD layout is in the original simulation's Z-up frame. This is the
		// same MuJoCo -> renderer basis change used by the flight bridge.
		this.boatModel = new Group();
		this.boatModel.rotation.x = - Math.PI / 2;
		this.boatRoot.add( this.boatModel );
		app.scene.add( this.boatRoot );

		this.orbit = {
			yaw: PRESETS.frontRight.yaw, pitch: PRESETS.frontRight.pitch,
			distance: PRESETS.frontRight.distance, targetOffset: new Vector3( 0, PRESETS.frontRight.targetY, 0 ),
		};
		this.fov = DEFAULTS.fov;
		this.preset = 'frontRight';
		this.shotName = PRESETS.frontRight.label;
		this._drag = null;
		this._loaded = false;
		this.meshes = [];
		this.materials = new Map();

		this._prepareApp();
		this._mountUI();
		this._bindInput();
		this._load().catch( error => this._fail( error ) );

	}

	_prepareApp() {

		const app = this.app;
		app.boat.group.visible = false;
		app.boatCtl.update = () => {};
		app.boatCtl.queueQueries = () => {};
		app.boatSpray.update = () => {};
		app.wake.update = () => {};
		app.boat.update = () => {};
		app.game.update = () => {};
		app.settings.timeSpeed = 0;
		app.settings.timeOfDay = DEFAULTS.time;
		app.settings.exposure = DEFAULTS.exposure;
		app.freeCam = true;
		// The camera is driven by the studio's orbit controls, not the fly camera.
		app.fly.update = () => this.applyCamera();
		// Stop the normal game's pointer-lock and keyboard shortcuts from stealing
		// clicks or changing the camera while the user frames the shot.
		app.input.enabled = false;
		app.input.requestLock = () => {};
		document.body.classList.add( 'studio-mode' );
		if ( app.qs.has( 'clean' ) ) document.body.classList.add( 'studio-clean' );
		this.applyCamera();

	}

	_mountUI() {

		const root = document.createElement( 'div' );
		root.id = 'ka-studio';
		root.innerHTML = `
			<div class="ka-top">
				<div class="ka-brand">
					<span class="ka-mark">A</span>
					<span><b>AERODOCK</b><small>Keyart studio</small></span>
				</div>
				<div class="ka-top-right">
					<span class="ka-shot" data-bind="shot">Front right · 16:21</span>
					<button class="ka-ghost" data-action="ui" type="button">Hide UI <kbd>H</kbd></button>
				</div>
			</div>
			<div class="ka-help">Drag to orbit <i></i> Wheel to dolly <i></i> Shift-drag to pan</div>
			<section class="ka-panel" aria-label="Keyart shot settings">
				<header class="ka-panel-head"><span>Shot settings</span><small>Preview only · no flight sim</small></header>
				<div class="ka-field"><label for="ka-time">Time of day</label><output data-bind="time">16:21</output></div>
				<input id="ka-time" class="ka-range" data-control="time" type="range" min="0" max="24" step="0.05" value="16.35">
				<div class="ka-presets">
					<button data-preset="frontRight" type="button" class="is-on">Front right</button>
					<button data-preset="profile" type="button">Starboard</button>
					<button data-preset="bow" type="button">Bow</button>
					<button data-preset="low" type="button">Waterline</button>
					<button data-preset="aerial" type="button">Aerial</button>
				</div>
				<div class="ka-field"><label for="ka-fov">Lens</label><output data-bind="fov">38°</output></div>
				<input id="ka-fov" class="ka-range" data-control="fov" type="range" min="24" max="70" step="1" value="38">
				<div class="ka-field"><label for="ka-exposure">Exposure</label><output data-bind="exposure">0.55</output></div>
				<input id="ka-exposure" class="ka-range" data-control="exposure" type="range" min="0.2" max="1.2" step="0.01" value="0.55">
				<footer class="ka-panel-foot">
					<button data-action="reset" type="button">Reset shot <kbd>R</kbd></button>
					<span data-bind="status">Loading AERODOCK CAD…</span>
				</footer>
			</section>
		`;
		document.body.append( root );
		this.el = root;
		this._bindings = new Map( Array.from( root.querySelectorAll( '[data-bind]' ), ( el ) => [ el.dataset.bind, el ] ) );
		root.addEventListener( 'click', ( event ) => {

			const preset = event.target.closest( '[data-preset]' )?.dataset.preset;
			if ( preset ) {

				this.setPreset( preset );
				return;

			}
			const action = event.target.closest( '[data-action]' )?.dataset.action;
			if ( action === 'reset' ) this.reset();
			else if ( action === 'ui' ) this.toggleUI();

		} );
		root.addEventListener( 'input', ( event ) => {

			const control = event.target.dataset.control;
			if ( control === 'time' ) this.setTime( Number( event.target.value ) );
			else if ( control === 'fov' ) this.setFov( Number( event.target.value ) );
			else if ( control === 'exposure' ) this.setExposure( Number( event.target.value ) );

		} );
		this._syncControls();

	}

	_bindInput() {

		const canvas = this.app.engine.domElement;
		const finish = ( event ) => {

			if ( ! this._drag || event.pointerId !== this._drag.id ) return;
			this._drag = null;
			canvas.releasePointerCapture?.( event.pointerId );

		};
		canvas.addEventListener( 'pointerdown', ( event ) => {

			if ( event.button !== 0 && event.button !== 1 && event.button !== 2 ) return;
			const pan = event.button !== 0 || event.shiftKey;
			this._drag = { id: event.pointerId, x: event.clientX, y: event.clientY, pan };
			try {

				canvas.setPointerCapture( event.pointerId );

			} catch { /* pointer capture is optional */ }
			event.preventDefault();

		} );
		canvas.addEventListener( 'pointermove', ( event ) => {

			const drag = this._drag;
			if ( ! drag || event.pointerId !== drag.id ) return;
			const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
			drag.x = event.clientX;
			drag.y = event.clientY;
			if ( drag.pan ) {

				const camera = this.app.camera;
				const forward = new Vector3();
				const right = new Vector3();
				const up = new Vector3();
				camera.getWorldDirection( forward );
				right.crossVectors( forward, camera.up ).normalize();
				up.crossVectors( right, forward ).normalize();
				const scale = this.orbit.distance * 0.0016;
				this.orbit.targetOffset.addScaledVector( right, - dx * scale ).addScaledVector( up, dy * scale );
				this.orbit.targetOffset.y = MathUtils.clamp( this.orbit.targetOffset.y, - 0.2, 3 );

			} else {

				this.orbit.yaw -= dx * 0.006;
				this.orbit.pitch = MathUtils.clamp( this.orbit.pitch + dy * 0.004, 0.02, 1.25 );

			}
			this.shotName = 'Custom';
			this._syncShot();
			this.applyCamera();

		} );
		canvas.addEventListener( 'pointerup', finish );
		canvas.addEventListener( 'pointercancel', finish );
		canvas.addEventListener( 'wheel', ( event ) => {

			if ( ! event.deltaY ) return;
			this.orbit.distance = MathUtils.clamp( this.orbit.distance * Math.exp( event.deltaY * 0.0012 ), 2.2, 30 );
			this.shotName = 'Custom';
			this._syncShot();
			this.applyCamera();
			event.preventDefault();

		}, { passive: false } );
		canvas.addEventListener( 'dblclick', () => this.setPreset( 'frontRight' ) );
		window.addEventListener( 'keydown', ( event ) => {

			const target = event.target;
			if ( target && ( target.tagName === 'INPUT' || target.tagName === 'SELECT' || target.tagName === 'TEXTAREA' ) ) return;
			if ( event.code === 'KeyH' ) {

				event.preventDefault();
				this.toggleUI();

			} else if ( event.code === 'KeyR' ) {

				event.preventDefault();
				this.reset();

			}

		} );

	}

	async _load() {

		const setStatus = ( text ) => {

			this._bind( 'status' )?.replaceChildren( text );

		};
		setStatus( 'Loading AERODOCK CAD…' );
		this.ui?.setLoading( 0.38, 'Loading AERODOCK CAD' );
		const [ manifestResponse, layoutResponse ] = await Promise.all( [
			fetch( assetURL( 'landing/vehicles.json' ) ),
			fetch( assetURL( 'landing/aerodock-layout.json' ) ),
		] );
		if ( ! manifestResponse.ok ) throw new Error( 'AERODOCK CAD manifest is missing' );
		if ( ! layoutResponse.ok ) throw new Error( 'AERODOCK static layout is missing' );
		const payload = await manifestResponse.json();
		const layout = await layoutResponse.json();
		const matrixFor = new Map( layout.parts.map( ( [ name, matrix ] ) => [ name, matrix ] ) );
		const textures = new Map();
		await Promise.all( payload.textures.map( async ( item ) => {

			const response = await fetch( assetURL( item.url ) );
			if ( ! response.ok ) throw new Error( `AERODOCK texture ${ item.name } is missing` );
			const bytes = new Uint8Array( await response.arrayBuffer() );
			textures.set( item.id, new Texture( {
				width: item.width, height: item.height, format: 'rgba8unorm-srgb', data: bytes,
				usage: [ 'sample', 'copyDst' ], mips: true, label: item.name,
			} ) );

		} ) );
		this.ui?.setLoading( 0.52, 'Loading AERODOCK CAD' );
		const materialCache = new Map();
		const parts = payload.geoms.filter( ( part ) => matrixFor.has( part.name ) );
		const chunk = 16;
		for ( let i = 0; i < parts.length; i += chunk ) {

			await Promise.all( parts.slice( i, i + chunk ).map( async ( part ) => {

				const response = await fetch( assetURL( part.url ) );
				if ( ! response.ok ) throw new Error( `AERODOCK part ${ part.name } is missing` );
				const bytes = await response.arrayBuffer();
				const count = part.vertex_count;
				const geometry = new BufferGeometry();
				geometry.setAttribute( 'position', new Float32BufferAttribute( new Float32Array( bytes, 0, count * 3 ), 3 ) );
				geometry.setAttribute( 'normal', new Float32BufferAttribute( new Float32Array( bytes, count * 12, count * 3 ), 3 ) );
				geometry.setAttribute( 'uv', new Float32BufferAttribute( new Float32Array( bytes, count * 24, count * 2 ), 2 ) );
				geometry.setIndex( new Uint32BufferAttribute( new Uint32Array( bytes, count * 32, part.index_count ), 1 ) );
				const data = part.material;
				const materialKey = JSON.stringify( [ data.rgba, data.roughness, data.texture ] );
				let material = materialCache.get( materialKey );
				if ( ! material ) {

					material = standard( {
						name: `CAD ${ data.name }`,
						color: new Color().setRGB( ...data.rgba.slice( 0, 3 ) ),
						opacity: data.rgba[ 3 ], roughness: data.roughness, metalness: 0,
						side: 'double',
					} );
					if ( data.texture >= 0 ) material.map = textures.get( data.texture );
					material.underwaterLighting = 'lite';
					materialCache.set( materialKey, material );

				}
				const mesh = new Mesh( geometry, material );
				mesh.name = part.name;
				mesh.matrixAutoUpdate = false;
				mesh.matrix.fromArray( matrixFor.get( part.name ) );
				mesh.matrixWorldNeedsUpdate = true;
				mesh.castShadow = true;
				mesh.receiveShadow = true;
				mesh.frustumCulled = true;
				this.boatModel.add( mesh );
				this.meshes.push( mesh );

			} ) );
			this.ui?.setLoading( 0.52 + 0.38 * Math.min( 1, ( i + chunk ) / parts.length ), `Loading AERODOCK CAD · ${ Math.min( parts.length, i + chunk ) }/${ parts.length }` );

		}
		if ( ! this.meshes.length ) throw new Error( 'The AERODOCK layout contained no boat parts' );
		this.app.scene.updateMatrixWorld( true );
		this.ui?.setLoading( 0.92, 'Compiling AERODOCK materials' );
		try {

			await this.app.precompile();

		} catch ( error ) {

			console.warn( 'Keyart studio precompile failed; the first frame will finish it', error );

		}
		await this.app.gpu.pipelinesReady();
		this.applyCamera();
		this._loaded = true;
		setStatus( 'Drag to orbit · wheel to dolly' );
		await this.ui?.hideLoader();
		this._resolve( this );

	}

	_fail( error ) {

		console.error( 'Keyart studio failed', error );
		this._bind( 'status' )?.replaceChildren( error.message );
		this.ui?.setLoadingError( 'Keyart studio: ' + error.message );
		this._reject( error );

	}

	_bind( name ) {

		return this._bindings?.get( name );

	}

	_syncControls() {

		const time = this.app.settings.timeOfDay;
		this.el.querySelector( '[data-control="time"]' ).value = String( time );
		this.el.querySelector( '[data-control="fov"]' ).value = String( this.fov );
		this.el.querySelector( '[data-control="exposure"]' ).value = String( this.app.settings.exposure );
		this._bind( 'time' ).textContent = clockText( time );
		this._bind( 'fov' ).textContent = `${ Math.round( this.fov ) }°`;
		this._bind( 'exposure' ).textContent = this.app.settings.exposure.toFixed( 2 );
		for ( const button of this.el.querySelectorAll( '[data-preset]' ) ) button.classList.toggle( 'is-on', button.dataset.preset === this.preset );
		this._syncShot();

	}

	_syncShot() {

		this._bind( 'shot' ).textContent = `${ this.shotName } · ${ clockText( this.app.settings.timeOfDay ) }`;

	}

	setTime( hours ) {

		this.app.settings.timeOfDay = MathUtils.clamp( Number( hours ) || 0, 0, 24 );
		this._syncControls();

	}

	setExposure( exposure ) {

		this.app.settings.exposure = MathUtils.clamp( Number( exposure ) || 0, 0.2, 1.2 );
		this._syncControls();

	}

	setFov( fov ) {

		this.fov = MathUtils.clamp( Number( fov ) || DEFAULTS.fov, 24, 70 );
		this._syncControls();
		this.applyCamera();

	}

	setPreset( name ) {

		const preset = PRESETS[ name ] || PRESETS.frontRight;
		this.preset = PRESETS[ name ] ? name : 'frontRight';
		this.orbit.yaw = preset.yaw;
		this.orbit.pitch = preset.pitch;
		this.orbit.distance = preset.distance;
		this.orbit.targetOffset.set( 0, preset.targetY, 0 );
		this.fov = preset.fov ?? DEFAULTS.fov;
		this.shotName = preset.label;
		this._syncControls();
		this.applyCamera();

	}

	reset() {

		this.preset = 'frontRight';
		this.app.settings.timeOfDay = DEFAULTS.time;
		this.app.settings.exposure = DEFAULTS.exposure;
		this.fov = DEFAULTS.fov;
		this.setPreset( 'frontRight' );

	}

	toggleUI() {

		const clean = document.body.classList.toggle( 'studio-clean' );
		const button = this.el.querySelector( '[data-action="ui"]' );
		if ( button ) button.setAttribute( 'aria-pressed', String( clean ) );

	}

	applyCamera() {

		const camera = this.app.camera;
		const target = this._target;
		if ( ! target ) this._target = new Vector3();
		const t = this._target.copy( this.boatRoot.position ).add( this.orbit.targetOffset );
		const r = Math.cos( this.orbit.pitch ) * this.orbit.distance;
		camera.position.set(
			t.x + Math.sin( this.orbit.yaw ) * r,
			t.y + Math.sin( this.orbit.pitch ) * this.orbit.distance,
			t.z + Math.cos( this.orbit.yaw ) * r,
		);
		camera.up.set( 0, 1, 0 );
		camera.lookAt( t );
		camera.fov = this.fov;
		camera.aspect = this.app.engine.canvas.width / Math.max( 1, this.app.engine.canvas.height );
		camera.near = 0.05;
		camera.updateProjectionMatrix();
		camera.updateMatrixWorld();

	}

}
