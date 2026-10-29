"""Restore or verify the pinned browser runtime without adding binaries to Git."""
import argparse,concurrent.futures,hashlib,json,shutil,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def inside(root,relative):
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError(f'Unsafe manifest path: {relative}')
    return p
def restore(web,source=None,verify=False):
    lock=json.loads((web/'runtime-lock.json').read_text(encoding='utf-8'))
    items=[(rel,info,inside(web,rel),inside(source,rel) if source else None) for rel,info in lock['files'].items()]
    if not verify:
        for _,_,dest,_ in items:dest.parent.mkdir(parents=True,exist_ok=True)
    def one(item):
        rel,info,dest,local=item
        if dest.exists():
            if dest.stat().st_size==info['bytes'] and digest(dest)==info['sha256']:return
            raise ValueError(f'{rel}: changed file; move it aside before restoring the pinned release')
        if verify:raise FileNotFoundError(rel)
        dest.parent.mkdir(parents=True,exist_ok=True);temp=dest.with_name(dest.name+'.part')
        try:
            if source:shutil.copyfile(local,temp)
            else:
                url=lock['base_url']+urllib.parse.quote(rel,safe='/')
                with urllib.request.urlopen(url,timeout=90) as r,temp.open('wb') as f:shutil.copyfileobj(r,f)
            if temp.stat().st_size!=info['bytes'] or digest(temp)!=info['sha256']:raise ValueError(f'{rel}: checksum mismatch')
            temp.replace(dest)
        finally:
            if temp.exists():temp.unlink()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(one,items))
    return len(lock['files'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--web',type=Path,default=ROOT/'web');p.add_argument('--from',dest='source',type=Path,help='Existing release directory (offline copy)');p.add_argument('--verify',action='store_true');a=p.parse_args()
    print(f"Verified {restore(a.web,a.source,a.verify)} pinned runtime files in {a.web}")
