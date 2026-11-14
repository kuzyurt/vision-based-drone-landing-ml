import { defineConfig } from 'vite';
import { handleSessionRecording } from './scripts/session-recording-endpoint.mjs';

// Dev key Z: the in-game session recorder appends to tidewater-game/recordings/.
const sessionRecording = {
	name: 'tidewater-session-recording',
	configureServer( server ) {

		server.middlewares.use( ( req, res, next ) => {

			if ( ! req.url?.startsWith( '/__session-recording' ) ) return next();
			handleSessionRecording( req, res ).then( handled => handled || next(), next );

		} );

	},
};

export default defineConfig( {
	// Relative assets support same-origin subpaths on hosts with COOP/COEP headers.
	base: './',
	plugins: [ sessionRecording ],
	build: { target: 'esnext', chunkSizeWarningLimit: 4000 },
	worker: { format: 'es' },
	server: { port: 5189, strictPort: true, host: '127.0.0.1', headers: { 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' } },
	preview: { headers: { 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' } },
} );
