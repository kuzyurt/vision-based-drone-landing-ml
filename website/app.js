// AERODOCK project site: architecture detail, benchmark chart, media behaviour.
// Benchmark numbers are copied from benchmark/benchmark.json and, for the final
// version, benchmark/evidence/final/summary.json (20-case suite).

const STAGES = {
	sense: {
		title: 'Camera and drone sensors',
		text: 'Everything the policy knows comes from the drone itself: one camera on a pan-tilt mount and the autopilot\'s own estimate of where the drone is and how it moves.',
		facts: [ [ 'Image', '640 × 360 colour, 25 frames per second' ], [ 'Own state', 'position, velocity, attitude, camera angles' ], [ 'Radio', 'optional: the boat\'s position helps find it, never lands it' ] ],
	},
	see: {
		title: 'See — two networks find the boat and the pad',
		text: 'Both share one image encoder. The search head marks every boat in the frame and says which one is the target. The main network says whether the pad is in view and where it is in the picture, so the camera can stay on it, and estimates where the pad is relative to the drone and how the deck moves, with a short memory of earlier frames.',
		facts: [ [ 'Search head', 'about 45,000 parameters: every boat, and which one is the target' ], [ 'Main network', 'about 1.55 million: pad in view, pad position and deck motion, GRU memory' ], [ 'Neither flies', 'they report what they see; control code decides the moves' ] ],
	},
	measure: {
		title: 'Measure — geometry locates the pad',
		text: 'Close to the boat, the known marking on the landing pad is fitted in the image with the calibrated camera. That gives the pad\'s position in metres — a measurement, not a guess. Tracking it over time gives the deck\'s motion.',
		facts: [ [ 'Input', 'pad markings and camera calibration' ], [ 'Output', 'pad position, heading and deck motion' ], [ 'Rule', 'a confident network alone cannot start the descent' ] ],
	},
	decide: {
		title: 'Decide — an explicit landing controller',
		text: 'A controller turns the estimates into a flight: search, approach, match the deck, descend, touch down. It limits every command and backs off when the measurement is lost.',
		facts: [ [ 'Output', 'three velocities, turn rate, camera pan and tilt' ], [ 'Rate', '25 commands per second' ], [ 'Safety', 'bounded commands, descent only on a measured pad, recovery' ] ],
	},
	fly: {
		title: 'Fly — PX4 turns commands into thrust',
		text: 'The open-source PX4 autopilot — the same software that flies real drones — stabilises the aircraft and drives the four motors. The policy only tells it where to go.',
		facts: [ [ 'Autopilot', 'PX4 1.16, unmodified' ], [ 'Loop', 'sensors and motors at 250 Hz' ], [ 'Commands', 'velocity setpoints in PX4 offboard mode' ] ],
	},
};

const MODELS = [
	{ key: 'teacher', name: 'Teacher', note: 'sees simulator truth', score: 99.2, landed: 20 },
	{ key: 'current', name: 'Final version', note: 'two networks, radio if offered', score: 79.9, landed: 18 },
	{ key: 'nov', name: '8 November', note: 'with pad finder, no radio', score: 72.8, landed: 18 },
	{ key: 'r15', name: 'Camera first', note: 'before the search head', score: 47.5, landed: 11 },
	{ key: 'radio', name: 'Radio-dependent', note: 'landed only with boat radio', score: 44.4, landed: 7 },
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
	</div>` ).join( '' );

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
document.querySelectorAll( '.band h2, .band .lead, .card, .story li, .phases li, .arch, .bar-row, .rates, .points li' ).forEach( ( el ) => el.classList.add( 'reveal' ) );
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

// The flight video in "Fly it yourself" starts by itself, muted (browsers allow
// autoplay only without sound), once 70 % of it is on screen, and pauses when
// it scrolls away. After the viewer pauses it themselves it stays paused.
const watchVideo = document.querySelector( '#watch video' );
if ( watchVideo && ! still ) {

	// The pause event arrives later than the pause() call, so the flag is cleared
	// by the event itself, not right after the call.
	let autoPlaying = false, userPaused = false, autoPausing = false;
	watchVideo.addEventListener( 'pause', () => { if ( autoPausing ) autoPausing = false; else userPaused = true; } );
	watchVideo.addEventListener( 'play', () => { userPaused = false; } );
	new IntersectionObserver( ( [ entry ] ) => {

		// A video taller than the window can never be 70 % visible; then filling
		// 70 % of the window counts instead.
		const view = entry.rootBounds?.height || innerHeight;
		if ( entry.intersectionRatio >= 0.7 || entry.intersectionRect.height >= 0.7 * view ) {

			if ( watchVideo.paused && ! userPaused ) {

				if ( ! autoPlaying ) watchVideo.muted = true;
				autoPlaying = true;
				watchVideo.play().catch( () => {} );

			}

		} else if ( ! watchVideo.paused ) {

			autoPausing = true;
			watchVideo.pause();

		}

	}, { threshold: [ 0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1 ] } ).observe( watchVideo );

}
