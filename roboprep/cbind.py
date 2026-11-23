"""Grade C or C++ code with the same tests as the Python exercises.

    lab.check("crc16", "d01_crc.c")        # instead of lab.check("crc16", crc16_ccitt_false, crc16_modbus)

1. Your files are compiled into a shared library with roboprep/c/include on the include path
   (gcc -std=gnu11 for .c, g++ -std=gnu++17 when any file is .cc/.cpp/.cxx). Compiler errors and warnings are shown.
2. The lab's grader has a `c_<check>(lib)` adapter that wraps your functions (prototypes in
   roboprep/c/include/<lab>.h) into Python callables with the same behavior as the Python exercise.
3. The tests run in a forked child process, so a segfault or an infinite loop in your code is reported as a failed
   check instead of killing the notebook.

C++: include the lab header, implement the functions it declares (they have C linkage through extern "C"),
and use classes, templates and the standard library freely inside them.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import os
import pathlib
import pickle
import re
import signal
import subprocess

from .core import ROOT

INC = ROOT / "roboprep" / "c" / "include"
CPP_EXT = (".cc", ".cpp", ".cxx")
SRC_EXT = (".c",) + CPP_EXT


def is_source(arg) -> bool:
    return isinstance(arg, (str, os.PathLike)) and str(arg).endswith(SRC_EXT)


def build(sources, flags: str = "") -> str:
    """Compile sources into a shared library and return its path. Raises AssertionError on compiler errors."""
    sources = [str(pathlib.Path(s).resolve()) for s in sources]
    for s in sources:
        if not os.path.exists(s):
            raise AssertionError(f"{s} not found: run its %%writefile cell first")
    cpp = any(s.endswith(CPP_EXT) for s in sources)
    digest = hashlib.sha1((flags + "".join(pathlib.Path(s).read_text() for s in sources)).encode()).hexdigest()[:12]
    out = pathlib.Path(f"_cbuild_{digest}.so").resolve()
    if not out.exists():
        cc = "g++ -std=gnu++17" if cpp else "gcc -std=gnu11"
        cmd = f"{cc} -shared -fPIC -O1 -g -Wall -Wextra -I{INC} -I. {flags} {' '.join(sources)} -o {out} -lm"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            raise AssertionError("compile failed:\n" + _short(r.stderr))
        if r.stderr.strip():
            print("compiler warnings:\n" + _short(r.stderr))
    return str(out)


def _short(text: str, limit: int = 2500) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "\n..."


def run_isolated(fn, timeout: int = 60):
    """Run fn() in a forked child. Return (ok, message)."""
    rd, wr = os.pipe()
    pid = os.fork()
    if pid == 0:  # child
        os.close(rd)
        signal.alarm(timeout)
        try:
            fn()
            res = (True, "")
        except NotImplementedError:
            res = (False, "not attempted yet (replace the TODO)")
        except AssertionError as e:
            res = (False, str(e) or "assertion failed")
        except Exception as e:  # noqa: BLE001
            res = (False, f"{type(e).__name__}: {e}")
        try:
            os.write(wr, pickle.dumps(res))
        finally:
            os._exit(0)
    os.close(wr)
    chunks = []
    while True:
        b = os.read(rd, 65536)
        if not b:
            break
        chunks.append(b)
    os.close(rd)
    _, status = os.waitpid(pid, 0)
    if os.WIFSIGNALED(status):
        sig = signal.Signals(os.WTERMSIG(status)).name
        if sig == "SIGALRM":
            return False, f"timed out after {timeout} s (infinite loop?)"
        return False, f"your C/C++ code crashed with {sig} (bad pointer, out-of-bounds index, or stack overflow)"
    if not chunks:
        return False, "the test process ended without a result"
    return pickle.loads(b"".join(chunks))


# ---------------------------------------------------------------- ctypes helpers used by the graders' adapters
_TYPES = {
    "void": None, "bool": C.c_bool, "char": C.c_char, "int": C.c_int, "unsigned": C.c_uint,
    "unsigned int": C.c_uint, "long": C.c_long, "size_t": C.c_size_t, "float": C.c_float, "double": C.c_double,
    "int8_t": C.c_int8, "uint8_t": C.c_uint8, "int16_t": C.c_int16, "uint16_t": C.c_uint16,
    "int32_t": C.c_int32, "uint32_t": C.c_uint32, "int64_t": C.c_int64, "uint64_t": C.c_uint64,
}
_PROTO = re.compile(r"^\s*(?P<ret>[\w\s\*]+?)\s*\b(?P<name>\w+)\s*\((?P<args>.*)\)\s*;?\s*$")


def _ctype(text: str, structs: dict):
    text = text.replace("const ", "").strip()
    stars = text.count("*")
    base = text.replace("*", "").strip()
    if base == "char" and stars == 1:
        return C.c_char_p
    if base == "char" and stars == 2:
        return C.POINTER(C.c_char_p)
    t = structs[base] if base in structs else _TYPES[base]
    for _ in range(stars):
        t = C.c_void_p if t is None else C.POINTER(t)
    return t


def bind(lib, proto: str, structs: dict | None = None):
    """bind(lib, "uint16_t crc(const uint8_t *data, size_t len)") -> ctypes function with types set."""
    structs = structs or {}
    m = _PROTO.match(proto)
    if not m:
        raise ValueError(f"cannot parse prototype: {proto}")
    try:
        f = getattr(lib, m.group("name"))
    except AttributeError:
        raise AssertionError(f"{m.group('name')} is not defined in your file (prototype: {proto.strip()})") from None
    f.restype = _ctype(m.group("ret"), structs)
    args = [a.strip() for a in m.group("args").split(",") if a.strip() and a.strip() != "void"]
    f.argtypes = [_ctype(re.sub(r"\b\w+\s*$", "", a) if re.search(r"[\w\*]\s+\w+$|\*\s*\w+$", a) else a, structs) for a in args]
    return f


def u8(data) -> tuple:
    """bytes-like -> (ctypes uint8 array, length)."""
    b = bytes(data)
    return (C.c_uint8 * max(1, len(b))).from_buffer_copy(b if b else b"\0"), len(b)


def arr(ctype, values):
    values = list(values)
    return (ctype * max(1, len(values)))(*values)


def out(ctype, n: int):
    return (ctype * max(1, n))()


class Functions:
    """Lazy view of the functions a lab header declares: lib_fns.crc16_modbus(...) binds on first use."""

    def __init__(self, lib, header: str, structs: dict | None = None):
        self._lib, self._structs = lib, structs or {}
        path = INC / f"{header}.h"
        text = re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        self._protos = {}
        for line in text.splitlines():
            line = line.strip()
            if line.endswith(");") and "(" in line and not line.startswith(("#", "typedef", "return")):
                m = _PROTO.match(line)
                if m:
                    self._protos[m.group("name")] = line
        self._bound = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._bound:
            if name not in self._protos:
                raise AttributeError(f"{name} is not declared in the lab header")
            self._bound[name] = bind(self._lib, self._protos[name], self._structs)
        return self._bound[name]
