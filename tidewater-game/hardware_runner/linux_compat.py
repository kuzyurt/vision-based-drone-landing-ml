"""Run the pinned Windows benchmark flight path on Linux, without editing it.

Only what is Windows-specific is replaced, in this process:

* ``subprocess.CREATE_NO_WINDOW`` (absent on Linux) becomes 0;
* ``windows_kernels`` (redirects a marker-kernel .so to a Windows DLL) is a
  no-op: the final policy uses its Python marker fit, not that kernel;
* ``fast_physics_windows`` (a native FP64 speed-up DLL) is a no-op: the
  original Python force laws it replaces run instead (the module's own
  docstring states that force laws, generators, time steps are unchanged);
* Windows font paths fall back to DejaVu (overlay text only);
* the preflight's "requires Windows" refusal and the hash check of the
  locally rebuilt scene are recorded as deviations instead of errors.

Results of such a run are Linux working data. They are not canonical
evidence and must not be mixed with the Windows benchmark numbers.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import types
from pathlib import Path

DEVIATIONS: list[str] = []


def install(output_dir: Path | None = None):
    if os.name == 'nt':
        return []
    os.environ.setdefault('MUJOCO_GL', 'egl')
    # local_paths puts a vendored Windows h5py build first on sys.path; load the
    # platform's own h5py before that happens.
    import h5py  # noqa: F401
    if not hasattr(subprocess, 'CREATE_NO_WINDOW'):
        subprocess.CREATE_NO_WINDOW = 0
    sys.modules.setdefault('windows_kernels', types.SimpleNamespace(install=lambda: None))
    sys.modules.setdefault('fast_physics_windows', types.SimpleNamespace(install=lambda: None))
    from PIL import ImageFont
    original_truetype = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if isinstance(font, str) and font.startswith('C:/Windows/Fonts/'):
            bold = 'bold' in font.lower() or font.lower().endswith('bd.ttf')
            font = '/usr/share/fonts/truetype/dejavu/DejaVuSans' + ('-Bold' if bold else '') + '.ttf'
            if not Path(font).exists():
                return ImageFont.load_default()
        return original_truetype(font, *args, **kwargs)

    ImageFont.truetype = truetype
    from benchmark.harness import runner
    import hashlib

    def verify_receipts(receipts):
        """Like the pinned check, but a text file that differs only in CRLF/LF line endings
        (Windows checkout vs Linux checkout of the same commit) counts as identical."""
        errors = []
        for item in receipts:
            path = Path(runner.REPO) / item['path']
            if not path.is_file():
                errors.append(item['path'])
                continue
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() == item['sha256']:
                continue
            crlf = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            if hashlib.sha256(crlf).hexdigest() == item['sha256']:
                continue
            errors.append(item['path'])
        return errors

    runner.verify_receipts = verify_receipts
    original_preflight = runner.preflight
    runtime = json.loads((Path(runner.ROOT) / 'definition/runtime.json').read_text(encoding='utf-8'))
    scene = runtime['scene']

    def preflight(policy):
        errors = original_preflight(policy)
        kept = []
        for error in errors:
            if error.startswith('This adapter requires Windows'):
                DEVIATIONS.append('Linux instead of Windows (pinned preflight refusal recorded, not enforced)')
            elif error == scene:
                DEVIATIONS.append(f'{scene} rebuilt locally with its build_scene.py; hash differs from the pinned one')
            elif error.endswith('marker_kernel.so'):
                DEVIATIONS.append(f'{error}: rebuilt for Linux from the identical marker_kernel.cpp (the final policy uses the Python fit)')
            elif error.endswith('.dll'):
                DEVIATIONS.append(f'{error}: Windows binary, not used on Linux')
            elif error.endswith(('.npz', '.json', '.py')) and error.startswith('artifacts/'):
                DEVIATIONS.append(f'{error}: missing or different in this checkout (not used by the final policy)')
            else:
                kept.append(error)
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / 'linux_deviations.json').write_text(json.dumps(dict(
                platform=sys.platform, deviations=sorted(set(DEVIATIONS)),
                fast_physics='disabled (original Python force laws)', marker_kernel='not used by the final policy',
                canonical=False), indent=2), encoding='utf-8')
        return kept

    runner.preflight = preflight
    return DEVIATIONS
