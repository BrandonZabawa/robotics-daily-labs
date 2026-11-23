import numpy as np

ANSWERS = {"M1": (44444, {"abs": 1}), "M2": 2500000, "M3": 100000}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Joint MCUs for current and position loops; encoders over SPI on the board",
    "Deterministic field bus to the controller: CAN FD at about 1 kHz, EtherCAT below 1 ms with synchronization",
    "Camera over Ethernet or USB to an edge computer; NPU or GPU for the detector within the power budget",
    "CPU for ROS 2 and planning; RPMsg between real-time and Linux cores on one chip",
]}
HINTS = {
    "throughput": "Divide the bit rate by the bits per payload byte: 10, 9, 8, or 111/8 for CAN.",
    "selection": "Translate each table row into an if statement, in order; return at the first match.",
}
BUS_CASES = [
    ({"same_chip": True, "on_board": True}, "RPMsg"),
    ({"on_board": True, "rate_Bps": 2000}, "I2C"),
    ({"on_board": True, "rate_Bps": 50_000}, "I2C"),
    ({"on_board": True, "rate_Bps": 3_000_000}, "SPI"),
    ({"smart_servos": True, "deterministic": True, "rate_Bps": 100_000}, "Serial"),
    ({"deterministic": True, "cycle_us": 250, "nodes": 12, "rate_Bps": 2_000_000}, "EtherCAT"),
    ({"deterministic": True, "cycle_us": 250, "nodes": 6, "rate_Bps": 200_000}, "CAN FD"),
    ({"deterministic": True, "cycle_us": 1000, "nodes": 6, "rate_Bps": 100_000}, "CAN FD"),
    ({"deterministic": True, "cycle_us": 2000, "nodes": 4, "rate_Bps": 5_000_000}, "Ethernet"),
    ({"rate_Bps": 40_000_000}, "Ethernet"),
]
COMPUTE_CASES = [
    ({"custom_io": True, "deadline_us": 1}, "FPGA"),
    ({"custom_io": True, "deadline_us": 500, "model_gops": 0.01}, "MCU"),
    ({"deadline_us": 50, "model_gops": 0.001}, "MCU"),
    ({"signal_processing": True, "power_w": 0.5, "deadline_us": 5000}, "DSP"),
    ({"model_gops": 50, "datacenter": True, "power_w": 300}, "TPU"),
    ({"model_gops": 8, "power_w": 5, "int8_ok": True}, "NPU"),
    ({"model_gops": 8, "power_w": 5, "int8_ok": False}, "GPU"),
    ({"model_gops": 30, "power_w": 40, "int8_ok": True}, "GPU"),
    ({"model_gops": 0.5}, "CPU"),
    ({}, "CPU"),
]


def check_throughput(bps):
    assert np.isclose(bps("i2c", 400_000), 400_000 / 9) and np.isclose(bps("spi", 20e6), 2.5e6)
    assert np.isclose(bps("uart", 1e6), 1e5) and np.isclose(bps("can", 1e6), 8e6 / 111)


def check_selection(bus, compute):
    for req, want in BUS_CASES:
        got = bus(req)
        assert got == want, f"choose_bus({req}) = {got!r}, table says {want!r}"
    for req, want in COMPUTE_CASES:
        got = compute(req)
        assert got == want, f"choose_compute({req}) = {got!r}, table says {want!r}"
