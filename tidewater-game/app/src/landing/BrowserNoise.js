import table from './NoiseTables.js';

// NumPy PCG64 XSL-RR and its double precision Ziggurat sampler. BigInt retains
// the exact 128 bit state; seeded sensor noise is shared with the reference.
export class BrowserNoise {
	constructor(state,increment) {this.state=BigInt(state);this.increment=BigInt(increment);}
	uint64() {
		this.state=BigInt.asUintN(128,this.state*47026247687942121848144207491837523525n+this.increment);
		const high=this.state>>64n,low=BigInt.asUintN(64,this.state),value=high^low,rotation=high>>58n;
		return BigInt.asUintN(64,(value>>rotation)|(value<<((-rotation)&63n)));
	}
	uniform() {return Number(this.uint64()>>11n)*(1/9007199254740992);}
	normal() {
		for(;;) {
			let r=this.uint64();const index=Number(r&255n);r>>=8n;
			const sign=Number(r&1n),absolute=Number((r>>1n)&0xfffffffffffffn);
			let x=absolute*table.wi_double[index];if(sign) x=-x;
			if(absolute<table.ki_double[index]) return x;
			if(index===0) {
				for(;;) {const xx=-table.ziggurat_nor_inv_r*Math.log1p(-this.uniform()),yy=-Math.log1p(-this.uniform());
					if(yy+yy>xx*xx) return (BigInt(absolute)>>8n)&1n?-(table.ziggurat_nor_r+xx):table.ziggurat_nor_r+xx;}
			} else if((table.fi_double[index-1]-table.fi_double[index])*this.uniform()+table.fi_double[index]<Math.exp(-.5*x*x)) return x;
		}
	}
}
