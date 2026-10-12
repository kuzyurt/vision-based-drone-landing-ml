"""Use MuJoCo's actual wave field for Tidewater geometry and water queries."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'tidewater/src'
BACKUP = ROOT / 'water_fix_originals'

def edit(relative, changes):
    path = SRC / relative
    original = path.read_text(encoding='utf-8')
    backup = BACKUP / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    result = original
    for before, after in changes:
        if after in result:
            continue
        if before not in result:
            raise ValueError(f'Missing patch anchor: {relative}: {before[:60]}')
        result = result.replace(before, after, 1)
    path.write_text(result, encoding='utf-8')

edit('landing/PhysicsWaves.js', [
    (" c0:['vec4f'", " enabled:['f32',0],\n c0:['vec4f'"),
])
edit('ocean/WaterSurface.js', [
    ("import { FFT_SIZE } from './OceanFFT.js';", "import { FFT_SIZE } from './OceanFFT.js';\nimport { landingWaveModule } from '../landing/PhysicsWaves.js';"),
    ("${ T ? /* wgsl */`\n\t// hide the water sheet", """// Landing mode: the same metre-scale coefficients drive MuJoCo buoyancy,
// rendered height, normals and camera water queries. Never add unrelated FFT/surf displacement.
\tif ( landingWaves.enabled > 0.5 ) {
\t\ttotal = vec3f( 0.0, landingWaveHeight( worldXZ ), 0.0 );
\t\ty = frame.seaLevel + total.y;
\t\tlet slope = landingWaveSlope( worldXZ );
\t\tshoreN = normalize( vec3f( -slope.x, 1.0, -slope.y ) );
\t\tfoam = 0.0; shoreFoam = 0.0; swash = 0.0; surfMask = vec2f( 0.0 );
\t}
${ T ? /* wgsl */`
\t// hide the water sheet"""),
    ("\t// whitecaps: persistent", """\tif ( landingWaves.enabled > 0.5 ) {
\t\tlet slope = landingWaveSlope( lagXZ );
\t\tnormal = normalize( vec3f( -slope.x, 1.0, -slope.y ) );
\t\tbaseNormal = normal;
\t\tfoamSum = 0.0; aeration = 0.0;
\t}
\t// whitecaps: persistent"""),
    ("\tvar whitecaps = vertexFoam + fresh;", "\tvar whitecaps = select( vertexFoam + fresh, 0.0, landingWaves.enabled > 0.5 );"),
    ("deps: [ commonModule, fft.module, this.cdlod.module", "deps: [ landingWaveModule, commonModule, fft.module, this.cdlod.module"),
])
edit('ocean/WaterQuery.js', [
    ("import { commonModule } from '../engine/render/wgsl/common.js';", "import { commonModule } from '../engine/render/wgsl/common.js';\nimport { landingWaveModule } from '../landing/PhysicsWaves.js';"),
    ("deps: [ commonModule, fft.module, S.attenuationModule", "deps: [ landingWaveModule, commonModule, fft.module, S.attenuationModule"),
    ("fn waterQueryDispAt( x0: vec2f, depth: f32 ) -> vec3f {", "fn waterQueryDispAt( x0: vec2f, depth: f32 ) -> vec3f {\n\tif ( landingWaves.enabled > 0.5 ) { return vec3f( 0.0, landingWaveHeight( x0 ), 0.0 ); }"),
])
for path in (SRC / 'landing').glob('*Bridge.js'):
    text = path.read_text(encoding='utf-8')
    anchor = "packet.waves.forEach("
    if anchor in text:
        edit('landing/' + path.name, [(anchor, "landingWaveParams.fields.enabled.value=1;" + anchor)])
print('Shared water surface patched; originals preserved.', flush=True)
