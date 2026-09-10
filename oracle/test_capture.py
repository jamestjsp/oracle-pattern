"""Explicit native-toolchain checks: run with make audit, not make verify."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock

import run as oracle


class CaptureTests(unittest.TestCase):
    def test_capture_without_go_and_audit(self):
        with tempfile.TemporaryDirectory() as work:
            output=Path(work)/"baseline"
            with mock.patch.object(oracle,"build_candidate",side_effect=AssertionError("capture must not build Go")):
                oracle.capture(output,[20260911],0,"asymmetric-LT")
                manifest,records=oracle.load_baseline(output)
                self.assertEqual(manifest["seeds"],[20260911])
                self.assertEqual(records[0]["expected"]["b"],["9.5","-19.5","-41.5","69.0","-88.5","132.0"])
                report=Path(work)/"audit.json"
                self.assertEqual(oracle.evaluate(output,report,audit=True),0)
                self.assertEqual(json.loads(report.read_text())["kind"],"audit")
            before=oracle.digest(output/"manifest.json")
            with self.assertRaises(FileExistsError):
                oracle.capture(output,[7],0)
            self.assertEqual(before,oracle.digest(output/"manifest.json"))


if __name__ == "__main__":
    unittest.main()
