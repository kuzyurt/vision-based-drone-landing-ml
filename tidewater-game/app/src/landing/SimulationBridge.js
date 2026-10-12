import * as E from '../engine/index.js';
import { standard } from '../materials/Materials.js';
import { Texture } from '../engine/gpu/Texture.js';
import { landingWaveParams } from './PhysicsWaves.js';
import { PoseTimeline } from './PoseTimeline.js';


export class SimulationBridge {

	constructor( app, onStatus ) {

		this.app = app;
		this.onStatus = onStatus;
		this.meshes = new Map();
		this.textures = new Map();
		this.state = null;
		this.socket = null;
		this.closed = false;
		this.connecting = false;
		this.lastInput = 0;
		this.lastStatus = 0;
		this.lastMapUpload = 0;
		this.cameraView = null;
		this.groups = new Map();
		this.layout = null;
		this.cameraTarget = { position: new E.Vector3(), quaternion: new E.Quaternion(), scale: new E.Vector3() };
		this.lastPacketTime = performance.now();
		this.timeline = new PoseTimeline();
		this._connect();

	}

	async _connect() {
        if ( this.closed || this.connecting || this.worker ) return;
        this.connecting = true;
        try {
            this._setStatus( { status: 'Loading original CAD camera and browser physics', ready: false } );
            this._openWorker();
            await this._installVehicles();
            await this._uploadMap();
        } catch ( error ) {
            this._setStatus( { status: 'Browser simulation startup failed', ready: false, error: error.message } );
        }
        this.connecting = false;
    }

	async _installVehicles() {

		if ( this.installed ) return;
		const response = await fetch( '/landing/vehicles.json', { cache: 'force-cache' } );
		if ( ! response.ok ) throw new Error( 'The original X500 / AERODOCK CAD manifest is missing' );
		const payload = await response.json();
		for ( const item of payload.textures ) {
			const bytes = new Uint8Array( await ( await fetch( item.url ) ).arrayBuffer() );
			this.textures.set( item.id, new Texture( {
				width: item.width, height: item.height, format: 'rgba8unorm-srgb', data: bytes,
				usage: [ 'sample', 'copyDst' ], mips: true, label: item.name,
			} ) );
		}
		const materials = new Map();
		for ( const part of payload.geoms ) {
			const bytes = await ( await fetch( part.url ) ).arrayBuffer();
			const count = part.vertex_count;
			const geometry = new E.BufferGeometry();
			geometry.setAttribute( 'position', new E.Float32BufferAttribute( new Float32Array( bytes, 0, count * 3 ), 3 ) );
			geometry.setAttribute( 'normal', new E.Float32BufferAttribute( new Float32Array( bytes, count * 12, count * 3 ), 3 ) );
			geometry.setAttribute( 'uv', new E.Float32BufferAttribute( new Float32Array( bytes, count * 24, count * 2 ), 2 ) );
			geometry.setIndex( new E.Uint32BufferAttribute( new Uint32Array( bytes, count * 32, part.index_count ), 1 ) );
			const materialKey = JSON.stringify( part.material );
			let material = materials.get( materialKey );
			if ( ! material ) {
				const data = part.material;
				material = standard( {
					name: `CAD ${ data.name }`, color: new E.Color().setRGB( ...data.rgba.slice( 0, 3 ) ),
					opacity: data.rgba[ 3 ], roughness: data.roughness, metalness: 0, side: 'double',
				} );
				if ( data.texture >= 0 ) material.map = this.textures.get( data.texture );
				material.underwaterLighting = 'lite';
				materials.set( materialKey, material );
			}
			const mesh = new E.Mesh( geometry, material );
			mesh.matrixAutoUpdate = false;
			mesh.castShadow = true;
			mesh.receiveShadow = true;
			mesh.frustumCulled = true;
			mesh.name = part.name;
			mesh.visible = false;
			this.meshes.set( part.name, mesh );
			this.app.scene.add( mesh );
		}
		if ( payload.hull ) {
			const bytes = await ( await fetch( payload.hull.url ) ).arrayBuffer();
			const geometry = new E.BufferGeometry();
			geometry.setAttribute( 'position', new E.Float32BufferAttribute( new Float32Array( bytes ), 3 ) );
			geometry.computeVertexNormals();
			this.hull = new E.Group();
			this.hull.target = { position: new E.Vector3(), quaternion: new E.Quaternion(), scale: new E.Vector3() };
			this.app.scene.add( this.hull );
			this.app.sceneRenderer.addHullMask( geometry, this.hull );
		}
		await this.app.precompile();
		await this.app.gpu.pipelinesReady();
		this.installed = true;
		if ( this.layout ) this._applyTransforms( this.layout );

	}

	async _uploadMap() {

		const terrain = this.app.terrainData;
		const colliders = this.app.colliders;
		const metadata = {
			origin: terrain.origin, size: terrain.size, res: terrain.res,
			colliders: {
				boxes: colliders.boxes.filter( box => box.solid ).map( box => ( {
					center: box.center.toArray(), half: box.half.toArray(), rotY: box.rotY, solid: true, tag: box.tag,
				} ) ),
				cylinders: colliders.cylinders.map( cylinder => ( { ...cylinder } ) ),
			},
		};
        // The renderer keeps its data while physics receives an owned copy.
        const heights = new Float32Array( terrain.heights ).buffer;
        const base = new URL( `${ import.meta.env?.BASE_URL || '/' }landing/`, location.href ).href;
        this.worker.postMessage( { type: 'initialize', base, meta: metadata, heights }, [ heights ] );
		this.lastMapUpload = Date.now();

	}

    _openWorker() {
        const worker = new Worker( new URL( './BrowserSimulationWorker.js', import.meta.url ), { type: 'module', name: 'Tidewater PX4 and MuJoCo' } );
        this.worker = worker;
        worker.onmessage = event => {
            try {
                const state = event.data;
                if ( state.disposed ) { this._disposeResolve?.(); return; }
                if ( state.bodies && ! this.layout ) this.send( { mode: this.app.flightOps.mode } );
                this.timeline.push( state, performance.now() );
                this._setStatus( state );
                if ( state.geoms ) this._applyTransforms( state.geoms );
                if ( state.bodies ) this._applyBodies( state.bodies );
                if ( state.views ) this._applyCamera( state );
            } catch ( error ) {
                this._setStatus( { ...this.state, ready: false, status: 'Could not display browser simulation', error: error.message } );
            }
        };
        worker.onerror = event => this._setStatus( { ...this.state, ready: false, status: 'Browser simulation stopped', error: event.message || 'Physics worker failed' } );
    }

	_setStatus( state ) {

		if ( state.route && ! state.route.points && this.state?.route?.points ) state.route.points = this.state.route.points;
		if ( ! state.coastline && this.state?.coastline ) state.coastline = this.state.coastline;
		this.state = state;
		this.lastPacketTime = performance.now();
		if ( this.onStatus ) this.onStatus( state );

	}

	_applyTransforms( transforms ) {

		this.layout = transforms;
		for ( const [ id, values, body ] of transforms ) {
			const mesh = this.meshes.get( id );
			if ( ! mesh ) continue;
			const group = this._bodyGroup( body );
			if ( mesh.parent !== group ) group.add( mesh );
			mesh.matrix.set( ...values );
			mesh.matrixWorldNeedsUpdate = true;
			mesh.visible = true;
		}

	}

	_bodyGroup( name ) {

		let group = this.groups.get( name );
		if ( ! group ) {
			group = new E.Group();
			group.name = `Physics body ${ name }`;
			group.target = { position: new E.Vector3(), quaternion: new E.Quaternion(), scale: new E.Vector3() };
			this.groups.set( name, group );
			this.app.scene.add( group );
		}
		return group;

	}

	_applyBodies( bodies ) {

		for ( const [ name, values ] of bodies ) {
			const group = this._bodyGroup( name );
			new E.Matrix4().set( ...values ).decompose( group.target.position, group.target.quaternion, group.target.scale );
			if ( ! group.initialized ) {
				group.position.copy( group.target.position );
				group.quaternion.copy( group.target.quaternion );
				group.initialized = true;
			}
		}
		if ( this.hull && this.state.hull_pose ) {
			new E.Matrix4().set( ...this.state.hull_pose ).decompose( this.hull.target.position, this.hull.target.quaternion, this.hull.target.scale );
			if ( ! this.hull.initialized ) {
				this.hull.position.copy( this.hull.target.position );
				this.hull.quaternion.copy( this.hull.target.quaternion );
				this.hull.initialized = true;
			}
		}

	}

	_applyCamera( state, snap = false ) {

		const controls = this.app.flightOps;
		const name = controls.mode === 'boat' ? controls.boatCamera : 'drone';
		const view = state.views[ name ];
		if ( ! view ) return;
		const camera = this.app.camera;
		const matrix = new E.Matrix4().set( ...view.matrix );
		camera.matrixAutoUpdate = true;
		matrix.decompose( this.cameraTarget.position, this.cameraTarget.quaternion, this.cameraTarget.scale );
		if ( snap || this.cameraView !== name ) {
			camera.position.copy( this.cameraTarget.position );
			camera.quaternion.copy( this.cameraTarget.quaternion );
		}
		camera.fov = view.fovy;
		camera.aspect = this.app.engine.canvas.width / Math.max( 1, this.app.engine.canvas.height );
		camera.near = .001;
		camera.updateProjectionMatrix();
		this.cameraView = name;

	}

	selectCamera() {

		if ( this.state?.views ) this._applyCamera( this.state, true );

	}

	update( dt ) {

		const sample = this.timeline?.sample( performance.now() );
		const alpha = 1 - Math.exp( -dt / .025 );
		for ( const group of this.groups.values() ) {
			if ( ! group.initialized ) continue;
			if ( sample && this.timeline.apply( group, group.name.slice( 'Physics body '.length ), sample ) ) continue;
			group.position.lerp( group.target.position, alpha );
			group.quaternion.slerp( group.target.quaternion, alpha );
		}
		if ( this.hull?.initialized ) {
			if ( ! sample || ! this.timeline.apply( this.hull, 'hull', sample ) ) {
				this.hull.position.lerp( this.hull.target.position, alpha );
				this.hull.quaternion.slerp( this.hull.target.quaternion, alpha );
			}
		}
		if ( this.cameraView ) {
			if ( ! sample || ! this.timeline.apply( this.app.camera, `camera:${ this.cameraView }`, sample ) ) {
				this.app.camera.position.lerp( this.cameraTarget.position, alpha );
				this.app.camera.quaternion.slerp( this.cameraTarget.quaternion, alpha );
			}
			this.app.camera.updateMatrix();
		}
		if ( this.state?.waves ) {
			const elapsed = this.state.error ? 0 : sample ? sample.time - this.state.time_s : ( Math.min( .1, ( performance.now() - this.lastPacketTime ) / 1000 ) - .025 ) * Math.min( 1.1, this.state.realtime_factor ?? 1 );
			for ( const [ i, c ] of this.state.waves.entries() ) {
				const omega = Math.sqrt( 9.80665 * Math.hypot( c[ 0 ], c[ 1 ] ) );
				landingWaveParams.fields[ `c${ i }` ].value.set( c[ 0 ], c[ 1 ], c[ 2 ], c[ 3 ] - omega * elapsed );
			}
		}

	}

    send( payload ) {
        if ( payload.action === 'reset' ) { this.retry(); return; }
        this.worker?.postMessage( payload );
    }

    async retry() {
        if ( this.restarting ) return;
        this.restarting = true;
        this._setStatus( { ...this.state, ready: false, error: null, status: 'Restarting browser simulation' } );
        await this._disposeWorker();
        this.timeline = new PoseTimeline(); this.cameraView = null; this.layout = null;
        this.lastMapUpload = 0; this.connecting = false;
        await this._connect();
        this.restarting = false;
    }

    close() {
        this.closed = true;
        this._disposeWorker();
    }

    async _disposeWorker() {
        const worker = this.worker;
        if ( ! worker ) return;
        this.worker = null;
        await new Promise( resolve => {
            const timer = setTimeout( resolve, 1500 );
            this._disposeResolve = () => { clearTimeout( timer ); resolve(); };
            worker.postMessage( { type: 'shutdown' } );
        } );
        worker.terminate(); this._disposeResolve = null;
    }
}
