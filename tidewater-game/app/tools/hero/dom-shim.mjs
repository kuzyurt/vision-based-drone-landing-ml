// Minimal browser environment for running the Tidewater App in Node (Dawn WebGPU, no window).
// Only what App.init and the render path touch: a canvas whose WebGPU context is an offscreen
// texture, local-file fetch, image decoding through Chromium-free PNG/JPEG decoders is not
// needed (the scene assets are binary/KTX-free: GLB images go through createImageBitmap below).
import { create, globals } from 'webgpu';
import { writePNG } from '../../test/headless.mjs'; // first: this shim then replaces its globals
export { writePNG };
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

Object.assign( globalThis, globals );
const gpu = create( [ 'backend=vulkan' ] );
export const PUBLIC = new URL( '../../public/', import.meta.url );
export const state = { width: 1280, height: 720, texture: null, device: null };

const noop = () => {};
function element( tag = 'div' ) {

	const el = {
		tagName: tag.toUpperCase(), style: {}, dataset: {}, children: [], classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
		appendChild( c ) { this.children.push( c ); return c; }, append: noop, remove: noop, removeChild: noop, prepend: noop,
		addEventListener: noop, removeEventListener: noop, setAttribute: noop, getAttribute: () => null, removeAttribute: noop,
		querySelector: () => null, querySelectorAll: () => [], getBoundingClientRect: () => ( { left: 0, top: 0, width: state.width, height: state.height, right: state.width, bottom: state.height } ),
		focus: noop, blur: noop, click: noop, setPointerCapture: noop, releasePointerCapture: noop, requestPointerLock: noop,
		get clientWidth() { return state.width; }, get clientHeight() { return state.height; },
		innerHTML: '', textContent: '', hidden: false,
	};
	if ( tag === 'canvas' ) {

		el.width = state.width; el.height = state.height;
		el.getContext = ( kind ) => kind !== 'webgpu' ? null : {
			configure( { device, format, usage } ) { state.device = device; state.format = format; state.usage = usage; },
			unconfigure: noop,
			getCurrentTexture() {

				if ( ! state.texture || state.texture.width !== el.width || state.texture.height !== el.height ) {

					state.texture?.destroy();
					state.texture = state.device.createTexture( { size: [ el.width, el.height ], format: state.format, usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC | GPUTextureUsage.COPY_DST | GPUTextureUsage.TEXTURE_BINDING } );

				}

				return state.texture;

			},
		};

	}

	return el;

}

const body = element( 'body' );
globalThis.document = {
	body, documentElement: element( 'html' ), head: element( 'head' ), visibilityState: 'visible', hidden: false, pointerLockElement: null, activeElement: null,
	getElementById: () => element( 'div' ), createElement: element, createElementNS: ( _, tag ) => element( tag ),
	querySelector: () => null, querySelectorAll: () => [], addEventListener: noop, removeEventListener: noop, exitPointerLock: noop, fonts: { ready: Promise.resolve() },
};
const win = globalThis;
win.window = win;
win.innerWidth = state.width; win.innerHeight = state.height; win.devicePixelRatio = 1;
win.addEventListener = noop; win.removeEventListener = noop; win.dispatchEvent = noop;
win.location = { search: process.env.HERO_QUERY || '?noAudio', href: 'http://localhost/', origin: 'http://localhost', pathname: '/', protocol: 'http:' };
win.history = { replaceState: noop };
win.matchMedia = () => ( { matches: false, addEventListener: noop, removeEventListener: noop } );
win.localStorage = { getItem: () => null, setItem: noop, removeItem: noop };
win.requestAnimationFrame = ( cb ) => setTimeout( () => cb( performance.now() ), 0 );
win.cancelAnimationFrame = clearTimeout;
Object.defineProperty( win, 'navigator', { value: { gpu, userAgent: 'Node.js', hardwareConcurrency: 4, getGamepads: () => [], maxTouchPoints: 0, storage: null }, configurable: true } );
win.ResizeObserver = class { observe() {} disconnect() {} };

const realFetch = globalThis.fetch;
win.fetch = async ( url, ...rest ) => {

	const text = String( url?.url ?? url );
	if ( /^https?:\/\/localhost\//.test( text ) || ! /^[a-z]+:/i.test( text ) ) {

		const path = text.replace( /^https?:\/\/localhost\//, '' ).replace( /^\.?\//, '' ).split( '?' )[ 0 ];
		try {

			return new Response( await readFile( new URL( path, PUBLIC ) ) );

		} catch ( error ) {

			return new Response( null, { status: 404, statusText: 'missing ' + path } );

		}

	}

	if ( text.startsWith( 'file:' ) ) return new Response( await readFile( fileURLToPath( text ) ) );
	return realFetch( url, ...rest );

};

// ---- the scene is fetched from files: page URLs resolve inside public/
win.location.href = PUBLIC.href;
gpu.getPreferredCanvasFormat = () => 'bgra8unorm';

// ---- embedded images (GLB textures, SMAA tables): decoded by Pillow, RGBA8 top row first
import { execFileSync } from 'node:child_process';
win.__assetImage = async ( bytes ) => {

	const out = execFileSync( 'python3', [ '-c', 'import sys,io,struct\nfrom PIL import Image\nim=Image.open(io.BytesIO(sys.stdin.buffer.read())).convert("RGBA")\nsys.stdout.buffer.write(struct.pack("<II",*im.size)+im.tobytes())' ], { input: Buffer.from( bytes.buffer, bytes.byteOffset, bytes.byteLength ), maxBuffer: 1 << 30 } );
	const width = out.readUInt32LE( 0 ), height = out.readUInt32LE( 4 );
	return { data: new Uint8Array( out.buffer, out.byteOffset + 8, width * height * 4 ).slice(), width, height };

};

// ---- web Workers: the production workers run through their Node adapters (wasm/tests)
import { Worker as NodeWorker } from 'node:worker_threads';
const ADAPTERS = {
	'BrowserSimulationWorker.js': new URL( '../../../wasm/tests/runtime-worker.mjs', import.meta.url ),
	'PolicyInferenceWorker.js': new URL( '../../../wasm/tests/policy-controller-worker.mjs', import.meta.url ),
};
win.Worker = class {

	constructor( url ) {

		const name = String( url ).split( '/' ).pop();
		if ( ! ADAPTERS[ name ] ) throw new Error( 'No Node adapter for worker ' + name );
		this.worker = new NodeWorker( ADAPTERS[ name ] );
		this.worker.on( 'message', ( data ) => this.onmessage?.( { data } ) );
		this.worker.on( 'error', ( error ) => this.onerror?.( { message: error?.stack || String( error ) } ) );

	}

	postMessage( message, transfer ) { this.worker.postMessage( message, transfer ); }
	terminate() { return this.worker.terminate(); }

};

// ---- frame readback: the canvas texture as RGBA8 rows
export async function readCanvas() {

	const { texture: t, device } = state;
	const bytesPerRow = Math.ceil( t.width * 4 / 256 ) * 256;
	const buffer = device.createBuffer( { size: bytesPerRow * t.height, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ } );
	const encoder = device.createCommandEncoder();
	encoder.copyTextureToBuffer( { texture: t }, { buffer, bytesPerRow }, [ t.width, t.height ] );
	device.queue.submit( [ encoder.finish() ] );
	await buffer.mapAsync( GPUMapMode.READ );
	const mapped = new Uint8Array( buffer.getMappedRange() );
	const out = new Uint8Array( t.width * t.height * 4 );
	for ( let y = 0; y < t.height; y ++ ) out.set( mapped.subarray( y * bytesPerRow, y * bytesPerRow + t.width * 4 ), y * t.width * 4 );
	for ( let i = 0; i < out.length; i += 4 ) { const b = out[ i ]; out[ i ] = out[ i + 2 ]; out[ i + 2 ] = b; out[ i + 3 ] = 255; } // BGRA canvas -> RGBA
	buffer.unmap(); buffer.destroy();
	return { data: out, width: t.width, height: t.height };

}
