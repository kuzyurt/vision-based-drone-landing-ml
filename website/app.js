// AERODOCK project site: architecture detail, benchmark chart, media behaviour.
// Benchmark numbers are copied from benchmark/benchmark.json (20-case suite).

const STAGES = {
	sense: {
		title: 'Camera and drone sensors',
		text: 'Everything the policy knows comes from the drone itself: one camera on a pan-tilt mount and the autopilot\'s own estimate of where the drone is and how it moves.',
		facts: [ [ 'Image', '640 × 360 colour, 25 frames per second' ], [ 'Own state', 'position, velocity, attitude, camera angles' ], [ 'Not used', 'the boat\'s position — the current policy flies without boat radio' ] ],
	},
	see: {
		title: 'See — a neural network finds the boat',
		text: 'A compact image network locates boats in the frame and estimates the target\'s position and motion. A small memory keeps track between frames, so a wave or a brief occlusion does not lose the boat.',
		facts: [ [ 'Encoder', 'MobileNetV3-Small, shared by all heads' ], [ 'Search', 'heatmap of boats, plus “is this the right one?”' ], [ 'Memory', 'recurrent unit (GRU) with 128 states' ] ],
	},
	measure: {
		title: 'Measure — geometry locates the pad',
		text: 'Close to the boat, the known pattern on the landing pad is fitted in the image with the calibrated camera. This gives a metric position, heading and tilt of the deck — a measurement, not a guess.',
		facts: [ [ 'Input', 'pad markings and camera calibration' ], [ 'Output', 'pad position, heading and deck motion' ], [ 'Rule', 'a confident network alone cannot start the descent' ] ],
	},
	decide: {
		title: 'Decide — an explicit landing controller',
		text: 'A hand-written controller turns the estimates into a flight: search, approach, match the deck, descend, touch down. It limits every command and backs off when the measurement is lost.',
		facts: [ [ 'Output', 'three velocities, turn rate, camera pan and tilt' ], [ 'Rate', '25 commands per second' ], [ 'Safety', 'bounded commands, wave-aware descent, recovery' ] ],
	},
	fly: {
		title: 'Fly — PX4 turns commands into thrust',
		text: 'The open-source PX4 autopilot — the same software that flies real drones — stabilises the aircraft and drives the four motors. The policy only tells it where to go.',
		facts: [ [ 'Autopilot', 'PX4 1.16, unmodified' ], [ 'Loop', 'sensors and motors at 250 Hz' ], [ 'Hardware path', 'the same interface a real X500 uses' ] ],
	},
};

const MODELS = [
	{ key: 'teacher', name: 'Teacher', note: 'sees simulator truth', score: 99.2, landed: 20 },
	{ key: 'current', name: 'Search policy', note: 'camera only', score: 87.8, landed: 18 },
	{ key: 'r15', name: 'Landing policy R15', note: 'before search training', score: 57.5, landed: 11 },
	{ key: 'radio', name: 'First radio policy', note: 'needs boat radio', score: 54.9, landed: 7 },
];

// current policy, per category (score out of 100)
const CATEGORIES = [
	[ 'Boat speed', 100 ], [ 'Wind', 100 ], [ 'Waves', 100 ], [ 'Finding the boat', 100 ], [ 'Everything at once', 0 ],
];

// ---- navigation bar turns solid after the hero
const nav = document.getElementById( 'nav' );
const hero = document.querySelector( '.hero' );
const onScroll = () => nav.classList.toggle( 'solid', window.scrollY > hero.offsetHeight - 80 );
window.addEventListener( 'scroll', onScroll, { passive: true } );
onScroll();

// ---- hero video: the cut hero film when present, otherwise the landing clip
const heroVideo = document.querySelector( '.hero-media' );
if ( heroVideo ) {

	const useFallback = () => {

		heroVideo.onerror = null;
		heroVideo.src = heroVideo.dataset.fallback;
		heroVideo.play().catch( () => {} );

	};

	heroVideo.onerror = useFallback;
	heroVideo.src = heroVideo.dataset.src;
	if ( matchMedia( '(prefers-reduced-motion: reduce)' ).matches ) heroVideo.removeAttribute( 'autoplay' );

}

// ---- architecture diagram
const detail = document.getElementById( 'arch-detail' );
const nodes = Array.from( document.querySelectorAll( '.arch-svg .node' ) );
function showStage( key ) {

	const stage = STAGES[ key ];
	nodes.forEach( ( node ) => node.classList.toggle( 'on', node.dataset.node === key ) );
	detail.innerHTML = `<div><h3>${ stage.title }</h3><p>${ stage.text }</p></div><ul>${ stage.facts.map( ( [ k, v ] ) => `<li><b>${ k }</b><span>${ v }</span></li>` ).join( '' ) }</ul>`;

}

nodes.forEach( ( node ) => {

	node.addEventListener( 'click', () => showStage( node.dataset.node ) );
	node.addEventListener( 'keydown', ( event ) => {

		if ( event.key === 'Enter' || event.key === ' ' ) {

			event.preventDefault();
			showStage( node.dataset.node );

		}

	} );

} );
showStage( 'see' );

// ---- benchmark chart
const chart = document.getElementById( 'chart' );
chart.innerHTML = MODELS.map( ( m ) => `
	<div class="bar-row ${ m.key }">
		<div class="bar-name"><b>${ m.name }</b><span>${ m.note }</span></div>
		<div class="bar-track"><div class="bar-fill" data-width="${ m.score }"></div></div>
		<div class="bar-value"><b>${ m.score.toFixed( 1 ) }</b><span>${ m.landed } / 20 landed</span></div>
	</div>` ).join( '' )
	+ `<div class="cats">${ CATEGORIES.map( ( [ name, score ] ) => `<div class="cat ${ score === 100 ? 'ok' : 'bad' }"><b>${ score === 100 ? 'All landed' : 'None landed' }</b><span>${ name }</span></div>` ).join( '' ) }</div>`;

// ---- boat: outside / inside
document.querySelectorAll( '[data-swap]' ).forEach( ( box ) => {

	const button = box.querySelector( 'button' );
	button.addEventListener( 'click', () => {

		const inside = box.classList.toggle( 'inside' );
		button.textContent = inside ? 'Show outside' : 'Show inside';
		button.setAttribute( 'aria-pressed', String( inside ) );

	} );

} );

// ---- reveal on scroll, bars grow, clips play only while visible
const still = matchMedia( '(prefers-reduced-motion: reduce)' ).matches;
document.querySelectorAll( '.band h2, .band .lead, .card, .story li, .phases li, .arch, .bar-row, .cat, .rates, .points li' ).forEach( ( el ) => el.classList.add( 'reveal' ) );
const seen = new IntersectionObserver( ( entries ) => {

	for ( const entry of entries ) {

		if ( ! entry.isIntersecting ) continue;
		entry.target.classList.add( 'in' );
		const fill = entry.target.querySelector?.( '.bar-fill' );
		if ( fill ) fill.style.width = fill.dataset.width + '%';
		seen.unobserve( entry.target );

	}

}, { threshold: 0.15 } );
document.querySelectorAll( '.reveal' ).forEach( ( el ) => seen.observe( el ) );

const clips = new IntersectionObserver( ( entries ) => {

	for ( const entry of entries ) {

		if ( entry.isIntersecting && ! still ) entry.target.play().catch( () => {} );
		else entry.target.pause();

	}

}, { threshold: 0.35 } );
document.querySelectorAll( 'video[data-autoplay]' ).forEach( ( video ) => clips.observe( video ) );
