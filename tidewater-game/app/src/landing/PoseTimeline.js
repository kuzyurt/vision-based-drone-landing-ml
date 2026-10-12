import { Matrix4, Vector3, Quaternion } from '../engine/index.js';

// Render authoritative samples on a continuous simulation clock. This never
// predicts forces or feeds interpolated values back into PX4/MuJoCo.
export class PoseTimeline {

	constructor( delay = .075 ) {

		this.delay = delay;
		this.frames = [];
		this.clock = null;
		this.lastWall = null;
		this.rate = 1;
		this.lastPresentation = - Infinity;
		this.matrix = new Matrix4();

	}

	push( state, now ) {

		if ( ! Number.isFinite( state.time_s ) || ! state.bodies || ! state.views ) return;
		const last = this.frames.at( - 1 );
		if ( last && state.time_s === last.time ) return; // Duplicate telemetry is not a new pose.
		if ( last && state.time_s < last.time ) this.reset();
		this.advance( now );
		this.rate = Math.max( .05, Math.min( 1.5, state.realtime_factor ?? 1 ) );
		if ( this.clock === null ) this.clock = state.time_s;
		else this.clock += Math.max( - .025, Math.min( .025, state.time_s - this.clock ) ) * .15;
		const poses = new Map();
		const add = ( name, values ) => {
			const pose = { position: new Vector3(), quaternion: new Quaternion(), scale: new Vector3() };
			this.matrix.set( ...values ).decompose( pose.position, pose.quaternion, pose.scale );
			poses.set( name, pose );
		};
		for ( const [ name, values ] of state.bodies ) add( name, values );
		for ( const [ name, view ] of Object.entries( state.views ) ) add( `camera:${ name }`, view.matrix );
		if ( state.hull_pose ) add( 'hull', state.hull_pose );
		this.frames.push( { time: state.time_s, poses } );
		if ( this.frames.length > 16 ) this.frames.shift();

	}

	advance( now ) {

		if ( this.lastWall !== null && this.clock !== null ) this.clock += Math.max( 0, now - this.lastWall ) / 1000 * this.rate;
		this.lastWall = now;

	}

	sample( now ) {

		if ( ! this.frames.length ) return null;
		this.advance( now );
		const latest = this.frames.at( - 1 );
		const time = Math.min( latest.time, Math.max( this.frames[ 0 ].time, this.lastPresentation, this.clock - this.delay * this.rate ) );
		this.lastPresentation = time;
		let a = this.frames[ 0 ], b = a;
		for ( const frame of this.frames ) {
			b = frame;
			if ( frame.time >= time ) break;
			a = frame;
		}
		const alpha = b.time > a.time ? Math.max( 0, Math.min( 1, ( time - a.time ) / ( b.time - a.time ) ) ) : 1;
		return { a, b, alpha, time };

	}

	apply( object, name, sample ) {

		const a = sample.a.poses.get( name ), b = sample.b.poses.get( name );
		if ( ! a || ! b ) return false;
		object.position.copy( a.position ).lerp( b.position, sample.alpha );
		object.quaternion.copy( a.quaternion ).slerp( b.quaternion, sample.alpha );
		if ( object.scale ) object.scale.copy( a.scale ).lerp( b.scale, sample.alpha );
		return true;

	}

	reset() {

		this.frames.length = 0;
		this.clock = null;
		this.lastWall = null;
		this.lastPresentation = - Infinity;

	}

}
