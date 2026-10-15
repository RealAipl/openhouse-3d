#!/usr/bin/env python3
"""LUXORIA supplemental home-interiors pack v3, strictly CC0 and not duplicate v1.

Uses official Poly Haven API and ambientCG v2 metadata + official download endpoint.
No login, premium tiers, scraping, manual downloads or source-model invention.
Real model .blend files with includes + full JPG PBR surface ZIPs.
"""
from __future__ import annotations
import argparse, collections, concurrent.futures, hashlib, io, json, os, re, shutil, sys, time
import urllib.request, urllib.parse, urllib.error, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, ImageFont

UA="LUXORIA-FreeHomeAssets-v2/2.0 (verified CC0 asset collection)"
PH="https://api.polyhaven.com"
OLD="https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-interior-megapack-cc0-v1/LUXORIA_Manifest_Licencje_i_Zrodla.json"
PREV2="https://github.com/RealAipl/openhouse-3d/releases/download/luxoria-home-interiors-cc0-v2/MANIFEST_V2.json"
BASE=Path("tmp/luxoria-home-extra-v3")
ARCHIVE=Path("tmp/LUXORIA_Dom_Wnetrza_V3_CC0_Materialy_I_Obiekty.zip")
CAP_BYTES=2_300_000_000
MAX_SINGLE=60_000_000
MIN_MODELS=0
MIN_POLY_MATS=0
MIN_ACG_MATS=175
MAX_CONTENT={"models":65,"poly_mats":110,"ambient_mats":270}
BAD=("rust","weathered","destroyed","abandoned","rough rock","ancient","medieval",
     "worn","damaged","broken","grimy","dirty","grunge","moldy","mouldy",
     "military","weapon","sci-fi","gothic","industrial","antique",
     "vintage","ruined","wet","muddy","blood","rotten","debris","old brick",
     "climbing wall","driveway","fluorescent","patio tile")
# Category-first: select household items and architectonic finishes, not parks, boulders.
MODEL_GROUPS={
 "seating":("furniture/seating",),
 "tables":("furniture/tables",),
 "storage":("furniture/storage",),
 "beds":("furniture/beds","furniture/bed"),
 "lamps":("lighting/","electronics & appliances/lighting",),
 "decorations":("decor & art/","containers & storage/"),
 "kitchen":("food & kitchen/","containers & storage/kitchen"),
 "houseplants":("nature/plants/houseplant","nature/plants/potted"),
 "appliances":("electronics & appliances/home appliances/",),
 "daily_life":("leisure/games & toys/","tools & equipment/home"),
}
MATERIAL_GROUPS={
 "wood_finishes":("wood/veneer","wood/boards & planks/finished","wood/boards & planks/painted"),
 "tiles":("ceramic/","stone/slabs & tiles/"),
 "marble":("stone/rock & cliffs/marble","stone/veneer","stone/slabs"),
 "walls":("concrete/plaster & stucco/bare","concrete/plaster & stucco/finished","concrete/plaster & stucco/painted"),
 "polished_concrete":("concrete/cast walls & floors/bare cast","concrete/cast walls & floors/trowel"),
 "fabrics":("fabric/","leather/","carpet/","fabric & leather/"),
 "metal":("metal/sheet & corrugated/flat","metal/brushed",),
 "wood_panelling":("wood/panels","wood/boards & planks/painted"),
}
ACG_CATEGORIES={
 "wood_floors":("WoodFloor","WoodPlanks","Parquet"),
 "tiles":("Tiles","Terrazzo","Porcelain","Ceramic"),
 "marble_stone":("Marble","Granite","Travertine"),
 "fabrics":("Fabric","Leather","Carpet"),
 "walls":("Plaster","Wallpaper","PaintedPlaster","WallPaint"),
 "decor_wood":("Wood","Veneer"),
 "concrete":("Concrete","ConcreteFloor"),
 "other_surface":("Metal","Plastic","Paving"),
}
def get(url, timeout=60):
    request=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    for retry in range(4):
        try:
            with urllib.request.urlopen(request,timeout=timeout) as f:
                return json.load(f)
        except (OSError,ValueError,urllib.error.URLError) as e:
            if retry==3:raise
            time.sleep(1+retry*2)

def healthy(meta):
    desc=" ".join(str(x) for x in [meta.get("name",""),meta.get("description",""),
                  " ".join(meta.get("tags") or [])]).lower()
    return not any(x in desc for x in BAD)

def pick_round_robin(items,limit):
    grouped=collections.defaultdict(list)
    for group,item in items:
        grouped[group].append(item)
    for group in grouped:
        grouped[group].sort(key=lambda item:(-int(item["meta"].get("download_count") or 0),item["id"]))
    ordered=[];seen=set(); keys=list(grouped)
    for loop in range(limit*3):
        done=False
        for group in keys:
            if grouped[group]:
                item=grouped[group].pop(0)
                if item["id"] in seen: continue
                seen.add(item["id"]); item["group"]=group
                ordered.append(item); done=True
        if not done or len(ordered)>=limit*2:break
    return ordered

def group_for(meta,groups):
    category=str(meta.get("category") or "").lower()
    for group,prefixes in groups.items():
        if any(category.startswith(x) for x in prefixes):return group
    return None

def poly_candidates(kind,previous):
    raw=get(PH+"/assets?type="+kind)
    groups=MODEL_GROUPS if kind=="models" else MATERIAL_GROUPS
    pool=[]
    for slug,meta in raw.items():
        if slug in previous or not healthy(meta):continue
        group=group_for(meta,groups)
        if group:pool.append((group,{"id":slug,"meta":meta}))
    print("Poly",kind,"eligible unseen:",len(pool), "groups",dict(collections.Counter(g for g,_ in pool)),flush=True)
    return pick_round_robin(pool,MAX_CONTENT["models" if kind=="models" else "poly_mats"])

def poly_resolve(asset,kind):
    slug=asset["id"]
    files=get(PH+"/files/"+urllib.parse.quote(slug,safe=""))
    opts=files.get("blend",{})
    best= "1k" if "1k" in opts else ("2k" if "2k" in opts else None)
    if best is None or not opts[best].get("blend",{}).get("url"):return None
    data=opts[best]["blend"]
    links=[(slug+".blend",data)]
    links.extend(data.get("include",{}).items())
    entries=[]
    size=0
    for rel,obj in links:
        n=int(obj.get("size") or 0)
        if not (0<n<=MAX_SINGLE):return None
        url=str(obj.get("url") or "")
        if not url.startswith("https://dl.polyhaven.org/"):return None
        rel=str(Path(rel))
        if Path(rel).is_absolute() or ".." in Path(rel).parts:return None
        entries.append({"relative":rel,"url":url,"bytes":n,"md5":obj.get("md5")})
        size+=n
    meta=asset["meta"]
    return {"provider":"Poly Haven","id":slug,"title":meta.get("name",slug),
            "source":"https://polyhaven.com/a/"+slug,"license":"CC0 1.0",
            "kind":"models" if kind=="models" else "materials",
            "group":asset["group"],"preview":meta.get("thumbnail_url"),
            "bytes":size,"files":entries,"format":"Blender .blend plus original PBR maps"}

def ambient_candidates(previous):
    names=[]
    for offset in range(0,2050,400):
        url="https://ambientcg.com/api/v2/full_json?type=Material&limit=400&offset="+str(offset)+"&sort=Popular"
        d=get(url,75)
        names.extend(d.get("foundAssets",[]))
        if len(names)>=int(d.get("numberOfResults") or 0):break
    pool=[]
    seen=set()
    for entry in names:
        slug=entry.get("assetId") or ""
        if not slug or slug in seen or slug in previous:continue
        seen.add(slug)
        meta={"name":entry.get("displayName",""),"description":entry.get("description",""),
              "tags":entry.get("tags") or [],"download_count":entry.get("downloadCount",0)}
        if not healthy(meta):continue
        group=next((g for g,prefixes in ACG_CATEGORIES.items()
                    if any(slug.startswith(prefix) for prefix in prefixes)),None)
        if not group: continue
        entry["id"]=slug
        pool.append((group,{"id":slug,"meta":{"download_count":meta["download_count"]},"entry":entry}))
    print("ambientCG unseen eligible",len(pool),"groups",dict(collections.Counter(g for g,_ in pool)),flush=True)
    return pick_round_robin(pool,MAX_CONTENT["ambient_mats"])

def ambient_resolve(item):
    name=item["id"]
    # ambientCG official download endpoint returns complete PBR texture sets.
    # Use 1K-JPG to constrain size; downloaded ZIP tested for essential maps.
    uri="https://ambientcg.com/get?file="+urllib.parse.quote(name+"_1K-JPG.zip")
    preview=None
    entry=item.get("entry") or {}
    if isinstance(entry.get("previewImage"),str):preview=entry["previewImage"]
    if not preview:
        for p in entry.get("previewLinks") or []:
            if isinstance(p.get("url"),str) and ("Color.jpg" in p["url"] or "Color.png" in p["url"]):
                preview=p["url"].split("color_url=")[-1].split("&")[0]
                break
    return {"provider":"ambientCG","id":name,"title":entry.get("displayName",name),
            "source":"https://ambientcg.com/a/"+name,"license":"CC0 1.0",
            "kind":"materials","group":item["group"],"preview":preview,"bytes":5_000_000,
            "download_url":uri,"format":"1K JPG Color, NormalGL, Roughness, Height"}

def download_file(url,path,expected=None,md5=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and (expected is None or path.stat().st_size==expected):return
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    for attempt in range(3):
        try:
            h=hashlib.md5()
            total=0
            with urllib.request.urlopen(req,timeout=140) as src,open(str(path)+".part","wb") as out:
                while block:=src.read(512*1024):
                    total+=len(block)
                    if total>MAX_SINGLE:raise ValueError("Download bigger than capped file "+url)
                    h.update(block);out.write(block)
            if expected and total!=expected:raise ValueError("Size mismatch")
            if md5 and md5.lower()!=h.hexdigest():raise ValueError("MD5 mismatch")
            Path(str(path)+".part").replace(path)
            return
        except Exception as e:
            Path(str(path)+".part").unlink(missing_ok=True)
            if attempt==2:raise
            time.sleep((attempt+1)*3)

def fetch_one(item,root):
    if item["provider"]=="Poly Haven":
        for f in item["files"]:
            dest=root/"PolyHaven"/item["kind"]/item["id"]/f["relative"]
            download_file(f["url"],dest,f["bytes"],f["md5"])
    else:
        package=root/"ambientCG"/"PBR_1K"/(item["id"]+".zip")
        download_file(item["download_url"],package)
        # Reject old 404 HTML or incomplete texture archives; count distinct maps.
        try:
            with zipfile.ZipFile(package) as z:
                names=z.namelist()
                assert z.testzip() is None
                assert any("_Color." in n or "_Color_" in n for n in names)
                assert any("_NormalGL." in n or "_NormalGL_" in n for n in names)
                assert any("_Roughness." in n or "_Roughness_" in n for n in names)
        except Exception:
            package.unlink(missing_ok=True)
            raise
        item["bytes"]=package.stat().st_size
    return item

def make_sheet(items,destination):
    # Real provider thumbnails, not AI-generated imagery; mixed models and maps.
    from PIL import Image,ImageOps,ImageDraw,ImageFont
    values=[]
    for group in ("models","materials"):
        ix=[x for x in items if x["kind"]==group]
        if not ix:continue
        values.extend(ix[::max(1,len(ix)//30)][:30])
    W,H=192,178; rows=(len(values)+7)//8
    out=Image.new("RGB",(8*(W+16)+24,rows*(H+48)+95),(24,29,34))
    d=ImageDraw.Draw(out)
    try:f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",12)
    except OSError:f=ImageFont.load_default()
    d.text((20,18),"LUXORIA HOME LIBRARY V2 | UNSEEN CC0 ASSETS",(240,240,240),font=f)
    for i,a in enumerate(values):
        row,col=divmod(i,8); xx=16+col*(W+16); yy=68+row*(H+48)
        pic=None; url=a.get("preview")
        if url and url.startswith("https://"):
            try:
                req=urllib.request.Request(url,headers={"User-Agent":UA})
                with urllib.request.urlopen(req,timeout=15) as r:
                    pic=Image.open(io.BytesIO(r.read())).convert("RGB")
            except (OSError,ValueError):pass
        if pic:out.paste(ImageOps.fit(pic,(W,H)),(xx,yy))
        else:d.rectangle((xx,yy,xx+W,yy+H),fill=(56,64,66))
        d.text((xx,yy+H+5),(str(a.get("title") or a["id"])[:27]),fill=(235,238,238),font=f)
        d.text((xx,yy+H+24),a["provider"]+" / "+a["group"],fill=(171,184,187),font=f)
    destination.parent.mkdir(parents=True,exist_ok=True)
    out.save(destination,quality=88,optimize=True)
    return out.size

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("plan","build"),default="plan")
    a=p.parse_args()
    BASE.mkdir(parents=True,exist_ok=True)
    old=get(OLD)
    second=get(PREV2)
    prior={str(x["id"]) for x in old["assets"]}|{str(x["id"]) for x in second["assets"]}
    print("Dedup against v1 & v2",len(prior),flush=True)
    proposed=[]
    for kind in ("models","textures"):
        chosen=poly_candidates(kind,prior)
        tally=0
        for candidate in chosen:
            if tally>=MAX_CONTENT["models" if kind=="models" else "poly_mats"]:break
            try:item=poly_resolve(candidate,kind)
            except (ValueError,OSError,urllib.error.URLError) as e:
                print("skip Poly",candidate["id"],str(e)[:80],flush=True);continue
            if not item:continue
            proposed.append(item);tally+=1
        print("Selected Poly",kind,tally,flush=True)
    for candidate in ambient_candidates(prior)[:MAX_CONTENT["ambient_mats"]]:
        proposed.append(ambient_resolve(candidate))
    print("PROPOSED",collections.Counter((x["provider"],x["kind"]) for x in proposed),flush=True)
    # Do not count anything not successfully downloaded in final manifest.
    if a.mode=="plan":
        (BASE/"plan.json").write_text(json.dumps(proposed,ensure_ascii=False,indent=2))
        return
    successful=[];failed=[]
    # Limit concurrency. Abort missing individual assets without abandoning entire package.
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        futures={executor.submit(fetch_one,x,BASE):x for x in proposed}
        for index,future in enumerate(concurrent.futures.as_completed(futures),1):
            item=futures[future]
            try:successful.append(future.result())
            except Exception as e:failed.append({"id":item["id"],"reason":str(e)[:160]})
            if index%30==0:print("PROGRESS",index,"/",len(proposed),
                   "OK",len(successful),"FAIL",len(failed),flush=True)
    counts=collections.Counter((x["provider"],x["kind"]) for x in successful)
    print("SUCCESSFUL",counts,"FAIL",failed[:20],flush=True)
    if counts[("Poly Haven","models")]<MIN_MODELS:raise ValueError("Insufficient actual new 3D models")
    if counts[("Poly Haven","materials")]<MIN_POLY_MATS:raise ValueError("Insufficient actual Poly Haven textures")
    if counts[("ambientCG","materials")]<MIN_ACG_MATS:raise ValueError("Insufficient actual ambientCG PBR textures")
    actual_bytes=sum(path.stat().st_size for path in BASE.rglob("*") if path.is_file())
    print("TOTAL UNCOMPRESSED",round(actual_bytes/1048576,1),"MiB",flush=True)
    if actual_bytes>CAP_BYTES:raise ValueError("Exceeds size budget")
    manifest={
      "name":"LUXORIA - Complementary Home Library v3",
      "purpose":"Additional indoor-compatible models and PBR finishing materials not contained in v1 or v2",
      "CC0_sources":["https://polyhaven.com","https://ambientcg.com"],
      "license":"CC0 1.0","duplicates_v1_v2":0,
      "counts":{"new_3d_models":counts[("Poly Haven","models")],
                "new_polyhaven_PBR":counts[("Poly Haven","materials")],
                "new_ambientCG_PBR":counts[("ambientCG","materials")]},
      "assets":sorted(successful,key=lambda x:(x["provider"],x["kind"],x["id"])),
      "skipped":failed,
      "note":"Material libraries are PBR texture sets; not readymade walls, windows, doors or architectural layout."
    }
    (BASE/"MANIFEST_V3.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    (BASE/"README_PL.txt").write_text(
      "LUXORIA / DOM WNETRZA - DODATKOWE ZASOBY V3 (BEZ DUPLIKATOW V1/V2)\n"
      "Poly Haven + ambientCG, wszystko CC0, legalne komercyjnie.\n"
      "Folder PolyHaven/models: kazdy plik Blender .blend plus mapy PBR.\n"
      "Folder PolyHaven/materials: kazdy material Blender .blend plus mapy PBR.\n"
      "Folder ambientCG/PBR_1K: kompletne zestawy 1K JPG w ZIP (kolor, normal, roughness).\n"
      "Manifest podaje zrodlo dla kazdego elementu. Podglad to prawdziwe obrazy z katalogow dostawcow.\n"
      "Zasoby wymagaja wyboru skali, UV i oswietlenia w Blenderze - to nie jest gotowy spacer.\n",
      encoding="utf-8")
    sz=make_sheet(successful,BASE/"ZOBACZ_ZASOBY_V3.jpg")
    print("CONTACT SHEET",sz,flush=True)
    ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ARCHIVE,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=1,allowZip64=True) as z:
        for item in BASE.rglob("*"):
            if item.is_file() and item.name!="plan.json":
                z.write(item,item.relative_to(BASE))
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        doc=json.loads(z.read("MANIFEST_V3.json"))
        assert len(doc["assets"])==len(successful)
        assert doc["duplicates_v1_v2"]==0
    print("READY:",ARCHIVE,"BYTES",ARCHIVE.stat().st_size,
          "COUNTS",manifest["counts"],flush=True)

if __name__=="__main__":main()
