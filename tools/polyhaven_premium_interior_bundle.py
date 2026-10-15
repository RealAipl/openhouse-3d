#!/usr/bin/env python3
"""Build one authentic CC0 furnishing + architectural surface material bundle.

Source: official https://api.polyhaven.com (no scraping/no auth) CC0.
Output: one ZIP with usable Blender 1K .blend materials/models and texture includes,
an actual image contact sheet from official Poly Haven thumbnail art, JSON manifest.
Budget intentionally capped at 800 MiB uncompressed / under 900 MB archive.
"""
import argparse, collections, hashlib, io, json, os, re, shutil, sys, time
import urllib.parse, urllib.request, urllib.error, zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageOps, ImageDraw, ImageFont

UA="Luxoria-OpenHouse-CC0-InteriorsBulk/2.0 (asset pack 1K)"
BASE="https://api.polyhaven.com"
ALLOW_HOST={"dl.polyhaven.org","dl.polyhaven.com","cdn.polyhaven.com","cdn.polyhaven.org"}
MAX_SOURCE_BYTES=800*1024*1024
MAX_SINGLE=46*1024*1024
TARGET_MODELS=95
TARGET_MATERIALS=105
MINS={"models":55,"textures":75}
ROOM_TAGS={
"chairs":("chair","armchair","sofa","couch","stool","seating","beanbag","ottoman"),
"tables":("table","desk","coffee table","side table"),
"storage":("cabinet","shelf","drawer","bookshelf","wardrobe","dresser","cupboard"),
"decor":("vase","pot","pillow","cushion","basket","book","decor","painting","frame","clock","sculpture"),
"lights":("lamp","light","lantern","pendant"),
"plants":("plant","flower","foliage"),
"kitchen":("kitchen","cup","plate","bowl","dish","kettle","pan","food","cutlery"),
"bath":("sink","bath","toilet","towel","soap","mirror"),
"appliances":("monitor","tv","television","microwave","fridge","computer","laptop","fan"),
"beds":("bed","pillow","blanket","nightstand"),
}
SURFACE_TAGS={
"floor_wood":("parquet","wood floor","floorboard","oak floor","wood plank","herringbone"),
"floor_tiles":("tile","ceramic","porcelain","terrazzo","mosaic","paver"),
"stone":("marble","travertine","granite","limestone","stone tile","quartz"),
"walls":("plaster","stucco","painted wall","drywall","wallpaper","interior wall","concrete wall","brick wall"),
"wood":("veneer","cabinet wood","wood panel","oak","wooden"),
"fabric":("fabric","linen","cotton","leather","upholstery","velvet","carpet","rug"),
"metal":("brushed metal","stainless steel","brass","copper","aluminum"),
"ceiling":("plaster","ceiling","painted wall","stucco"),
}
EXCLUDE_TERMS=("broken","derelict","abandoned","rust","rusty","mold","mouldy","dirty",
               "grime","war","scifi","sci-fi","medieval","antique","vintage industrial",
               "graffiti","damaged","weathered","cracked","destroyed",
               "debris","industrial warehouse")
REPORT_FIELDS=("name","category","tags","description","thumbnail_url","download_count","authors")

def api(path):
    q=urllib.request.Request(BASE+path,headers={"User-Agent":UA,"Accept":"application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(q,timeout=55) as r:
                return json.load(r)
        except (urllib.error.URLError,TimeoutError,ValueError) as e:
            if attempt==2: raise
            print("API retry",path,str(e)[:100],flush=True)
            time.sleep(2+attempt*4)

def selection_score(meta, kind):
    cat=str(meta.get("category") or "").lower()
    text=" ".join([str(meta.get("name","")),cat," ".join(meta.get("tags") or []),
                   str(meta.get("description",""))[:150]]).lower()
    if any(word in text for word in EXCLUDE_TERMS): return None
    groups=ROOM_TAGS if kind=="models" else SURFACE_TAGS
    memberships=[]
    for group,keys in groups.items():
        if any(k in text for k in keys):
            memberships.append(group)
    if not memberships: return None
    if kind=="models":
        if not (cat.startswith(("furniture","decor","props","electronics","plants","kitchen","food","containers","lighting"))
                or any(x in cat for x in ("household","decor","interior","tableware","plant","appliance"))):
            return None
    else:
        if (cat.startswith(("ground","terrain","rock","nature","vegetation"))
             or "exterior" in cat): return None
        # Prioritize surfaces explicitly tagged indoor and man-made
        setting=(meta.get("attributes") or {}).get("setting")
        indoor_bonus=3 if setting=="indoor" else (1 if setting in (None,"either") else -2)
    usage=int(meta.get("download_count") or 0)
    importance=sorted(memberships,key=lambda x:{"walls":-1,"floor_wood":-1,"floor_tiles":-1}.get(x,0))[0]
    score=(min(usage,250000)//3000) + (12 if cat.startswith("furniture") else 0) \
         + (indoor_bonus if kind=="textures" else 0)
    return (importance,score, memberships)

def asset_block(slug,meta,kind):
    files=api("/files/"+urllib.parse.quote(slug,safe=""))
    blend=files.get("blend",{})
    res="1k" if "1k" in blend else ("2k" if "2k" in blend else "")
    if not res or "blend" not in blend[res]: return None
    node=blend[res]["blend"]
    if not node.get("url"): return None
    entries=[]
    def record(filename,data):
        url=str(data.get("url") or "")
        host=urllib.parse.urlparse(url).hostname
        if host not in ALLOW_HOST: raise ValueError("Unexpected CDN host: "+str(host))
        safe=Path(filename)
        if safe.is_absolute() or ".." in safe.parts: raise ValueError("Unsafe path")
        size=int(data.get("size") or 0)
        if not 0<size<=MAX_SINGLE: raise ValueError("Oversized file "+filename)
        entries.append({"path":str(safe),"url":url,"bytes":size,"md5":data.get("md5")})
    record(slug+".blend",node)
    for path,sub in node.get("include",{}).items():
        record(path,sub)
    total=sum(e["bytes"] for e in entries)
    attrs={k:meta.get(k) for k in REPORT_FIELDS}
    attrs.update({"id":slug,"type":kind,"resolution":res,"bytes":total,
                  "source":"https://polyhaven.com/a/"+slug,"files":entries})
    return attrs

def build_candidates(kind,raw):
    groups=ROOM_TAGS if kind=="models" else SURFACE_TAGS
    seeds=collections.defaultdict(list)
    for slug,meta in raw.items():
        ranked=selection_score(meta,kind)
        if not ranked: continue
        group,score,memberships=ranked
        for g in memberships: seeds[g].append((score,slug))
    print(kind,"matching groups", {k:len(v) for k,v in seeds.items()},flush=True)
    for key in seeds:
        seeds[key].sort(key=lambda x:(-x[0],x[1]))
    result=[];used=set();all_keys=list(groups.keys())
    rounds=0
    # round-robin all uses, forcing decorative variety rather than all sofas/wood
    while len(result)<(TARGET_MODELS if kind=="models" else TARGET_MATERIALS)*2:
        added=0
        for g in all_keys:
            while seeds[g]:
                _score,slug=seeds[g].pop(0)
                if slug in used:continue
                used.add(slug);result.append((slug,raw[slug],g));added+=1;break
        rounds+=1
        if not added or rounds>75:break
    return result

def download_file(rec,root):
    destination=root/rec["file"]
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_file() and destination.stat().st_size==rec["bytes"]:
        return
    temp=Path(str(destination)+".part")
    for attempt in range(3):
        try:
            req=urllib.request.Request(rec["url"],headers={"User-Agent":UA})
            md5=hashlib.md5()
            n=0
            with urllib.request.urlopen(req,timeout=140) as src,temp.open("wb") as dst:
                while chunk:=src.read(768*1024):
                    n+=len(chunk)
                    if n>MAX_SINGLE:raise ValueError("Oversized source "+rec["file"])
                    md5.update(chunk);dst.write(chunk)
            if n!=rec["bytes"]:raise ValueError("Byte mismatch "+str(n))
            if rec.get("md5") and md5.hexdigest().lower()!=rec["md5"].lower():
                raise ValueError("MD5 hash mismatch "+rec["file"])
            temp.replace(destination);return
        except (OSError,urllib.error.URLError,TimeoutError,ValueError) as e:
            temp.unlink(missing_ok=True)
            if attempt==2:raise
            time.sleep(2+3*attempt)

def contact_sheet(assets,outpath):
    # Pictures are the REAL Poly Haven preview photographs/renders.
    ordered=[]
    # sample both real models and real scanned materials
    for kind in ("models","textures"):
        items=[a for a in assets if a["type"]==kind]
        stride=max(1,len(items)//24)
        ordered.extend(items[::stride][:24])
    thumb=190;label_h=44;cols=8;rows=(len(ordered)+cols-1)//cols
    cw,ch=thumb+20,thumb+label_h+27
    bg=(24,29,34)
    canvas=Image.new("RGB",(cols*cw+28,rows*ch+116),bg)
    draw=ImageDraw.Draw(canvas)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
        hfont=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",28)
    except OSError:font=hfont=ImageFont.load_default()
    draw.text((24,17),"LUXORIA / REAL CC0 INTERIOR ASSETS",font=hfont,fill=(245,247,247))
    draw.text((24,59),f"Actual Poly Haven thumbnails  •  {sum(a['type']=='models' for a in assets)} 3D models  •  {sum(a['type']=='textures' for a in assets)} PBR materials",font=font,fill=(185,201,202))
    for i,item in enumerate(ordered):
        r,c=divmod(i,cols)
        left=14+c*cw+8; top=103+r*ch
        u=item.get("thumbnail_url")
        img=None
        if u:
            try:
                req=urllib.request.Request(u,headers={"User-Agent":UA})
                with urllib.request.urlopen(req,timeout=15) as response:
                    img=Image.open(io.BytesIO(response.read())).convert("RGB")
            except (OSError,TimeoutError,urllib.error.URLError):pass
        if img:
            canvas.paste(ImageOps.fit(img,(thumb,thumb)),(left,top))
        else:
            draw.rectangle((left,top,left+thumb,top+thumb),fill=(45,56,61))
            draw.text((left+12,top+20),"thumbnail unavailable",font=font,fill=(207,207,207))
        draw.rectangle((left+4,top+4,left+92,top+22),fill=(15,20,25))
        draw.text((left+8,top+5),("3D" if item["type"]=="models" else "PBR"),font=font,fill=(221,238,237))
        name=str(item["name"] or item["id"]).strip()
        if len(name)>25:name=name[:23]+"…"
        draw.text((left+3,top+thumb+5),name,font=font,fill=(237,240,239))
        draw.text((left+3,top+thumb+24),item["id"][:25],font=font,fill=(146,156,163))
    canvas.save(outpath,quality=88,optimize=True)
    print("PREVIEW",outpath,canvas.size,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["plan","download"],default="download")
    args=p.parse_args()
    root=Path("tmp/luxoria-cc0-interior-megapack")
    root.mkdir(parents=True,exist_ok=True)
    all_assets={}
    for kind in ("models","textures"):
        data=api("/assets?type="+kind)
        print("Found",len(data),kind,flush=True)
        chosen=build_candidates(kind,data)
        all_assets[kind]=chosen
    selection=[];budget=0
    quota={"models":TARGET_MODELS,"textures":TARGET_MATERIALS}
    for index in range(max(quota.values())+25):
        for kind in ("models","textures"):
            if sum(t["type"]==kind for t in selection)>=quota[kind]:continue
            if index>=len(all_assets[kind]):continue
            slug,meta,group=all_assets[kind][index]
            try:info=asset_block(slug,meta,kind)
            except (OSError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
                print("SKIP",kind,slug,str(e)[:100],flush=True);continue
            if not info or info["bytes"]>40*1024*1024:continue
            if budget+info["bytes"]>MAX_SOURCE_BYTES:
                print("BUDGET reached",budget//1048576,"MB",flush=True)
                continue
            info["group"]=group
            selection.append(info);budget+=info["bytes"]
            if len(selection)%15==0:
                print("PLAN",len(selection),"assets",round(budget/1048576),"MiB",flush=True)
    counts=collections.Counter(i["type"] for i in selection)
    print("FINAL PLAN:",counts,round(budget/1048576,1),"MiB",flush=True)
    for key,v in MINS.items():
        if counts[key]<v:raise ValueError(f"Too few {key} ({counts[key]} < {v})")
    manifest={"provider":"Poly Haven","license":"CC0 1.0","api_credit":"Powered by Poly Haven: https://polyhaven.com",
              "models":counts["models"],"pbr_materials":counts["textures"],
              "raw_file_count":sum(len(x["files"]) for x in selection),
              "raw_bytes":budget,"assets":selection,
              "note":"1K Blender files with dependent PBR maps; floors/walls/ceilings are material presets, not finished 3D architecture."}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    (root/"README_PL.txt").write_text(
        "LUXORIA — OGROMNA BIBLIOTEKA WNETRZ / CC0\n\n"
        f"Modele 3D: {counts['models']}. Materialy PBR na podlogi, sciany, sufity, tkaniny, drewno, kamien: {counts['textures']}.\n"
        "Wszystko jest darmowe, CC0; komercyjne wizualizacje sa dozwolone.\n"
        "Zrodlo: Poly Haven (https://polyhaven.com). Powered by Poly Haven.\n"
        "Foldery models/<slug>/<slug>.blend i textures/<slug>/<slug>.blend plus pliki tekstur.\n"
        "W Blenderze wybierz File > Append, wskaż plik .blend, i wybierz Collection lub Material.\n"
        "To biblioteka zasobow. NIE jest to gotowy, urzadzony dom ani niezawodny automat PDF -> spacer.\n"
        "Brak komercyjnych modeli Blendkit; zawartosc jest wyłącznie CC0 Poly Haven.\n",encoding="utf-8")
    if args.mode=="plan":return
    records=[]
    for i,asset in enumerate(selection,1):
        for item in asset["files"]:
            dest=f"{asset['type']}/{asset['id']}/{item['path']}"
            records.append({"url":item["url"],"bytes":item["bytes"],"md5":item.get("md5"),"file":dest})
        if i%25==0:print("QUEUED",i,"assets",flush=True)
    # Parallel bounded IO with strict checksum validation.
    with ThreadPoolExecutor(max_workers=8) as pool:
        work=[pool.submit(download_file,v,root) for v in records]
        for i,fut in enumerate(as_completed(work),1):
            fut.result()
            if i%80==0:print("DOWNLOADED",i,"/",len(work),flush=True)
    contact_sheet(selection,root/"ZOBACZ_ZAWARTOSC.jpg")
    archive=Path("tmp/luxoria-interior-megapack-CC0.zip")
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for item in sorted(root.rglob("*")):
            if item.is_file():
                z.write(item,item.relative_to(root))
    with zipfile.ZipFile(archive) as z:
        problem=z.testzip()
        if problem:raise ValueError("Invalid ZIP member "+problem)
        manifest_read=json.loads(z.read("manifest.json"))
        blend=[n for n in z.namelist() if n.endswith(".blend")]
        if len(blend)!=counts["models"]+counts["textures"]:
            raise ValueError("Model/material .blend mismatch")
        if manifest_read["raw_file_count"]!=len(records):
            raise ValueError("Unexpected file count")
    print("DONE",archive,round(archive.stat().st_size/1048576,1),"MiB",
          counts["models"],"models",counts["textures"],"PBR materials",flush=True)

if __name__=="__main__":main()
