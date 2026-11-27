"""Build the radio-bridge firmware for the PC (simulation library and unit tests).

    python -m flight_electronics.firmware.build_host          # library + tests, runs tests
    python -m flight_electronics.firmware.build_host --windows-dll   # cross-build with MinGW

The firmware sources in esp32_radio_bridge/src are compiled unchanged; only the
SX1262 bus and the UART are replaced (platform/host).
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'esp32_radio_bridge'
OUT = ROOT / 'build_host'
SOURCES = [ROOT / 'src' / name for name in ('protocol.cpp', 'sx1262.cpp', 'bridge.cpp')]
HOST = [ROOT / 'platform/host/sx1262_model.cpp']


def library_name(windows=None):
    windows = platform.system() == 'Windows' if windows is None else windows
    return 'fe_radio_bridge.dll' if windows else ('libfe_radio_bridge.dylib' if sys.platform == 'darwin'
                                                  else 'libfe_radio_bridge.so')


def _compiler():
    for name in (os.environ.get('CXX'), 'g++', 'clang++', 'c++'):
        if name and shutil.which(name):
            return name
    return None


def _newest_source():
    files = SOURCES + HOST + [ROOT / 'platform/host/sim_api.cpp'] + list((ROOT / 'include').glob('*.h'))
    return max(f.stat().st_mtime for f in files)


def build_library(force=False, windows_dll=False) -> Path:
    OUT.mkdir(exist_ok=True)
    target = OUT / library_name(True if windows_dll else None)
    if target.exists() and not force and target.stat().st_mtime >= _newest_source():
        return target
    flags = ['-std=c++17', '-O2', '-Wall', '-I', str(ROOT / 'include'), '-I', str(ROOT / 'platform/host')]
    sources = [str(s) for s in SOURCES + HOST + [ROOT / 'platform/host/sim_api.cpp']]
    if windows_dll:
        cmd = ['x86_64-w64-mingw32-g++-posix', *flags, '-shared', '-static', '-static-libgcc',
               '-static-libstdc++', *sources, '-o', str(target)]
    elif platform.system() == 'Windows' and not _compiler() and shutil.which('cl'):
        cmd = ['cl', '/nologo', '/O2', '/std:c++17', '/LD', f'/I{ROOT / "include"}',
               f'/I{ROOT / "platform/host"}', *sources, f'/Fe:{target}']
    else:
        cxx = _compiler()
        if cxx is None:
            raise RuntimeError('No C++ compiler found (install g++/clang++, MinGW or MSVC)')
        cmd = [cxx, *flags, '-shared', '-fPIC', *sources, '-o', str(target)]
    subprocess.run(cmd, check=True)
    return target


def run_tests() -> int:
    cxx = _compiler()
    if cxx is None:
        print('No C++ compiler; firmware unit tests skipped')
        return 0
    OUT.mkdir(exist_ok=True)
    exe = OUT / ('test_firmware.exe' if platform.system() == 'Windows' else 'test_firmware')
    subprocess.run([cxx, '-std=c++17', '-O2', '-Wall', '-Wextra', '-I', str(ROOT / 'include'),
                    *[str(s) for s in SOURCES + HOST], str(ROOT / 'tests/test_firmware.cpp'), '-o', str(exe)],
                   check=True)
    return subprocess.run([str(exe)]).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-dll', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    print('built', build_library(force=args.force, windows_dll=args.windows_dll))
    return 0 if args.windows_dll else run_tests()


if __name__ == '__main__':
    raise SystemExit(main())
