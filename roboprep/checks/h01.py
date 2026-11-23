import math
import numpy as np

ANSWERS = {"M1": (1.055, {"abs": 1e-3}), "M2": (41.46, {"abs": 0.02}), "M3": 16}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Noise sources: reference or supply noise, motor/DC-DC switching coupling through ground, digital activity",
    "Source impedance too high for the sampling time; no anti-alias filter",
    "Fixes: clean decoupled reference, RC at the pin, longer sampling time, analog ground, sample at quiet times",
    "Oversampling helps with white noise (dither) but not with correlated interference, offset, gain or nonlinearity",
]}
HINTS = {
    "ntc": "1/T = 1/T0 + ln(R/R0)/beta with T in kelvin.",
    "enob": "np.linalg.lstsq on [sin, cos, 1]; signal RMS = amplitude / sqrt(2).",
    "oversample": "Group size 4**k; (sum + 2**(k-1)) >> k.",
}


def check_ntc(div, ohms, temp):
    assert abs(div(3.3, 10e3, 4.7e3) - 3.3 * 4.7 / 14.7) < 1e-12
    assert abs(ohms(2048, 12, 10e3) - 10e3) < 1e-9 and abs(ohms(1024, 12, 10e3) - 10e3 / 3) < 1e-9
    assert abs(temp(10e3) - 25.0) < 1e-9
    want = 1 / (1 / 298.15 + math.log(0.5) / 3950) - 273.15
    assert abs(temp(5e3) - want) < 1e-9, f"5 kOhm -> {temp(5e3)}"


def _capture(bits, noise_lsb, n=4096, fs=10000.0, f0=97.0, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs
    full = 2 ** bits
    x = (full / 2 - 0.5) * np.sin(2 * np.pi * f0 * t + 0.3) + full / 2 + rng.normal(0, noise_lsb, n)
    return np.clip(np.round(x), 0, full - 1), fs, f0


def check_enob(fn):
    x, fs, f0 = _capture(12, 0.0)
    e = fn(x, fs, f0)
    assert 11.8 < e < 12.2, f"ideal 12-bit ADC -> ENOB {e:.2f}"
    x, fs, f0 = _capture(12, 2.0)
    e2 = fn(x, fs, f0)
    expect = 12 - math.log2(math.sqrt(1 + 12 * 4.0))
    assert abs(e2 - expect) < 0.15, f"2 LSB of noise -> ENOB {e2:.2f}, expected about {expect:.2f}"


def check_oversample(fn):
    assert fn([1, 2, 3, 4, 5, 6, 7, 8, 9], 1) == [5, 13], "groups of 4, >> 1"
    rng = np.random.default_rng(3)
    true = 1000.37
    s = [int(round(true + rng.normal(0, 1.5))) for _ in range(4096 * 16)]
    out = fn(s, 2)
    assert len(out) == 4096
    est = np.mean(out) / 4
    assert abs(est - true) < 0.05, f"oversampled estimate {est:.3f} vs {true}"


def c_ntc(lib):
    from roboprep.cbind import Functions
    f = Functions(lib, "h01")
    return (f.divider, f.ntc_ohms_from_code,
            lambda r, r0=10e3, t0_c=25.0, beta=3950.0: f.ntc_temp_c(r, r0, t0_c, beta))


def c_enob(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "h01")
    return (lambda s, fs, f0: f.enob(arr(C.c_double, [float(v) for v in s]), len(s), fs, f0),)


def c_oversample(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr, out
    f = Functions(lib, "h01")

    def oversample(samples, extra_bits):
        buf = out(C.c_int32, len(samples))
        n = f.oversample(arr(C.c_int32, [int(v) for v in samples]), len(samples), extra_bits, buf, len(samples))
        return list(buf[:n])
    return (oversample,)
