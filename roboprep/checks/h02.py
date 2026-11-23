ANSWERS = {"M1": (21.33, {"abs": 0.01}), "M2": (58674, {"rel": 2e-3}), "M3": 200}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Sleep (0.6 mA s per cycle) dominates over read (0.25) and radio (0.05)",
    "Cut sleep current first: power-gate the sensor, deeper stop mode with RTC wake, remove leakage",
    "Then shorten the read, or wake less often",
]}
HINTS = {
    "pingpong": "Deadline = (n/2)/fs; read the half the DMA is NOT in.",
    "battery": "Sum I*t over active phases, add sleep current times the rest of the period, divide by the period.",
    "alias": "Fold: |f - fs * round(f / fs)|.",
}


def check_pingpong(dl, half):
    assert abs(dl(48000, 2048) - 1024 / 48000) < 1e-12
    assert half(0, 2048) == 1 and half(1023, 2048) == 1 and half(1024, 2048) == 0 and half(2047, 2048) == 0


def check_battery(avg, life):
    a = avg([(5.0, 0.05), (10.0, 0.005)], 0.002, 300.0)
    want = (0.25 + 0.05 + 0.002 * (300 - 0.055)) / 300
    assert abs(a - want) < 1e-12, f"average {a}"
    assert abs(life(220, want) - 220 * 0.8 / want) < 1e-6


def check_alias(fn):
    assert abs(fn(900, 1000) - 100) < 1e-9 and abs(fn(1200, 1000) - 200) < 1e-9
    assert abs(fn(400, 1000) - 400) < 1e-9 and abs(fn(25000, 10000) - 5000) < 1e-9


def c_pingpong(lib):
    from roboprep.cbind import Functions
    f = Functions(lib, "h02")
    return f.half_deadline_s, f.half_to_process


def c_battery(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "h02")

    def average_current_mA(phases, sleep_mA, period_s):
        return f.average_current_mA(arr(C.c_double, [i for i, _ in phases]), arr(C.c_double, [t for _, t in phases]),
                                    len(phases), sleep_mA, period_s)
    return average_current_mA, lambda cap, avg, derating=0.8: f.battery_life_hours(cap, avg, derating)


def c_alias(lib):
    from roboprep.cbind import Functions
    return (Functions(lib, "h02").alias,)
