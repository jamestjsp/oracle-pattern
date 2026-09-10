#!/usr/bin/env python3
"""Capture legacy calls once; verify Go offline; audit the reference explicitly."""
import argparse
import gzip
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
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GUARD = -987654321.125
EPS = sys.float_info.epsilon
SCHEMA = 2
POLICY = "mb01ud-float64-v1"
BASELINE = ROOT / "oracle/baselines/mb01ud-v1"


def invoke(args, *, data=None, cwd=ROOT):
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    p = subprocess.run(args, input=data, text=True, capture_output=True, cwd=cwd, env=env, timeout=120)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {shlex.join(map(str, args))}\n{p.stderr}\n{p.stdout}")
    return p.stdout


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_reference(build_dir):
    build_dir.mkdir(parents=True, exist_ok=True)
    fc = shutil.which(os.environ.get("FC", "gfortran"))
    if not fc:
        raise RuntimeError("gfortran is required for capture/audit, not offline verify")
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
    compile_cmd = [fc, "-O2", "-fcheck=all", "-fno-fast-math", str(ROOT / "oracle/reference/driver.f90"), str(src), *libs, "-o", str(reference)]
    invoke(compile_cmd)
    link_tool = "otool" if sys.platform == "darwin" else "ldd"
    link_cmd = [link_tool, "-L", str(reference)] if sys.platform == "darwin" else [link_tool, str(reference)]
    linked = invoke(link_cmd)
    linked_hashes = {}
    for token in linked.split():
        p = Path(token)
        if token.startswith("/") and p.is_file():
            linked_hashes[str(p.resolve())] = digest(p)
    if invoke(["git", "-C", str(src.parent.parent), "status", "--porcelain"]):
        raise RuntimeError("reference submodule is dirty")
    return reference, {
        "platform": platform.platform(), "python": platform.python_version(),
        "fortran": invoke([fc, "--version"]).splitlines()[0],
        "backend": backend, "linked_libraries": linked, "linked_sha256": linked_hashes,
        "reference_commit": invoke(["git", "-C", str(src.parent.parent), "rev-parse", "HEAD"]).strip(),
        "project_commit": invoke(["git", "rev-parse", "HEAD"]).strip(),
        "project_dirty": bool(invoke(["git", "status", "--porcelain"])),
        "compile_command": compile_cmd,
        "threads": {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (src, ROOT/"oracle/reference/driver.f90", ROOT/"oracle/run.py", ROOT/"oracle/cases.json")},
        "binary_sha256": digest(reference),
    }


def build_candidate(build_dir):
    build_dir.mkdir(parents=True, exist_ok=True)
    go = shutil.which("go")
    if not go:
        raise RuntimeError("Go is required for verify")
    candidate = build_dir / "mb01ud-go"
    invoke([go, "build", "-trimpath", "-o", str(candidate), "./cmd/mb01ud-go"])
    sources = [ROOT/"go.mod", ROOT/"go.sum", ROOT/"oracle/run.py"]
    sources += sorted((ROOT/"hessenberg").glob("*.go"))
    sources += sorted((ROOT/"cmd/mb01ud-go").glob("*.go"))
    return candidate, {
        "platform": platform.platform(), "python": platform.python_version(),
        "go": invoke([go,"version"]).strip(),
        "go_environment": json.loads(invoke([go,"env","-json","GOOS","GOARCH","CGO_ENABLED","GOFLAGS","GOTOOLCHAIN"])),
        "gonum": json.loads(invoke([go,"list","-m","-json","gonum.org/v1/gonum"])),
        "source_sha256": {str(p.relative_to(ROOT)):digest(p) for p in sources},
        "binary_sha256": digest(candidate),
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


def observe_reference(c, executable):
    return parse_reference(invoke([str(executable)],data=reference_input(c)),c)


def verify_call(record, executable, *, audit=False):
    c,expected = record["case"],record["expected"]
    actual = observe_reference(c,executable) if audit else json.loads(invoke([str(executable)],data=json.dumps(c)))
    failures,ratio = compare(c,expected,actual)
    if audit and actual.get("handler") != expected["handler"]:
        failures.append("reference error handler changed")
    return dict(case_id=c["id"],trace=record["trace"],actual=actual,failures=failures,max_error_over_bound=ratio)


def json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return str(value)
    if isinstance(value,dict):
        return {k:json_safe(v) for k,v in value.items()}
    if isinstance(value,list):
        return [json_safe(v) for v in value]
    return value


def select(records, case_id):
    selected = [r for r in records if r["case"]["id"] == case_id] if case_id else records
    if not selected:
        raise ValueError("no matching calls; an empty verification is not a pass")
    return selected


def load_baseline(path):
    manifest = json.loads((path/"manifest.json").read_text())
    if manifest.get("schema") != SCHEMA or manifest.get("kind") != "legacy-baseline" or manifest.get("policy") != POLICY:
        raise ValueError("unsupported baseline schema or comparison policy")
    calls = path/"calls.jsonl.gz"
    if digest(calls) != manifest["calls_sha256"]:
        raise ValueError("baseline calls checksum mismatch")
    with gzip.open(calls,"rt") as f:
        records = [json.loads(line) for line in f]
    if not records or len(records) != manifest["count"] or len({r["case"]["id"] for r in records}) != len(records):
        raise ValueError("baseline must contain the declared number of unique calls")
    for r in records:
        validate_case(r["case"])
        if r["trace"] != trace(r["case"]):
            raise ValueError("invalid MB01UD harness trace identity")
        failures,_ = compare(r["case"],r["expected"],r["expected"])
        if failures:
            raise ValueError("invalid captured observation: " + "; ".join(failures))
    return manifest,records


def trace(c):
    return dict(scenario=c["id"],caller="oracle/reference/driver.f90",callee="MB01UD",invocation=1)


def capture(output,seeds,count,case_id=None):
    if output.exists():
        raise FileExistsError("baseline already exists; choose a new version directory")
    cases = {}
    for seed in seeds:
        for c in corpus(seed,count):
            cases.setdefault(c["id"],c)
    selected = select([dict(case=c) for c in cases.values()],case_id)
    records=[]
    with tempfile.TemporaryDirectory(prefix="oracle-capture-") as work:
        reference,provenance = build_reference(Path(work))
        for r in selected:
            c=r["case"]
            validate_case(c)
            expected=observe_reference(c,reference)
            failures,_=compare(c,expected,expected)
            if failures:
                raise ValueError(f"reference capture failed for {c['id']}: {failures}")
            records.append(dict(trace=trace(c),case=c,expected=expected))
    output.mkdir(parents=True,exist_ok=False)
    payload="".join(json.dumps(r,separators=(",",":"),allow_nan=False)+"\n" for r in records).encode()
    calls=output/"calls.jsonl.gz"
    calls.write_bytes(gzip.compress(payload,mtime=0))
    manifest=dict(schema=SCHEMA,kind="legacy-baseline",routine="MB01UD",policy=POLICY,seeds=seeds,
                  random_cases_per_seed=count,count=len(records),calls_sha256=digest(calls),reference=provenance)
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Captured {len(records)} calls: {output}")


def evaluate(baseline,report,case_id=None,*,audit=False):
    manifest,records=load_baseline(baseline)
    records=select(records,case_id)
    if report.resolve().is_relative_to(baseline.resolve()):
        raise ValueError("report must not overwrite any part of the baseline")
    results=[]
    with tempfile.TemporaryDirectory(prefix="oracle-verify-") as work:
        executable,provenance=(build_reference if audit else build_candidate)(Path(work))
        for record in records:
            try:
                result=verify_call(record,executable,audit=audit)
            except (RuntimeError,ValueError,KeyError,TypeError,OverflowError,OSError,subprocess.TimeoutExpired) as e:
                result=dict(case_id=record["case"]["id"],trace=record["trace"],failures=[f"infrastructure: {e}"],max_error_over_bound=None)
            results.append(result)
            if result["failures"]:
                print(f"FAIL {result['case_id']}: {result['failures'][0]}",file=sys.stderr)
    failed=sum(bool(r["failures"]) for r in results)
    result=dict(schema=SCHEMA,kind="audit" if audit else "verification",policy=POLICY,
                baseline=dict(manifest_sha256=digest(baseline/"manifest.json"),calls_sha256=manifest["calls_sha256"],seeds=manifest["seeds"]),
                build=provenance,summary=dict(calls=len(results),passed=len(results)-failed,failed=failed,
                    max_error_over_bound=max((r["max_error_over_bound"] or 0 for r in results),default=0)),results=results)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(json_safe(result),indent=2,allow_nan=False)+"\n")
    print(json.dumps(result["summary"]))
    print(f"Report: {report}")
    return int(bool(failed))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    record=commands.add_parser("capture",help="create a new legacy-only baseline; never overwrite")
    record.add_argument("--output",type=Path,required=True)
    record.add_argument("--seed",type=int,action="append",help="repeat for multiple seeds")
    record.add_argument("--random-cases",type=int,default=400)
    record.add_argument("--case",help="capture one matching case")
    for command in ("verify","audit"):
        sub=commands.add_parser(command,help="run Go offline" if command=="verify" else "recheck the legacy executable")
        sub.add_argument("--baseline",type=Path,default=BASELINE)
        sub.add_argument("--case",help="replay one captured call")
        sub.add_argument("--report",type=Path,default=ROOT/f"artifacts/{command}.json")
    args=parser.parse_args()
    if args.command=="capture":
        if args.random_cases<0:
            parser.error("random case count must be nonnegative")
        capture(args.output,args.seed or [20260910,20260911],args.random_cases,args.case)
        return 0
    return evaluate(args.baseline,args.report,args.case,audit=args.command=="audit")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError,ValueError,KeyError,TypeError,OSError,OverflowError,subprocess.TimeoutExpired) as exc:
        print(f"oracle: {exc}",file=sys.stderr)
        sys.exit(2)
