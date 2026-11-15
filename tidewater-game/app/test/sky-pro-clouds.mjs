// SkyProClouds (the game's clouds) as the scene background with a moving camera: writes frames to
// look for reconstruction artefacts. usage: node test/sky-pro-clouds.mjs [outDir] [W] [H] [motion]
// motion: still | pan | fly | shake (drone-like yaw + pitch jitter while translating)
import { readFile } from 'node:fs/promises';
import { GPU, G, E, setFrameCamera, RenderTarget, tonemapPass, savePNG, setTimeOfDay, applyReadback, wait } from './sky-harness.mjs';
import { Atmosphere, SUN_ILLUMINANCE } from '../src/sky/Atmosphere.js';
import { Sky, sunDirectionFromTime } from '../src/sky/Sky.js';
import { SkyProClouds } from '../src/sky/SkyProClouds.js';
import { MeshRenderer } from '../src/engine/render/MeshRenderer.js';
import { SceneRenderer } from '../src/engine/render/SceneRenderer.js';

const realFetch = globalThis.fetch;
globalThis.fetch = async ( url, ...rest ) => {

	if ( typeof url === 'string' && ! /^[a-z]+:/.test( url ) ) return new Response( await readFile( new URL( '../public/' + url.replace( /^\//, '' ), import.meta.url ) ) );
	return realFetch( url, ...rest );

};

await GPU.init( { headless: true } );
const out = process.argv[ 2 ] || '/tmp';
const W = Number( process.argv[ 3 ] || 960 ), H = Number( process.argv[ 4 ] || 540 );
const motion = process.argv[ 5 ] || 'pan';
const atmosphere = new Atmosphere();
const sky = new Sky( atmosphere );
const clouds = new SkyProClouds( null, atmosphere );
clouds.outputSize = { x: W, y: H };
sky.clouds = clouds;
await clouds.ready;
const scene = new E.Scene();
const camera = new E.PerspectiveCamera( Number( process.env.FOV || 55 ), W / H, 0.1, 60000 );
const mr = new MeshRenderer();
const sr = new SceneRenderer( mr, scene, camera );
sr.setSize( W, H );
sr.background = sky.background;
const ldr = new RenderTarget( W, H, { colors: [ 'rgba8unorm' ], label: 'ldr' } );
const app = { atmosphere, sky };
setTimeOfDay( app, 15, sunDirectionFromTime, SUN_ILLUMINANCE );
G.exposure.value = 1;
const N = Number( process.env.FRAMES || 48 ), every = Number( process.env.EVERY || 8 ), dt = 1 / Number( process.env.FPS || 60 );
for ( let f = 0; f < N; f ++ ) {

	const t = f * dt;
	let yaw = 0.6, pitch = 0.28, x = 0, y = 30, z = 0;
	if ( motion === 'pan' ) yaw += t * 0.5;
	if ( motion === 'fly' ) { x = t * 12; y = 30 + t * 2; }
	if ( motion === 'shake' ) { yaw += t * 0.35 + Math.sin( t * 9 ) * 0.02; pitch += Math.sin( t * 5 ) * 0.04; x = t * 6; }
	camera.position.set( x, y, z );
	camera.lookAt( x + Math.cos( yaw ), y + Math.tan( pitch ), z + Math.sin( yaw ) );
	camera.updateMatrixWorld();
	GPU.beginFrame();
	atmosphere._irrTimer = f % 4 === 0 ? 0 : atmosphere._irrTimer;
	atmosphere.update( dt, camera.position.y );
	clouds.update( dt, camera );
	setFrameCamera( camera, W, H );
	sr.render();
	tonemapPass( sr.sceneRT.texture ).render( { colorViews: [ ldr.texture ] } );
	GPU.submit();
	await wait( 2 );
	applyReadback( app );
	if ( f % every === every - 1 || f === 0 || ( process.env.DENSE && f >= N - 4 ) ) {

		await GPU.queue.onSubmittedWorkDone();
		await savePNG( ldr.texture, `${ out }/skypro-${ motion }-${ String( f ).padStart( 3, '0' ) }.png` );
		console.log( 'frame', f );

	}

}

await wait( 100 );
process.exit( 0 );
