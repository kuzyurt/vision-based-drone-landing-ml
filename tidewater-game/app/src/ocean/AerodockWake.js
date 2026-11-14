import { Vector2 } from '../engine/index.js';
import { GPU, UniformBlock, Texture, StorageBuffer, ShaderModule, ComputeKernel, commonModule } from '../engine/webgpu.js';

// Visual wake for the CAD AERODOCK in the flight simulation.
//
// The flight water is the four-wave field that MuJoCo also uses for buoyancy, so nothing here
// changes the vertex height or water queries: the wake is purely optical (surface normal slopes,
// turbulent wake slick / roughness modulation, subsurface turquoise aeration, and multi-scale
// foam) laid over the rendered surface while landingWaves is enabled.
//
// Simulation (512^2 toroidal grid, 0.20 m cells, 102.4 m window):
//   1. Row pass: per-cell physics (hull pressure forcing P, 2D slipstream velocity & semi-Lagrangian
//      advection, twin propeller wash & streaky transom churn, bow wave curl, turbulent boil
//      forcing, nonlinear foam decay & mottled aeration, convex eddy viscosity), writes
//      aerodockMask (foam, aeration, slopeX, slopeZ), and runs forward 1D FFT along X.
//   2. Column pass: forward 1D FFT along Z, exact dispersive water-wave operator L(k) = k tanh(k H)
//      with smooth high-k dealiasing roll-off, and inverse 1D FFT along Z.
//   3. Inverse row pass: inverse 1D FFT along X, symplectic Euler step for (h, w) with finite
//      clamping, and quadratic sponge absorption at the window edges.

const N = 512;
const LOG2N = 9;
const HALF = N / 2;
const MASK = N - 1;
const CELL = 0.20; // m (102.4 m window)
const SIZE = N * CELL;
const SPONGE = 26; // cells of perimeter sponge absorption
const SETTLE_TIME = 32; // s of calm before compute sleeps

const WAKE_G = 7.2;
const WAKE_DEPTH = 4.2;

const f = ( x ) => {

	const s = String( x );
	return /[.e]/.test( s ) ? s : s + '.0';

};

export class AerodockWake {

	constructor( renderer ) {

		this.renderer = renderer;

		const K = this.kernelParams = new UniformBlock( 'AerodockWakeKernel', {
			origin: [ 'vec2f', new Vector2() ],
			prev: [ 'vec2f', new Vector2() ],
			center: [ 'vec2f', new Vector2() ],
			boatPos: [ 'vec2f', new Vector2() ],
			fwd: [ 'vec2f', new Vector2( 0, 1 ) ],
			right: [ 'vec2f', new Vector2( 1, 0 ) ],
			vel: [ 'vec2f', new Vector2() ],
			propThrust: [ 'vec2f', new Vector2() ],
			speed: [ 'f32', 0 ],
			fwdSpeed: [ 'f32', 0 ],
			latSpeed: [ 'f32', 0 ],
			yawRate: [ 'f32', 0 ],
			amount: [ 'f32', 0 ],
			dt: [ 'f32', 1 / 60 ],
			reset: [ 'f32', 1 ],
		}, { label: 'aerodock wake kernel' } );

		const R = this.readerParams = new UniformBlock( 'AerodockWakeParams', {
			origin: 'vec2f',
			center: 'vec2f',
			boatPos: 'vec2f',
			fwd: 'vec2f',
			right: 'vec2f',
			vel: 'vec2f',
			propThrust: 'vec2f',
			speed: 'f32',
			fwdSpeed: 'f32',
			latSpeed: 'f32',
			yawRate: 'f32',
			amount: 'f32',
		}, { label: 'aerodock wake params' } );
		for ( const k of R.order ) R.fields[ k ] = K.fields[ k ];

		// (h, w, foam, turb)
		this.state = new StorageBuffer( { label: 'aerodockWakeState', count: N * N, type: 'vec4f' } );
		this.scratch = new StorageBuffer( { label: 'aerodockWakeScratch', count: N * N, type: 'vec4f' } );
		// 2D Fourier transform of (h + P)
		this.spec = new StorageBuffer( { label: 'aerodockWakeSpec', count: N * N, type: 'vec2f' } );
		// (velX, velZ, aeration, unused)
		this.auxA = new StorageBuffer( { label: 'aerodockWakeAuxA', count: N * N, type: 'vec4f' } );
		this.auxB = new StorageBuffer( { label: 'aerodockWakeAuxB', count: N * N, type: 'vec4f' } );

		this.mask = new Texture( {
			label: 'aerodockWakeMask', width: N, height: N, format: 'rgba16float',
			usage: [ 'sample', 'storage' ], sampler: 'linearRepeat',
		} );

		this.amount = K.fields.amount;
		this.center = new Vector2( 0, 0 );
		this.hasWindow = false;

		this._fwd = new Vector2( 0, 1 );
		this._right = new Vector2( 1, 0 );
		this._prevPos = new Vector2();
		this._vel = new Vector2();
		this._hasPrev = false;
		this._heading = null;
		this._speed = 0;
		this._fwdSpeed = 0;
		this._latSpeed = 0;
		this._fwdAccel = 0;
		this._yawRate = 0;
		this._portThrust = 0;
		this._stbdThrust = 0;
		this._idleTime = 1e9;
		this._everActive = false;

		this._portProp = null;
		this._stbdProp = null;
		this._prevPortSpin = null;
		this._prevStbdSpin = null;
		this._portSpinRate = 0;
		this._stbdSpinRate = 0;

		this._buildKernel();
		this._buildReader();

	}

	_buildKernel() {

		this.commonModule = new ShaderModule( {
			name: 'aerodockWakeCommon',
			deps: [ commonModule ],
			code: /* wgsl */`
const AW_N: u32 = ${ N }u;
const AW_HALF: u32 = ${ HALF }u;
const AW_MASK: i32 = ${ MASK }i;
const AW_UMASK: u32 = ${ MASK }u;
const AW_LOG2N: u32 = ${ LOG2N }u;
const AW_CELL: f32 = ${ f( CELL ) };
const AW_SIZE: f32 = ${ f( SIZE ) };

fn awFinite( x: f32, lo: f32, hi: f32 ) -> f32 {
	if ( x != x ) { return 0.0; }
	return clamp( x, lo, hi );
}

fn awSanitize4( v: vec4f, lo: vec4f, hi: vec4f ) -> vec4f {
	if ( any( v != v ) ) { return vec4f( 0.0 ); }
	return clamp( v, lo, hi );
}

fn awSafeNorm( v: vec2f ) -> vec2f {
	let l2 = dot( v, v );
	if ( l2 <= 1e-10 || l2 != l2 ) { return vec2f( 0.0 ); }
	return v * inverseSqrt( l2 );
}

fn awHash( ix: i32, iy: i32 ) -> f32 {
	var v = ( u32( ix ) * 0x8da6b343u ) ^ ( u32( iy ) * 0xd8163841u );
	v = ( v ^ ( v >> 13u ) ) * 0x5bd1e995u;
	v = v ^ ( v >> 15u );
	return f32( v >> 8u ) * ( 1.0 / 16777216.0 );
}

fn awNoise( q: vec2f ) -> f32 {
	let i = floor( q );
	let fr = q - i;
	let u = fr * fr * ( 3.0 - 2.0 * fr );
	let ix = i32( i.x ); let iy = i32( i.y );
	let a = awHash( ix, iy ); let b = awHash( ix + 1, iy );
	let c = awHash( ix, iy + 1 ); let d = awHash( ix + 1, iy + 1 );
	return mix( mix( a, b, u.x ), mix( c, d, u.x ), u.y );
}

fn awNoiseGrad( q: vec2f ) -> vec3f {
	let i = floor( q );
	let fr = q - i;
	let u = fr * fr * fr * ( fr * ( fr * 6.0 - 15.0 ) + 10.0 );
	let du = 30.0 * fr * fr * ( fr * ( fr - 2.0 ) + 1.0 );
	let ix = i32( i.x ); let iy = i32( i.y );
	let a = awHash( ix, iy ); let b = awHash( ix + 1, iy );
	let c = awHash( ix, iy + 1 ); let d = awHash( ix + 1, iy + 1 );
	let k1 = b - a;
	let k2 = c - a;
	let k3 = a - b - c + d;
	let val = a + k1 * u.x + k2 * u.y + k3 * u.x * u.y;
	let gx = ( k1 + k3 * u.y ) * du.x;
	let gy = ( k2 + k3 * u.x ) * du.y;
	return vec3f( val, gx, gy );
}

// Signed distance (m) to the AERODOCK waterline and smooth hull immersion depth (m).
// Boat frame: bx = starboard (+), bz = forward (+); transom at bz = -1.16, stem at bz = +1.18.
fn awHullShape( bx: f32, bz: f32 ) -> vec2f {
	let bowT = sat( ( bz - 0.42 ) / 0.76 );
	let sternT = sat( ( - 0.96 - bz ) / 0.22 );
	let halfW = 0.53 * ( 1.0 - 0.86 * bowT * sqrt( bowT ) - 0.05 * sternT * sternT );
	let zc = bz - 0.01;
	let q = vec2f( abs( bx ) - max( halfW - 0.08, 0.01 ), abs( zc ) - 1.09 );
	let sd = length( max( q, vec2f( 0.0 ) ) ) + min( max( q.x, q.y ), 0.0 ) - 0.08;
	let imm = 0.22 * smoothstep( 0.04, - 0.22, sd ) * smoothstep( - 1.18, - 0.82, bz ) * smoothstep( 1.22, 0.52, bz );
	return vec2f( sd, imm );
}
`,
		} );

		const sim = new ShaderModule( {
			name: 'aerodockWakeSim',
			deps: [ this.commonModule ],
			uniforms: this.kernelParams,
			uniformName: 'aw',
			bindings: {
				trailState: { storage: this.state, access: 'read_write' },
				trailScratch: { storage: this.scratch, access: 'read_write' },
				trailSpec: { storage: this.spec, access: 'read_write' },
				trailAuxA: { storage: this.auxA, access: 'read_write' },
				trailAuxB: { storage: this.auxB, access: 'read_write' },
			},
			code: /* wgsl */`
fn awBrev( v: u32 ) -> u32 { return reverseBits( v ) >> ( 32u - AW_LOG2N ); }
fn awWorldIndex( i: i32, o: i32 ) -> i32 { return o + ( ( i - o ) & AW_MASK ); }

fn awInPrevWindow( I: i32, J: i32 ) -> bool {
	let ox = i32( aw.prev.x );
	let oy = i32( aw.prev.y );
	return aw.reset < 0.5 && I >= ox && I < ox + i32( AW_N ) && J >= oy && J < oy + i32( AW_N );
}

fn awLoadStateWorld( I: i32, J: i32 ) -> vec4f {
	if ( ! awInPrevWindow( I, J ) ) { return vec4f( 0.0 ); }
	let c = u32( I & AW_MASK );
	let r = u32( J & AW_MASK );
	return awSanitize4( trailState[ r * AW_N + c ], vec4f( - 0.35, - 1.8, 0.0, 0.0 ), vec4f( 0.35, 1.8, 3.0, 3.0 ) );
}

fn awLoadAuxWorld( I: i32, J: i32 ) -> vec4f {
	if ( ! awInPrevWindow( I, J ) ) { return vec4f( 0.0 ); }
	let c = u32( I & AW_MASK );
	let r = u32( J & AW_MASK );
	return awSanitize4( trailAuxA[ r * AW_N + c ], vec4f( - 2.5, - 2.5, 0.0, 0.0 ), vec4f( 2.5, 2.5, 3.0, 3.0 ) );
}

fn awLoadState( c: u32, r: u32 ) -> vec4f {
	let I = awWorldIndex( i32( c ), i32( aw.origin.x ) );
	let J = awWorldIndex( i32( r ), i32( aw.origin.y ) );
	return awLoadStateWorld( I, J );
}

fn awLoadAux( c: u32, r: u32 ) -> vec4f {
	let I = awWorldIndex( i32( c ), i32( aw.origin.x ) );
	let J = awWorldIndex( i32( r ), i32( aw.origin.y ) );
	return awLoadAuxWorld( I, J );
}

fn awCellPos( c: u32, r: u32 ) -> vec2f {
	let I = awWorldIndex( i32( c ), i32( aw.origin.x ) );
	let J = awWorldIndex( i32( r ), i32( aw.origin.y ) );
	return vec2f( f32( I ) + 0.5, f32( J ) + 0.5 ) * AW_CELL;
}

fn awSampleStateAt( p: vec2f ) -> vec4f {
	let gc = p / AW_CELL - 0.5;
	let fl = floor( gc );
	let fr = gc - fl;
	let i0 = i32( fl.x );
	let j0 = i32( fl.y );
	let s00 = awLoadStateWorld( i0, j0 );
	let s10 = awLoadStateWorld( i0 + 1, j0 );
	let s01 = awLoadStateWorld( i0, j0 + 1 );
	let s11 = awLoadStateWorld( i0 + 1, j0 + 1 );
	return mix( mix( s00, s10, fr.x ), mix( s01, s11, fr.x ), fr.y );
}

fn awSampleAuxAt( p: vec2f ) -> vec4f {
	let gc = p / AW_CELL - 0.5;
	let fl = floor( gc );
	let fr = gc - fl;
	let i0 = i32( fl.x );
	let j0 = i32( fl.y );
	let a00 = awLoadAuxWorld( i0, j0 );
	let a10 = awLoadAuxWorld( i0 + 1, j0 );
	let a01 = awLoadAuxWorld( i0, j0 + 1 );
	let a11 = awLoadAuxWorld( i0 + 1, j0 + 1 );
	return mix( mix( a00, a10, fr.x ), mix( a01, a11, fr.x ), fr.y );
}

fn awTwiddle( t: u32, s: u32, dir: f32 ) -> vec2f {
	let half = 1u << s;
	let pos = t & ( half - 1u );
	let ang = f32( pos ) * ( dir * PI / f32( half ) );
	return vec2f( cos( ang ), sin( ang ) );
}

fn awStageIndex( t: u32, s: u32 ) -> u32 {
	let half = 1u << s;
	return ( ( t >> s ) << ( s + 1u ) ) | ( t & ( half - 1u ) );
}

fn awCmul( b: vec2f, w: vec2f ) -> vec2f {
	return vec2f( b.x * w.x - b.y * w.y, b.x * w.y + b.y * w.x );
}
`,
		} );

		const stages = ( sh, dir ) => /* wgsl */`
	for ( var s = 0u; s < AW_LOG2N; s++ ) {
		let half = 1u << s;
		let i = awStageIndex( t, s );
		let j = i + half;
		let w = awTwiddle( t, s, ${ f( dir ) } );
		let a = ${ sh }[ i ];
		let bw = awCmul( ${ sh }[ j ], w );
		${ sh }[ i ] = a + bw;
		${ sh }[ j ] = a - bw;
		workgroupBarrier();
	}
`;

		const cellPhysics = /* wgsl */`
fn awCell( col: u32, row: u32 ) -> f32 {
	let dt = clamp( aw.dt, 1.0 / 240.0, 1.0 / 25.0 );
	let idx = row * AW_N + col;
	let p = awCellPos( col, row );

	let cL = ( col + AW_UMASK ) & AW_UMASK;
	let cR = ( col + 1u ) & AW_UMASK;
	let rD = ( row + AW_UMASK ) & AW_UMASK;
	let rU = ( row + 1u ) & AW_UMASK;

	let sC = awLoadState( col, row );
	let sL = awLoadState( cL, row );
	let sR = awLoadState( cR, row );
	let sD = awLoadState( col, rD );
	let sU = awLoadState( col, rU );

	let aC = awLoadAux( col, row );
	let aL = awLoadAux( cL, row );
	let aR = awLoadAux( cR, row );
	let aD = awLoadAux( col, rD );
	let aU = awLoadAux( col, rU );

	let rel = p - aw.boatPos;
	let bx = dot( rel, aw.right );
	let bz = dot( rel, aw.fwd );
	let time = frame.time;

	let hs = awHullShape( bx, bz );
	let sd = hs.x;
	let Ph = hs.y;

	// ---- Hull pressure forcing P(bx, bz) for the spectral Kelvin wave solver (after Havelock)
	let e = 0.32;
	let immF = awHullShape( bx, bz + e ).y;
	let immB = awHullShape( bx, bz - e ).y;
	let immR = awHullShape( bx + 0.24, bz ).y;
	let immL = awHullShape( bx - 0.24, bz ).y;
	let entry = max( ( immB - immF ) / ( 2.0 * e ), 0.0 );
	let sideSlope = ( immL - immR ) / 0.48;

	let spd = aw.speed;
	let fwdSpd = max( aw.fwdSpeed, 0.0 );
	let meanThrust = 0.5 * ( aw.propThrust.x + aw.propThrust.y );
	let moveFac = smoothstep( 0.04, 0.40, spd + meanThrust * 0.35 );
	let dynHead = ( 0.32 * fwdSpd * fwdSpd + 0.16 * spd ) * moveFac;
	let latPush = clamp( aw.latSpeed - bz * aw.yawRate * 0.65, - 1.2, 1.2 );

	// Transom separation hollow behind bz = -1.16 m
	let behind = - 1.16 - bz;
	let hollowLen = 0.35 + 0.35 * spd;
	let transomImm = awHullShape( bx, - 0.92 ).y;
	let hollow = transomImm * exp( - max( behind, 0.0 ) / hollowLen ) * smoothstep( - 0.24, 0.24, behind ) * smoothstep( 0.15, 1.1, fwdSpd );

	let P = clamp( ( max( Ph * 0.65, hollow * 0.55 ) + entry * dynHead + sideSlope * latPush * 0.14 ) * moveFac, - 0.25, 0.25 );

	// On reset, initialize the forced depression under the hull so starting doesn't ring
	let hAvg = 0.25 * ( sL.x + sR.x + sD.x + sU.x );
	let h = select( mix( sC.x, hAvg, 0.025 ), - P, aw.reset > 0.5 );
	let w = sC.y;

	let gx = ( sR.x - sL.x ) * ( 1.0 / ( 2.0 * AW_CELL ) );
	let gz = ( sU.x - sD.x ) * ( 1.0 / ( 2.0 * AW_CELL ) );
	let slope = length( vec2f( gx, gz ) );
	let outsideHull = smoothstep( - 0.02, 0.08, sd );
	let brk = sat( ( slope - 0.16 ) / 0.18 ) * outsideHull;

	// ---- 2D Slipstream Velocity & Divergence-Free Turbulent Swirl
	let turb = sC.w;
	let g1 = awNoiseGrad( p * 1.10 + vec2f( time * 0.28, - time * 0.21 ) );
	let g2 = awNoiseGrad( p * 2.50 + vec2f( - time * 0.52 + 7.3, time * 0.41 + 3.1 ) );
	let curlDir = vec2f( - ( g1.z * 0.65 + g2.z * 0.35 ), g1.y * 0.65 + g2.y * 0.35 );
	let swirlVel = curlDir * min( turb * 0.35, 0.50 );

	let pBack = p - clamp( aC.xy + swirlVel, vec2f( - 2.2 ), vec2f( 2.2 ) ) * dt;
	let sAdv = awSampleStateAt( pBack );
	let aAdv = awSampleAuxAt( pBack );

	let velAvg = 0.25 * ( aL.xy + aR.xy + aD.xy + aU.xy );
	var vel = mix( aAdv.xy, velAvg, clamp( dt * ( 1.6 + turb * 3.0 ), 0.0, 0.30 ) ) * exp( - dt / 4.0 );

	// ---- Propeller Wash & Transom Wake (WakeSim-style streaky/mottled plume + twin-jet structure)
	let turnDeflect = clamp( - aw.yawRate * 0.22 + aw.latSpeed * 0.16, - 0.42, 0.42 );
	let bxTurn = bx - turnDeflect * max( behind, 0.0 ) * 0.35;
	let washW = max( behind, 0.0 ) * 0.11 + 0.34;
	let inWash = smoothstep( - 0.35, 0.22, behind ) * smoothstep( 5.2, 1.0, behind ) * smoothstep( washW, washW * 0.22, abs( bxTurn ) );

	// Twin-propeller lobes at bx = +/-0.205 m right behind the transom that merge into the wash
	let dProp = max( behind - 0.08, 0.0 );
	let propR = 0.12 + 0.11 * dProp;
	let pLobe0 = exp( - ( ( bxTurn + 0.205 ) * ( bxTurn + 0.205 ) ) / ( propR * propR ) ) * aw.propThrust.x;
	let pLobe1 = exp( - ( ( bxTurn - 0.205 ) * ( bxTurn - 0.205 ) ) / ( propR * propR ) ) * aw.propThrust.y;
	let twinFocus = mix( ( pLobe0 + pLobe1 ) * 0.85, meanThrust, smoothstep( 0.15, 1.8, dProp ) );

	// Backward slipstream velocity behind the propellers
	if ( behind > - 0.25 && behind < 3.5 && abs( bxTurn ) < 1.6 && meanThrust > 0.01 ) {
		let jetEnv = smoothstep( - 0.20, 0.18, behind ) * exp( - dProp / 1.45 ) * smoothstep( washW * 1.1, 0.0, abs( bxTurn ) );
		let jetDir = awSafeNorm( - aw.fwd + aw.right * ( turnDeflect * 0.38 + bxTurn * 0.24 ) );
		vel += jetDir * ( ( 0.85 + 1.10 * twinFocus ) * jetEnv * dt * 4.0 );
	}

	let streak = awNoise( vec2f( bxTurn * 3.4, time * 1.3 ) );
	let patchN = awNoise( p * 0.95 + time * 0.16 );
	let race = smoothstep( 4.2, 0.0, behind ) * 0.95;

	// Fixed water-space streaks stretched along the boat track so the plume is laid down as
	// ragged longitudinal streaks rather than a uniform ribbon
	let along = dot( p, aw.fwd );
	let across = dot( p, aw.right );
	let streaks = awNoise( vec2f( along * 0.32, across * 2.2 ) ) * 0.68 + awNoise( vec2f( along * 0.78, across * 4.6 ) + 5.3 ) * 0.32;
	let mottle = clamp( ( streaks - 0.5 ) * 3.2, - 0.85, 0.85 ) + 1.0;

	let washDrive = twinFocus * 1.25 + smoothstep( 0.15, 1.4, spd ) * 0.55;
	let washGen = inWash * washDrive * ( streak * patchN * 0.65 + race + 0.12 ) * mix( mottle, 1.0, smoothstep( 2.2, 0.0, behind ) * 0.55 );

	// ---- Bow Wave & Forward Shoulder Spray (rolls off the pointed bow wedge and forward cheeks)
	let nearBow = smoothstep( 0.42, - 0.02, sd ) * smoothstep( - 0.04, 0.04, sd );
	let bowBand = nearBow * smoothstep( - 0.45, 0.38, bz ) * smoothstep( 1.26, 0.82, bz );
	let sideSign = select( - 1.0, 1.0, bx >= 0.0 );
	let turnBias = clamp( 1.0 + sideSign * ( aw.latSpeed * 0.70 - aw.yawRate * 0.38 ), 0.55, 1.60 );
	let bowDrive = smoothstep( 0.15, 1.35, spd ) * turnBias;
	let bowGen = bowBand * bowDrive * ( awNoise( vec2f( bz * 3.2, time * 3.0 ) ) * 1.35 + 0.18 ) * 0.95;

	if ( bowBand > 0.01 && spd > 0.08 ) {
		vel += ( aw.right * ( sideSign * 0.45 ) + aw.fwd * 0.15 ) * ( bowBand * spd * dt * 3.5 );
	}

	vel = clamp( vel, vec2f( - 2.2 ), vec2f( 2.2 ) );

	// ---- Turbulent Eddy Viscosity & Mass-Conserving Surface Boils on w
	// Strictly convex spatial blend (alpha in [0, 0.25]) -> unconditionally stable for any cell size
	let wAvg = 0.25 * ( sL.y + sR.y + sD.y + sU.y );
	let viscAlpha = clamp( dt * ( 0.8 + min( turb, 1.5 ) * 4.5 ), 0.0, 0.25 );
	let wVisc = mix( w, wAvg, viscAlpha );

	// Laplacian boil forcing: zero net volume, excites circular ring ripples in the turbulent wash
	var boil = 0.0;
	if ( turb + sL.w + sR.w + sD.w + sU.w > 0.02 ) {
		let drift = vec2f( time * 0.55, - time * 0.38 );
		let bScale = 1.15;
		let c0 = ( awNoise( p * bScale + drift ) - 0.5 ) * min( turb, 1.4 );
		boil = ( awNoise( ( p - vec2f( AW_CELL, 0.0 ) ) * bScale + drift ) - 0.5 ) * min( sL.w, 1.4 )
			+ ( awNoise( ( p + vec2f( AW_CELL, 0.0 ) ) * bScale + drift ) - 0.5 ) * min( sR.w, 1.4 )
			+ ( awNoise( ( p - vec2f( 0.0, AW_CELL ) ) * bScale + drift ) - 0.5 ) * min( sD.w, 1.4 )
			+ ( awNoise( ( p + vec2f( 0.0, AW_CELL ) ) * bScale + drift ) - 0.5 ) * min( sU.w, 1.4 )
			- c0 * 4.0;
	}
	let w1 = awFinite( ( wVisc + boil * ( dt * 0.85 ) ) * exp( - dt * 0.015 ), - 1.8, 1.8 );

	// ---- Foam Evolution: thick churn thins quickly (-0.55 * f^2), ragged lace lingers
	let foamAvg = 0.25 * ( sL.z + sR.z + sD.z + sU.z );
	let alphaFoam = clamp( dt * ( 1.4 + turb * 3.8 ), 0.0, 0.28 );
	let f0 = max( mix( sAdv.z, foamAvg, alphaFoam ), 0.0 );

	let gen = ( washGen * 1.45 + bowGen * 1.25 + brk * 2.2 );
	let breakup = awNoise( p * 0.42 + vec2f( 13.1, 7.3 ) ) * 0.65 + awNoise( p * 1.35 + vec2f( 3.7, 1.9 ) ) * 0.35;
	let clr = smoothstep( 0.28, 0.72, breakup ) * 2.6 + 0.22;
	let foam1 = awFinite( f0 * exp( - dt * ( f0 * f0 * 0.55 + clr / 18.0 ) ) + gen * dt, 0.0, 2.6 );

	// ---- Turbulence & Subsurface Aeration Evolution
	let turbAvg = 0.25 * ( sL.w + sR.w + sD.w + sU.w );
	let t0 = max( mix( sAdv.w, turbAvg, clamp( dt * 2.2, 0.0, 0.28 ) ), 0.0 );
	let turb1 = awFinite( t0 * exp( - dt / 6.0 ) + ( inWash * washDrive * 0.85 + bowGen * 0.45 + brk * 3.0 ) * dt, 0.0, 2.5 );

	let aerAvg = 0.25 * ( aL.z + aR.z + aD.z + aU.z );
	let a0 = max( mix( aAdv.z, aerAvg, clamp( dt * ( 2.2 + turb * 4.5 ), 0.0, 0.32 ) ), 0.0 );
	let wA = washW * ( awNoise( p * 0.55 + time * 0.06 ) * 0.75 + 0.82 );
	let aerBand = smoothstep( - 0.35, 0.25, behind ) * smoothstep( 6.5, 1.4, behind ) * smoothstep( wA, wA * 0.20, abs( bxTurn ) );
	let aerGen = aerBand * washDrive * ( ( race * 1.1 + 0.15 ) * ( patchN * 1.2 + streak * 0.5 + 0.1 ) ) * ( mottle * mottle * 0.55 ) + bowGen * 0.55 + brk * 1.2;
	let rise = smoothstep( 0.25, 0.75, breakup * 0.6 + patchN * 0.4 ) * 1.3 + 0.45;
	let aer1 = awFinite( a0 * exp( - dt * ( a0 * 0.08 + rise / 18.0 ) ) + aerGen * dt, 0.0, 2.5 );

	trailScratch[ idx ] = vec4f( h, w1, foam1, turb1 );
	trailAuxB[ idx ] = vec4f( vel.x, vel.y, aer1, 0.0 );

	// Mask out the forced depression slope directly under the hull while keeping the free Kelvin
	// waves and adding turbulent boil slopes in the propeller wash
	let hullMask = smoothstep( - 0.06, 0.10, sd );
	let boilAmp = min( turb1 * 0.055 + foam1 * 0.035, 0.16 ) * hullMask;
	let boilSlope = vec2f( g1.y * 0.55 + g2.y * 0.45, g1.z * 0.55 + g2.z * 0.45 ) * boilAmp;
	let outSlope = clamp( vec2f( gx, gz ) * ( 1.45 * hullMask ) + boilSlope, vec2f( - 0.35 ), vec2f( 0.35 ) );

	textureStore( trailOut, vec2u( col, row ), vec4f( foam1, aer1, outSlope.x, outSlope.y ) );

	return awFinite( h + P, - 0.45, 0.45 );
}
`;

		this.rowKernel = new ComputeKernel( {
			label: 'Aerodock Wake Rows',
			modules: [ sim ],
			bindings: {
				trailOut: { storageTexture: this.mask, access: 'write' },
			},
			workgroupSize: [ HALF, 1, 1 ],
			code: cellPhysics + /* wgsl */`
var<workgroup> shRow: array<vec2f, ${ N }>;

@compute @workgroup_size( WG_X, 1, 1 )
fn main( @builtin( local_invocation_id ) lid: vec3u, @builtin( workgroup_id ) wid: vec3u ) {
	let t = lid.x;
	let row = wid.x;
	for ( var e = 0u; e < 2u; e++ ) {
		let col = t + e * AW_HALF;
		shRow[ awBrev( col ) ] = vec2f( awCell( col, row ), 0.0 );
	}
	workgroupBarrier();
${ stages( 'shRow', - 1 ) }
	for ( var e = 0u; e < 2u; e++ ) {
		let col = t + e * AW_HALF;
		trailSpec[ row * AW_N + col ] = shRow[ col ];
	}
}
`,
		} );

		const dk = 2 * Math.PI / SIZE;
		const norm = 1 / ( N * N );

		this.colKernel = new ComputeKernel( {
			label: 'Aerodock Wake Columns',
			modules: [ sim ],
			workgroupSize: [ HALF, 1, 1 ],
			code: /* wgsl */`
var<workgroup> shCol: array<vec2f, ${ N }>;

@compute @workgroup_size( WG_X, 1, 1 )
fn main( @builtin( local_invocation_id ) lid: vec3u, @builtin( workgroup_id ) wid: vec3u ) {
	let t = lid.x;
	let col = wid.x;
	for ( var e = 0u; e < 2u; e++ ) {
		let r = t + e * AW_HALF;
		let v = trailSpec[ r * AW_N + col ];
		shCol[ awBrev( r ) ] = select( vec2f( 0.0 ), v, all( v == v ) );
	}
	workgroupBarrier();
${ stages( 'shCol', - 1 ) }
	let fx = f32( select( i32( col ) - i32( AW_N ), i32( col ), col < AW_HALF ) ) * ${ f( dk ) };
	var outs: array<vec2f, 2>;
	for ( var e = 0u; e < 2u; e++ ) {
		let r = t + e * AW_HALF;
		let fz = f32( select( i32( r ) - i32( AW_N ), i32( r ), r < AW_HALF ) ) * ${ f( dk ) };
		let k = length( vec2f( fx, fz ) );
		let kh = min( k * ${ f( WAKE_DEPTH ) }, 12.0 );
		let kr = k * ( 1.0 / 11.0 );
		let dealias = exp( - ( kr * kr ) * ( kr * kr ) );
		let op = k * tanh( kh ) * dealias * ${ f( norm ) };
		outs[ e ] = shCol[ r ] * op;
	}
	workgroupBarrier();
	for ( var e = 0u; e < 2u; e++ ) {
		let r = t + e * AW_HALF;
		shCol[ awBrev( r ) ] = outs[ e ];
	}
	workgroupBarrier();
${ stages( 'shCol', 1 ) }
	for ( var e = 0u; e < 2u; e++ ) {
		let r = t + e * AW_HALF;
		trailSpec[ r * AW_N + col ] = shCol[ r ];
	}
}
`,
		} );

		this.invKernel = new ComputeKernel( {
			label: 'Aerodock Wake Inverse',
			modules: [ sim ],
			workgroupSize: [ HALF, 1, 1 ],
			code: /* wgsl */`
var<workgroup> shRow: array<vec2f, ${ N }>;

@compute @workgroup_size( WG_X, 1, 1 )
fn main( @builtin( local_invocation_id ) lid: vec3u, @builtin( workgroup_id ) wid: vec3u ) {
	let t = lid.x;
	let row = wid.x;
	let dt = clamp( aw.dt, 1.0 / 240.0, 1.0 / 25.0 );
	for ( var e = 0u; e < 2u; e++ ) {
		let col = t + e * AW_HALF;
		let v = trailSpec[ row * AW_N + col ];
		shRow[ awBrev( col ) ] = select( vec2f( 0.0 ), v, all( v == v ) );
	}
	workgroupBarrier();
${ stages( 'shRow', 1 ) }
	let rl = f32( ( i32( row ) - i32( aw.origin.y ) ) & AW_MASK ) + 0.5;
	let ez = min( rl, f32( AW_N ) - rl );
	for ( var e = 0u; e < 2u; e++ ) {
		let col = t + e * AW_HALF;
		let idx = row * AW_N + col;
		let Lu = awFinite( shRow[ col ].x, - 2.0, 2.0 );
		let sc = trailScratch[ idx ];
		let w1 = awFinite( sc.y - Lu * ( dt * ${ f( WAKE_G ) } ), - 1.8, 1.8 );
		let h1 = awFinite( sc.x + w1 * dt, - 0.35, 0.35 );

		let cl = f32( ( i32( col ) - i32( aw.origin.x ) ) & AW_MASK ) + 0.5;
		let edge = min( min( cl, f32( AW_N ) - cl ), ez );
		let sig = smoothstep( ${ f( SPONGE ) }, 0.0, edge );
		let k = exp( - dt * ( sig * sig * 6.5 ) );
		let dampTrail = 1.0 - sig * sig * 0.15;

		trailState[ idx ] = vec4f( h1 * k, w1 * k, sc.z * dampTrail, sc.w * dampTrail );
		let aux = trailAuxB[ idx ];
		trailAuxA[ idx ] = vec4f( aux.xy * k, aux.z * dampTrail, 0.0 );
	}
}
`,
		} );

	}

	_buildReader() {

		this.module = new ShaderModule( {
			name: 'aerodockWake',
			deps: [ this.commonModule ],
			uniforms: this.readerParams,
			uniformName: 'aerodockWake',
			bindings: { aerodockMask: { texture: this.mask } },
			code: /* wgsl */`
struct AerodockWakeFrag {
	slopes: vec2f,
	coverage: f32,
	fresh: f32,
	aeration: f32,
	slick: f32,
	roughBoost: f32,
};

fn aerodockWakeOn() -> bool { return aerodockWake.amount > 1e-4; }

fn aerodockWakeEdgeDist( xz: vec2f ) -> f32 {
	let rel = abs( xz - aerodockWake.center );
	return AW_SIZE * 0.5 - max( rel.x, rel.y );
}

fn aerodockWakeSampleMask( xz: vec2f ) -> vec4f {
	let sRaw = textureSampleLevel( aerodockMask, smpLinearRepeat, fract( xz / AW_SIZE ), 0.0 );
	if ( any( sRaw != sRaw ) ) { return vec4f( 0.0 ); }
	return clamp( sRaw, vec4f( 0.0, 0.0, - 0.35, - 0.35 ), vec4f( 3.0, 3.0, 0.35, 0.35 ) );
}

// Backwards-compatible helpers
fn aerodockWakeTrail( xz: vec2f ) -> vec2f {
	if ( ! aerodockWakeOn() ) { return vec2f( 0.0 ); }
	let edge = aerodockWakeEdgeDist( xz );
	if ( edge <= 3.0 ) { return vec2f( 0.0 ); }
	let fade = smoothstep( 3.0, 22.0, edge ) * aerodockWake.amount;
	let s = aerodockWakeSampleMask( xz );
	return vec2f( s.x, s.y * 0.25 ) * fade;
}

fn aerodockWakeHull( xz: vec2f ) -> vec2f {
	return vec2f( 0.0 );
}

// Evaluates the simulated wake at world xz (foam, mottled subsurface aeration, wave & boil slopes)
fn aerodockWakeFragment( xz: vec2f, footprint: f32, waveH: f32 ) -> AerodockWakeFrag {
	var o: AerodockWakeFrag;
	o.slopes = vec2f( 0.0 );
	o.coverage = 0.0;
	o.fresh = 0.0;
	o.aeration = 0.0;
	o.slick = 0.0;
	o.roughBoost = 0.0;
	if ( ! aerodockWakeOn() ) { return o; }

	let edgeDist = aerodockWakeEdgeDist( xz );
	if ( edgeDist <= 3.0 ) { return o; }

	let amt = aerodockWake.amount;
	let fadeWave = smoothstep( 3.0, 14.0, edgeDist ) * amt;
	let fadeLong = smoothstep( 3.0, 28.0, edgeDist ) * amt;

	let s = aerodockWakeSampleMask( xz );
	let foamRaw = s.x * fadeLong;
	let aerRaw = s.y * fadeLong;
	var slopes = s.zw * fadeWave;

	// Sub-texel boil ripple detail inside active turbulence
	let activeBoil = sat( foamRaw * 0.45 + aerRaw * 0.25 ) * smoothstep( 0.14, 0.01, footprint );
	if ( activeBoil > 0.01 ) {
		let bg = awNoiseGrad( xz * 3.2 + vec2f( frame.time * 0.65, - frame.time * 0.48 ) );
		slopes += vec2f( bg.y, bg.z ) * ( activeBoil * 0.055 );
	}

	// Mottled subsurface aeration (WakeSim-style soft irregular cloud edges, subtle turquoise)
	var aerOut = 0.0;
	if ( aerRaw > 0.01 ) {
		let m = awNoise( xz * 0.55 + vec2f( frame.time * 0.03, 0.0 ) ) * 0.55 + awNoise( xz * 1.55 + 17.3 ) * 0.45;
		let aN = ( 1.0 - exp( - aerRaw * 0.55 ) ) * ( m * 0.8 + 0.6 );
		aerOut = smoothstep( m * 0.2 + 0.04, m * 0.2 + 0.58, aN ) * 0.18 * fadeLong;
	}

	let freshFrac = smoothstep( 0.35, 1.35, foamRaw );
	let slick = sat( aerRaw * 0.45 + foamRaw * 0.25 ) * ( 1.0 - freshFrac * 0.4 );

	o.slopes = clamp( slopes, vec2f( - 0.32 ), vec2f( 0.32 ) );
	o.coverage = awFinite( foamRaw, 0.0, 2.2 );
	o.fresh = awFinite( freshFrac, 0.0, 1.0 );
	o.aeration = awFinite( aerOut, 0.0, 0.22 );
	o.slick = awFinite( slick, 0.0, 0.80 );
	o.roughBoost = awFinite( freshFrac * 0.12, 0.0, 0.18 );
	return o;
}

// Shades the wake foam using FoamTexture (waterFoamTex) at boat-proportioned scales so thick
// propeller churn tears naturally into bubbly rafts, circular Worley holes, and dissolving lace.
fn aerodockWakeShadeFoam( xz: vec2f, footprint: f32, aw: AerodockWakeFrag, wf1: vec4f, wf2: vec4f ) -> f32 {
	let cov = sat( aw.coverage * 0.82 );
	if ( cov <= 1e-4 ) { return 0.0; }

	let pattern = wf1.x * 0.58 + wf2.x * 0.42;
	let bubbles = wf1.y * 0.45 + wf2.y * 0.55;
	let thresh = 1.03 - cov * 1.08;
	let soft = 0.09 + footprint * 0.12;
	let detail = smoothstep( thresh - soft, thresh + soft, pattern ) * ( bubbles * 0.28 + 0.76 );
	let far = smoothstep( 0.15, 1.0, footprint );
	return awFinite( mix( detail, cov * 0.80, far ), 0.0, 0.88 );
}
`,
		} );

	}

	_findPropGroups( group ) {

		const parent = group.parent;
		if ( ! parent ) return;
		if ( this._portProp && this._portProp.parent === parent && this._stbdProp && this._stbdProp.parent === parent ) return;
		this._portProp = null;
		this._stbdProp = null;
		for ( const ch of parent.children ) {

			if ( ch.name === 'Physics body port_prop' ) this._portProp = ch;
			else if ( ch.name === 'Physics body starboard_prop' ) this._stbdProp = ch;

		}

	}

	_dispatch() {

		GPU.computePass( 'Aerodock Wake', ( pass ) => {

			this.rowKernel.dispatch( N, { pass } );
			this.colKernel.dispatch( N, { pass } );
			this.invKernel.dispatch( N, { pass } );

		} );

	}

	// dt seconds; group is the rendered boat body (position in world space); active only with the
	// flight water (landingWater). sim is the latest physics state (optional): its boat velocity,
	// heading and motor powers drive the wake. Without it the wake falls back to guessing motion
	// from the drawn pose, which jumps whenever the physics briefly waits (ML inference), and from
	// the propeller angle, which can read as spinning on a boat that is standing still.
	update( dt, group, active, sim = null ) {

		if ( ! active || ! group || group.initialized === false ) {

			this.amount.value = Math.max( 0, this.amount.value - dt * 2.5 );
			this._hasPrev = false;
			this._heading = null;
			this._prevPortSpin = null;
			this._prevStbdSpin = null;
			this._simYaw = null;
			this._idleTime = 1e9;
			return;

		}

		const h = Math.min( Math.max( dt, 1 / 240 ), 1 / 25 );
		const p = group.position;

		this._findPropGroups( group );
		const portProp = this._portProp?.initialized ? this._portProp : null;
		const stbdProp = this._stbdProp?.initialized ? this._stbdProp : null;

		if ( ! this._hasPrev ) {

			this._prevPos.set( p.x, p.z );
			this._hasPrev = true;
			this._vel.set( 0, 0 );
			this._speed = 0;
			this._fwdSpeed = 0;
			this._latSpeed = 0;
			this._fwdAccel = 0;
			this._yawRate = 0;

		}

		const boat = sim?.boat;
		const physicsVelocity = boat && Array.isArray( boat.velocity ) && Number.isFinite( boat.velocity[ 0 ] ) && Number.isFinite( boat.velocity[ 2 ] ) ? boat.velocity : null;
		const jump = Math.hypot( p.x - this._prevPos.x, p.z - this._prevPos.y );
		const rawVx = physicsVelocity ? physicsVelocity[ 0 ] : ( p.x - this._prevPos.x ) / Math.max( dt, 1e-4 );
		const rawVz = physicsVelocity ? physicsVelocity[ 2 ] : ( p.z - this._prevPos.y ) / Math.max( dt, 1e-4 );
		this._prevPos.set( p.x, p.z );

		// A reset/teleport moves the boat metres in one frame; a pose that only catches up after a
		// short physics pause does not.
		if ( jump > 5 || ( ! physicsVelocity && Math.hypot( rawVx, rawVz ) > 25 ) ) {

			this._vel.set( 0, 0 );
			this._speed = 0;
			this._fwdSpeed = 0;
			this._latSpeed = 0;
			this._fwdAccel = 0;
			this._yawRate = 0;
			this.hasWindow = false;
			this.kernelParams.fields.reset.value = 1;

		} else {

			const vAlpha = Math.min( 1, dt / 0.085 );
			this._vel.x += ( rawVx - this._vel.x ) * vAlpha;
			this._vel.y += ( rawVz - this._vel.y ) * vAlpha;

		}

		// ---- Determine true hull heading (stern-to-bow) and starboard vector
		let fx = this._fwd.x, fz = this._fwd.y;
		let hasPoseHeading = false;

		if ( portProp && stbdProp ) {

			const pmx = 0.5 * ( portProp.position.x + stbdProp.position.x );
			const pmz = 0.5 * ( portProp.position.z + stbdProp.position.z );
			const dx = p.x - pmx;
			const dz = p.z - pmz;
			const dLen = Math.hypot( dx, dz );
			if ( dLen > 0.25 ) {

				fx = dx / dLen;
				fz = dz / dLen;
				hasPoseHeading = true;

			}

		}

		if ( ! hasPoseHeading ) {

			const rawSpd = Math.hypot( this._vel.x, this._vel.y );
			if ( rawSpd > 0.14 ) {

				fx = this._vel.x / rawSpd;
				fz = this._vel.y / rawSpd;
				hasPoseHeading = true;

			} else if ( group.quaternion ) {

				const q = group.quaternion;
				const qfx = 1 - 2 * ( q.y * q.y + q.z * q.z );
				const qfz = 2 * ( q.x * q.z + q.w * q.y );
				const qLen = Math.hypot( qfx, qfz );
				if ( qLen > 0.1 ) {

					fx = qfx / qLen;
					fz = qfz / qLen;
					hasPoseHeading = true;

				}

			}

		}

		const newHeading = Math.atan2( fx, fz );
		const simYaw = Number.isFinite( boat?.yaw ) && Number.isFinite( sim?.time_s ) ? boat.yaw : null;
		if ( simYaw !== null ) {

			// Turn rate from the physics heading over physics time: no render-frame jitter.
			if ( this._simYaw !== undefined && this._simYaw !== null && sim.time_s > this._simTime ) {

				let dYaw = simYaw - this._simYaw;
				while ( dYaw > Math.PI ) dYaw -= 2 * Math.PI;
				while ( dYaw < - Math.PI ) dYaw += 2 * Math.PI;
				const rawYawRate = Math.max( - 4.0, Math.min( 4.0, dYaw / ( sim.time_s - this._simTime ) ) );
				this._yawRate += ( rawYawRate - this._yawRate ) * Math.min( 1, ( sim.time_s - this._simTime ) / 0.10 );

			}
			if ( this._simYaw === undefined || this._simYaw === null || sim.time_s !== this._simTime ) {

				this._simYaw = simYaw;
				this._simTime = sim.time_s;

			}

		} else if ( this._heading !== null ) {

			let dYaw = newHeading - this._heading;
			while ( dYaw > Math.PI ) dYaw -= 2 * Math.PI;
			while ( dYaw < - Math.PI ) dYaw += 2 * Math.PI;
			const rawYawRate = Math.max( - 4.0, Math.min( 4.0, dYaw / Math.max( dt, 1e-4 ) ) );
			this._yawRate += ( rawYawRate - this._yawRate ) * Math.min( 1, dt / 0.10 );

		}

		this._heading = newHeading;
		this._fwd.set( Math.sin( newHeading ), Math.cos( newHeading ) );

		let rx = Math.cos( newHeading ), rz = - Math.sin( newHeading );
		if ( portProp && stbdProp ) {

			const sdx = stbdProp.position.x - portProp.position.x;
			const sdz = stbdProp.position.z - portProp.position.z;
			if ( sdx * rx + sdz * rz < 0 ) {

				rx = - rx;
				rz = - rz;

			}

		}

		this._right.set( rx, rz );

		// ---- Decompose velocity into hull frame & compute longitudinal acceleration
		const fwdVel = this._vel.x * this._fwd.x + this._vel.y * this._fwd.y;
		const latVel = this._vel.x * this._right.x + this._vel.y * this._right.y;
		const totalSpd = Math.hypot( this._vel.x, this._vel.y );

		const rawFwdAccel = Math.max( - 5.0, Math.min( 5.0, ( fwdVel - this._fwdSpeed ) / Math.max( dt, 1e-4 ) ) );
		this._fwdAccel += ( rawFwdAccel - this._fwdAccel ) * Math.min( 1, dt / 0.14 );
		this._fwdSpeed = fwdVel;
		this._latSpeed = latVel;
		this._speed = totalSpd;

		// ---- Propeller activity: the real motor powers when the physics state has them, otherwise
		// guessed from the port_prop & starboard_prop relative quaternions
		const portPower = Number.isFinite( boat?.port_power ) ? boat.port_power : null;
		const stbdPower = Number.isFinite( boat?.starboard_power ) ? boat.starboard_power : null;
		if ( portPower !== null && stbdPower !== null ) {

			// 0-100 % motor power -> the same 0-8 activity scale as the spin estimate (x0.32 later)
			this._portSpinRate += ( clamp( portPower / 100 * 7.8, 0, 8 ) - this._portSpinRate ) * Math.min( 1, dt / 0.12 );
			this._stbdSpinRate += ( clamp( stbdPower / 100 * 7.8, 0, 8 ) - this._stbdSpinRate ) * Math.min( 1, dt / 0.12 );
			this._prevPortSpin = null;
			this._prevStbdSpin = null;

		} else if ( portProp && stbdProp && group.quaternion ) {

			const bq = group.quaternion;
			const pq = portProp.quaternion;
			const sq = stbdProp.quaternion;
			const pDot = bq.x * pq.x + bq.y * pq.y + bq.z * pq.z + bq.w * pq.w;
			const sDot = bq.x * sq.x + bq.y * sq.y + bq.z * sq.z + bq.w * sq.w;
			if ( this._prevPortSpin !== null ) {

				const pStep = Math.abs( pDot - this._prevPortSpin ) / Math.max( dt, 1e-4 );
				const sStep = Math.abs( sDot - this._prevStbdSpin ) / Math.max( dt, 1e-4 );
				this._portSpinRate += ( Math.min( pStep, 8.0 ) - this._portSpinRate ) * Math.min( 1, dt / 0.12 );
				this._stbdSpinRate += ( Math.min( sStep, 8.0 ) - this._stbdSpinRate ) * Math.min( 1, dt / 0.12 );

			}

			this._prevPortSpin = pDot;
			this._prevStbdSpin = sDot;

		} else {

			this._portSpinRate *= Math.exp( - dt / 0.15 );
			this._stbdSpinRate *= Math.exp( - dt / 0.15 );

		}

		// ---- Effective port & starboard propeller thrust
		const cruiseDrive = Math.max( 0, fwdVel ) / 1.25 + Math.abs( Math.min( 0, fwdVel ) ) * 0.55;
		const accelDrive = Math.max( 0, this._fwdAccel ) * 0.70 - Math.max( 0, - this._fwdAccel ) * 0.28;
		const turnDrive = Math.abs( this._yawRate ) * 0.32;
		const turnDiff = clamp( this._yawRate * 0.26, - 0.42, 0.42 );

		const targetPort = clamp( Math.max( cruiseDrive + accelDrive + turnDrive + turnDiff, this._portSpinRate * 0.32 ), 0, 1.75 );
		const targetStbd = clamp( Math.max( cruiseDrive + accelDrive + turnDrive - turnDiff, this._stbdSpinRate * 0.32 ), 0, 1.75 );

		const tAlpha = Math.min( 1, dt / 0.12 );
		this._portThrust += ( targetPort - this._portThrust ) * tAlpha;
		this._stbdThrust += ( targetStbd - this._stbdThrust ) * tAlpha;

		const wakeActive = totalSpd > 0.06 || this._portThrust > 0.04 || this._stbdThrust > 0.04;
		if ( wakeActive ) {

			this._idleTime = 0;
			this._everActive = true;

		} else {

			this._idleTime += dt;

		}

		if ( ! this._everActive || this._idleTime > SETTLE_TIME ) {

			this.amount.value = Math.max( 0, this.amount.value - dt * 0.5 );
			return;

		}

		const settleFade = Math.min( 1, ( SETTLE_TIME - this._idleTime ) / 4.0 );
		this.amount.value += ( settleFade - this.amount.value ) * Math.min( 1, dt * 4.0 );

		// ---- Toroidal window management
		const lookBack = 16.0 / CELL;
		const targetCx = Math.round( p.x / CELL - this._fwd.x * lookBack );
		const targetCz = Math.round( p.z / CELL - this._fwd.y * lookBack );
		const bxCell = p.x / CELL;
		const bzCell = p.z / CELL;
		const c = this.center;

		this.kernelParams.fields.prev.value.copy( this.kernelParams.fields.origin.value );
		if ( ! this.hasWindow || Math.abs( bxCell - c.x ) > N * 0.75 || Math.abs( bzCell - c.y ) > N * 0.75 ) {

			c.set( targetCx, targetCz );
			this.hasWindow = true;
			this.kernelParams.fields.reset.value = 1;

		}

		const box = 115;
		if ( targetCx - c.x > box ) c.x = Math.ceil( targetCx - box );
		if ( c.x - targetCx > box ) c.x = Math.floor( targetCx + box );
		if ( targetCz - c.y > box ) c.y = Math.ceil( targetCz - box );
		if ( c.y - targetCz > box ) c.y = Math.floor( targetCz + box );

		this.kernelParams.fields.origin.value.set( c.x - HALF, c.y - HALF );
		if ( this.kernelParams.fields.reset.value > 0.5 ) {

			this.kernelParams.fields.prev.value.copy( this.kernelParams.fields.origin.value );

		}

		this.kernelParams.fields.center.value.set( c.x * CELL, c.y * CELL );
		this.kernelParams.fields.boatPos.value.set( p.x, p.z );
		this.kernelParams.fields.fwd.value.copy( this._fwd );
		this.kernelParams.fields.right.value.copy( this._right );
		this.kernelParams.fields.vel.value.copy( this._vel );
		this.kernelParams.fields.propThrust.value.set( this._portThrust, this._stbdThrust );
		this.kernelParams.fields.speed.value = totalSpd;
		this.kernelParams.fields.fwdSpeed.value = fwdVel;
		this.kernelParams.fields.latSpeed.value = latVel;
		this.kernelParams.fields.yawRate.value = this._yawRate;
		this.kernelParams.fields.dt.value = h;

		this._dispatch();
		this.kernelParams.fields.reset.value = 0;

	}

}

function clamp( x, a, b ) {

	return Math.max( a, Math.min( b, x ) );

}
