#!/usr/bin/env python3
"""Build, compare, and replay the independent MB01UD oracle."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARD = -987654321.125
EPS = sys.float_info.epsilon
SCHEMA = 1


def invoke(args, *, data=None, cwd=ROOT):
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    p = subprocess.run(args, input=data, text=True, capture_output=True, cwd=cwd, env=env, timeout=120)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {shlex.join(map(str, args))}\n{p.stderr}\n{p.stdout}")
    return p.stdout


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(build_dir):
    build_dir.mkdir(parents=True, exist_ok=True)
    fc = shutil.which(os.environ.get("FC", "gfortran"))
    go = shutil.which("go")
    if not fc or not go:
        raise RuntimeError("Go and gfortran are required; the oracle cannot be skipped")
    src = ROOT / "reference/SLICOT-Reference/src/MB01UD.f"
    if not src.exists():
        raise RuntimeError("run git submodule update --init --recursive")
    flags = os.environ.get("ORACLE_BLAS_LIBS")
    if flags:
        libs = shlex.split(flags)
        backend = "explicit ORACLE_BLAS_LIBS; see linked-library evidence"
    else:
        pkg = shutil.which("pkg-config")
        if pkg:
            libs = shlex.split(invoke([pkg, "--libs", "openblas"]).strip())
            backend = "OpenBLAS " + invoke([pkg, "--modversion", "openblas"]).strip()
        elif shutil.which("brew"):
            prefix = invoke(["brew", "--prefix", "openblas"]).strip()
            libs = ["-L" + prefix + "/lib", "-lopenblas"]
            backend = "Homebrew OpenBLAS; see linked-library hashes"
        else:
            libs = ["-lopenblas"]
            backend = "system OpenBLAS; see linked-library hashes"
    reference = build_dir / "mb01ud-reference"
    candidate = build_dir / "mb01ud-go"
    compile_cmd = [fc, "-O2", "-fcheck=all", "-fno-fast-math", str(ROOT / "oracle/reference/driver.f90"), str(src), *libs, "-o", str(reference)]
    invoke(compile_cmd)
    invoke([go, "build", "-trimpath", "-o", str(candidate), "./cmd/mb01ud-go"])
    link_tool = "otool" if sys.platform == "darwin" else "ldd"
    link_cmd = [link_tool, "-L", str(reference)] if sys.platform == "darwin" else [link_tool, str(reference)]
    linked = invoke(link_cmd)
    linked_hashes = {}
    for token in linked.split():
        p = Path(token)
        if token.startswith("/") and p.is_file():
            linked_hashes[str(p.resolve())] = digest(p)
    tracked = [src, ROOT / "oracle/reference/driver.f90", ROOT / "oracle/run.py", ROOT / "oracle/test_oracle.py", ROOT / "oracle/cases.json", ROOT / "go.mod", ROOT / "go.sum"]
    tracked += sorted((ROOT / "hessenberg").glob("*.go"))
    tracked += sorted((ROOT / "cmd/mb01ud-go").glob("*.go"))
    return reference, candidate, {
        "platform": platform.platform(), "machine": platform.machine(),
        "fortran": invoke([fc, "--version"]).splitlines()[0],
        "go": invoke([go, "version"]).strip(),
        "go_environment": json.loads(invoke([go, "env", "-json", "GOOS", "GOARCH", "CGO_ENABLED", "GOFLAGS", "GOTOOLCHAIN", "GOAMD64", "GOARM64"])),
        "gonum": json.loads(invoke([go, "list", "-m", "-json", "gonum.org/v1/gonum"])),
        "backend": backend, "linked_libraries": linked, "linked_sha256": linked_hashes,
        "reference_commit": invoke(["git", "-C", str(src.parent.parent), "rev-parse", "HEAD"]).strip(),
        "reference_dirty": bool(invoke(["git", "-C", str(src.parent.parent), "status", "--porcelain"])),
        "project_commit": invoke(["git", "rev-parse", "HEAD"]).strip(),
        "project_dirty": bool(invoke(["git", "status", "--porcelain"])),
        "compile_command": compile_cmd,
        "threads": {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in tracked},
        "binary_sha256": {"reference": digest(reference), "candidate": digest(candidate)},
    }


def strings(values):
    return [repr(v) if math.isfinite(v) else str(v) for v in values]


def make_case(name, side="L", trans="N", m=3, n=2, alpha=1.0, pad=2, scale=1.0, rng=None):
    rng = rng or random.Random(77)
    k = m if side.upper() == "L" else n
    h = [scale * rng.uniform(-2, 2) if i <= j+1 else math.nan for i in range(k) for j in range(k)]
    a = [scale * rng.uniform(-2, 2) for _ in range(m*n)]
    return dict(id=name, side=side, trans=trans, m=m, n=n, alpha=repr(alpha), pad=pad, invalid=0,
                h=strings(h), a=strings(a), b=strings([GUARD] * (m*n)))


def corpus(seed, count):
    cases = json.loads((ROOT / "oracle/cases.json").read_text())
    shapes = [(0, 0), (0, 3), (3, 0), (1, 1), (1, 4), (4, 1), (3, 5), (5, 3)]
    for side in ("L", "R", "l", "r"):
        for trans in ("N", "T", "C", "n", "t", "c"):
            for m, n in shapes:
                for alpha in (0.0, 1.0, -0.75):
                    name = f"grid-{side}{trans}-{m}x{n}-{alpha}"
                    c = make_case(name, side, trans, m, n, alpha)
                    if alpha == 0:
                        c["h"] = ["nan"] * len(c["h"])
                        c["a"] = ["nan"] * len(c["a"])
                        c["b"] = ["nan"] * len(c["b"])
                    cases.append(c)
    for bad in (1, 2, 3, 4, 7, 9, 11):
        for m,n,alpha in ((3,2,1.0),(0,0,0.0),(3,2,0.0)):
            c = make_case(f"invalid-{bad}-{m}x{n}-{alpha}",m=m,n=n,alpha=alpha)
            c["invalid"] = bad
            cases.append(c)
    rng = random.Random(seed)
    for i in range(count):
        c = make_case(f"random-{seed}-{i}",rng.choice("LR"),rng.choice("NTC"),rng.randrange(1,17),rng.randrange(1,17),
                      rng.choice([1.0,-1.0,0.125,1e-50,1e50]),rng.randrange(4),rng.choice([1.0,1e-100,1e100]),rng)
        cases.append(c)
    return cases


def validate_case(c):
    expected = {"id", "side", "trans", "m", "n", "alpha", "pad", "invalid", "h", "a", "b"}
    if set(c) != expected:
        raise ValueError("case fields do not match schema")
    if not isinstance(c["id"],str) or not c["id"] or c["side"] not in ("L","R","l","r") or c["trans"] not in ("N","T","C","n","t","c"):
        raise ValueError("invalid case identity or flags")
    if any(type(c[x]) is not int or not 0 <= c[x] <= 256 for x in ("m","n","pad")):
        raise ValueError("wire dimensions/padding must be integers in [0,256]")
    if c["invalid"] not in (0,1,2,3,4,7,9,11):
        raise ValueError("unknown invalid-argument probe")
    if not isinstance(c["alpha"],str) or not math.isfinite(float(c["alpha"])):
        raise ValueError("alpha must be a finite float encoded as a string")
    k = c["m"] if c["side"].upper() == "L" else c["n"]
    for key,length in (("h",k*k),("a",c["m"]*c["n"]),("b",c["m"]*c["n"])):
        if len(c[key]) != length or any(not isinstance(v,str) for v in c[key]):
            raise ValueError(f"invalid {key} wire array")
        for v in c[key]:
            float(v)


def reference_input(c):
    k = c["m"] if c["side"].upper() == "L" else c["n"]
    lines = [f'{c["side"]} {c["trans"]} {c["m"]} {c["n"]} {c["alpha"]} {c["pad"]} {c["invalid"]}']
    for key,cols in (("h",k),("a",c["n"]),("b",c["n"])):
        if cols:
            lines += [" ".join(c[key][i:i+cols]) for i in range(0,len(c[key]),cols)]
    return "\n".join(lines) + "\n"


def parse_reference(text,c):
    tokens = text.split()
    expected = 3 + len(c["h"]) + len(c["a"]) + len(c["b"])
    if len(tokens) != expected:
        raise ValueError(f"reference returned {len(tokens)} tokens; expected {expected}")
    info,handler,padding = map(int,tokens[:3])
    if padding not in (0,1):
        raise ValueError("invalid reference padding status")
    result = dict(info=info, handler=handler, padding_ok=bool(padding))
    pos = 3
    for key in ("h","a","b"):
        result[key] = strings([float(v) for v in tokens[pos:pos+len(c[key])]])
        pos += len(c[key])
    return result


def exact(a,b):
    x,y = float(a),float(b)
    if math.isnan(x) or math.isnan(y):
        return math.isnan(x) and math.isnan(y)
    return x == y and (x != 0 or math.copysign(1,x) == math.copysign(1,y))


def entry_scale(c,i,j):
    m,n = c["m"],c["n"]
    k = m if c["side"].upper() == "L" else n
    h,a = list(map(float,c["h"])),list(map(float,c["a"]))
    def at(row,col):
        if c["trans"].upper() != "N":
            row,col = col,row
        return h[row*k+col] if row <= col+1 else 0.0
    terms = (abs(at(i,q)*a[q*n+j]) for q in range(k)) if c["side"].upper() == "L" else (abs(a[i*n+q]*at(q,j)) for q in range(k))
    return abs(float(c["alpha"])) * math.fsum(terms)


def compare(c,ref,got):
    failures = []
    for label,result in (("reference",ref),("candidate",got)):
        if type(result.get("info")) is not int:
            failures.append(f"{label}: missing/invalid status")
        if result.get("padding_ok") is not True:
            failures.append(f"{label}: changed padding")
        for key in ("h","a","b"):
            values = result.get(key)
            if not isinstance(values,list) or len(values) != len(c[key]):
                failures.append(f"{label}: {key} length mismatch")
                continue
            if key in ("h","a") or c["invalid"]:
                if not all(exact(x,y) for x,y in zip(values,c[key])):
                    failures.append(f"{label}: changed {key}")
    if failures:
        return failures,0.0
    if ref.get("handler") != -min(ref["info"],0):
        failures.append("reference: XERBLA observation disagrees with INFO")
    if ref["info"] != -c["invalid"]:
        failures.append("reference: unexpected status for contract probe")
    if got["info"] != ref["info"]:
        failures.append(f"status: reference={ref['info']}, candidate={got['info']}")
    if ref["info"] != 0 or failures:
        return failures,0.0
    worst = 0.0
    k = c["m"] if c["side"].upper() == "L" else c["n"]
    for idx,(x,y) in enumerate(zip(ref["b"],got["b"])):
        x,y = float(x),float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            failures.append(f"b[{idx}]: nonfinite result outside accepted domain")
            continue
        if float(c["alpha"]) == 0:
            tolerance = 0.0
        else:
            tolerance = 64 * EPS * max(1,k) * entry_scale(c,idx//c["n"],idx%c["n"]) + 16*math.ulp(0.0)
        if not math.isfinite(tolerance):
            failures.append(f"b[{idx}]: nonfinite comparison scale")
            continue
        error = abs(x-y)
        ratio = error/tolerance if tolerance else (0.0 if error == 0 else math.inf)
        worst = max(worst,ratio)
        if error > tolerance:
            failures.append(f"b[{idx}]: reference={x!r}, candidate={y!r}, abs_error={error!r}, bound={tolerance!r}")
    return failures,worst


def run_case(c,reference,candidate):
    validate_case(c)
    ref = parse_reference(invoke([str(reference)],data=reference_input(c)),c)
    got = json.loads(invoke([str(candidate)],data=json.dumps(c)))
    failures,ratio = compare(c,ref,got)
    return dict(case=c,reference=ref,candidate=got,failures=failures,max_error_over_bound=ratio)


def json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return str(value)
    if isinstance(value,dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):
        return [json_safe(v) for v in value]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int,default=20260910,help="generated-case seed; replay retains its original seed")
    parser.add_argument("--random-cases",type=int,default=400)
    parser.add_argument("--report",type=Path,default=ROOT/"artifacts/report.json")
    parser.add_argument("--cases",type=Path,help="run exactly the cases in this JSON array")
    parser.add_argument("--replay",type=Path,help="replay inputs from a previous report with current binaries")
    parser.add_argument("--case",help="select one case ID")
    args = parser.parse_args()
    if args.random_cases < 0 or (args.cases and args.replay):
        parser.error("use a nonnegative count and choose either --cases or --replay")
    if args.replay:
        prior = json.loads(args.replay.read_text())
        if prior.get("schema") != SCHEMA:
            parser.error("unsupported replay schema")
        cases = [x["case"] for x in prior["results"]]
        campaign_seed = prior.get("seed")
        origin = dict(kind="replay",report_sha256=digest(args.replay),source_corpus_sha256=prior["corpus_sha256"])
    elif args.cases:
        cases = json.loads(args.cases.read_text())
        campaign_seed = None
        origin = dict(kind="imported",cases_sha256=digest(args.cases))
    else:
        cases = corpus(args.seed,args.random_cases)
        campaign_seed = args.seed
        origin = dict(kind="generated")
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
    if not cases or len({c["id"] for c in cases}) != len(cases):
        parser.error("cases must be nonempty with unique IDs")
    for c in cases:
        validate_case(c)
    reference,candidate,provenance = build(ROOT/"artifacts/build")
    if provenance["reference_dirty"]:
        raise RuntimeError("reference submodule is dirty; restore or explicitly version reference changes")
    results = []
    for c in cases:
        try:
            result = run_case(c,reference,candidate)
        except (RuntimeError,ValueError,KeyError,TypeError,OverflowError,subprocess.TimeoutExpired) as e:
            result = dict(case=c,failures=[f"infrastructure: {e}"],max_error_over_bound=None)
        results.append(result)
        if result["failures"]:
            print(f"FAIL {c['id']}: {result['failures'][0]}",file=sys.stderr)
    failed = sum(bool(r["failures"]) for r in results)
    report = dict(schema=SCHEMA,seed=campaign_seed,origin=origin,provenance=provenance,
                  comparison="64*epsilon*max(1,k)*abs(alpha)*sum(abs(product_terms)) + 16*smallest_subnormal; alpha=0 exact",
                  corpus_sha256=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest(),
                  summary=dict(cases=len(results),passed=len(results)-failed,failed=failed,
                               max_error_over_bound=max((r["max_error_over_bound"] or 0 for r in results),default=0)),
                  results=results)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(json_safe(report),indent=2,allow_nan=False)+"\n")
    print(json.dumps(report["summary"]))
    print(f"Report: {args.report}")
    return int(bool(failed))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print(f"oracle: {exc}",file=sys.stderr)
        sys.exit(2)
