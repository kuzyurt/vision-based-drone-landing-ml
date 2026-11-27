"""Minimal ctypes binding to the ngspice shared library (libngspice).

Two uses:

* ``Spice.run(netlist)`` runs a complete analysis (the switching testbenches)
  and returns the vectors as numpy arrays.
* ``Spice.load`` + ``Spice.advance(t)`` runs a transient analysis in lockstep
  with outside code. Current sources declared ``external`` in the netlist read
  their value from Python at every internal time step, so a firmware or
  policy loop can drive the circuit while the circuit is being solved.

Only the C API documented in the ngspice manual (chapter "ngspice as shared
library") is used. ngspice is not thread safe; one process holds one circuit.
"""
from __future__ import annotations

import ctypes as C
import ctypes.util
import threading

import numpy as np

_LIB = None
_LOCK = threading.Lock()
_OUTPUT: list[str] = []
_EXTERNAL: dict[str, float] = {}

_PRINT = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
_STAT = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
_EXIT = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
_BG = C.CFUNCTYPE(C.c_int, C.c_bool, C.c_int, C.c_void_p)
_SRC = C.CFUNCTYPE(C.c_int, C.POINTER(C.c_double), C.c_double, C.c_char_p, C.c_int, C.c_void_p)


class _VecInfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('type', C.c_int), ('flags', C.c_short),
                ('realdata', C.POINTER(C.c_double)), ('compdata', C.c_void_p),
                ('length', C.c_int)]


def _on_print(text, _ident, _user):
    _OUTPUT.append(text.decode(errors='replace'))
    return 0


def _on_stat(_text, _ident, _user):
    return 0


def _on_exit(_status, _unload, _quit, _ident, _user):
    return 0


def _on_bg(_running, _ident, _user):
    return 0


def _on_source(ret, _time, name, _ident, _user):
    ret[0] = _EXTERNAL.get(name.decode().lower(), 0.0)
    return 0


_callbacks = (_PRINT(_on_print), _STAT(_on_stat), _EXIT(_on_exit), _BG(_on_bg),
              _SRC(_on_source), _SRC(_on_source))


class SpiceUnavailable(RuntimeError):
    pass


def library():
    global _LIB
    if _LIB is None:
        path = ctypes.util.find_library('ngspice') or 'libngspice.so.0'
        try:
            lib = C.CDLL(path)
        except OSError as exc:
            raise SpiceUnavailable('libngspice not found; install ngspice (apt install libngspice0, '
                                   'or the ngspice shared DLL on Windows)') from exc
        lib.ngSpice_Init(_callbacks[0], _callbacks[1], _callbacks[2], None, None, _callbacks[3], None)
        lib.ngSpice_Init_Sync(_callbacks[4], _callbacks[5], None, None, None)
        lib.ngSpice_Command.argtypes = [C.c_char_p]
        lib.ngGet_Vec_Info.restype = C.POINTER(_VecInfo)
        lib.ngSpice_CurPlot.restype = C.c_char_p
        lib.ngSpice_AllVecs.restype = C.POINTER(C.c_char_p)
        _LIB = lib
    return _LIB


class Spice:
    """One loaded circuit. Use as a context manager or call close()."""

    def __init__(self):
        self.lib = library()
        _LOCK.acquire()
        self._open = True
        self._started = False
        self.time = 0.0
        self.command('destroy all')
        self.command('reset')

    def close(self):
        if self._open:
            self.command('destroy all')
            _LOCK.release()
            self._open = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def command(self, text):
        _OUTPUT.clear()
        self.lib.ngSpice_Command(text.encode())
        errors = [line for line in _OUTPUT if 'error' in line.lower() and 'stderr' in line.lower()]
        return errors

    def load(self, netlist: str):
        lines = [line for line in netlist.strip().splitlines()]
        array = (C.c_char_p * (len(lines) + 1))(*[line.encode() for line in lines], None)
        _OUTPUT.clear()
        self.lib.ngSpice_Circ(array)
        errors = [line for line in _OUTPUT if 'error' in line.lower()]
        if errors:
            raise RuntimeError('ngspice rejected the netlist:\n' + '\n'.join(errors[:10]))

    def run(self, netlist: str | None = None) -> dict[str, np.ndarray]:
        if netlist is not None:
            self.load(netlist)
        self.command('run')
        return self.vectors()

    def set_external(self, **values: float):
        """Set the value read by ``external`` sources, keyed by element name."""
        for name, value in values.items():
            _EXTERNAL[name.lower()] = float(value)

    def advance(self, until_s: float) -> dict[str, float]:
        """Continue the transient analysis to ``until_s`` and return the last sample."""
        if not self._started:
            until_s = max(until_s, 1e-3)   # the analysis needs one step before vectors exist
        elif until_s <= self.time:
            return self.last()
        self.command(f'stop when time > {until_s:.9g}')
        self.command('resume' if self._started else 'run')
        self.command('delete all')
        self._started = True
        self.time = until_s
        return self.last()

    def names(self):
        plot = self.lib.ngSpice_CurPlot()
        vectors = self.lib.ngSpice_AllVecs(plot)
        out, index = [], 0
        while vectors[index]:
            out.append(vectors[index].decode())
            index += 1
        return out

    def vector(self, name: str) -> np.ndarray:
        info = self.lib.ngGet_Vec_Info(name.encode())
        if not info:
            raise KeyError(name)
        info = info.contents
        if not info.realdata:
            raise KeyError(f'{name} is not a real vector')
        # The returned struct is a shared buffer: copy before the next call.
        return np.ctypeslib.as_array(info.realdata, shape=(info.length,)).copy()

    def vectors(self) -> dict[str, np.ndarray]:
        return {name: self.vector(name) for name in self.names()}

    def last(self) -> dict[str, float]:
        out = {}
        for name in self.names():
            info = self.lib.ngGet_Vec_Info(name.encode())
            if info and info.contents.realdata and info.contents.length:
                out[name] = float(info.contents.realdata[info.contents.length - 1])
        return out
