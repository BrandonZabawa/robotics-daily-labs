import hashlib
import re

ANSWERS = {"M1": 3, "M2": 2048}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "Download and verify a signed bundle; write the inactive slot while the active one runs",
    "Bootloader tries the new slot with a boot counter or try flag",
    "Health check marks it good; failure, hang or watchdog makes the bootloader fall back",
    "Data partition keeps configuration, calibration and logs across updates and rollbacks",
]}
HINTS = {
    "sstate": "Build signatures in order; a task's text includes its dependencies' signatures.",
    "fragments": "Later files override earlier ones; '# CONFIG_X is not set' means 'n'.",
    "module_recipe": "inherit module; RPROVIDES:${PN} += \"kernel-module-rdl-led\".",
}

TASKS = {
    "fetch": {"inputs": ["SRC_URI=git://example/rdl;branch=main", "SRCREV=abc123"], "deps": []},
    "unpack": {"inputs": ["S=${UNPACKDIR}"], "deps": ["fetch"]},
    "patch": {"inputs": ["0001-fix.patch"], "deps": ["unpack"]},
    "configure": {"inputs": ["EXTRA_OECMAKE="], "deps": ["patch"]},
    "compile": {"inputs": ["CFLAGS=-O2"], "deps": ["configure"]},
    "install": {"inputs": ["bindir=/usr/bin"], "deps": ["compile"]},
    "package": {"inputs": ["PACKAGES=${PN}"], "deps": ["install"]},
}




SIGNATURES = {
    "fetch": "29f5a19b43539569a6e8dd67547cc1915119322847c01d75514b4e0222110271",
    "unpack": "cdde0522c82f7e03fb1f26f4fcfbf6436ea9fabb5012dbe49536ed49f899961a",
    "patch": "ab2a671b2f203846f180349a728bd6d7f193a05d8609730949f5ee013fb1911a",
    "configure": "8b5693cf9630602e5411b97de9db1d17f5b89b968033be2cc25a6fa6af12e846",
    "compile": "64efedf68b500075bfaaa38306b92132ff6586b24f9f5346f80f052008d18e9e",
    "install": "30b52320eb2548161fc05ade909e1234e383288833b5994f74219be050ef6850",
    "package": "64f49f9604f79c77a21d0907820c77155509c0ed6aecb41ad63aef8c4b4ab4ec",
}


def check_sstate(signatures, rerun):
    s = signatures(TASKS)
    assert s == SIGNATURES, "signature recipe differs from the spec"
    t2 = {k: dict(v) for k, v in TASKS.items()}
    t2["compile"] = {"inputs": ["CFLAGS=-O2 -g"], "deps": ["configure"]}
    assert rerun(s, signatures(t2)) == {"compile", "install", "package"}, "a compile flag change reruns compile and later"
    t3 = {k: dict(v) for k, v in TASKS.items()}
    t3["fetch"] = {"inputs": ["SRC_URI=git://example/rdl;branch=main", "SRCREV=def456"], "deps": []}
    assert rerun(s, signatures(t3)) == set(TASKS), "a new source revision reruns everything"
    assert rerun(s, signatures(TASKS)) == set(), "nothing changed, nothing reruns"


def check_fragments(fn):
    base = "CONFIG_IIO=m\nCONFIG_SPI_STM32=y\n# CONFIG_DEBUG_INFO is not set\nCONFIG_LOCALVERSION=\"-std\"\n"
    frag1 = "CONFIG_IIO=y\nCONFIG_INV_ICM42600_SPI=m\n"
    frag2 = "CONFIG_DEBUG_INFO=y\n# CONFIG_SPI_STM32 is not set\nCONFIG_LOCALVERSION=\"-rdl\"\n"
    got = fn(base, frag1, frag2)
    want = {"CONFIG_IIO": "y", "CONFIG_SPI_STM32": "n", "CONFIG_DEBUG_INFO": "y", "CONFIG_LOCALVERSION": "-rdl",
            "CONFIG_INV_ICM42600_SPI": "m"}
    assert got == want, f"merged: {got}"


def check_module_recipe():
    t = open("rdl-led-mod_0.1.bb").read()
    assert re.search(r'^inherit\s+module\b', t, re.M), "inherit module"
    assert re.search(r'^LICENSE\s*=\s*"GPL-2\.0', t, re.M), "kernel modules are GPL-2.0-only"
    assert re.search(r'LIC_FILES_CHKSUM\s*=\s*"file://COPYING;md5=[0-9a-f]{32}"', t), "LIC_FILES_CHKSUM for COPYING"
    src = re.search(r'SRC_URI\s*=\s*"([^"]*)"', t)
    assert src and all(f in src.group(1) for f in ("file://Makefile", "file://rdl_led.c", "file://COPYING")), "SRC_URI files"
    assert re.search(r'RPROVIDES:\$\{PN\}\s*\+=\s*"kernel-module-rdl-led"', t), "RPROVIDES:${PN} += \"kernel-module-rdl-led\""
