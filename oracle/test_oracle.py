import copy
import json
import math
from pathlib import Path
import tempfile
import sys
import unittest

import run as oracle


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.case = json.loads((oracle.ROOT / "oracle/cases.json").read_text())[0]
        self.reference = dict(info=0,handler=0,padding_ok=True,h=self.case["h"],a=self.case["a"],
                              b=["-23","33","58.5","-106","-41","62"])
        self.candidate = copy.deepcopy(self.reference)
        del self.candidate["handler"]

    def test_accepts_identical_and_roundoff(self):
        self.assertEqual(oracle.compare(self.case,self.reference,self.candidate)[0],[])
        self.candidate["b"][0] = repr(math.nextafter(-23,0))
        self.assertEqual(oracle.compare(self.case,self.reference,self.candidate)[0],[])

    def test_rejects_result_status_storage_and_nonfinite_mutations(self):
        for key,value in (("info",-1),("padding_ok",False),("b",["0"]*6),("b",[]),("h",[])):
            with self.subTest(key=key,value=value):
                got=copy.deepcopy(self.candidate)
                got[key]=value
                self.assertTrue(oracle.compare(self.case,self.reference,got)[0])
        for key in ("h","a"):
            got=copy.deepcopy(self.candidate)
            got[key][0]="123"
            self.assertTrue(oracle.compare(self.case,self.reference,got)[0])
        for bad in ("nan","inf","-inf"):
            got=copy.deepcopy(self.candidate)
            ref=copy.deepcopy(self.reference)
            got["b"][0]=bad
            self.assertTrue(oracle.compare(self.case,ref,got)[0])
            ref["b"][0]=bad
            self.assertTrue(oracle.compare(self.case,ref,got)[0],"matching nonfinite outputs must not pass")

    def test_small_results_have_no_unit_absolute_tolerance_floor(self):
        c=oracle.make_case("tiny",m=1,n=1,scale=1e-100)
        ref=dict(info=0,handler=0,padding_ok=True,h=c["h"],a=c["a"],b=["1e-200"])
        got=copy.deepcopy(ref)
        got["b"]=["0"]
        self.assertTrue(oracle.compare(c,ref,got)[0])

    def test_protocol_truncation_extra_output_and_error_hook(self):
        for text in ("", "0 0 1", "0 0 1 extra"):
            with self.assertRaises(ValueError):
                oracle.parse_reference(text,self.case)
        self.reference["handler"]=1
        self.assertTrue(oracle.compare(self.case,self.reference,self.candidate)[0])

    def test_replay_float_roundtrip_and_validation(self):
        c=oracle.make_case("replay")
        c["h"][0]="-0.0"
        c["a"][0]=repr(math.nextafter(1,2))
        restored=json.loads(json.dumps(c))
        oracle.validate_case(restored)
        self.assertEqual(restored,c)
        self.assertTrue(oracle.exact("-0.0","-0"))
        self.assertFalse(oracle.exact("-0.0","0"))
        c["a"].pop()
        with self.assertRaises(ValueError):
            oracle.validate_case(c)
        json.dumps(oracle.json_safe({"error_ratio":math.inf}),allow_nan=False)


class ExecutableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="oracle-validation-")
        cls.build=Path(cls.temp.name)
        cls.reference,cls.candidate,_=oracle.build(cls.build)
        cls.cases=json.loads((oracle.ROOT / "oracle/cases.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_independent_hand_calculated_adapter_anchors(self):
        expected={"LN":[-23,33,58.5,-106,-41,62],"LT":[9.5,-19.5,-41.5,69,-88.5,132],
                  "RN":[-8,-9.5,-14.5,-32,31.5,71],"RT":[2,-14.5,10.5,-17,-23.5,36]}
        for c in self.cases[:6]:
            with self.subTest(case=c["id"]):
                result=oracle.run_case(c,self.reference,self.candidate)
                self.assertEqual(result["failures"],[])
                key=c["side"]+("T" if c["trans"]=="C" else c["trans"])
                self.assertEqual(list(map(float,result["reference"]["b"])),expected[key])
                self.assertEqual(list(map(float,result["candidate"]["b"])),expected[key])

    def test_rejects_real_candidate_mutations(self):
        source=oracle.ROOT / "hessenberg/product.go"
        original=source.read_text()
        edits={
            "omit-subdiagonal":("v := h.Data[(j+1)*h.Stride+j]","v := 0.0"),
            "ignore-transpose":("if trans == blas.ConjTrans {","trans = blas.NoTrans\n\tif trans == blas.ConjTrans {"),
            "corrupt-input":("\n\treturn nil\n}\n\nfunc upper", "\n\ta.Data[0] += 1\n\treturn nil\n}\n\nfunc upper"),
        }
        for name,(old,new) in edits.items():
            with self.subTest(mutation=name):
                self.assertEqual(original.count(old),1,"mutation no longer identifies one source site")
                mutated=self.build / (name+".go")
                mutated.write_text(original.replace(old,new))
                overlay=self.build / (name+".json")
                overlay.write_text(json.dumps({"Replace":{str(source):str(mutated)}}))
                binary=self.build / name
                oracle.invoke(["go","build","-overlay",str(overlay),"-o",str(binary),"./cmd/mb01ud-go"])
                results=[oracle.run_case(c,self.reference,binary) for c in self.cases[:6]]
                self.assertTrue(any(r["failures"] for r in results),f"oracle accepted {name}")

    def test_cli_replay_preserves_exact_inputs_and_rebuilds(self):
        first=self.build / "first.json"
        second=self.build / "replayed.json"
        oracle.invoke([sys.executable,"oracle/run.py","--seed","20260911","--random-cases","0","--case",self.cases[1]["id"],"--report",str(first)])
        oracle.invoke([sys.executable,"oracle/run.py","--replay",str(first),"--case",self.cases[1]["id"],"--report",str(second)])
        a,b=json.loads(first.read_text()),json.loads(second.read_text())
        self.assertEqual(a["summary"]["failed"],0)
        self.assertEqual(b["summary"]["failed"],0)
        self.assertEqual(a["seed"],b["seed"])
        self.assertEqual(b["origin"]["kind"],"replay")
        self.assertEqual(b["origin"]["report_sha256"],oracle.digest(first))
        self.assertEqual(a["corpus_sha256"],b["corpus_sha256"])
        self.assertEqual(a["results"][0]["case"],b["results"][0]["case"])
        self.assertEqual(a["results"][0]["reference"],b["results"][0]["reference"])
        with self.assertRaises(RuntimeError):
            oracle.invoke([sys.executable,"oracle/run.py","--replay",str(first),"--case","absent","--report",str(second)])

    def test_invalid_contract_and_padding(self):
        for bad in (1,2,3,4,7,9,11):
            c=oracle.make_case(f"invalid-{bad}")
            c["invalid"]=bad
            result=oracle.run_case(c,self.reference,self.candidate)
            self.assertEqual(result["failures"],[])
            self.assertEqual(result["reference"]["info"],-bad)
            self.assertEqual(result["reference"]["handler"],bad)


if __name__ == "__main__":
    unittest.main()
