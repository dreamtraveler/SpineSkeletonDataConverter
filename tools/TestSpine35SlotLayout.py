#!/usr/bin/env python3
"""Regression tests for Spine 3.5 slots, which have no binary dark-color field.

Run: python tools/TestSpine35SlotLayout.py --exe build/Release/SpineSkeletonDataConverter.exe
"""

import argparse
import copy
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


# Hand-encoded independently of the converter's reader and writer. Two slots
# expose a cursor error in the first slot when reading the second bone index.
def skeleton_binary(nonessential):
    binary = b"\x01\x073.5.35"  # Empty hash and version string.
    binary += struct.pack(">ff?", 0, 0, nonessential)
    if nonessential:
        binary += struct.pack(">f", 30) + b"\x00"  # FPS, null images path.
    binary += b"\x02"  # Bone count.
    transform = struct.pack(">8f", 0, 0, 0, 1, 1, 0, 0, 0) + b"\x00"
    for name_and_parent in (b"\x05root", b"\x04tip\x00"):
        binary += name_and_parent + transform
        if nonessential:
            binary += bytes.fromhex("9b9b9bff")
    binary += (
        b"\x02"  # Slot count.
        b"\x0bzuojianjia\x00\xff\xff\xff\xff\x0bzuojianjia\x00"
        b"\x06other\x01\x11\x22\x33\x44\x00\x01"
    )
    # IK, transform, path, default skin slots, additional skins, events, animations.
    return binary + b"\x00" * 7


SKELETON_JSON = {
    "skeleton": {"hash": "", "spine": "3.5.35", "width": 0, "height": 0},
    "bones": [{"name": "root"}, {"name": "tip", "parent": "root"}],
    "slots": [
        {"name": "zuojianjia", "bone": "root", "attachment": "zuojianjia"},
        {"name": "other", "bone": "tip", "color": "11223344", "blend": "additive"},
    ],
    "skins": {"default": {}},
}


class Spine35SlotLayoutTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def convert(self, source, output, *options):
        result = subprocess.run(
            [str(self.exe), str(source), str(output), *options],
            capture_output=True, text=True, errors="replace", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reads_slots_without_dark_color(self):
        for nonessential in (False, True):
            for version in ("3.5.35", "3.8.99"):
                with self.subTest(nonessential=nonessential, output_version=version):
                    source = self.directory / "input.skel"
                    output = self.directory / "output.json"
                    source.write_bytes(skeleton_binary(nonessential))
                    self.convert(source, output, "-v", version)
                    actual = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(actual["skeleton"]["spine"], version)
                    self.assertEqual(actual["bones"], SKELETON_JSON["bones"])
                    self.assertEqual(actual["slots"], SKELETON_JSON["slots"])

    def test_writes_slots_without_dark_color(self):
        for input_version in ("3.5.35", "3.6.32"):
            with self.subTest(input_version=input_version):
                data = copy.deepcopy(SKELETON_JSON)
                data["skeleton"]["spine"] = input_version
                if input_version == "3.6.32":
                    data["slots"][0]["dark"] = "123456"
                source = self.directory / "input.json"
                output = self.directory / "output.skel"
                source.write_text(json.dumps(data), encoding="utf-8")
                self.convert(source, output, "-v", "3.5.35")
                self.assertEqual(output.read_bytes(), skeleton_binary(True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    args = parser.parse_args()
    Spine35SlotLayoutTest.exe = args.exe.resolve()
    unittest.main(argv=[__file__], verbosity=2)
