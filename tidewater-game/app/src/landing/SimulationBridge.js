import * as E from '../engine/index.js';
import { standard } from '../materials/Materials.js';
import { Texture } from '../engine/gpu/Texture.js';
import { landingWaveParams } from './PhysicsWaves.js';
import { PoseTimeline } from './PoseTimeline.js';
import { PolicyControl } from './PolicyControl.js';

// Download many asset files with a limited number of requests in flight and
// return one promise per file, in input order. The caller still builds the
// meshes one by one in that order; only the waiting overlaps. (Fetching them
// one after another took minutes over the internet: ~1,000 small files, each
// with its own round trip.)
function fetchAll( urls, signal, limit = 16 ) {

	const slots = urls.map( () => {

		let resolve, reject;
		const promise = new Promise( ( a, b ) => { resolve = a; reject = b; } );
		promise.catch( () => {} ); // a slot the caller never reaches must not report an unhandled rejection
		return { promise, resolve, reject };

	} );
	let next = 0;
	const run = async () => {

		while ( next < urls.length ) {

			const i = next ++;
			try { slots[ i ].resolve( await ( await fetch( urls[ i ], { signal } ) ).arrayBuffer() ); } catch ( error ) { slots[ i ].reject( error ); }

		}

	};
	for ( let k = 0; k < Math.min( limit, urls.length ); k ++ ) run();
	return slots.map( slot => slot.promise );

}


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
        this.assetAbort = new AbortController();
		this.lastInput = 0;
		this.lastStatus = 0;
		this.lastMapUpload = 0;
		this.cameraView = null;
		this.cameraPaused = false;
		this.groups = new Map();
		this.layout = null;
		this.cameraTarget = { position: new E.Vector3(), quaternion: new E.Quaternion(), scale: new E.Vector3() };
		this.lastPacketTime = performance.now();
		this.timeline = new PoseTimeline();
		this.policy = new PolicyControl(this);
		this._connect();

	}

	async _connect() {
        if (this.closed || this.connecting || this.worker) return;
        this.connecting = true;
        let worker;
        try {
            this._setStatus({status:'Loading original CAD camera and browser physics',ready:false});
            worker=this._openWorker();
            // Reset may happen while CAD downloads are still in flight. Share
            // that installation and only initialize the worker that owns it.
            if(!this.vehicleInstallation)this.vehicleInstallation=this._installVehicles().catch(error=>{this.vehicleInstallation=null;throw error;});
            await this.vehicleInstallation;
            if(!this.closed && this.worker===worker && !worker.shuttingDown)await this._uploadMap();
        }catch(error){
            if(!this.closed && this.worker===worker)this._setStatus({status:'Browser simulation startup failed',ready:false,error:error.message});
        }finally{this.connecting=false;}
    }

	async _installVehicles() {

		if ( this.installed ) return;
		const response = await fetch( new URL('landing/vehicles.json', new URL(import.meta.env?.BASE_URL || './', location.href)), { cache: 'force-cache', signal:this.assetAbort.signal } );
		if ( ! response.ok ) throw new Error( 'The original X500 / AERODOCK CAD manifest is missing' );
		const payload = await response.json();
		const assetBase = new URL( import.meta.env?.BASE_URL || './', location.href );
		const assetUrl = url => new URL( url.replace( /^\/+/, '' ), assetBase );
		const textureBytes = fetchAll( payload.textures.map( item => assetUrl( item.url ) ), this.assetAbort.signal );
		const geomBytes = fetchAll( payload.geoms.map( part => assetUrl( part.url ) ), this.assetAbort.signal );
		for ( const [ index, item ] of payload.textures.entries() ) {
			const bytes = new Uint8Array( await textureBytes[ index ] );
			this.textures.set( item.id, new Texture( {
				width: item.width, height: item.height, format: 'rgba8unorm-srgb', data: bytes,
				usage: [ 'sample', 'copyDst' ], mips: true, label: item.name,
			} ) );
		}
		const materials = new Map();
		for ( const [ index, part ] of payload.geoms.entries() ) {
			const bytes = await geomBytes[ index ];
			const count = part.vertex_count;
			const geometry = new E.BufferGeometry();
			geometry.setAttribute( 'position', new E.Float32BufferAttribute( new Float32Array( bytes, 0, count * 3 ), 3 ) );
			geometry.setAttribute( 'normal', new E.Float32BufferAttribute( new Float32Array( bytes, count * 12, count * 3 ), 3 ) );
			geometry.setAttribute( 'uv', new E.Float32BufferAttribute( new Float32Array( bytes, count * 24, count * 2 ), 2 ) );
			geometry.setIndex( new E.Uint32BufferAttribute( new Uint32Array( bytes, count * 32, part.index_count ), 1 ) );
			// CAD names identify source parts, not different visual properties.
			const materialKey = JSON.stringify( { rgba: part.material.rgba, roughness: part.material.roughness, texture: part.material.texture } );
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
		await this._installDetailMeshes();
		if ( payload.hull ) {
			const bytes = await ( await fetch( new URL(payload.hull.url.replace(/^\/+/, ''),new URL(import.meta.env?.BASE_URL || './', location.href)), {signal:this.assetAbort.signal} ) ).arrayBuffer();
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

	// Optional higher-detail meshes for the operator view only (tools/build-detail-meshes.py).
	// The drone camera keeps drawing the trained meshes: PolicyCamera swaps them back for its
	// capture. A missing or broken detail set only means the trained meshes are shown everywhere.
	async _installDetailMeshes() {

		this.detailPairs = [];
		this.detailExtras = [];
		const base = new URL( import.meta.env?.BASE_URL || './', location.href );
		try {
			const response = await fetch( new URL( 'landing/detail/detail.json', base ), { cache: 'force-cache', signal: this.assetAbort.signal } );
			if ( ! response.ok ) return;
			const manifest = await response.json();
			// Parts the operator view leaves out (the Khadas Edge2 the drone no longer carries). They
			// stay in the trained scene: PolicyCamera shows them again for the drone camera's capture.
			const hiddenPrefixes = manifest.operator_hidden?.prefixes || [];
			this.operatorHidden = [ ...this.meshes.values() ].filter( mesh => hiddenPrefixes.some( prefix => mesh.name.startsWith( prefix ) ) );
			for ( const mesh of this.operatorHidden ) mesh.operatorHidden = true;
			const detailGeoms = ( manifest.geoms || [] ).filter( part => this.meshes.has( part.name ) );
			const extras = ( manifest.extras || [] ).filter( part => this.meshes.has( part.anchor ) );
			const detailBytes = fetchAll( detailGeoms.map( part => new URL( part.url.replace( /^\/+/, '' ), base ) ), this.assetAbort.signal );
			const extraBytes = fetchAll( extras.map( part => new URL( part.url.replace( /^\/+/, '' ), base ) ), this.assetAbort.signal );
			for ( const [ index, part ] of detailGeoms.entries() ) {
				const trained = this.meshes.get( part.name );
				if ( ! trained || trained.detailMesh ) continue;
				const bytes = await detailBytes[ index ];
				const count = part.vertex_count;
				if ( bytes.byteLength !== count * 32 + part.index_count * 4 ) continue;
				const geometry = new E.BufferGeometry();
				geometry.setAttribute( 'position', new E.Float32BufferAttribute( new Float32Array( bytes, 0, count * 3 ), 3 ) );
				geometry.setAttribute( 'normal', new E.Float32BufferAttribute( new Float32Array( bytes, count * 12, count * 3 ), 3 ) );
				geometry.setAttribute( 'uv', new E.Float32BufferAttribute( new Float32Array( bytes, count * 24, count * 2 ), 2 ) );
				geometry.setIndex( new E.Uint32BufferAttribute( new Uint32Array( bytes, count * 32, part.index_count ), 1 ) );
				const mesh = new E.Mesh( geometry, trained.material );
				mesh.matrixAutoUpdate = false;
				mesh.castShadow = trained.castShadow;
				mesh.receiveShadow = trained.receiveShadow;
				mesh.frustumCulled = true;
				mesh.name = `${ part.name } (operator view detail)`;
				mesh.visible = false;
				trained.detailMesh = mesh;
				this.detailPairs.push( [ trained, mesh ] );
				this.app.scene.add( mesh );
			}
			// Parts that exist in the operator view only (the battery cradle, its straps and screws:
			// tools/battery_cradle.py). Each is modelled in the mesh frame of a trained part, its
			// anchor, and follows that part; it has its own material.
			for ( const [ index, part ] of extras.entries() ) {
				const anchor = this.meshes.get( part.anchor );
				if ( ! anchor ) continue;
				const bytes = await extraBytes[ index ];
				const count = part.vertex_count;
				if ( bytes.byteLength !== count * 32 + part.index_count * 4 ) continue;
				const geometry = new E.BufferGeometry();
				geometry.setAttribute( 'position', new E.Float32BufferAttribute( new Float32Array( bytes, 0, count * 3 ), 3 ) );
				geometry.setAttribute( 'normal', new E.Float32BufferAttribute( new Float32Array( bytes, count * 12, count * 3 ), 3 ) );
				geometry.setAttribute( 'uv', new E.Float32BufferAttribute( new Float32Array( bytes, count * 24, count * 2 ), 2 ) );
				geometry.setIndex( new E.Uint32BufferAttribute( new Uint32Array( bytes, count * 32, part.index_count ), 1 ) );
				const data = part.material;
				const material = standard( {
					name: `CAD ${ data.name }`, color: new E.Color().setRGB( ...data.rgba.slice( 0, 3 ) ),
					opacity: data.rgba[ 3 ], roughness: data.roughness, metalness: data.metalness ?? 0, side: 'double',
				} );
				material.underwaterLighting = 'lite';
				const mesh = new E.Mesh( geometry, material );
				mesh.matrixAutoUpdate = false;
				mesh.castShadow = true;
				mesh.receiveShadow = true;
				mesh.frustumCulled = true;
				mesh.name = `${ part.name } (operator view only)`;
				mesh.visible = false;
				( anchor.detailExtras ||= [] ).push( mesh );
				this.detailExtras.push( mesh );
				this.app.scene.add( mesh );
			}
		} catch ( error ) {
			if ( error?.name === 'AbortError' ) throw error;
			console.warn( 'Operator-view detail meshes unavailable; showing the trained meshes:', error );
		}

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
        const base = new URL( 'landing/', new URL(import.meta.env?.BASE_URL || './', location.href) ).href;
        this.worker.postMessage( { type: 'initialize', base, meta: metadata, heights }, [ heights ] );
		this.lastMapUpload = Date.now();

	}

    _openWorker() {
        const worker = new Worker( new URL( './BrowserSimulationWorker.js', import.meta.url ), { type: 'module', name: 'AERODOCK PX4 and MuJoCo' } );
        this.worker = worker;
        worker.onmessage = event => {
            try {
                const state = event.data;
                if(state.type==='policy_control'){if(state.ml.enabled)this.policy.awaitActivation=false;else if(this.policy.status.enabled)this.policy.disable(state.ml.error||state.message);return;}
                if(state.type==='policy_capture'){if(!this.closed&&!worker.shuttingDown)this.policy.capture(state);return;}
                if ( state.disposed ) { this._disposeResolve?.(); return; }
                if (this.closed || worker.shuttingDown) return;
                if ( state.bodies && ! this.layout ) this.send( { mode: this.app.flightOps.mode } );
                this.timeline.push( state, performance.now() );
                this._setStatus( state );
                if(state.ml?.enabled)this.policy.awaitActivation=false;
                if(state.ml && !state.ml.enabled && this.policy.status.enabled && !this.policy.awaitActivation)this.policy.disable(state.ml.error);
                if ( state.geoms ) this._applyTransforms( state.geoms );
                if ( state.bodies ) this._applyBodies( state.bodies );
                if ( state.views ) this._applyCamera( state );
            } catch ( error ) {
                this._setStatus( { ...this.state, ready: false, status: 'Could not display browser simulation', error: error.message } );
            }
        };
        worker.onerror = event => { if(!this.closed && this.worker===worker && !worker.shuttingDown){this.policy.disable();this._setStatus( { ...this.state, ready: false, status: 'Browser simulation stopped', error: event.message || 'Physics worker failed' } );} };
        return worker;
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
			const detail = mesh.detailMesh;
			if ( detail ) {
				// The operator view shows the detail mesh; the trained mesh stays in place for the
				// drone camera, which swaps it back in for its own capture.
				if ( detail.parent !== group ) group.add( detail );
				detail.matrix.copy( mesh.matrix );
				detail.matrixWorldNeedsUpdate = true;
				detail.visible = true;
				mesh.visible = false;
			}
			if ( mesh.operatorHidden ) {
				mesh.operatorPlaced = true;
				mesh.visible = false;
				if ( detail ) detail.visible = false;
			}
			for ( const extra of mesh.detailExtras || [] ) {
				if ( extra.parent !== group ) group.add( extra );
				extra.matrix.copy( mesh.matrix );
				extra.matrixWorldNeedsUpdate = true;
				extra.visible = true;
			}
		}

	}

	_bodyGroup( name ) {

		let group = this.groups.get( name );
		if ( ! group ) {
			group = new E.Group();
			group.name = `Physics body ${ name }`;
			if ( name === 'boat' ) this.boatObject = group;
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

		if ( this.cameraPaused ) return;
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
		if ( this.cameraView && ! this.cameraPaused ) {
			if ( ! sample || ! this.timeline.apply( this.app.camera, `camera:${ this.cameraView }`, sample ) ) {
				this.app.camera.position.lerp( this.cameraTarget.position, alpha );
				this.app.camera.quaternion.slerp( this.cameraTarget.quaternion, alpha );
			}
			this.app.camera.updateMatrix();
		}
		if ( this.state?.waves ) {
			if ( ! this.landingWater ) this._takeLandingWater();
			const elapsed = this.state.error ? 0 : sample ? sample.time - this.state.time_s : ( Math.min( .1, ( performance.now() - this.lastPacketTime ) / 1000 ) - .025 ) * Math.min( 1.1, this.state.realtime_factor ?? 1 );
			for ( const [ i, c ] of this.state.waves.entries() ) {
				const omega = Math.sqrt( 9.80665 * Math.hypot( c[ 0 ], c[ 1 ] ) );
				landingWaveParams.fields[ `c${ i }` ].value.set( c[ 0 ], c[ 1 ], c[ 2 ], c[ 3 ] - omega * elapsed );
			}
		}

	}

    send( payload ) {
        if(payload.action==='land'||payload.action==='takeoff')this.policy?.disable();
        if ( payload.action === 'reset' ) { this.retry(); return; }
        if(this.worker && !this.worker.shuttingDown)this.worker.postMessage( payload );
    }

    async retry() {
        if ( this.restarting ) return;
        this.restarting = true;
        this.policy.disable();
        this._setStatus( { ...this.state, ready: false, error: null, status: 'Restarting browser simulation' } );
        try {
        await this._disposeWorker();
        this.timeline = new PoseTimeline(); this.cameraView = null; this.layout = null;
        this.lastMapUpload = 0; this.connecting = false;
        await this._connect();
        } catch(error) { this._setStatus({...this.state,ready:false,status:'Simulation shutdown failed; reload the page',error:error.message}); }
        finally { this.restarting = false; }
    }

    	// The flight simulation's water is the shared MuJoCo field: four metre-scale waves replace the
	// FFT ocean's height and normals (WaterSurface), so buoyancy and the rendered surface agree.
	// The shore surf stays on: its displacement is discarded by that same branch, but its analytic
	// swash edge, edge foam and surf-zone turbidity are what keep the waterline from ending on mesh
	// triangles (WaterMaterial clips the sheet per pixel). Take the field over when the first wave
	// packet arrives (the camera cuts to the vehicle then) and hand the ocean back on close.
	_takeLandingWater() {

		this.landingWater = true;
		landingWaveParams.fields.enabled.value = 1;

	}

	_releaseLandingWater() {

		if ( ! this.landingWater ) return;
		this.landingWater = false;
		landingWaveParams.fields.enabled.value = 0;

	}

	close() {

		this.policy.close();
		this._releaseLandingWater();
		this.closed = true;
        this.assetAbort.abort();
        return this._disposeWorker().catch(error => this._setStatus({...this.state, ready:false, error:error.message}));
    }

    async _disposeWorker() {
        const worker = this.worker;
        if (!worker) return;
        if (this.disposing) return this.disposing;
        this.disposing = new Promise((resolve,reject) => {
            const timer=setTimeout(()=>reject(new Error('PX4 threads did not confirm shutdown')),30000);
            this._disposeResolve=()=>{clearTimeout(timer);resolve();};
            worker.shuttingDown=true;
            worker.postMessage({type:'shutdown'});
        });
        try {
            await this.disposing;
            worker.terminate();
            if(this.worker===worker)this.worker=null;
        } finally {this.disposing=null;this._disposeResolve=null;}
    }
}
