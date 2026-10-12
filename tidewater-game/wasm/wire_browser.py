from pathlib import Path
p=Path(__file__).resolve().parents[1]/'app/src/landing/SimulationBridge.js'
s=p.read_text().replace("const API = 'http://127.0.0.1:5195';\n",'')
a=s.index('\tasync _connect()');b=s.index('\tasync _installVehicles()',a)
s=s[:a]+'''\tasync _connect() {
        if ( this.closed || this.connecting || this.worker ) return;
        this.connecting = true;
        try {
            this._setStatus( { status: 'Loading original CAD camera and browser physics', ready: false } );
            this._openWorker();
            await this._installVehicles();
            await this._uploadMap();
        } catch ( error ) {
            this._setStatus( { status: 'Browser simulation startup failed', ready: false, error: error.message } );
        }
        this.connecting = false;
    }

'''+s[b:]
a=s.index('\t\tconst header = new TextEncoder()');b=s.index('\n\t\tthis.lastMapUpload = Date.now();',a)
s=s[:a]+'''        // The renderer keeps its data while physics receives an owned copy.
        const heights = new Float32Array( terrain.heights ).buffer;
        const base = new URL( `${ import.meta.env?.BASE_URL || '/' }landing/`, location.href ).href;
        this.worker.postMessage( { type: 'initialize', base, meta: metadata, heights }, [ heights ] );'''+s[b:]
a=s.index('\t_openSocket()');b=s.index('\t_setStatus( state )',a)
s=s[:a]+'''    _openWorker() {
        const worker = new Worker( new URL( './BrowserSimulationWorker.js', import.meta.url ), { type: 'module', name: 'Tidewater PX4 and MuJoCo' } );
        this.worker = worker;
        worker.onmessage = event => {
            try {
                const state = event.data;
                if ( state.disposed ) { this._disposeResolve?.(); return; }
                if ( state.bodies && ! this.layout ) this.send( { mode: this.app.flightOps.mode } );
                this.timeline.push( state, performance.now() );
                this._setStatus( state );
                if ( state.geoms ) this._applyTransforms( state.geoms );
                if ( state.bodies ) this._applyBodies( state.bodies );
                if ( state.views ) this._applyCamera( state );
            } catch ( error ) {
                this._setStatus( { ...this.state, ready: false, status: 'Could not display browser simulation', error: error.message } );
            }
        };
        worker.onerror = event => this._setStatus( { ...this.state, ready: false, status: 'Browser simulation stopped', error: event.message || 'Physics worker failed' } );
    }

'''+s[b:]
a=s.index('\tsend( payload )');s=s[:a]+'''    send( payload ) {
        if ( payload.action === 'reset' ) { this.retry(); return; }
        this.worker?.postMessage( payload );
    }

    async retry() {
        if ( this.restarting ) return;
        this.restarting = true;
        this._setStatus( { ...this.state, ready: false, error: null, status: 'Restarting browser simulation' } );
        await this._disposeWorker();
        this.timeline = new PoseTimeline(); this.cameraView = null; this.layout = null;
        this.lastMapUpload = 0; this.connecting = false;
        await this._connect();
        this.restarting = false;
    }

    close() {
        this.closed = true;
        this._disposeWorker();
    }

    async _disposeWorker() {
        const worker = this.worker;
        if ( ! worker ) return;
        this.worker = null;
        await new Promise( resolve => {
            const timer = setTimeout( resolve, 1500 );
            this._disposeResolve = () => { clearTimeout( timer ); resolve(); };
            worker.postMessage( { type: 'shutdown' } );
        } );
        worker.terminate(); this._disposeResolve = null;
    }
}
'''
p.write_text(s,encoding='utf-8')
