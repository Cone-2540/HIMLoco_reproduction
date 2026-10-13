#!/usr/bin/env python3
"""Fetch the pinned official Go2 assets into shared storage, verifying every SHA."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=Path.home()/'robotics/assets/mujoco-menagerie-go2')
    p.add_argument('--proxy',help='Optional process-only HTTPS proxy')
    a=p.parse_args()
    source=Path(__file__).with_name('asset-source.json')
    manifest=json.loads(source.read_text())
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'https':a.proxy}) if a.proxy else urllib.request.ProxyHandler())
    def fetch(record):
        target=a.destination/record['path']
        if target.exists():
            content=target.read_bytes()
        else:
            url=f"https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/{manifest['commit']}/{record['path']}"
            with opener.open(url,timeout=60) as response:content=response.read()
        if hashlib.sha256(content).hexdigest()!=record['sha256'] or len(content)!=record['bytes']:
            raise ValueError(f"Hash/size mismatch: {target}; refusing overwrite")
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
        return str(target)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for file in pool.map(fetch,manifest['files']):print(file)
    (a.destination/'SOURCE.json').write_text(source.read_text())
    print(f"Verified {len(manifest['files'])} pinned files")


if __name__=='__main__':main()
