"""Build the CURRENT native source as WASM in an ignored, isolated build directory."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def prepare(work):
    source=work/'source'
    if source.exists():raise FileExistsError(f'{source}: choose a new --work directory to avoid stale or overwritten source')
    source.mkdir(parents=True)
    for name in ['engine','third_party']:shutil.copytree(ROOT/name,source/name,ignore=shutil.ignore_patterns('__pycache__','.git'))
    shutil.copy2(ROOT/'CMakeLists.txt',source/'CMakeLists.txt')
    subprocess.run([sys.executable,str(Path(__file__).with_name('patch_engine.py')),str(source)],check=True)
    return source
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emsdk',type=Path,default=os.environ.get('EMSDK'));p.add_argument('--work',type=Path,default=ROOT/'build/wasm');p.add_argument('--prepare-only',action='store_true');p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
    source=prepare(a.work.resolve())
    if a.prepare_only:print(source);return
    if not a.emsdk:p.error('Set EMSDK or pass --emsdk; install/activate Emscripten first')
    sdk=a.emsdk.resolve();env=os.environ.copy();env['EMSDK']=str(sdk);env['EM_CONFIG']=str(sdk/'.emscripten');env['EM_CACHE']=str(a.work.resolve()/'em-cache')
    env['PATH']=str(sdk/'upstream/emscripten')+os.pathsep+str(sdk/'upstream/bin')+os.pathsep+env['PATH']
    # SDK config records its activated Python/Node; no machine-specific paths are embedded here.
    build=a.work.resolve()/'engine'
    flags='-fwasm-exceptions -sMODULARIZE=1 -sEXPORT_ES6=1 -sEXPORT_NAME=createEngine -sENVIRONMENT=web,worker,node -sINVOKE_RUN=0 -sEXIT_RUNTIME=0 -sEXPORTED_RUNTIME_METHODS=callMain,FS,HEAPU8 -sEXPORTED_FUNCTIONS=_main,_as_clear_sample_cache -sFORCE_FILESYSTEM=1 -sALLOW_MEMORY_GROWTH=1 -sMAXIMUM_MEMORY=4GB -sSTACK_SIZE=8MB'
    subprocess.run(['cmake','-G','Ninja','-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DAGENTSOUND_BUILD_TESTS=OFF','-DCMAKE_TOOLCHAIN_FILE='+str(sdk/'upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'),'-DCMAKE_C_FLAGS=-fwasm-exceptions','-DCMAKE_CXX_FLAGS=-fwasm-exceptions','-DCMAKE_EXE_LINKER_FLAGS='+flags],env=env,check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel',str(a.jobs)],env=env,check=True)
    print(f'Built {build}/agentsound.js and agentsound.wasm. The pinned web release was not changed.')
if __name__=='__main__':main()
