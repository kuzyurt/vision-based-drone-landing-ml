import { pathToFileURL } from 'node:url';
const path = process.argv[2];
if ( !path ) throw new Error('Pass the generated PX4 module path');
const { default: load } = await import(pathToFileURL(path));
const module = await load({ noInitialRun:true, print:console.log, printErr:console.error });
console.log('PX4 WebAssembly loaded');
module._tw_init();
console.log('PX4 platform initialized');
for (const command of ['param set SYS_AUTOSTART 10016', 'param set COM_RC_IN_MODE 4', 'uorb status']) {
    const result = module.ccall('tw_command','number',['string'],[command]);
    if (result !== 0) throw new Error(`${command} returned ${result}`);
}
console.log('Pinned PX4 modules initialized in WebAssembly');
process.exit(0);
