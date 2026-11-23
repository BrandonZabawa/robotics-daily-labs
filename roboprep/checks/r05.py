import re

ANSWERS = {"M1": 7, "M2": 1, "M3": 3}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "MACHINE: hardware description in a BSP layer (conf/machine), selected in local.conf",
    "DISTRO: policy (DISTRO_FEATURES, init manager, toolchain) in a distro layer",
    "Image recipe: IMAGE_INSTALL / IMAGE_FEATURES for one root filesystem, in your layer",
    "Separation lets one image build for many machines and one machine run many images",
]}
HINTS = {
    "evaluator": "Apply = ?= := += =+ .= =. while parsing; store :append/:prepend/:remove and overrides; resolve them when reading.",
    "tasks": "Fetch, unpack, patch, configure, compile, install, package.",
    "recipe": "do_install: install -d ${D}${bindir}; install -m 0755 hello ${D}${bindir}.",
}

CASES = [
    ('A ?= "aval"\nA ?= "bval"', (), {"A": "aval"}),
    ('W ??= "x"\nW ??= "y"', (), {"W": "y"}),
    ('W ??= "x"\nW = "z"', (), {"W": "z"}),
    ('W ??= "x"\nA := "${W}"\nW ??= "y"\nB := "${W}"\nW ??= "z"\nC = "${W}"\nW ?= "i"', (),
     {"W": "i", "A": "x", "B": "y", "C": "i"}),
    ('B = "bval"\nB += "additional"', (), {"B": "bval additional"}),
    ('C = "cval"\nC =+ "test"', (), {"C": "test cval"}),
    ('B = "bval"\nB .= "additional"', (), {"B": "bvaladditional"}),
    ('C = "cval"\nC =. "test"', (), {"C": "testcval"}),
    ('T = "123"\nA := "test ${T}"\nT = "456"\nB := "${T} ${C}"\nC = "cval"\nC := "${C}append"', (),
     {"T": "456", "A": "test 123", "B": "456 cvalappend", "C": "cvalappend"}),
    ('KBRANCH = "standard"\nKBRANCH:mymachine = "special"', ("arm", "mymachine"), {"KBRANCH": "special"}),
    ('KBRANCH = "standard"\nKBRANCH:mymachine = "special"', ("arm",), {"KBRANCH": "standard"}),
    ('DEPENDS = "glibc ncurses"\nDEPENDS:append = " doxygen"', (), {"DEPENDS": "glibc ncurses doxygen"}),
    ('A:append = " late"\nA = "early"', (), {"A": "early late"}),
    ('A = "Y"\nA:append:foo = "Z"', ("foo",), {"A": "YZ"}),
    ('A = "Y"\nA:append:foo = "Z"', (), {"A": "Y"}),
    ('A = "x"\nA:append = " app"\nA:foo = "over"', ("foo",), {"A": "over app"}),
    ('FOO = "123 456 789 123456 123 456 123 456"\nFOO:remove = "123"\nFOO:remove = "456"', (), {"FOO": "789 123456"}),
    ('B = "bval"\nB:prepend = "additional "', (), {"B": "additional bval"}),
    ('# comment\nA = "${B} world"\n\nB = "hello"', (), {"A": "hello world", "B": "hello"}),
]


def check_evaluator(fn):
    for text, ovr, want in CASES:
        got = fn(text, ovr)
        got = {k: (" ".join(v.split()) if "remove" in text else v) for k, v in got.items()}
        assert got == want, f"\n{text}\nOVERRIDES={list(ovr)}\n-> {got}, want {want}"


def check_tasks(chain):
    if chain is None:
        raise NotImplementedError
    assert list(chain) == ["do_fetch", "do_unpack", "do_patch", "do_configure", "do_compile", "do_install", "do_package"], chain


def check_recipe():
    t = open("hello-rdl_1.0.bb").read()
    assert re.search(r'^LICENSE\s*=\s*"MIT"', t, re.M), "LICENSE = \"MIT\""
    assert re.search(r'LIC_FILES_CHKSUM\s*=\s*"file://\$\{COMMON_LICENSE_DIR\}/MIT;md5=[0-9a-f]{32}"', t), "LIC_FILES_CHKSUM with an md5"
    assert re.search(r'SRC_URI\s*=\s*"[^"]*file://hello\.c', t), "SRC_URI must fetch file://hello.c"
    comp = re.search(r"do_compile\(\)\s*\{\n(.*?)\n\}", t, re.S)
    assert comp and "${CC}" in comp.group(1) and "${LDFLAGS}" in comp.group(1), "do_compile must use ${CC} and ${LDFLAGS}"
    inst = re.search(r"do_install\(\)\s*\{\n(.*?)\n\}", t, re.S)
    assert inst and "install -d ${D}${bindir}" in inst.group(1) and "${D}${bindir}" in inst.group(1).split("install -d", 1)[1], \
        "do_install must create and install into ${D}${bindir}"
