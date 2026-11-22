// AERODOCK project site: architecture detail, media behaviour, language switching.
// Benchmark numbers are copied from benchmark/benchmark.json and, for the final
// version, benchmark/evidence/final/summary.json (20-case suite).
// All text comes from i18n.js; this file only builds it into the page.

const i18n = window.AERODOCK_I18N;
const t = i18n.t;

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
let currentStage = 'see';
function showStage( key ) {

	currentStage = key;
	nodes.forEach( ( node ) => node.classList.toggle( 'on', node.dataset.node === key ) );
	const facts = [ 1, 2, 3 ].map( ( n ) => [ t( `stage.${ key }.f${ n }k` ), t( `stage.${ key }.f${ n }v` ) ] );
	detail.innerHTML = `<div><h3>${ t( `stage.${ key }.title` ) }</h3><p>${ t( `stage.${ key }.text` ) }</p></div><ul>${ facts.map( ( [ k, v ] ) => `<li><b>${ k }</b><span>${ v }</span></li>` ).join( '' ) }</ul>`;

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
showStage( currentStage );

// ---- boat: outside / inside
const swapLabels = [];
document.querySelectorAll( '[data-swap]' ).forEach( ( box ) => {

	const button = box.querySelector( 'button' );
	const label = () => {

		button.textContent = box.classList.contains( 'inside' ) ? t( 'veh.boat.showOutside' ) : t( 'veh.boat.showInside' );

	};
	swapLabels.push( label );
	button.addEventListener( 'click', () => {

		const inside = box.classList.toggle( 'inside' );
		button.setAttribute( 'aria-pressed', String( inside ) );
		label();

	} );
	label();

} );

// ---- a new language: rebuild the generated text in place
i18n.onChange( () => {

	showStage( currentStage );
	swapLabels.forEach( ( label ) => label() );

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

// ---- custom player controls: seek bar, 1-4x speed, fullscreen
const player = document.querySelector( '[data-player]' );
if ( player ) {

	const video = player.querySelector( 'video' );
	const seek = player.querySelector( '.player-seek' );
	const clockEl = player.querySelector( '.player-time' );
	const toggles = Array.from( player.querySelectorAll( '[data-player-play]' ) );
	const speeds = Array.from( player.querySelectorAll( '[data-speed]' ) );
	const fsButton = player.querySelector( '[data-player-fs]' );
	const canHide = matchMedia( '(hover: hover) and (pointer: fine)' ).matches;
	let quietTimer = 0;

	const clock = ( seconds ) => {

		if ( ! Number.isFinite( seconds ) || seconds < 0 ) return '0:00';
		const whole = Math.floor( seconds );
		return `${ Math.floor( whole / 60 ) }:${ String( whole % 60 ).padStart( 2, '0' ) }`;

	};

	const labels = () => {

		const playing = ! video.paused && ! video.ended;
		const full = document.fullscreenElement === player;
		toggles.forEach( ( button ) => button.setAttribute( 'aria-label', t( playing ? 'play.player.pause' : 'play.player.play' ) ) );
		fsButton.setAttribute( 'aria-label', t( full ? 'play.player.exitFullscreen' : 'play.player.fullscreen' ) );

	};

	const paint = () => {

		const duration = video.duration || 0;
		const progress = duration ? ( video.currentTime / duration ) * 100 : 0;
		seek.value = String( Math.round( progress * 10 ) );
		seek.style.setProperty( '--played', `${ progress }%` );
		clockEl.textContent = `${ clock( video.currentTime ) } / ${ clock( duration ) }`;
		player.classList.toggle( 'playing', ! video.paused && ! video.ended );
		labels();

	};

	const wake = () => {

		player.classList.remove( 'quiet' );
		clearTimeout( quietTimer );
		if ( canHide && ! video.paused && ! video.ended ) quietTimer = setTimeout( () => player.classList.add( 'quiet' ), 2600 );

	};

	const toggle = () => {

		if ( video.paused || video.ended ) {

			if ( video.ended ) video.currentTime = 0;
			video.play().catch( () => {} );

		} else video.pause();
		wake();

	};

	toggles.forEach( ( button ) => button.addEventListener( 'click', toggle ) );
	video.addEventListener( 'click', toggle );

	seek.addEventListener( 'input', () => {

		if ( video.duration ) video.currentTime = ( Number( seek.value ) / 1000 ) * video.duration;
		seek.style.setProperty( '--played', `${ Number( seek.value ) / 10 }%` );
		wake();

	} );

	speeds.forEach( ( button ) => button.addEventListener( 'click', () => {

		video.playbackRate = Number( button.dataset.speed );
		speeds.forEach( ( other ) => other.setAttribute( 'aria-pressed', String( other === button ) ) );
		wake();

	} ) );

	fsButton.addEventListener( 'click', () => {

		if ( document.fullscreenElement === player ) document.exitFullscreen?.();
		else if ( player.requestFullscreen ) player.requestFullscreen().catch( () => {} );

	} );

	document.addEventListener( 'fullscreenchange', () => {

		player.classList.toggle( 'full', document.fullscreenElement === player );
		labels();

	} );

	video.addEventListener( 'loadedmetadata', paint );
	video.addEventListener( 'durationchange', paint );
	video.addEventListener( 'timeupdate', paint );
	video.addEventListener( 'play', () => { paint(); wake(); } );
	video.addEventListener( 'pause', () => { paint(); player.classList.remove( 'quiet' ); } );
	video.addEventListener( 'ended', () => { paint(); player.classList.remove( 'quiet' ); } );
	player.addEventListener( 'pointermove', wake );
	player.addEventListener( 'focusin', () => { player.classList.remove( 'quiet' ); clearTimeout( quietTimer ); } );
	player.addEventListener( 'focusout', wake );
	i18n.onChange( labels );
	paint();

}
