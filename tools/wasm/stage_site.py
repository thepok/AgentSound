"""Prepare a NEW standalone Pages directory. Does not commit, push or publish."""
import argparse,shutil
from pathlib import Path
from runtime import ROOT,restore
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('Choose a new output directory; existing checkouts are not overwritten')
    restore(ROOT/'web',verify=True)
    shutil.copytree(ROOT/'web',a.out,ignore=shutil.ignore_patterns('.gitignore','runtime-lock.json','*.part'))
    (a.out/'.nojekyll').touch();print(a.out)
if __name__=='__main__':main()
