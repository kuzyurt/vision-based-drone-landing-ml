import assert from 'node:assert/strict';
import { PoseTimeline } from '../src/landing/PoseTimeline.js';
import { FlightOperations } from '../src/game/FlightOperations.js';
import * as E from '../src/engine/index.js';

const matrix = x => [ 1,0,0,x, 0,1,0,0, 0,0,1,0, 0,0,0,1 ];
const state = time => ( { time_s:time, realtime_factor:1, bodies:[ [ 'drone', matrix( time ) ] ],
	views:{ drone:{ matrix:matrix( time + .2 ), fovy:60 } }, hull_pose:matrix( time + .4 ) } );
const timeline = new PoseTimeline();
const body = new E.Group(), camera = new E.PerspectiveCamera(), hull = new E.Group();
let nextPacket = 0, previous = null, maxStepError = 0;
// A 25 FPS renderer and a 40 Hz transport with alternating arrival jitter.
for ( let wall = 0; wall <= 2000; wall += 40 ) {
	while ( nextPacket <= wall ) {
		const sim = nextPacket / 1000;
		timeline.push( state( sim ), nextPacket + ( Math.round( nextPacket / 25 ) % 2 ? 3 : 0 ) );
		timeline.push( state( sim ), nextPacket + 4 ); // Duplicates cannot alter the clock.
		nextPacket += 25;
	}
	const sample = timeline.sample( wall );
	timeline.apply( body, 'drone', sample );
	timeline.apply( camera, 'camera:drone', sample );
	timeline.apply( hull, 'hull', sample );
	assert.ok( Math.abs( camera.position.x - body.position.x - .2 ) < 1e-12 );
	assert.ok( Math.abs( hull.position.x - body.position.x - .4 ) < 1e-12 );
	if ( previous !== null && wall > 200 ) maxStepError = Math.max( maxStepError, Math.abs( body.position.x - previous - .04 ) );
	previous = body.position.x;
}
assert.ok( maxStepError < .003, `25 FPS presentation step error ${ maxStepError }` );
const stalled = timeline.sample( 10000 );
assert.equal( stalled.time, timeline.frames.at( -1 ).time ); // No speculative physics after stalls.
timeline.push( state( 0 ), 10001 );
assert.equal( timeline.frames.length, 1 );
assert.equal( timeline.sample( 10001 ).time, 0 );
const packets = [], keys = new Set( [ 'KeyW', 'KeyE' ] );
const op = { active:true, mode:'drone', state:{ ready:true }, suppressedKeys:new Set( [ 'KeyE' ] ),
	app:{ input:{ down:code => keys.has( code ) } }, bridge:{ installed:true, send:p => packets.push(p) } };
FlightOperations.prototype._sendDroneKeys.call( op );
assert.deepEqual( packets.at( -1 ).keys, [ 'KeyW' ] );
keys.clear(); FlightOperations.prototype._sendDroneKeys.call( op );
assert.deepEqual( packets.at( -1 ).keys, [] );
assert.equal( op.suppressedKeys.size, 0 );
console.log( `25 FPS pose interpolation, synchronized camera/hull, reset, duplicate and stale packets, immediate key transitions passed; max step error ${ ( maxStepError * 1000 ).toFixed(3) } mm` );
