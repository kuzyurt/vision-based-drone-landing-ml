import { state, readCanvas, writePNG } from './dom-shim.mjs';
const { App } = await import( '../../src/App.js' );
const { SimulationBridge } = await import( '../../src/landing/SimulationBridge.js' );
const app = new App();
const t0 = performance.now(), el = () => ( ( performance.now() - t0 ) / 1000 ).toFixed( 1 );
await app.init( () => {} );
app.settings.timeOfDay = 15;
console.log( el(), 'init ok' );
const ops = app.flightOps = { active: true, freeCamera: false, mode: 'drone', boatCamera: 'boat_dock', beforePhysics() {}, update( dt ) { this.bridge?.update( dt ); }, _refreshUI() {} };
for ( const m of [ '_installVehicles', '_uploadMap' ] ) { const f = SimulationBridge.prototype[ m ]; SimulationBridge.prototype[ m ] = async function ( ...a ) { try { return await f.apply( this, a ); } catch ( e ) { console.log( m, e.stack.split( '\n' ).slice( 0, 6 ).join( '\n' ) ); throw e; } }; }
ops.bridge = new SimulationBridge( app, ( s ) => { if ( s.status !== ops.last ) { ops.last = s.status; if ( ! /collision meshes ·/.test( s.status ) ) console.log( el(), 'status', s.status, s.error || '' ); } } );
let frames = 0;
const frame = async () => { app._frame( 1 / 30 ); frames ++; await state.device.queue.onSubmittedWorkDone(); };
while ( ! ( ops.bridge.state?.ready && ops.bridge.state.drone?.px4_ready ) && performance.now() - t0 < 400000 && ! ops.bridge.state?.error ) { await frame(); await new Promise( r => setTimeout( r, 20 ) ); }
console.log( el(), 'ready', !! ops.bridge.state?.ready, 'frames', frames );
for ( let i = 0; i < 6; i ++ ) await frame();
const img = await readCanvas();
writePNG( '/tmp/hero-boot.png', img.width, img.height, img.data );
console.log( el(), 'wrote', img.width, img.height, JSON.stringify( ops.bridge.state?.drone?.position ) );
process.exit( 0 );
