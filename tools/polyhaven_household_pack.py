#!/usr/bin/env python3
"""Create a single CC0 ZIP with real Blender furniture + texture dependencies.

Sources: https://api.polyhaven.com, https://polyhaven.com (CC0 models).
Poly Haven requests credit when its API powers a project.
No premium assets, no auth, no copyrighted package redistribution.
"""
import argparse
import hashlib
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import zipfile
from pathlib import Path, PurePosixPath

IDS = (
 "sofa_03","sofa_02","modern_arm_chair_01","dining_table",
 "dining_chair_02","modern_coffee_table_02","modern_wooden_cabinet",
 "throw_pillows_01","ceramic_vase_02","wooden_bowl_01",
 "mid_century_lounge_chair","round_wooden_table_02","television_02",
 "tea_set_01","modern_coffee_table_01","potted_plant_01",
 "desk_lamp_arm_01","wicker_basket_01","drawer_cabinet","vintage_day_bed"
)
BASE = "https://api.polyhaven.com"
AGENT = "OpenHouse3D-Luxoria-CC0-Bulk-Build/1.0"
HOSTS = {"dl.polyhaven.org","dl.polyhaven.com","cdn.polyhaven.com","cdn.polyhaven.org"}
MAX_PACK = 650*1024*1024
MAX_FILE = 100*1024*1024

def json_fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=50) as response: return json.load(response)

def asset_data(slug, meta):
    files=json_fetch(BASE+"/files/"+urllib.parse.quote(slug,safe=""))
    blend=files.get("blend",{})
    res = "1k" if "1k" in blend else ("2k" if "2k" in blend else None)
    if not res: raise ValueError("No 1K/2K Blender model: "+slug)
    desc=blend[res].get("blend",{})
    if not desc.get("url"): raise ValueError("No Blender URL: "+slug)
    entries=[]
    def collect(name,info):
        uri=str(info["url"])
        if urllib.parse.urlparse(uri).hostname not in HOSTS:
            raise ValueError("Invalid download host: "+slug)
        safe=PurePosixPath(name)
        if safe.is_absolute() or ".." in safe.parts or "\\" in name or ":" in name:
            raise ValueError("Invalid relative file path")
        size=int(info["size"])
        if not 0<size<=MAX_FILE: raise ValueError("Too large or invalid: "+name)
        entries.append({"name":str(safe),"url":uri,"size":size,"md5":info.get("md5")})
    collect(slug+".blend",desc)
    for rel,info in desc.get("include",{}).items():collect(rel,info)
    return {"id":slug,"name":meta.get("name",slug),"category":meta.get("category"),
            "author":list((meta.get("authors") or {}).keys()),
            "resolution":res,"url":"https://polyhaven.com/a/"+slug,
            "bytes":sum(e["size"] for e in entries),"files":entries}

def download(item,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    for attempt in range(3):
        try:
            req=urllib.request.Request(item["url"],headers={"User-Agent":AGENT})
            digest=hashlib.md5();seen=0
            with urllib.request.urlopen(req,timeout=110) as src, open(str(target)+".part","wb") as sink:
                while block:=src.read(512*1024):
                    seen+=len(block)
                    if seen>MAX_FILE:raise ValueError("Download exceeded limit")
                    digest.update(block);sink.write(block)
            if seen!=item["size"]:raise ValueError("File-size mismatch")
            if item["md5"] and digest.hexdigest().lower()!=item["md5"].lower():
                raise ValueError("MD5 checksum mismatch")
            Path(str(target)+".part").replace(target);return
        except (OSError,ValueError,urllib.error.URLError) as ex:
            Path(str(target)+".part").unlink(missing_ok=True)
            if attempt==2:raise
            print("Retry after",str(ex)[:110],flush=True)
            time.sleep(3*(attempt+1))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["plan","download"],default="plan")
    parser.add_argument("--folder",default="tmp/polyhaven-household-pack")
    a=parser.parse_args()
    folder=Path(a.folder);folder.mkdir(parents=True,exist_ok=True)
    all_items=json_fetch(BASE+"/assets?type=models")
    selection=[]
    for slug in IDS:
        if slug not in all_items:
            print("Unavailable:",slug,flush=True)
            continue
        info=asset_data(slug,all_items[slug])
        selection.append(info)
        print(f"{info['name']}: {info['bytes']/1048576:.1f}MB; {len(info['files'])} files",flush=True)
        time.sleep(.07)
    assert len(selection)>=15, "Too few free realistic models"
    if sum(s["bytes"] for s in selection)>MAX_PACK:
        # Keep at least 15 complete models; omit the largest optional ones.
        selection.sort(key=lambda x:x["bytes"])
        while sum(s["bytes"] for s in selection)>MAX_PACK and len(selection)>15:
            dropped=selection.pop()
            print("Dropped size-heavy:",dropped["id"],flush=True)
    size=sum(s["bytes"] for s in selection)
    assert size<=MAX_PACK, f"Size budget exceeded: {size}"
    manifest={"provider":"Poly Haven","license":"CC0 1.0",
              "api_credit":"Powered by Poly Haven - https://polyhaven.com",
              "item_count":len(selection),"byte_count":size,"models":selection}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf8")
    print(f"PLAN: {len(selection)} CC0 assets, {size/1048576:.1f} MB incl. all textures",flush=True)
    if a.mode=="plan":return
    (folder/"README.txt").write_text(
        "OpenHouse 3D / LUXORIA: realistic household model kit.\n"
        "These are real models, not low-poly placeholders.\n"
        "Source: https://polyhaven.com\n"
        "Powered by Poly Haven. Model license: CC0 1.0.\n"
        "Import to Blender: File > Append > models/<id>/<id>.blend > Collection.\n"
        "Original authors, links, texture file paths: manifest.json.\n"
        "This is furniture/props, not an entire finished interior or bathroom.\n",
        encoding="utf8")
    for idx,asset in enumerate(selection,1):
        print(f"Downloading {idx}/{len(selection)}: {asset['id']}",flush=True)
        for f in asset["files"]:
            download(f,folder/"models"/asset["id"]/f["name"])
    outfile=folder.parent/"polyhaven-home-premium-cc0-pack.zip"
    with zipfile.ZipFile(outfile,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=2,allowZip64=True) as z:
        for file in folder.rglob("*"):
            if file.is_file():z.write(file,file.relative_to(folder))
    with zipfile.ZipFile(outfile) as z:
        assert z.testzip() is None
        assert len([a for a in z.namelist() if a.endswith(".blend")])>=15
    print("READY",outfile,round(outfile.stat().st_size/1048576,1),"MB",flush=True)

if __name__=="__main__":main()
