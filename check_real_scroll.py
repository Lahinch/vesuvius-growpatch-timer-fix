"""Check final timer metadata while tracing an actual local scroll crop.

Requires the normal native tracer and real input volumes. No synthetic fixture.
The output folder must not exist. Logs and an explicit result are retained.
This checks timer behavior only; it does not certify surface accuracy.
"""
import argparse,json,math,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--executable',required=True,type=Path)
p.add_argument('--volume',required=True,type=Path)
p.add_argument('--params',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--seed',required=True,nargs=3,type=int)
p.add_argument('--library-directory',type=Path,help='Optional local macOS test build; preserves the original app')
p.add_argument('--asan-runtime',type=Path,help='Optional matching macOS sanitizer runtime')
a=p.parse_args();out=a.output.resolve()
if out.exists():p.error('Output already exists; use a fresh test folder.')
out.mkdir(parents=True)
params=json.loads(a.params.read_text());params['snapshot-interval']=0
(out/'params.json').write_text(json.dumps(params,indent=2)+'\n')
cmd=[str(a.executable.resolve()),'-v',str(a.volume.resolve()),'-t',str(out/'surface'),'-p',str(out/'params.json'),'-s',*[str(v) for v in a.seed],'--segment-name','timer-real-scroll-check']
env=os.environ.copy();env['VC_GROWPATCH_RNG_SEED']='0'
if a.library_directory:
    env['DYLD_LIBRARY_PATH']=str(a.library_directory.resolve());env['DYLD_PRINT_LIBRARIES']='1'
if a.asan_runtime:
    env['DYLD_INSERT_LIBRARIES']=str(a.asan_runtime.resolve());env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
start=time.monotonic()
with (out/'trace.log').open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
wall=time.monotonic()-start;meta=out/'surface/meta.json';elapsed=None
if meta.exists():elapsed=json.loads(meta.read_text()).get('elapsed_time_s')
log=(out/'trace.log').read_text()
ok=(r.returncode==0 and isinstance(elapsed,(int,float)) and math.isfinite(elapsed) and 0<=elapsed<=wall+1 and 'ERROR: AddressSanitizer' not in log)
expected_library_loaded=(not a.library_directory or str(a.library_directory.resolve()/'libvc_tracer.dylib') in log)
ok=ok and expected_library_loaded
report=dict(expected_library_loaded=expected_library_loaded,passed=ok,tracer_exit=r.returncode,elapsed_time_s=elapsed,wall_seconds=wall,allowed_clock_margin_seconds=1,command=cmd,seed_xyz=a.seed,rng_seed=0,checks=['native exit status','finite nonnegative elapsed metadata within process wall time + 1 second','no AddressSanitizer error in log'])
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(0 if ok else 1)
