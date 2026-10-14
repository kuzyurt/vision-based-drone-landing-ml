import { defineConfig } from 'vite';

export default defineConfig( {
	// Relative assets support same-origin subpaths on hosts with COOP/COEP headers.
	base: './',
	build: { target: 'esnext', chunkSizeWarningLimit: 4000 },
	worker: { format: 'es' },
	server: { port: 5189, strictPort: true, host: '127.0.0.1', headers: { 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' } },
	preview: { headers: { 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' } },
} );
