ANSWERS = {"M1": 0xA064, "M2": 20, "M3": 12}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Switched Ethernet: store-and-forward, queuing and per-device stacks make latency load-dependent",
    "EtherCAT: one frame through all slaves, processed on the fly in hardware with fixed nanosecond delay",
    "Distributed clocks keep slaves synchronized (tens of ns)",
    "Working counter shows in the same cycle whether every addressed slave processed its data",
]}
HINTS = {
    "vlan": "Tagged when bytes 12..13 are 0x8100; TCI = bytes 14..15 big-endian.",
    "ptp": "Slave stamps = master time + true offset; t2 = t1 + d_forward + offset, t4 = (t3 - offset) + d_reverse.",
    "rstp_ecat": "Root = lowest (priority, MAC as a number). WKC: inputs +1, outputs +2.",
}


def check_vlan(fn):
    tagged = bytes(12) + bytes.fromhex("8100A0640800") + bytes(46)
    assert fn(tagged) == (100, 5, 0, 0x0800), f"tagged frame -> {fn(tagged)}"
    tagged2 = bytes(12) + bytes.fromhex("8100F0010800") + bytes(46)
    assert fn(tagged2) == (1, 7, 1, 0x0800), f"PCP 7, DEI 1, VID 1 -> {fn(tagged2)}"
    assert fn(bytes(12) + bytes.fromhex("0800") + bytes(46)) is None, "untagged frame -> None"


def check_ptp(ptp, sim):
    assert ptp(1000, 1060, 1100, 1120) == (20, 40)
    t = sim(true_offset=3.0, d_forward=7.0, d_reverse=7.0)
    off, dly = ptp(*t)
    assert abs(off - 3.0) < 1e-9 and abs(dly - 7.0) < 1e-9, f"symmetric path must recover the offset: {off}, {dly}"
    off, dly = ptp(*sim(true_offset=0.0, d_forward=10.0, d_reverse=14.0))
    assert abs(off + 2.0) < 1e-9 and abs(dly - 12.0) < 1e-9, f"asymmetric path: offset {off}, delay {dly}"


def check_rstp_ecat(root, wkc):
    br = [(32768, "00:1b:21:aa:00:05"), (4096, "00:1b:21:ff:00:01"), (4096, "00:1b:21:0a:00:09")]
    assert root(br) == "00:1b:21:0a:00:09", "lowest priority first, then lowest MAC"
    assert wkc([(True, True)] * 4) == 12
    assert wkc([(True, False), (False, True), (True, True)]) == 6


def c_vlan(lib):
    import ctypes as C
    from roboprep.cbind import Functions, u8
    f = Functions(lib, "d13")

    def parse_vlan(frame):
        vid, pcp, dei, et = C.c_uint16(), C.c_uint8(), C.c_uint8(), C.c_uint16()
        if not f.parse_vlan(*u8(frame), C.byref(vid), C.byref(pcp), C.byref(dei), C.byref(et)):
            return None
        return vid.value, pcp.value, dei.value, et.value
    return (parse_vlan,)


def c_ptp(lib):
    import ctypes as C
    from roboprep.cbind import Functions, out
    f = Functions(lib, "d13")

    def ptp(t1, t2, t3, t4):
        o, d = C.c_double(), C.c_double()
        f.ptp(t1, t2, t3, t4, C.byref(o), C.byref(d))
        return o.value, d.value

    def simulate_exchange(true_offset, d_forward, d_reverse, t1=0.0, t3_after_t2=5.0):
        t = out(C.c_double, 4)
        f.simulate_exchange(true_offset, d_forward, d_reverse, t1, t3_after_t2, t)
        return tuple(t[:4])
    return ptp, simulate_exchange


def c_rstp_ecat(lib):
    import ctypes as C
    from roboprep.cbind import Functions, arr
    f = Functions(lib, "d13")

    def root_bridge(bridges):
        macs = (C.c_char_p * len(bridges))(*[m.encode() for _, m in bridges])
        return bridges[f.root_bridge(arr(C.c_uint16, [p for p, _ in bridges]), macs, len(bridges))][1]

    def expected_wkc_lrw(slaves):
        return f.expected_wkc_lrw(arr(C.c_bool, [bool(i) for i, _ in slaves]), arr(C.c_bool, [bool(o) for _, o in slaves]), len(slaves))
    return root_bridge, expected_wkc_lrw
