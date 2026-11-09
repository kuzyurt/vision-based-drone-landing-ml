"""Create the inventory, static suite and environment pins without executing models."""
import re
from .common import REPO, ROOT, read, sha, utc, write
from .inventory import build, receipt, tree_receipts
from .suite import main as prepare_suite


def pin_environment():
    local = REPO / 'artifacts/local_curriculum_20261020'
    bridge = (local / 'px4_windows_bridge_v2.mjs').read_text(encoding='utf-8')
    # A separate bridge is bound to the current working tree's exact PX4 build.
    # Historical review pins remain untouched; no parity claim is inherited.
    bridge, count = re.subn(r"Object\.entries\(\{'px4\.mjs':.*?\}\)",
        "Object.entries(JSON.parse(fs.readFileSync(new URL('../environments/runtime.json',import.meta.url))).px4_hashes)",
        bridge, count=1)
    if count != 1:
        raise ValueError('Existing PX4 bridge layout changed; review the port before preparing.')
    (ROOT / 'runtime').mkdir(exist_ok=True)
    (ROOT / 'runtime/px4_bridge.mjs').write_text(bridge, encoding='utf-8')
    mission = REPO / 'artifacts/landing_hardening_20261018/r15_native_completion_verified/r15_fresh_E60/mission_sources'
    source_files = []
    for folder in [REPO / 'landing_training', REPO / 'AERODOCK_MuJoCo/usv',
                   REPO / 'px4-mujoco-drone-simulation/sim']:
        source_files += [receipt(p) for p in sorted(folder.glob('*.py'))]
    source_files += tree_receipts(mission)
    for name in ['local_paths.py', 'windows_px4_v2.py', 'windows_kernels.py', 'fast_physics_windows.py',
                 'windows_renderer.py', 'review_helpers.py']:
        source_files.append(receipt(local / name))
    source_files += tree_receipts(local / 'sources/target_learning')
    source_files += tree_receipts(REPO / 'artifacts/approved_curriculum_20261020/candidate_exports/experimental_v48_local_recovery/package/sources/target_learning')
    assets = [REPO / 'artifacts/city80_decoys_20261023/scene.mjb', local / 'physics_math.dll', local / 'models/index.json',
              REPO / 'artifacts/approved_curriculum_20261020/candidate_exports/native_windows/marker_kernel.dll',
              REPO / 'AERODOCK_MuJoCo/config.json']
    for folder in ['px4-mujoco-drone-simulation/models/metadata', 'tidewater-game/app/public/landing/physics']:
        assets += sorted((REPO / folder).glob('*.json'))
    px4 = REPO / 'tidewater-game/app/public/landing/wasm'
    assets += [px4 / n for n in ['px4.mjs', 'px4.wasm']]
    runtime = dict(schema='aerodock.benchmark.environment.v1', captured_utc=utc(),
                   backend='Windows MuJoCo 3.14 + pinned real PX4 WASM; separate from Linux and Tidewater qualification',
                   px4_hashes={n: sha(px4 / n) for n in ['px4.mjs', 'px4.wasm']},
                   source_files=source_files, assets=[receipt(p) for p in assets],
                   scene='artifacts/city80_decoys_20261023/scene.mjb',
                   scene_recipe='Same target/drone CAD and six authored boat distractors (three similar, three dissimilar). Clear cases hide every decoy geom and disable its collision masks. No target/drone mass, solver or scoring changes.',
                   procedural_maps=['island', 'beach', 'city', 'gravel', 'rock'],
                   map_recipe='Environment → BoatSim.new_world(kind, world_seed, path_seed); exact seeds/rotation/route direction in suite.json.',
                   benchmark_extension='Scenario subclass permits 100 m and 240 s only for this suite; original validation and collection ranges unchanged.',
                   harness_files=[receipt(p) for p in sorted(ROOT.glob('*.py'))] + [receipt(ROOT / 'runtime/px4_bridge.mjs')],
                   preparation_only=True, training_eligible=False)
    write(ROOT / 'environments/runtime.json', runtime)
    from .report import build_report
    build_report()
    print('Prepared dashboard and pinned runtime. No simulation, inference, training or benchmarks executed.')


def prepare():
    build()
    prepare_suite()
    pin_environment()


if __name__ == '__main__':
    prepare()
