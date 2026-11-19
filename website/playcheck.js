// "Check my computer and play": a quick guess, before a 150 MB download, of
// whether the realistic simulator will run here. Hard blockers (no WebGPU, a
// phone, software rendering) say "cannot run"; little memory or a slow GPU say
// "will probably be slow". The game itself measures its real speed later and
// offers the video again if it runs far below real time.
( () => {

	const PLAY_URL = 'play/';
	// GPU throughput from the 0.5 s compute test, in GFLOP/s. A laptop with
	// Intel UHD graphics (gen-9) scores about 120 here (measured 19 Nov 2026)
	// and runs the game with the policy at 5-35 % of real time, so ask for
	// about five times that. This is a rough line, not a guarantee.
	const GOOD_GFLOPS = 600;
	const MIN_MEMORY_GB = 8;   // navigator.deviceMemory is rounded, and capped in some browsers

	const button = document.getElementById( 'play-check' );
	const result = document.getElementById( 'play-result' );
	if ( ! button || ! result ) return;

	button.addEventListener( 'click', async () => {

		button.disabled = true;
		show( 'checking', 'Checking your computer…', [], [] );
		let verdict;
		try { verdict = await check(); } catch ( error ) { verdict = { level: 'no', reasons: [ 'The check failed: ' + error.message ] }; }
		button.disabled = false;
		if ( verdict.level === 'good' ) show( 'good', 'Your computer looks ready.', verdict.reasons, [ [ 'Start the simulator', PLAY_URL, true ], [ 'Watch the video', '#watch' ] ],
			'The first start compiles the graphics and can take a minute or two.' );
		else if ( verdict.level === 'slow' ) show( 'slow', 'It will probably run slowly here.', verdict.reasons, [ [ 'Watch the video', '#watch', true ], [ 'Play anyway', PLAY_URL ] ] );
		else show( 'no', 'The simulator cannot run here.', verdict.reasons, [ [ 'Watch the video', '#watch', true ] ] );

	} );

	async function check() {

		const ua = navigator.userAgent;
		const phone = /Android|iPhone|iPad|iPod|Mobile/i.test( ua ) || ( /Macintosh/.test( ua ) && navigator.maxTouchPoints > 1 );
		if ( phone ) return { level: 'no', reasons: [ 'Phones and tablets cannot run it yet. Open this page on a computer.' ] };
		if ( ! navigator.gpu ) return { level: 'no', reasons: [ 'This browser has no WebGPU. Use a current Chrome or Edge.' ] };
		const adapter = await navigator.gpu.requestAdapter( { powerPreference: 'high-performance' } );
		if ( ! adapter ) return { level: 'no', reasons: [ 'WebGPU is turned off or the graphics driver is blocked.' ] };
		const info = adapter.info || {};
		if ( adapter.isFallbackAdapter || info.isFallbackAdapter ) return { level: 'no', reasons: [ 'The browser draws without the graphics card (software rendering).' ] };

		const reasons = [], slow = [];
		const gpu = [ info.vendor, info.architecture ].filter( Boolean ).join( ' ' ) || 'graphics card';
		const device = await adapter.requestDevice();
		let gflops;
		try { gflops = await gpuThroughput( device ); } finally { device.destroy(); }
		if ( gflops < GOOD_GFLOPS ) slow.push( `The ${ gpu } is too slow for real time (about ${ Math.round( gflops ) } GFLOP/s in a short test).` );
		else reasons.push( `WebGPU on ${ gpu }, about ${ Math.round( gflops ) } GFLOP/s.` );
		const memory = navigator.deviceMemory;
		if ( memory && memory < MIN_MEMORY_GB ) slow.push( `About ${ memory } GB of memory; it needs 8 GB or more.` );
		else if ( memory ) reasons.push( `${ memory >= 8 ? '8 GB or more' : memory + ' GB' } of memory.` );
		const connection = navigator.connection;
		if ( connection?.saveData ) slow.push( 'Data saver is on; the simulator downloads about 150 MB.' );
		return slow.length ? { level: 'slow', reasons: slow.concat( reasons ) } : { level: 'good', reasons };

	}

	// A short compute test: many fused multiply-adds per thread, timed on the GPU queue.
	async function gpuThroughput( device ) {

		const threads = 1 << 18, iterations = 512;
		const flopsPerDispatch = threads * iterations * 16;
		const buffer = device.createBuffer( { size: threads * 16, usage: GPUBufferUsage.STORAGE } );
		const module = device.createShaderModule( { code: `
@group(0) @binding(0) var<storage, read_write> data: array<vec4f>;
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) id: vec3u) {
	var a = data[id.x] + vec4f(0.5);
	var b = vec4f(0.999);
	for (var i = 0u; i < ${ iterations }u; i++) { a = fma(a, b, vec4f(0.0001)); b = fma(b, a, vec4f(-0.0001)); }
	data[id.x] = a + b;
}` } );
		const pipeline = device.createComputePipeline( { layout: 'auto', compute: { module, entryPoint: 'main' } } );
		const group = device.createBindGroup( { layout: pipeline.getBindGroupLayout( 0 ), entries: [ { binding: 0, resource: { buffer } } ] } );
		const run = async () => {

			const encoder = device.createCommandEncoder(), pass = encoder.beginComputePass();
			pass.setPipeline( pipeline ); pass.setBindGroup( 0, group ); pass.dispatchWorkgroups( threads / 64 ); pass.end();
			device.queue.submit( [ encoder.finish() ] );
			await device.queue.onSubmittedWorkDone();

		};
		await run(); await run(); // warm-up and shader compile
		let count = 0;
		const start = performance.now();
		while ( performance.now() - start < 500 && count < 200 ) { await run(); count ++; }
		const seconds = ( performance.now() - start ) / 1000;
		buffer.destroy();
		return flopsPerDispatch * count / seconds / 1e9;

	}

	function show( level, title, reasons, actions, note ) {

		result.hidden = false;
		result.className = 'play-result ' + level;
		result.replaceChildren();
		const heading = document.createElement( 'p' ); heading.className = 'play-title'; heading.textContent = title;
		result.append( heading );
		if ( reasons.length ) {

			const list = document.createElement( 'ul' );
			for ( const reason of reasons ) { const item = document.createElement( 'li' ); item.textContent = reason; list.append( item ); }
			result.append( list );

		}
		if ( note ) { const p = document.createElement( 'p' ); p.className = 'play-note'; p.textContent = note; result.append( p ); }
		if ( actions.length ) {

			const row = document.createElement( 'div' ); row.className = 'play-actions';
			for ( const [ label, href, primary ] of actions ) {

				const link = document.createElement( 'a' );
				link.className = 'button ' + ( primary ? 'primary' : 'ghost' ); link.href = href; link.textContent = label;
				row.append( link );

			}
			result.append( row );

		}

	}

} )();
