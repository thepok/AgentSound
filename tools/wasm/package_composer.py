"""Repackage the pinned composer with its tracked browser adapter; never mix in current native sources silently."""
import argparse,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path,default=ROOT/'web/py/repo.zip');p.add_argument('--out',type=Path,default=ROOT/'build/wasm/repo.zip');a=p.parse_args()
    if a.out.resolve()==a.baseline.resolve():p.error('Output must differ from the pinned baseline')
    wrapper=Path(__file__).with_name('compose_web.py').read_bytes();a.out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.baseline) as src,zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as dst:
        for entry in src.infolist():
            data=wrapper if entry.filename=='compose_web.py' else src.read(entry)
            dst.writestr(entry,data)
    print(a.out)
if __name__=='__main__':main()
