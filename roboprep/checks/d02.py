from roboprep import clab

ANSWERS = {"M1": 101, "M2": 64, "M3": [0x02, 0x11, 0x02, 0x22]}
CHOICES = {"K1": "b"}
RUBRIC = {"K2": [
    "0x00 never appears inside a COBS frame, so the next delimiter always realigns",
    "At most the damaged frame is lost; the CRC rejects it",
    "Length prefix: a lost byte corrupts the length and shifts everything after it",
    "Length-prefixed resync needs byte-by-byte hunting or timeouts; COBS overhead is only 1 byte per 254",
]}
HINTS = {
    "cobs": "Encode: keep the index of the current code byte; on a zero (or 254 data bytes) write the code and start a new block.",
    "parser": "Non-zero bytes go into raw[] (set overflow if full); on 0x00 decode, check CRC (big-endian last 2 bytes), then reset.",
    "dispatch": "Loop over table; check args length; compare seq with last_seq before calling the handler.",
}
SRC = ["cobs.c", "proto.c", "crc.c"]


def check_cobs():
    clab.run_ctest(SRC, "d02_test.c", run_args="cobs").require(9)


def check_parser():
    clab.run_ctest(SRC, "d02_test.c", run_args="parser").require(5)


def check_dispatch():
    clab.run_ctest(SRC, "d02_test.c", run_args="dispatch").require(7)
