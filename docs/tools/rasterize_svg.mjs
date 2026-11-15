// Rasterize docs/media/{benchmark-comparison,policy-flow}.svg to PNG at 2x with Playwright's Chromium.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const { chromium } = createRequire( import.meta.url )( 'playwright' );
const media = new URL( '../media/', import.meta.url );
const browser = await chromium.launch();
for ( const name of [ 'benchmark-comparison', 'policy-flow' ] ) {

	const svg = readFileSync( new URL( name + '.svg', media ), 'utf8' );
	const [ , width, height ] = svg.match( /width="(\d+)" height="(\d+)"/ );
	const page = await browser.newPage( { viewport: { width: Number( width ), height: Number( height ) }, deviceScaleFactor: 2 } );
	await page.setContent( `<style>body{margin:0}</style>${ svg }` );
	await page.screenshot( { path: new URL( name + '.png', media ).pathname } );
	await page.close();

}

await browser.close();
